import { Fragment, useCallback, useEffect, useMemo, useState } from 'react'
import { useSearchParams } from 'react-router'
import AppShell from '@/components/AppShell'
import { StatusDot } from '@/components/StatusDot'
import { ResumeViewer } from '@/components/ResumeViewer'
import { apiBase, fetchRecentArtifacts, postEscalate, postHumanReview } from '@/lib/api'
import {
  artifactHrRowStatus,
  formatArtifactTime,
  isReviewQueueArtifact,
  modelVersionLabel,
  shapPairs,
  shortHash,
  violationLabel,
} from '@/lib/artifactHelpers'
import type { AgentGuardArtifact } from '@/types/agentguard'
import { useDemoAuth } from '@/contexts/DemoAuthContext'
import TechReviewerSummaryPanel from '@/components/TechReviewerSummaryPanel'

type ReviewStatus =
  | 'BLOCKED'
  | 'UNDER REVIEW'
  | 'APPROVED (HR Override)'
  | 'ESCALATED'
  | 'REJECTED'
  | 'TECH_RESOLVED'

interface ReviewRow {
  id: string
  artifact: AgentGuardArtifact
  candidate: string
  role: string
  status: ReviewStatus
  violation: string
  shapFeature: string
  shapValue: number
  submitted: string
  decisionId: string
  candidateId: string
  routingClass: string
  confidence: string
  policyRule: string
  artifactHash: string
  servicenowTicket?: string
  modelVersion: string
  shapData: { feature: string; value: number }[]
}

function mapArtifact(a: AgentGuardArtifact): ReviewRow | null {
  if (!isReviewQueueArtifact(a)) return null

  const pairs = shapPairs(a)
  const sorted = [...pairs].sort((x, y) => Math.abs(y.value) - Math.abs(x.value))
  const top = sorted[0] ?? { feature: '—', value: 0 }
  const st = artifactHrRowStatus(a)

  const statusMap: Record<string, ReviewStatus> = {
    BLOCKED: 'BLOCKED',
    'UNDER REVIEW': 'UNDER REVIEW',
    'APPROVED (HR Override)': 'APPROVED (HR Override)',
    ESCALATED: 'ESCALATED',
    REJECTED: 'REJECTED',
    TECH_RESOLVED: 'TECH_RESOLVED',
  }

  const bulk = a.workflow_context?.ingestion_source === 'bulk_zip_rank'
  return {
    id: a.decision_id,
    artifact: a,
    candidate: a.candidate_name ?? a.candidate_id ?? 'Unknown',
    role: bulk ? 'Bulk ZIP pool' : 'Applicant',
    status: statusMap[st] ?? 'UNDER REVIEW',
    violation: violationLabel(a),
    shapFeature: top.feature,
    shapValue: top.value,
    submitted: formatArtifactTime(a.timestamp),
    decisionId: a.decision_id,
    candidateId: a.candidate_id ?? '—',
    routingClass: a.routing_classification ?? '—',
    confidence:
      typeof a.confidence_score === 'number' ? a.confidence_score.toFixed(2) : '—',
    policyRule: a.policy_rule_cited ?? 'NONE',
    artifactHash: shortHash(a.artifact_hash, 10, 4),
    servicenowTicket: a.servicenow_ticket_id ?? undefined,
    modelVersion: modelVersionLabel(a),
    shapData: sorted,
  }
}

function ShapBar({ value }: { value: number }) {
  const maxVal = 0.5
  const pct = Math.min(Math.abs(value) / maxVal, 1) * 100
  const isPositive = value >= 0

  return (
    <div className="flex items-center gap-2">
      <div className="relative" style={{ width: '120px', height: '4px', backgroundColor: '#E4E2DC' }}>
        <div
          style={{
            position: 'absolute',
            left: isPositive ? '50%' : `${50 - pct / 2}%`,
            width: `${pct / 2}%`,
            height: '4px',
            backgroundColor: isPositive ? '#B91C1C' : '#15803D',
            top: 0,
          }}
        />
        <div
          style={{
            position: 'absolute',
            left: '50%',
            width: '1px',
            height: '8px',
            backgroundColor: '#9B9B9B',
            top: '-2px',
          }}
        />
      </div>
      <span className="font-mono text-[11px]" style={{ color: '#6B6B6B', minWidth: '40px' }}>
        {value > 0 ? '+' : ''}
        {value.toFixed(2)}
      </span>
    </div>
  )
}

function ShapMiniBar({ value }: { value: number }) {
  const maxVal = 0.5
  const pct = Math.min(Math.abs(value) / maxVal, 1) * 100
  const color = value >= 0 ? '#B91C1C' : '#15803D'

  return (
    <div className="flex flex-col gap-1">
      <div style={{ width: '60px', height: '4px', backgroundColor: '#E4E2DC' }}>
        <div
          style={{
            width: `${pct}%`,
            height: '4px',
            backgroundColor: color,
            marginLeft: value >= 0 ? '0' : `${100 - pct}%`,
          }}
        />
      </div>
    </div>
  )
}

function statusToDot(status: ReviewStatus): { color: 'green' | 'amber' | 'red' | 'purple'; text: string } {
  switch (status) {
    case 'APPROVED (HR Override)':
      return { color: 'green', text: status }
    case 'ESCALATED':
      return { color: 'purple', text: status }
    case 'TECH_RESOLVED':
      return { color: 'green', text: 'TECH CLEARED' }
    case 'REJECTED':
      return { color: 'red', text: status }
    case 'BLOCKED':
      return { color: 'red', text: status }
    case 'UNDER REVIEW':
      return { color: 'amber', text: status }
    default:
      return { color: 'amber', text: status }
  }
}

export default function ReviewQueuePage() {
  const { user } = useDemoAuth()
  const [searchParams] = useSearchParams()
  const highlightDecision = searchParams.get('decision')
  const sessionFilter = searchParams.get('session')

  const [rows, setRows] = useState<ReviewRow[]>([])
  const [loadErr, setLoadErr] = useState<string | null>(null)
  const [busyId, setBusyId] = useState<string | null>(null)
  const [expandedId, setExpandedId] = useState<string | null>(null)
  const [activeTab, setActiveTab] = useState<'all' | 'blocked' | 'review'>('all')
  const [actionState, setActionState] = useState<{
    id: string
    type: 'approve' | 'escalate' | 'reject'
    note: string
  } | null>(null)
  const [resumeViewer, setResumeViewer] = useState<{ decisionId: string; candidate: string } | null>(null)

  const reload = useCallback(async () => {
    setLoadErr(null)
    try {
      const arts = await fetchRecentArtifacts(420)
      setRows(
        arts
          .map(mapArtifact)
          .filter((x): x is ReviewRow => x !== null)
      )
    } catch (e) {
      setLoadErr(e instanceof Error ? e.message : 'Failed to load queue')
    }
  }, [])

  useEffect(() => {
    void reload()
  }, [reload])

  const scopeRows = useMemo(() => {
    if (!sessionFilter) return rows
    return rows.filter((r) => r.artifact.workflow_context?.bulk_session_id === sessionFilter)
  }, [rows, sessionFilter])

  const filteredRows = scopeRows.filter((r) => {
    if (activeTab === 'all') return true
    if (activeTab === 'blocked') return r.status === 'BLOCKED'
    if (activeTab === 'review')
      return r.status === 'UNDER REVIEW' || r.status === 'ESCALATED' || r.routingClass === 'YELLOW'
    return true
  })

  const counts = {
    all: scopeRows.length,
    blocked: scopeRows.filter((r) => r.status === 'BLOCKED').length,
    review: scopeRows.filter((r) => r.status === 'UNDER REVIEW' || r.status === 'ESCALATED').length,
  }

  const isDone = (s: ReviewStatus) =>
    ['APPROVED (HR Override)', 'ESCALATED', 'REJECTED', 'TECH_RESOLVED'].includes(s)

  const handleConfirmAction = async () => {
    if (!actionState) return
    const row = rows.find((r) => r.id === actionState.id)
    if (!row) return

    setBusyId(actionState.id)
    const note = actionState.note.trim()
    try {
      const reviewerId = user?.id ?? 'HR-UNKNOWN'
      if (actionState.type === 'approve') {
        await postHumanReview(row.decisionId, {
          action: 'APPROVE',
          reviewer_id: reviewerId,
          reason: note || 'HR override approval recorded from AgentGuard UI.',
        })
      } else if (actionState.type === 'reject') {
        await postHumanReview(row.decisionId, {
          action: 'REJECT',
          reviewer_id: reviewerId,
          reason: note || 'Rejected from review queue.',
        })
      } else if (actionState.type === 'escalate') {
        await postEscalate(row.decisionId, { reviewer_id: reviewerId, note })
      }
      await reload()
    } catch (e) {
      setLoadErr(e instanceof Error ? e.message : 'Action failed')
    } finally {
      setBusyId(null)
      setActionState(null)
    }
  }

  return (
    <AppShell>
      <div className="flex items-center justify-between mb-7">
        <div>
          <h1 className="font-sans font-semibold" style={{ fontSize: '22px', color: '#0D0D0D' }}>
            Review Queue
          </h1>
          <p className="font-sans text-sm mt-1" style={{ color: '#6B6B6B' }}>
            Hydrated from <span className="font-mono text-xs">{apiBase()}</span>/artifacts/recent · Shows policy
            BLOCK, RED, YELLOW, and bulk ZIP candidates until HR records review, escalation, or tech clearance. Standard
            single-candidate GREEN runs still skip this queue.
          </p>
          {sessionFilter ? (
            <p className="font-sans text-xs mt-2 font-mono" style={{ color: '#0D6EFD' }}>
              Filtered to bulk session {shortHash(sessionFilter, 8, 6)}
            </p>
          ) : null}
          {highlightDecision ? (
            <p className="font-sans text-xs mt-2 font-mono" style={{ color: '#0D6EFD' }}>
              Deep-linked to decision {shortHash(highlightDecision, 8, 4)}
            </p>
          ) : null}
          {loadErr && (
            <p className="font-sans text-xs mt-2" style={{ color: '#B91C1C' }}>
              {loadErr}{' '}
              <button
                type="button"
                onClick={() => void reload()}
                style={{ color: '#0D6EFD', background: 'none', border: 'none', cursor: 'pointer', padding: 0 }}
              >
                Retry
              </button>
            </p>
          )}
        </div>
        <div className="flex items-center gap-2">
          <div style={{ width: '8px', height: '8px', borderRadius: '2px', backgroundColor: '#B45309' }} />
          <span className="font-sans font-semibold text-sm" style={{ color: '#B45309' }}>
            {counts.review + counts.blocked} items loaded
          </span>
          <button
            type="button"
            className="font-sans text-xs ml-4"
            onClick={() => void reload()}
            style={{ color: '#0D6EFD', background: 'none', border: 'none', cursor: 'pointer' }}
          >
            Refresh
          </button>
        </div>
      </div>

      <div className="flex gap-6 mb-6" style={{ borderBottom: '1px solid #E4E2DC' }}>
        {[
          { key: 'all' as const, label: `All (${counts.all})` },
          { key: 'blocked' as const, label: `Blocked (${counts.blocked})` },
          { key: 'review' as const, label: `Under Review (${counts.review})` },
        ].map((tab) => (
          <button
            key={tab.key}
            type="button"
            onClick={() => setActiveTab(tab.key)}
            className="font-sans font-medium text-sm pb-3 transition-colors"
            style={{
              color: activeTab === tab.key ? '#0D0D0D' : '#6B6B6B',
              background: 'none',
              cursor: 'pointer',
              border: 'none',
              borderBottom: activeTab === tab.key ? '2px solid #0D0D0D' : '2px solid transparent',
            }}
          >
            {tab.label}
          </button>
        ))}
      </div>

      <div style={{ backgroundColor: '#FFFFFF', border: '1px solid #E4E2DC', borderRadius: '8px' }}>
        <table className="w-full">
          <thead>
            <tr style={{ backgroundColor: '#F7F6F3' }}>
              {['CANDIDATE', 'STATUS', 'VIOLATION / REASON', 'SHAP RISK', 'SUBMITTED', 'ACTIONS'].map((h) => (
                <th
                  key={h}
                  className="font-sans font-medium text-xs uppercase text-left px-5 py-3"
                  style={{ color: '#6B6B6B', letterSpacing: '0.06em' }}
                >
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {filteredRows.length === 0 && (
              <tr>
                <td colSpan={6} className="px-5 py-8 text-center font-sans text-sm" style={{ color: '#9B9B9B' }}>
                  No review items. RED / YELLOW / policy BLOCK decisions appear here automatically after{' '}
                  <span className="font-semibold">Run pipeline</span> or{' '}
                  <span className="font-semibold">Bulk rank</span> batches.
                </td>
              </tr>
            )}
            {filteredRows.map((row) => {
              const done = isDone(row.status)
              const expanded = expandedId === row.id
              const dot = statusToDot(row.status)
              const isBusy = busyId === row.id

              return (
                <Fragment key={row.id}>
                  <tr
                    data-decision-id={row.decisionId}
                    style={{
                      borderTop: '1px solid #E4E2DC',
                      cursor: 'pointer',
                      outline:
                        highlightDecision === row.decisionId ? '2px solid rgba(13,110,253,0.45)' : undefined,
                      backgroundColor:
                        highlightDecision === row.decisionId ? 'rgba(13,110,253,0.06)' : undefined,
                    }}
                    onClick={() => {
                      if (!actionState) setExpandedId(expanded ? null : row.id)
                    }}
                  >
                    <td className="px-5 py-3">
                      <div className="font-sans font-medium text-sm" style={{ color: done ? '#9B9B9B' : '#0D0D0D' }}>
                        {row.candidate}
                      </div>
                      <div className="font-sans text-xs mt-0.5" style={{ color: '#9B9B9B' }}>
                        {row.role}
                      </div>
                    </td>
                    <td className="px-5 py-3">
                      <StatusDot color={dot.color} label={dot.text} />
                    </td>
                    <td className="px-5 py-3 font-mono text-xs" style={{ color: done ? '#9B9B9B' : '#0D0D0D' }}>
                      {row.violation}
                    </td>
                    <td className="px-5 py-3">
                      {!done && (
                        <>
                          <ShapMiniBar value={row.shapValue} />
                          <div className="font-mono text-[11px] mt-1" style={{ color: '#6B6B6B' }}>
                            {row.shapFeature}{' '}
                            {row.shapValue > 0 ? '+' : ''}
                            {row.shapValue.toFixed(2)}
                          </div>
                        </>
                      )}
                    </td>
                    <td className="px-5 py-3 font-sans text-xs" style={{ color: '#9B9B9B' }}>
                      {row.submitted}
                    </td>
                    <td className="px-5 py-3">
                      {!done && actionState?.id === row.id ? (
                        <div
                          className="p-3 rounded-md"
                          style={{ backgroundColor: '#F7F6F3', border: '1px solid #E4E2DC' }}
                          onClick={(e) => e.stopPropagation()}
                        >
                          {actionState.type === 'approve' && (
                            <>
                              <p className="font-sans text-xs mb-2" style={{ color: '#0D0D0D' }}>
                                Confirm override approval for <strong>{row.candidate}</strong>? Logged via{' '}
                                <span className="font-mono">POST /human-review</span>.
                              </p>
                              <div className="flex gap-2">
                                <button
                                  type="button"
                                  onClick={() => void handleConfirmAction()}
                                  disabled={isBusy}
                                  className="font-sans text-xs font-medium px-3 py-1.5 rounded-md"
                                  style={{
                                    backgroundColor: '#15803D',
                                    color: '#FFFFFF',
                                    border: 'none',
                                    cursor: isBusy ? 'wait' : 'pointer',
                                  }}
                                >
                                  {isBusy ? 'Saving…' : 'Confirm Approval'}
                                </button>
                                <button
                                  type="button"
                                  onClick={() => setActionState(null)}
                                  className="font-sans text-xs font-medium px-3 py-1.5 rounded-md"
                                  style={{
                                    border: '1px solid #E4E2DC',
                                    color: '#0D0D0D',
                                    background: 'none',
                                    cursor: 'pointer',
                                  }}
                                >
                                  Cancel
                                </button>
                              </div>
                            </>
                          )}
                          {actionState.type === 'escalate' && (
                            <>
                              <p className="font-sans text-xs mb-2" style={{ color: '#0D0D0D' }}>
                                Escalate <strong>{row.candidate}</strong> to Tech Review (<span className="font-mono">
                                  POST /escalate
                                </span>
                                ):
                              </p>
                              <textarea
                                className="w-full mb-2 font-sans text-xs p-2 rounded-md"
                                style={{ border: '1px solid #E4E2DC', backgroundColor: '#FFFFFF', resize: 'none' }}
                                rows={2}
                                value={actionState.note}
                                onChange={(e) => setActionState({ ...actionState, note: e.target.value })}
                                placeholder="Add a note…"
                              />
                              <div className="flex gap-2">
                                <button
                                  type="button"
                                  onClick={() => void handleConfirmAction()}
                                  disabled={isBusy}
                                  className="font-sans text-xs font-medium px-3 py-1.5 rounded-md"
                                  style={{
                                    backgroundColor: '#0D6EFD',
                                    color: '#FFFFFF',
                                    border: 'none',
                                    cursor: isBusy ? 'wait' : 'pointer',
                                  }}
                                >
                                  {isBusy ? 'Saving…' : 'Send to Tech Lead'}
                                </button>
                                <button
                                  type="button"
                                  onClick={() => setActionState(null)}
                                  className="font-sans text-xs font-medium px-3 py-1.5 rounded-md"
                                  style={{
                                    border: '1px solid #E4E2DC',
                                    color: '#0D0D0D',
                                    background: 'none',
                                    cursor: 'pointer',
                                  }}
                                >
                                  Cancel
                                </button>
                              </div>
                            </>
                          )}
                          {actionState.type === 'reject' && (
                            <>
                              <p className="font-sans text-xs mb-2" style={{ color: '#0D0D0D' }}>
                                Reject <strong>{row.candidate}</strong>? Reason:
                              </p>
                              <textarea
                                className="w-full mb-2 font-sans text-xs p-2 rounded-md"
                                style={{ border: '1px solid #E4E2DC', backgroundColor: '#FFFFFF', resize: 'none' }}
                                rows={2}
                                value={actionState.note}
                                onChange={(e) => setActionState({ ...actionState, note: e.target.value })}
                                placeholder="Reason for rejection…"
                              />
                              <div className="flex gap-2">
                                <button
                                  type="button"
                                  onClick={() => void handleConfirmAction()}
                                  disabled={isBusy}
                                  className="font-sans text-xs font-medium px-3 py-1.5 rounded-md"
                                  style={{
                                    backgroundColor: '#B91C1C',
                                    color: '#FFFFFF',
                                    border: 'none',
                                    cursor: isBusy ? 'wait' : 'pointer',
                                  }}
                                >
                                  {isBusy ? 'Saving…' : 'Confirm Reject'}
                                </button>
                                <button
                                  type="button"
                                  onClick={() => setActionState(null)}
                                  className="font-sans text-xs font-medium px-3 py-1.5 rounded-md"
                                  style={{
                                    border: '1px solid #E4E2DC',
                                    color: '#0D0D0D',
                                    background: 'none',
                                    cursor: 'pointer',
                                  }}
                                >
                                  Cancel
                                </button>
                              </div>
                            </>
                          )}
                        </div>
                      ) : !done ? (
                        <div className="flex gap-2 flex-wrap">
                          <button
                            type="button"
                            onClick={(e) => {
                              e.stopPropagation()
                              setResumeViewer({ decisionId: row.decisionId, candidate: row.candidate })
                            }}
                            className="font-sans text-xs font-medium px-2 py-1 rounded"
                            style={{ border: '1px solid #0D6EFD', color: '#0D6EFD', background: 'none', cursor: 'pointer' }}
                          >
                            View Resume
                          </button>
                          <button
                            type="button"
                            onClick={(e) => {
                              e.stopPropagation()
                              setActionState({ id: row.id, type: 'approve', note: '' })
                            }}
                            className="font-sans text-xs font-medium px-2 py-1 rounded"
                            style={{ border: '1px solid #15803D', color: '#15803D', background: 'none', cursor: 'pointer' }}
                          >
                            Approve Override
                          </button>
                          <button
                            type="button"
                            onClick={(e) => {
                              e.stopPropagation()
                              setActionState({ id: row.id, type: 'escalate', note: '' })
                            }}
                            className="font-sans text-xs font-medium px-2 py-1 rounded"
                            style={{ border: '1px solid #0D6EFD', color: '#0D6EFD', background: 'none', cursor: 'pointer' }}
                          >
                            Escalate
                          </button>
                          <button
                            type="button"
                            onClick={(e) => {
                              e.stopPropagation()
                              setActionState({ id: row.id, type: 'reject', note: '' })
                            }}
                            className="font-sans text-xs font-medium px-2 py-1 rounded"
                            style={{ border: '1px solid #B91C1C', color: '#B91C1C', background: 'none', cursor: 'pointer' }}
                          >
                            Reject
                          </button>
                        </div>
                      ) : null}
                    </td>
                  </tr>
                  {expanded && !done && (
                    <tr style={{ borderTop: '2px solid #0D6EFD' }}>
                      <td colSpan={6} className="p-0">
                        <div
                          style={{
                            backgroundColor: '#F7F6F3',
                            borderLeft: '3px solid #0D6EFD',
                            padding: '20px',
                          }}
                        >
                          <div className="flex gap-8">
                            <div className="flex-1">
                              <h4 className="font-sans font-medium text-[13px] mb-3" style={{ color: '#0D0D0D' }}>
                                Decision Data
                              </h4>
                              <div className="flex flex-col">
                                {[
                                  { key: 'decision_id', value: row.decisionId },
                                  { key: 'candidate_id', value: row.candidateId },
                                  { key: 'routing_class', value: row.routingClass },
                                  { key: 'confidence', value: row.confidence },
                                  { key: 'policy_rule_cited', value: row.policyRule },
                                  { key: 'artifact_hash', value: row.artifactHash },
                                  ...(row.servicenowTicket
                                    ? [{ key: 'servicenow_ticket', value: row.servicenowTicket }]
                                    : []),
                                  { key: 'model_version', value: row.modelVersion },
                                ].map((item, idx, arr) => (
                                  <div
                                    key={item.key}
                                    className="flex items-center justify-between py-2"
                                    style={idx < arr.length - 1 ? { borderBottom: '1px solid #E4E2DC' } : {}}
                                  >
                                    <span className="font-mono text-xs" style={{ color: '#9B9B9B' }}>
                                      {item.key}
                                    </span>
                                    <span className="font-mono text-xs" style={{ color: '#0D0D0D' }}>
                                      {item.value}
                                    </span>
                                  </div>
                                ))}
                              </div>

                              {String(row.routingClass || '')
                                .trim()
                                .toUpperCase() !== 'GREEN' && (
                                <TechReviewerSummaryPanel
                                  key={row.decisionId}
                                  decisionId={row.decisionId}
                                  routingClassification={row.routingClass}
                                />
                              )}

                              <div className="mt-4 flex items-center gap-3">
                                <button
                                  type="button"
                                  className="font-sans text-xs font-medium px-3 py-2 rounded-md"
                                  style={{
                                    border: '1px solid #E4E2DC',
                                    backgroundColor: '#FFFFFF',
                                    color: '#0D0D0D',
                                    cursor: 'pointer',
                                  }}
                                  onClick={(e) => {
                                    e.stopPropagation()
                                    const jsonText = JSON.stringify(row.artifact, null, 2)
                                    const blob = new Blob([jsonText], { type: 'application/json' })
                                    const url = URL.createObjectURL(blob)
                                    const a = document.createElement('a')
                                    a.href = url
                                    a.download = `artifact_${row.decisionId}.json`
                                    a.click()
                                    URL.revokeObjectURL(url)
                                  }}
                                >
                                  Download artifact JSON
                                </button>
                                <span className="font-sans text-xs" style={{ color: '#9B9B9B' }}>
                                  Streamlit parity: “Download Regulatory Export” (client-side)
                                </span>
                              </div>
                            </div>
                            <div className="flex-1">
                              <h4 className="font-sans font-medium text-[13px] mb-3" style={{ color: '#0D0D0D' }}>
                                SHAP Feature Attribution
                              </h4>
                              <div className="flex flex-col gap-2">
                                {row.shapData.map((s) => (
                                  <div key={s.feature} className="flex items-center justify-between">
                                    <span className="font-mono text-[11px]" style={{ color: '#6B6B6B', width: '140px' }}>
                                      {s.feature}
                                    </span>
                                    <ShapBar value={s.value} />
                                  </div>
                                ))}
                              </div>
                            </div>
                          </div>
                        </div>
                      </td>
                    </tr>
                  )}
                </Fragment>
              )
            })}
          </tbody>
        </table>
      </div>

      {resumeViewer && (
        <ResumeViewer
          decisionId={resumeViewer.decisionId}
          candidateName={resumeViewer.candidate}
          onClose={() => setResumeViewer(null)}
        />
      )}
    </AppShell>
  )
}
