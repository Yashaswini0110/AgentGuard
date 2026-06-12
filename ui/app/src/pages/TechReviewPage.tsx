import { useCallback, useEffect, useState } from 'react'
import AppShell from '@/components/AppShell'
import { ResumeViewer } from '@/components/ResumeViewer'
import { apiBase, fetchRecentArtifacts, postTechReview } from '@/lib/api'
import {
  formatArtifactTime,
  formatRejectionEmailStatus,
  modelVersionLabel,
  normalizeRoutingClass,
  routingClassColors,
  shapPairs,
  shortHash,
  type RoutingClass,
} from '@/lib/artifactHelpers'
import type { AgentGuardArtifact } from '@/types/agentguard'
import { useDemoAuth } from '@/contexts/DemoAuthContext'
import TechReviewerSummaryPanel from '@/components/TechReviewerSummaryPanel'

interface TechCase {
  id: string
  artifact: AgentGuardArtifact
  candidate: string
  role: string
  routingClass: RoutingClass
  policyRule: string
  confidence: string
  servicenowTicket?: string
  hrNote: string
  escalatedTime: string
  shapData: { feature: string; value: number }[]
  decisionId: string
  candidateId: string
  artifactHash: string
  modelVersion: string
}

function mapEscalated(a: AgentGuardArtifact): TechCase | null {
  if (!a.escalation) return null
  const route = normalizeRoutingClass(a.routing_classification, 'RED')
  const pairs = shapPairs(a)

  return {
    id: a.decision_id,
    artifact: a,
    candidate: a.candidate_name ?? a.candidate_id ?? 'Unknown',
    role: 'Applicant',
    routingClass: route,
    policyRule: a.policy_rule_cited ?? 'NONE',
    confidence:
      typeof a.confidence_score === 'number' ? a.confidence_score.toFixed(2) : '—',
    servicenowTicket: a.servicenow_ticket_id ?? undefined,
    hrNote: a.escalation.note || '—',
    escalatedTime: formatArtifactTime(a.escalation.escalated_at ?? a.timestamp),
    shapData: pairs.sort((x, y) => Math.abs(y.value) - Math.abs(x.value)),
    decisionId: a.decision_id,
    candidateId: a.candidate_id ?? '—',
    artifactHash: shortHash(a.artifact_hash, 10, 4),
    modelVersion: modelVersionLabel(a),
  }
}

function ShapBar({ value }: { value: number }) {
  const maxVal = 0.5
  const pct = Math.min(Math.abs(value) / maxVal, 1) * 100
  const isPositive = value >= 0

  return (
    <div className="flex items-center gap-2">
      <div
        className="relative flex-shrink-0"
        style={{ width: '120px', height: '4px', backgroundColor: '#E4E2DC' }}
      >
        <div
          style={{
            position: 'absolute',
            left: '50%',
            transform: 'translateX(-50%)',
            width: '1px',
            height: '8px',
            backgroundColor: '#9B9B9B',
            top: '-2px',
            zIndex: 2,
          }}
        />
        <div
          style={{
            position: 'absolute',
            left: isPositive ? '50%' : `${50 - pct / 2}%`,
            width: `${pct / 2}%`,
            height: '4px',
            backgroundColor: isPositive ? '#B91C1C' : '#15803D',
            top: 0,
            zIndex: 1,
          }}
        />
      </div>
      <span className="font-mono text-[11px] flex-shrink-0" style={{ color: '#6B6B6B', minWidth: '40px' }}>
        {value > 0 ? '+' : ''}
        {value.toFixed(2)}
      </span>
    </div>
  )
}

export default function TechReviewPage() {
  const { user } = useDemoAuth()
  const [cases, setCases] = useState<TechCase[]>([])
  const [techNotes, setTechNotes] = useState<Record<string, string>>({})
  const [busyId, setBusyId] = useState<string | null>(null)
  const [err, setErr] = useState<string | null>(null)
  const [actionNotice, setActionNotice] = useState<string | null>(null)
  const [resumeViewer, setResumeViewer] = useState<{ decisionId: string; candidate: string } | null>(null)

  const reload = useCallback(async () => {
    setErr(null)
    try {
      const arts = await fetchRecentArtifacts(160)
      const mapped = arts
        .filter((a) => a.escalation != null && a.tech_review == null)
        .map(mapEscalated)
        .filter((x): x is TechCase => x !== null)

      setCases(mapped.sort((x, y) => y.artifact.timestamp.localeCompare(x.artifact.timestamp)))
    } catch (e) {
      setErr(e instanceof Error ? e.message : 'Load failed')
    }
  }, [])

  useEffect(() => {
    void reload()
  }, [reload])

  const persistTech = async (id: string, action: 'ACCEPT' | 'REJECT') => {
    const c = cases.find((x) => x.id === id)
    if (!c) return
    setBusyId(id)
    setErr(null)
    setActionNotice(null)
    try {
      const res = await postTechReview(c.decisionId, {
        action,
        reviewer_id: user?.id ?? 'TECH-REVIEWER-UNKNOWN',
        note: techNotes[id] ?? '',
      })
      if (action === 'REJECT') {
        const emailNote = formatRejectionEmailStatus(res.rejection_email)
        if (emailNote) setActionNotice(emailNote)
      }
      await reload()
    } catch (e) {
      setErr(e instanceof Error ? e.message : 'Tech review failed')
    } finally {
      setBusyId(null)
    }
  }

  return (
    <AppShell>
      <div className="flex items-center justify-between mb-7">
        <div>
          <h1 className="font-sans font-semibold" style={{ fontSize: '22px', color: '#0D0D0D' }}>
            Technical Review
          </h1>
          <p className="font-sans text-sm mt-1" style={{ color: '#6B6B6B' }}>
            Cases with <span className="font-mono text-xs">escalation</span> and no{' '}
            <span className="font-mono text-xs">tech_review</span> yet —{' '}
            <span className="font-mono text-xs">{apiBase()}</span>
          </p>
          {err && (
            <p className="font-sans text-xs mt-2" style={{ color: '#B91C1C' }}>
              {err}
            </p>
          )}
          {actionNotice && (
            <p className="font-sans text-xs mt-2" style={{ color: '#15803D' }}>
              {actionNotice}
            </p>
          )}
        </div>
        <div className="flex items-center gap-2">
          <div style={{ width: '8px', height: '8px', borderRadius: '2px', backgroundColor: '#7C3AED' }} />
          <span className="font-sans font-semibold text-sm" style={{ color: '#7C3AED' }}>
            {cases.length} awaiting review
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

      <div className="flex flex-col" style={{ gap: '12px' }}>
        {cases.length === 0 && (
          <p className="font-sans text-sm" style={{ color: '#9B9B9B' }}>
            No open escalations. Use Review Queue → Escalate to enqueue a candidate here (
            <span className="font-mono">POST /escalate</span>
            ).
          </p>
        )}
        {cases.map((c) => {
          const note = techNotes[c.id] || ''
          const isBusy = busyId === c.id
          const routeColors = routingClassColors(c.routingClass)

          return (
            <div
              key={c.id}
              style={{
                backgroundColor: '#FFFFFF',
                border: '1px solid #E4E2DC',
                borderRadius: '12px',
                padding: '24px',
              }}
            >
              <div className="flex items-start justify-between">
                <div>
                  <h3 className="font-sans font-semibold text-base" style={{ color: '#0D0D0D' }}>
                    {c.candidate}
                  </h3>
                  <p className="font-sans text-sm mt-0.5" style={{ color: '#6B6B6B' }}>
                    {c.role}
                  </p>
                </div>
                <span className="font-sans text-xs" style={{ color: '#9B9B9B' }}>
                  Escalated by HR · {c.escalatedTime}
                </span>
              </div>

              <div className="my-4" style={{ height: '1px', backgroundColor: '#E4E2DC' }} />

              <TechReviewerSummaryPanel
                key={c.decisionId}
                decisionId={c.decisionId}
                routingClassification={c.routingClass}
                allowAdvisoryOnGreen
              />

              <div className="flex gap-8 mt-4">
                <div style={{ width: '60%' }}>
                  <div className="flex flex-col">
                    {[
                      { key: 'decision_id', value: c.decisionId },
                      {
                        key: 'routing_class',
                        value: (
                          <div className="flex items-center gap-2">
                            <div
                              style={{
                                width: '8px',
                                height: '8px',
                                borderRadius: '2px',
                                backgroundColor: routeColors.dot,
                              }}
                            />
                            <span className="font-mono text-xs" style={{ color: routeColors.text }}>
                              {c.routingClass}
                            </span>
                          </div>
                        ),
                      },
                      { key: 'policy_rule_cited', value: c.policyRule },
                      { key: 'confidence', value: c.confidence },
                      ...(c.servicenowTicket
                        ? [
                            {
                              key: 'servicenow_ticket',
                              value: (
                                <span className="font-mono text-xs" style={{ color: '#0D0D0D' }}>
                                  {c.servicenowTicket}
                                </span>
                              ),
                            },
                          ]
                        : []),
                      {
                        key: 'hr_note',
                        value: (
                          <span className="font-sans text-xs italic" style={{ color: '#6B6B6B' }}>
                            &ldquo;{c.hrNote}&rdquo;
                          </span>
                        ),
                      },
                    ].map((item, idx, arr) => (
                      <div
                        key={typeof item.key === 'string' ? item.key : idx}
                        className="flex items-center justify-between"
                        style={{
                          minHeight: '32px',
                          ...(idx < arr.length - 1 ? { borderBottom: '1px solid #E4E2DC' } : {}),
                        }}
                      >
                        <span className="font-mono text-xs" style={{ color: '#9B9B9B' }}>
                          {item.key}
                        </span>
                        <div style={{ color: '#0D0D0D' }}>{item.value}</div>
                      </div>
                    ))}
                  </div>
                </div>

                <div style={{ width: '40%' }}>
                  <h4 className="font-sans font-medium text-[13px] mb-3" style={{ color: '#0D0D0D' }}>
                    Feature risk attribution
                  </h4>
                  <div className="flex flex-col gap-2">
                    {c.shapData.map((s) => (
                      <div key={s.feature} className="flex items-center justify-between gap-2">
                        <span
                          className="font-mono text-[11px] flex-shrink-0"
                          style={{
                            color: '#6B6B6B',
                            width: '130px',
                            overflow: 'hidden',
                            textOverflow: 'ellipsis',
                            whiteSpace: 'nowrap',
                          }}
                          title={s.feature}
                        >
                          {s.feature}
                        </span>
                        <ShapBar value={s.value} />
                      </div>
                    ))}
                  </div>
                </div>
              </div>

              <div className="mt-4 pt-4 flex items-center gap-3" style={{ borderTop: '1px solid #E4E2DC' }}>
                <button
                  type="button"
                  onClick={() => setResumeViewer({ decisionId: c.decisionId, candidate: c.candidate })}
                  className="font-sans text-sm font-medium px-4 py-2.5 rounded-lg transition-opacity hover:opacity-90"
                  style={{
                    border: '1px solid #0D6EFD',
                    color: '#0D6EFD',
                    background: 'none',
                    cursor: 'pointer',
                  }}
                >
                  View Resume
                </button>
                <button
                  type="button"
                  onClick={() => void persistTech(c.id, 'ACCEPT')}
                  disabled={isBusy}
                  className="font-sans text-sm font-medium px-5 py-2.5 rounded-lg transition-opacity hover:opacity-90"
                  style={{
                    backgroundColor: '#15803D',
                    color: '#FFFFFF',
                    border: 'none',
                    cursor: isBusy ? 'wait' : 'pointer',
                  }}
                >
                  Accept Candidate
                </button>
                <input
                  type="text"
                  placeholder="Add technical note (optional)"
                  className="flex-1 font-sans text-xs px-3 py-2 rounded-md"
                  style={{
                    border: '1px solid #E4E2DC',
                    backgroundColor: '#FFFFFF',
                    height: '36px',
                    outline: 'none',
                  }}
                  value={note}
                  onChange={(e) => setTechNotes((prev) => ({ ...prev, [c.id]: e.target.value }))}
                />
                <button
                  type="button"
                  onClick={() => void persistTech(c.id, 'REJECT')}
                  disabled={isBusy}
                  className="font-sans text-sm font-medium px-5 py-2.5 rounded-lg transition-opacity hover:opacity-90"
                  style={{
                    border: '1px solid #B91C1C',
                    color: '#B91C1C',
                    background: 'none',
                    cursor: isBusy ? 'wait' : 'pointer',
                  }}
                >
                  Reject Candidate
                </button>
              </div>
            </div>
          )
        })}
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
