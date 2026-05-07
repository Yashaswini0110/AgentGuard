import type {
  CandidatePayload,
  BatchRankResponse,
  DecisionPipelineResponse,
  DriftReport,
} from '@/types/agentguard'

type HealthResponse = { status?: string; version?: string }

export function joinUrl(base: string, path: string) {
  const b = base.replace(/\/+$/, '')
  const p = path.startsWith('/') ? path : `/${path}`
  return `${b}${p}`
}

export function apiBase() {
  const env = (import.meta as any).env as Record<string, string | undefined>
  // Prefer explicit env var, otherwise use the dev/preview proxy in vite.config.ts.
  // FastAPI mounts routes at /. If someone copies `…/api` from another stack, normalize it away.
  const raw = (env?.VITE_API_BASE_URL || '').trim()
  if (!raw) return '/agentguard-api'
  const noTrail = raw.replace(/\/+$/, '')
  const base = noTrail.replace(/\/api$/i, '')
  return base || '/agentguard-api'
}

function batchEndpointMissingHint(status: number, url: string) {
  if (status !== 404) return ''
  if (typeof window === 'undefined') return ''
  try {
    const u = url.startsWith('http') ? new URL(url) : new URL(url, window.location.origin)
    if (!u.pathname.includes('/batch_rank')) return ''
    return (
      ' The process answering that URL is not running the current api/main.py (common: stale uvicorn on port 8000, or VITE_API_BASE_URL with an /api prefix).' +
      ' Open http://127.0.0.1:8000/health and confirm batch_rank_available:true and api_module_file matches this repo.' +
      ' If false: stop all servers, run `netstat -ano | findstr :8000`, kill the PID, then from the repo root run' +
      ' `python -m uvicorn api.main:app --host 127.0.0.1 --port 8000` once without --reload.'
    )
  } catch {
    return ''
  }
}

async function httpJson<T>(path: string, init?: RequestInit): Promise<T> {
  const url = joinUrl(apiBase(), path)
  const res = await fetch(url, {
    ...init,
    headers: {
      Accept: 'application/json',
      ...(init?.body ? { 'Content-Type': 'application/json' } : {}),
      ...(init?.headers ?? {}),
    },
  })

  if (!res.ok) {
    const text = await res.text().catch(() => '')
    throw new Error(`HTTP ${res.status} ${res.statusText}${text ? ` — ${text}` : ''}`)
  }

  return (await res.json()) as T
}

export async function fetchHealth() {
  return await httpJson<HealthResponse>('/health')
}

export async function fetchDrift() {
  return await httpJson<DriftReport>('/drift')
}

export async function fetchRecentArtifacts(limit = 200) {
  const data = await httpJson<{ artifacts?: any[] }>('/artifacts/recent?limit=' + encodeURIComponent(String(limit)))
  return (data.artifacts ?? []) as any[]
}

export async function postDecision(payload: CandidatePayload) {
  return await httpJson<DecisionPipelineResponse>('/decision', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export async function postHumanReview(
  decisionId: string,
  body: { action: 'APPROVE' | 'REJECT'; reviewer_id: string; reason: string }
) {
  return await httpJson<{ message?: string; artifact?: unknown }>(`/human-review/${encodeURIComponent(decisionId)}`, {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

export async function postEscalate(decisionId: string, body: { reviewer_id: string; note: string }) {
  return await httpJson<{ message?: string; artifact?: unknown }>(`/escalate/${encodeURIComponent(decisionId)}`, {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

export async function postTechReview(
  decisionId: string,
  body: { action: 'ACCEPT' | 'REJECT'; reviewer_id: string; note: string }
) {
  return await httpJson<{ message?: string; artifact?: unknown }>(`/tech-review/${encodeURIComponent(decisionId)}`, {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

export async function postBatchRank(file: File, jobDescription: string, openPositions: number) {
  const url = joinUrl(apiBase(), '/batch_rank')
  const form = new FormData()
  form.append('file', file)
  form.append('job_description', jobDescription)
  form.append('open_positions', String(openPositions))
  const res = await fetch(url, { method: 'POST', body: form })
  if (!res.ok) {
    const text = await res.text().catch(() => '')
    const hint = batchEndpointMissingHint(res.status, url)
    throw new Error(`HTTP ${res.status} ${res.statusText}${text ? ` — ${text}` : ''}.${hint}`)
  }
  return (await res.json()) as BatchRankResponse
}

export async function postBatchRankStream(
  file: File,
  jobDescription: string,
  openPositions: number,
  onEvent: (evt: Record<string, unknown>) => void
): Promise<BatchRankResponse> {
  const url = joinUrl(apiBase(), '/batch_rank/stream')
  const form = new FormData()
  form.append('file', file)
  form.append('job_description', jobDescription)
  form.append('open_positions', String(openPositions))

  const res = await fetch(url, { method: 'POST', body: form })
  if (!res.ok) {
    const text = await res.text().catch(() => '')
    const hint = batchEndpointMissingHint(res.status, url)
    throw new Error(`HTTP ${res.status} ${res.statusText}${text ? ` — ${text}` : ''}.${hint}`)
  }

  const reader = res.body?.getReader()
  if (!reader) throw new Error('Missing response body stream')

  const dec = new TextDecoder()
  let buf = ''
  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buf += dec.decode(value, { stream: true })
    const parts = buf.split('\n\n')
    buf = parts.pop() ?? ''
    for (const part of parts) {
      const line = part.split('\n').find((l) => l.startsWith('data: '))
      if (!line) continue
      const raw = line.slice(6).trim()
      let evt: Record<string, unknown>
      try {
        evt = JSON.parse(raw) as Record<string, unknown>
      } catch {
        continue
      }
      onEvent(evt)
      if (evt.type === 'result' && evt.payload) {
        return evt.payload as BatchRankResponse
      }
      if (evt.type === 'error') {
        throw new Error(String(evt.message ?? 'Batch stream error'))
      }
    }
  }
  throw new Error('Stream ended before result')
}

export async function postResumeParse(file: File, jobDescription: string) {
  const url = joinUrl(apiBase(), '/resume/parse')
  const form = new FormData()
  form.append('file', file)
  form.append('job_description', jobDescription)

  const res = await fetch(url, { method: 'POST', body: form })
  if (!res.ok) {
    const text = await res.text().catch(() => '')
    throw new Error(`HTTP ${res.status} ${res.statusText}${text ? ` — ${text}` : ''}`)
  }
  return (await res.json()) as Record<string, unknown>
}
