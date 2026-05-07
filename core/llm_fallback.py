"""
LLM routing helper: Gemini primary, OpenRouter secondary.

We already use the OpenAI SDK against Gemini's OpenAI-compatible endpoint.
This module centralizes:
- client construction from env
- JSON-oriented chat calls
- fallback behavior for quota / rate-limit / transient failures
"""

from __future__ import annotations

import json
import os
import time
from typing import Any, Optional

from openai import OpenAI


def _env(name: str) -> str:
    return (os.getenv(name) or "").strip()


# #region agent log
def _dbg_write(payload: dict[str, Any]) -> None:
    # Never log secrets or full resume/JD contents.
    try:
        path = str((os.getenv("AGENTGUARD_DEBUG_LOG_PATH") or "debug-ec0bcc.log").strip() or "debug-ec0bcc.log")
        payload = dict(payload)
        payload.setdefault("sessionId", "ec0bcc")
        payload.setdefault("timestamp", int(time.time() * 1000))
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=False) + "\n")
    except Exception:
        pass
# #endregion


def _gemini_api_key() -> str:
    # Repo historically uses either GOOGLE_API_KEY or GEMINI_API_KEY.
    return _env("GOOGLE_API_KEY") or _env("GEMINI_API_KEY")


def _openrouter_api_key() -> str:
    return _env("OPENROUTER_API_KEY")


def gemini_client() -> OpenAI:
    return OpenAI(
        api_key=_gemini_api_key(),
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
    )


def openrouter_client() -> OpenAI:
    # OpenRouter recommends referer + title, but does not require them.
    headers: dict[str, str] = {}
    site = _env("OPENROUTER_SITE_URL")
    title = _env("OPENROUTER_APP_NAME") or "AgentGuard"
    if site:
        headers["HTTP-Referer"] = site
    if title:
        headers["X-Title"] = title
    return OpenAI(
        api_key=_openrouter_api_key(),
        base_url="https://openrouter.ai/api/v1",
        default_headers=headers or None,
    )


def _looks_transient_or_quota(exc: Exception) -> bool:
    s = (str(exc) or "").lower()
    # Gemini free-tier quota exceeded and common transient indicators.
    needles = [
        "error code: 429",
        "429",
        "resource_exhausted",
        "quota exceeded",
        "rate limit",
        "too many requests",
        "temporarily unavailable",
        "timeout",
        "timed out",
        "connection reset",
        "connection aborted",
        "service unavailable",
        "bad gateway",
        "gateway timeout",
    ]
    return any(n in s for n in needles)


def _strip_code_fence(raw: str) -> str:
    t = (raw or "").strip()
    if t.startswith("```json"):
        t = t[7:]
    elif t.startswith("```"):
        t = t[3:]
    if t.endswith("```"):
        t = t[:-3]
    return t.strip()


def _extract_json_object(text: str) -> str:
    """
    Providers sometimes wrap JSON with prose or return multiple objects.
    Extract the first plausible top-level JSON object span.
    """
    t = _strip_code_fence(text)
    if not t:
        return t
    # Fast path: already looks like a JSON object.
    if t.lstrip().startswith("{") and t.rstrip().endswith("}"):
        return t
    start = t.find("{")
    end = t.rfind("}")
    if 0 <= start < end:
        return t[start : end + 1].strip()
    return t


def chat_completion(
    *,
    system: str,
    user: str,
    gemini_model: str,
    openrouter_model: str,
    temperature: float = 0.0,
    max_tokens: Optional[int] = None,
    json_mode: bool = False,
    retries: int = 2,
) -> str:
    """
    Return assistant message content using Gemini first, then OpenRouter fallback.

    If json_mode is True we attempt response_format=json_object when supported, but still
    defensively strip fences because providers sometimes ignore it.
    """
    if not _gemini_api_key() and not _openrouter_api_key():
        raise ValueError("No LLM API key configured (set GEMINI_API_KEY/GOOGLE_API_KEY and/or OPENROUTER_API_KEY).")

    attempts: list[tuple[str, OpenAI, str]] = []
    if _gemini_api_key():
        attempts.append(("gemini", gemini_client(), gemini_model))
    if _openrouter_api_key():
        attempts.append(("openrouter", openrouter_client(), openrouter_model))

    last_exc: Exception | None = None
    for provider, client, model in attempts:
        for delay in [0.0] + [0.6 * (2**i) for i in range(max(0, retries))]:
            if delay:
                time.sleep(delay)
            try:
                # #region agent log
                _dbg_write(
                    {
                        "runId": "llm-call",
                        "hypothesisId": "H1",
                        "location": "core/llm_fallback.py:chat_completion:entry",
                        "message": "LLM request attempt",
                        "data": {
                            "provider": provider,
                            "model": model,
                            "json_mode": bool(json_mode),
                            "temperature": float(temperature),
                            "max_tokens": int(max_tokens) if max_tokens is not None else None,
                            "system_len": len(system or ""),
                            "user_len": len(user or ""),
                        },
                    }
                )
                # #endregion
                kwargs: dict[str, Any] = {}
                if json_mode:
                    # Some providers ignore/disable this; we will fallback to parsing anyway.
                    kwargs["response_format"] = {"type": "json_object"}
                if max_tokens is not None:
                    kwargs["max_tokens"] = int(max_tokens)
                resp = client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                    temperature=float(temperature),
                    **kwargs,
                )
                content = (resp.choices[0].message.content or "").strip()
                # #region agent log
                _dbg_write(
                    {
                        "runId": "llm-call",
                        "hypothesisId": "H2",
                        "location": "core/llm_fallback.py:chat_completion:success",
                        "message": "LLM response received",
                        "data": {
                            "provider": provider,
                            "model": model,
                            "content_len": len(content),
                            "content_head": content[:180],
                        },
                    }
                )
                # #endregion
                return content
            except Exception as exc:
                last_exc = exc
                # #region agent log
                _dbg_write(
                    {
                        "runId": "llm-call",
                        "hypothesisId": "H3",
                        "location": "core/llm_fallback.py:chat_completion:exception",
                        "message": "LLM request exception",
                        "data": {
                            "provider": provider,
                            "model": model,
                            "exc_type": type(exc).__name__,
                            "exc_str": str(exc)[:400],
                            "transient_or_quota": _looks_transient_or_quota(exc),
                        },
                    }
                )
                # #endregion
                # Only continue retrying/falling back on transient/quota failures.
                if not _looks_transient_or_quota(exc):
                    raise
                # If Gemini failed transiently, we keep retrying within Gemini first; once we switch
                # providers the outer loop handles it.
                continue

    raise ValueError(f"LLM request failed after fallback: {last_exc}")


def chat_json(
    *,
    system: str,
    user: str,
    gemini_model: str,
    openrouter_model: str,
    temperature: float = 0.0,
    max_tokens: Optional[int] = None,
    retries: int = 2,
) -> dict[str, Any]:
    """
    JSON helper with repair:
    - Call Gemini first, then OpenRouter as fallback.
    - If provider returns malformed/truncated JSON, do one "repair" re-ask on the same provider.
    - If still invalid, try the next provider.
    """

    providers: list[tuple[str, str]] = []
    if _gemini_api_key():
        providers.append(("gemini", gemini_model))
    if _openrouter_api_key():
        providers.append(("openrouter", openrouter_model))
    if not providers:
        raise ValueError("No LLM API key configured (set GEMINI_API_KEY/GOOGLE_API_KEY and/or OPENROUTER_API_KEY).")

    last_exc: Exception | None = None
    for provider, model in providers:
        client = gemini_client() if provider == "gemini" else openrouter_client()

        def _call(prompt_user: str, *, local_retries: int) -> str:
            kwargs: dict[str, Any] = {"response_format": {"type": "json_object"}}
            if max_tokens is not None:
                kwargs["max_tokens"] = int(max_tokens)
            last: Exception | None = None
            for delay in [0.0] + [0.6 * (2**i) for i in range(max(0, local_retries))]:
                if delay:
                    time.sleep(delay)
                try:
                    resp = client.chat.completions.create(
                        model=model,
                        messages=[
                            {"role": "system", "content": system},
                            {"role": "user", "content": prompt_user},
                        ],
                        temperature=float(temperature),
                        **kwargs,
                    )
                    return (resp.choices[0].message.content or "").strip()
                except Exception as exc:
                    last = exc
                    if not _looks_transient_or_quota(exc):
                        raise
                    continue
            raise last or ValueError("LLM request failed")

        # First attempt (with transient retries like chat_completion)
        try:
            # #region agent log
            _dbg_write(
                {
                    "runId": "llm-json",
                    "hypothesisId": "H4",
                    "location": "core/llm_fallback.py:chat_json:provider_attempt",
                    "message": "Provider JSON attempt",
                    "data": {"provider": provider, "model": model},
                }
            )
            # #endregion
            raw = _call(user, local_retries=retries)
            cleaned = _extract_json_object(raw)
            obj = json.loads(cleaned)
            # #region agent log
            _dbg_write(
                {
                    "runId": "llm-json",
                    "hypothesisId": "H4",
                    "location": "core/llm_fallback.py:chat_json:parsed",
                    "message": "LLM JSON parsed",
                    "data": {"keys": sorted(list(obj.keys()))[:30] if isinstance(obj, dict) else type(obj).__name__},
                }
            )
            # #endregion
            return obj
        except Exception as exc:
            last_exc = exc
            cleaned = _extract_json_object(raw if "raw" in locals() else "")
            # #region agent log
            _dbg_write(
                {
                    "runId": "llm-json",
                    "hypothesisId": "H5",
                    "location": "core/llm_fallback.py:chat_json:json_error",
                    "message": "LLM JSON parse failed (pre-repair)",
                    "data": {
                        "provider": provider,
                        "model": model,
                        "exc_type": type(exc).__name__,
                        "exc_str": str(exc)[:260],
                        "cleaned_head": cleaned[:220],
                    },
                }
            )
            # #endregion

        # Repair attempt on the same provider (do not log raw content; may contain PII).
        try:
            repair_user = (
                user
                + "\n\nIMPORTANT: Your previous response was INVALID JSON (truncated or malformed). "
                + "Return ONLY a single valid JSON object that matches the schema in the system prompt. "
                + "No markdown, no prose, no trailing commas. Ensure all strings are properly quoted and closed."
            )
            repaired_raw = _call(repair_user, local_retries=max(0, retries))
            repaired_clean = _extract_json_object(repaired_raw)
            obj = json.loads(repaired_clean)
            # #region agent log
            _dbg_write(
                {
                    "runId": "llm-json",
                    "hypothesisId": "H6",
                    "location": "core/llm_fallback.py:chat_json:repair_ok",
                    "message": "LLM JSON repair succeeded",
                    "data": {
                        "provider": provider,
                        "model": model,
                        "content_len": len(repaired_raw),
                    },
                }
            )
            # #endregion
            return obj
        except Exception as exc:
            last_exc = exc
            # #region agent log
            _dbg_write(
                {
                    "runId": "llm-json",
                    "hypothesisId": "H7",
                    "location": "core/llm_fallback.py:chat_json:repair_fail",
                    "message": "LLM JSON repair failed; trying next provider",
                    "data": {
                        "provider": provider,
                        "model": model,
                        "exc_type": type(exc).__name__,
                        "exc_str": str(exc)[:260],
                    },
                }
            )
            # #endregion
            continue

    raise ValueError(f"LLM JSON parse failed after repair+fallback: {last_exc}")

