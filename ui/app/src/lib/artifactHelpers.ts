import type { AgentGuardArtifact } from '@/types/agentguard'

export type RoutingClass = 'GREEN' | 'YELLOW' | 'RED'

/** Normalize artifact routing_classification for display and UI gates. */
export function normalizeRoutingClass(
  raw?: string | null,
  fallback: RoutingClass = 'RED'
): RoutingClass {
  const u = String(raw ?? '')
    .trim()
    .toUpperCase()
  if (u === 'GREEN' || u === 'YELLOW' || u === 'RED') return u
  return fallback
}

export function routingClassColors(route: RoutingClass): { dot: string; text: string } {
  switch (route) {
    case 'GREEN':
      return { dot: '#15803D', text: '#15803D' }
    case 'YELLOW':
      return { dot: '#B45309', text: '#B45309' }
    default:
      return { dot: '#B91C1C', text: '#B91C1C' }
  }
}

export function shortHash(hash?: string | null, head = 10, tail = 4) {
  if (!hash) return '—'
  const s = String(hash)
  if (s.length <= head + tail + 1) return s
  return `${s.slice(0, head)}…${s.slice(-tail)}`
}

export function formatArtifactTime(ts?: string | null) {
  if (!ts) return '—'
  const d = new Date(ts)
  if (Number.isNaN(d.getTime())) return String(ts)
  return d.toLocaleString()
}

export function shapPairs(a: AgentGuardArtifact): { feature: string; value: number }[] {
  const scores = a.shap_scores ?? {}
  return Object.entries(scores)
    .map(([feature, v]) => ({ feature, value: Number(v) }))
    .filter((x) => Number.isFinite(x.value))
}

export function modelVersionLabel(a: AgentGuardArtifact) {
  const v = a.model_version_hash ?? ''
  return v ? shortHash(v, 14, 6) : 'unknown'
}

export function violationLabel(a: AgentGuardArtifact) {
  if (a.policy_result === 'BLOCK') return a.policy_rule_cited ? `POLICY · ${a.policy_rule_cited}` : 'POLICY · BLOCK'
  if (a.routing_classification === 'RED') return a.policy_rule_cited ? `RED · ${a.policy_rule_cited}` : 'RED'
  if (a.routing_classification === 'YELLOW') return 'YELLOW · Supervisor review'
  return '—'
}

export function dashboardRowStatus(a: AgentGuardArtifact): 'APPROVED' | 'REVIEW' | 'BLOCKED' {
  if (a.policy_result === 'BLOCK') return 'BLOCKED'
  if (a.routing_classification === 'RED') return 'BLOCKED'
  if (a.routing_classification === 'YELLOW') return 'REVIEW'
  if (a.human_review?.action === 'REJECT') return 'BLOCKED'
  return 'APPROVED'
}

export function artifactHrRowStatus(
  a: AgentGuardArtifact
):
  | 'BLOCKED'
  | 'UNDER REVIEW'
  | 'APPROVED (HR Override)'
  | 'ESCALATED'
  | 'REJECTED'
  | 'TECH_RESOLVED' {
  if (a.tech_review?.decision === 'ACCEPT') return 'TECH_RESOLVED'
  if (a.human_review?.action === 'APPROVE') return 'APPROVED (HR Override)'
  if (a.human_review?.action === 'REJECT') return 'REJECTED'
  if (a.escalation) return 'ESCALATED'
  if (a.policy_result === 'BLOCK' || a.routing_classification === 'RED') return 'BLOCKED'
  return 'UNDER REVIEW'
}

export function isReviewQueueArtifact(a: AgentGuardArtifact) {
  const bulkPending = a.workflow_context?.bulk_review_pending === true
  return (
    bulkPending ||
    a.policy_result === 'BLOCK' ||
    a.routing_classification === 'RED' ||
    a.routing_classification === 'YELLOW' ||
    Boolean(a.human_review) ||
    Boolean(a.escalation) ||
    Boolean(a.tech_review)
  )
}

export function isShortlisted(a: AgentGuardArtifact) {
  if (a.human_review?.action === 'APPROVE') return true
  if (a.tech_review?.decision === 'ACCEPT') return true
  const supervisorVerdict = (a.supervisor_review as any)?.supervisor_verdict
  if (supervisorVerdict === 'APPROVE') return true
  return a.policy_result === 'PASS' && a.routing_classification === 'GREEN'
}

export function shortlistSource(a: AgentGuardArtifact) {
  if (a.tech_review?.decision === 'ACCEPT') return 'Tech Review'
  if (a.human_review?.action === 'APPROVE') return 'HR Override'
  const supervisorVerdict = (a.supervisor_review as any)?.supervisor_verdict
  if (supervisorVerdict === 'APPROVE') return 'Supervisor'
  return 'Auto (GREEN)'
}

export function candidateJobRole(a: AgentGuardArtifact): string | null {
  const direct = (a.job_role ?? '').trim()
  const fromContext = (a.workflow_context?.job_role ?? '').trim()
  const raw = direct || fromContext
  if (!raw) return null
  const normalized = raw.replace(/^role:\s*/i, '').trim()
  return normalized || null
}

export function candidateEmail(a: AgentGuardArtifact): string | null {
  const direct = (a.candidate_email ?? '').trim()
  if (direct) return direct
  const fromContext = (a.workflow_context?.candidate_email ?? '').trim()
  if (fromContext) return fromContext
  return null
}

export function placeholderEmail(name?: string | null, decisionId?: string | null) {
  const base =
    (name ?? '')
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, '.')
      .replace(/^\.+|\.+$/g, '') || 'candidate'
  const suffix = decisionId ? shortHash(decisionId, 6, 4).replace('…', '') : '0000'
  return `${base}.${suffix}@example.com`
}

export function formatRejectionEmailStatus(
  result?: { status?: string; email?: string; reason?: string; error?: string } | null
): string | null {
  if (!result) return null
  if (result.status === 'SENT') {
    return result.email
      ? `Rejection email sent to ${result.email}.`
      : 'Rejection email sent.'
  }
  if (result.status === 'SKIPPED' && result.reason === 'no_email_on_resume') {
    return 'Decision saved — no résumé email on file, so no rejection notice was sent.'
  }
  if (result.status === 'SKIPPED' && result.reason === 'already_sent') {
    return 'Decision saved — rejection email was already sent for this candidate.'
  }
  if (result.status === 'FAILED') {
    return result.error ? `Decision saved — rejection email failed: ${result.error}` : 'Decision saved — rejection email failed.'
  }
  return null
}
