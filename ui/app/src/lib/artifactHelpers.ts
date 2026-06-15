import type { AgentGuardArtifact } from '@/types/agentguard'

export type RoutingClass = 'GREEN' | 'YELLOW' | 'RED'

/** Human-readable labels for the 6 governance-safe router features. */
export const FEATURE_LABELS: Record<string, string> = {
  years_of_experience: 'Years of Experience',
  skill_match_score: 'Skill Match Score',
  interview_score: 'Interview Score',
  assessment_score: 'Assessment Score',
  decision_confidence: 'AI Decision Confidence',
  feature_count: 'Number of Features Considered',
}

/** Plain one-sentence descriptions for judges (SAFE_FEATURES glossary). */
export const FEATURE_GLOSSARY: Record<string, string> = {
  years_of_experience:
    'How many years of relevant work experience the candidate has.',
  skill_match_score:
    "How closely the candidate's skills match the job's requirements (0 = no match, 1 = perfect match).",
  interview_score:
    "The candidate's interview performance score (out of 10).",
  assessment_score:
    "The candidate's score on the skills assessment test (out of 100).",
  decision_confidence:
    'How confident the AI hiring screener was in its own recommendation (0 = very unsure, 1 = very confident).',
  feature_count:
    'How many distinct factors the AI screener said it weighed when making its decision.',
}

export const SAFE_FEATURE_ORDER = [
  'years_of_experience',
  'skill_match_score',
  'interview_score',
  'assessment_score',
  'decision_confidence',
  'feature_count',
] as const

export function shapFeatureLabel(feature: string): string {
  return FEATURE_LABELS[feature] ?? feature.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())
}

export function shapPairs(a: AgentGuardArtifact): { feature: string; label: string; value: number }[] {
  const scores = a.shap_scores ?? {}
  return Object.entries(scores)
    .map(([feature, v]) => ({
      feature,
      label: shapFeatureLabel(feature),
      value: Number(v),
    }))
    .filter((x) => Number.isFinite(x.value))
}

export function shapTopContributor(
  pairs: { label: string; value: number }[],
  riskLevel: string
): string | null {
  if (!pairs.length) return null
  const level = (riskLevel || 'UNKNOWN').toUpperCase()
  const top = [...pairs].sort((a, b) => Math.abs(b.value) - Math.abs(a.value))[0]
  const verb =
    top.value >= 0
      ? `pushed toward the ${level} classification`
      : `pushed away from the ${level} classification`
  return `The strongest factor in this decision was ${top.label}, which ${verb}.`
}

function skillMatchQualifier(score: number): string {
  if (score >= 0.85) return 'strong match'
  if (score >= 0.6) return 'good match'
  if (score >= 0.4) return 'partial match'
  return 'weak match'
}

function confidenceQualifier(score: number): string {
  if (score >= 0.85) return 'very high'
  if (score >= 0.65) return 'high'
  if (score >= 0.45) return 'moderate'
  return 'low'
}

/** Format a router feature value for judge-facing SHAP bullets. */
export function formatRouterFeatureValue(feature: string, value: number): string {
  if (!Number.isFinite(value)) return '—'
  switch (feature) {
    case 'years_of_experience': {
      const n = Math.round(value * 10) / 10
      const unit = n === 1 ? 'year' : 'years'
      return `${n} ${unit}`
    }
    case 'skill_match_score':
      return `${value.toFixed(2)} — ${skillMatchQualifier(value)}`
    case 'interview_score':
      return value <= 15 ? `${value.toFixed(1)}/10` : `${value.toFixed(1)}/100`
    case 'assessment_score':
      return `${value.toFixed(0)}/100`
    case 'decision_confidence':
      return `${value.toFixed(2)} — ${confidenceQualifier(value)}`
    case 'feature_count': {
      const n = Math.round(value)
      return String(n)
    }
    default:
      return String(value)
  }
}

function shapStrengthWord(rankIndex: number): string {
  if (rankIndex === 0) return 'strongly'
  if (rankIndex <= 2) return 'moderately'
  return 'slightly'
}

/** Six plain-language bullets ordered by |SHAP| magnitude (largest first). */
export function shapBreakdownLines(
  shapScores: Record<string, number> | null | undefined,
  routerFeatures: Record<string, number> | null | undefined,
  riskLevel: string
): string[] {
  const level = (riskLevel || 'UNKNOWN').toUpperCase()
  const scores = shapScores ?? {}
  const features = routerFeatures ?? {}

  const ordered = SAFE_FEATURE_ORDER.map((key) => ({
    key,
    label: shapFeatureLabel(key),
    impact: Number(scores[key]),
    raw: features[key],
  }))
    .filter((row) => Number.isFinite(row.impact))
    .sort((a, b) => Math.abs(b.impact) - Math.abs(a.impact))

  return ordered.map((row, idx) => {
    const strength = shapStrengthWord(idx)
    const direction =
      row.impact >= 0
        ? `pushed toward ${level}`
        : 'pushed toward a different outcome'
    const valueText =
      row.raw !== undefined && Number.isFinite(Number(row.raw))
        ? formatRouterFeatureValue(row.key, Number(row.raw))
        : 'value not recorded'
    return `${row.label} (${valueText}) ${strength} ${direction}.`
  })
}

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

export function isOnHold(a: AgentGuardArtifact) {
  return String(a.hold_status ?? '').trim().toUpperCase() === 'ON_HOLD'
}

export function artifactHrRowStatus(
  a: AgentGuardArtifact
):
  | 'BLOCKED'
  | 'UNDER REVIEW'
  | 'ON HOLD'
  | 'APPROVED (HR Override)'
  | 'ESCALATED'
  | 'REJECTED'
  | 'TECH_RESOLVED' {
  if (a.tech_review?.decision === 'ACCEPT') return 'TECH_RESOLVED'
  if (a.human_review?.action === 'APPROVE') return 'APPROVED (HR Override)'
  if (a.human_review?.action === 'REJECT') return 'REJECTED'
  if (isOnHold(a)) return 'ON HOLD'
  if (a.escalation) return 'ESCALATED'
  if (a.policy_result === 'BLOCK' || a.routing_classification === 'RED') return 'BLOCKED'
  return 'UNDER REVIEW'
}

export function isReviewQueueArtifact(a: AgentGuardArtifact) {
  const bulkPending = a.workflow_context?.bulk_review_pending === true
  return (
    bulkPending ||
    isOnHold(a) ||
    a.policy_result === 'BLOCK' ||
    a.routing_classification === 'RED' ||
    a.routing_classification === 'YELLOW' ||
    Boolean(a.human_review) ||
    Boolean(a.escalation) ||
    Boolean(a.tech_review)
  )
}

export function isShortlisted(a: AgentGuardArtifact) {
  if (isOnHold(a)) return false
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
