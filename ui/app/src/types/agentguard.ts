/** Saved compliance artifact (subset of fields the UI uses). */
export interface AgentGuardArtifact {
  decision_id: string
  timestamp: string
  candidate_id?: string | null
  candidate_name?: string | null
  candidate_email?: string | null
  job_role?: string | null
  email_dispatch?: {
    sent_at?: string
    sent_by?: string
    to?: string
    subject?: string
    role_title?: string
    status?: string
    mock?: boolean
  } | null
  rejection_email_dispatch?: {
    sent_at?: string
    sent_by?: string
    to?: string
    subject?: string
    role_title?: string
    rejection_source?: string
    reviewer_comment?: string
    status?: string
    mock?: boolean
  } | null
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
  hold_status?: string | null
  hold_reason?: string | null
  held_by?: string | null
  hold_timestamp?: string | null
  workflow_context?: {
    ingestion_source?: string
    bulk_review_pending?: boolean
    bulk_session_id?: string
    bulk_job_fingerprint?: string
    open_positions_requested?: number
    job_role?: string
    bulk_hr_cleared_at?: string
    bulk_processing_failure?: boolean
    bulk_failure_phase?: string
    bulk_failure_detail?: string
    candidate_email?: string
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

export interface BatchRankCandidateRow {
  rank: number
  candidate_name: string
  candidate_id?: string | null
  composite_score?: number
  classification?: string
  governance_status?: string
  policy_rule?: string | null
  score_breakdown?: Record<string, number>
  top_skills?: string[]
  experience_summary?: string
  reasoning?: string
  artifact_reference?: {
    decision_id?: string | null
    artifact_path?: string | null
    routing_classification?: string | null
    bulk_session_id?: string | null
  }
}

export interface BatchRankResponse {
  job_role: string
  bulk_session_id?: string
  total_candidates?: number
  successful_ingestion?: number
  open_positions?: number
  processing_time_ms?: number
  job_description_digest?: string
  pool_quota_policy?: {
    triggered?: boolean
    freeze_final_approvals?: boolean
    tentative_hold?: boolean
    reviewed_pool_percentage?: number
    min_pool_review_threshold?: number
    violations?: Array<Record<string, unknown>>
  }
  ranked_candidates: BatchRankCandidateRow[]
  skipped_files?: Array<{ file: string; reason: string }>
  [key: string]: unknown
}

export interface ShortlistEmailResultRow {
  decision_id: string
  email?: string
  status: string
  reason?: string
  error?: string
}

export interface ShortlistEmailResponse {
  sent: number
  failed: number
  skipped: number
  results: ShortlistEmailResultRow[]
}

export interface RejectionEmailResult {
  decision_id?: string
  email?: string
  status: string
  reason?: string
  error?: string
}

export interface ReviewActionResponse {
  message?: string
  artifact?: unknown
  rejection_email?: RejectionEmailResult
}
