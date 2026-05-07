import type { AgentGuardArtifact } from '@/types/agentguard'

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

export function placeholderEmail(name?: string | null, decisionId?: string | null) {
  const base =
    (name ?? '')
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, '.')
      .replace(/^\.+|\.+$/g, '') || 'candidate'
  const suffix = decisionId ? shortHash(decisionId, 6, 4).replace('…', '') : '0000'
  return `${base}.${suffix}@example.com`
}
