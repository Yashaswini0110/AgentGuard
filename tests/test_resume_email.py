"""Tests for résumé email extraction helpers."""

from core.resume_parser import extract_email_from_text, resolve_candidate_email


def test_extract_email_from_text_finds_header_email():
    text = "Jane Doe\njane.doe@acme.io\n+1 555-0100\nPython developer"
    assert extract_email_from_text(text) == "jane.doe@acme.io"


def test_extract_email_skips_placeholder_domains():
    text = "Contact: demo.user@example.com or real@company.co.in"
    assert extract_email_from_text(text) == "real@company.co.in"


def test_resolve_candidate_email_prefers_structured():
    structured = {"email": "  Rahul.S@Gmail.COM  "}
    assert resolve_candidate_email(structured, "other@ignored.com") == "rahul.s@gmail.com"


def test_resolve_candidate_email_falls_back_to_text():
    structured = {"email": None}
    text = "Arjun Mehta\narjun.mehta@startup.dev\nSkills: Python"
    assert resolve_candidate_email(structured, text) == "arjun.mehta@startup.dev"
