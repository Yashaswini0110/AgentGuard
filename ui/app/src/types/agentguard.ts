/** Saved compliance artifact (subset of fields the UI uses). */
export interface AgentGuardArtifact {
  decision_id: string
  timestamp: string
  candidate_id?: string | null
  candidate_name?: string | null
  decision_outcome?: string | null
  policy_result: string
  policy_violations?: Array<Record<string, unknown>>
  policy_rule_cited?: string
  routing_classification?: string | null
  confidence_score?: number | null
  shap_scores?: Record<string, number>
  model_version_hash?: string | null
  servicenow_ticket_id?: string | null
  artifact_hash?: string
  supervisor_review?: Record<string, unknown> | null
  human_review?: {
    action: string
    reviewer_id: string
    reason: string
    reviewed_at?: string
  }
  escalation?: {
    reviewer_id: string
    note: string
    escalated_at?: string
  }
  tech_review?: {
    decision: string
    reviewer_id: string
    note: string
    reviewed_at?: string
  }
}

export interface DriftReport {
  artifacts_analysed?: number
  alert?: boolean
  green_pct?: number
  yellow_pct?: number
  red_pct?: number
  [key: string]: unknown
}

export interface DecisionPipelineResponse {
  decision_id: string
  classification: string
  policy_blocked: boolean
  total_latency_ms: number
  artifact: AgentGuardArtifact
  servicenow_result?: { ticket_id?: string | null; status?: string } | null
  [key: string]: unknown
}

export interface CandidatePayload {
  candidate_id: string
  name: string
  years_of_experience: number
  skill_match_score: number
  interview_score: number
  assessment_score: number
  career_gap_months?: number | null
  gender?: string | null
  institution_tier?: number | null
  applicant_surname?: string | null
  home_district?: string | null
  village_code?: string | null
  emotion_score?: number | null
}
