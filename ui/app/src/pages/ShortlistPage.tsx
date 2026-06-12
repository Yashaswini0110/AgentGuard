import { useCallback, useEffect, useState } from 'react'
import AppShell from '@/components/AppShell'
import { apiBase, fetchRecentArtifacts, postShortlistEmail } from '@/lib/api'
import { useDemoAuth } from '@/contexts/DemoAuthContext'
import {
  candidateEmail,
  candidateJobRole,
  formatArtifactTime,
  isShortlisted,
  placeholderEmail,
  shortlistSource,
} from '@/lib/artifactHelpers'

interface CandidateRow {
  id: string
  name: string
  role: string
  source: string
  email: string
  emailFromResume: boolean
  /** Present when shortlisted via tech ACCEPT — shown to HR */
  techReviewerId?: string
  techReviewedAtLabel?: string
}

const DEFAULT_SHORTLIST_SUBJECT =
  'AgentGuard – Application Shortlisted for Interview Process'

const DEFAULT_SHORTLIST_BODY = `Dear [Candidate Name],

Thank you for your interest in the [Role Title] opportunity.

We are delighted to inform you that your profile has successfully cleared our initial evaluation process and has been shortlisted for the interview stage.

Our recruitment team will contact you shortly to coordinate and schedule your interview. Additional information regarding the interview process, timing, and next steps will be shared in the upcoming communication.

We appreciate your interest in joining our team and look forward to discussing your qualifications and experience in more detail.

Thank you for your patience, and congratulations on progressing to the next stage.

Best regards,

AgentGuard Recruitment Team
agentguard.hr@gmail.com
+91 9000000001`

export default function ShortlistPage() {
  const { user } = useDemoAuth()
  const [candidates, setCandidates] = useState<CandidateRow[]>([])
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set())
  const [subject, setSubject] = useState(DEFAULT_SHORTLIST_SUBJECT)
  const [body, setBody] = useState(DEFAULT_SHORTLIST_BODY)
  const [emailedCount, setEmailedCount] = useState(0)
  const [showSuccess, setShowSuccess] = useState(false)
  const [sendError, setSendError] = useState<string | null>(null)
  const [sendDetail, setSendDetail] = useState<string | null>(null)
  const [sending, setSending] = useState(false)
  const [loadErr, setLoadErr] = useState<string | null>(null)

  const reload = useCallback(async () => {
    setLoadErr(null)
    try {
      const arts = await fetchRecentArtifacts(160)
      const rows: CandidateRow[] = arts
        .filter((a) => isShortlisted(a))
        .map((a) => {
          const parsed = candidateEmail(a)
          return {
          id: a.decision_id,
          name: a.candidate_name ?? a.candidate_id ?? 'Unknown',
          role: candidateJobRole(a) ?? 'Role not recorded',
          source: shortlistSource(a),
          email: parsed ?? placeholderEmail(a.candidate_name, a.decision_id),
          emailFromResume: Boolean(parsed),
          techReviewerId:
            a.tech_review?.decision === 'ACCEPT' ? a.tech_review.reviewer_id : undefined,
          techReviewedAtLabel:
            a.tech_review?.decision === 'ACCEPT'
              ? formatArtifactTime(a.tech_review.reviewed_at)
              : undefined,
        }})
      setCandidates(rows)
    } catch (e) {
      setLoadErr(e instanceof Error ? e.message : 'Failed to load shortlist')
    }
  }, [])

  useEffect(() => {
    void reload()
  }, [reload])

  const allSelected =
    candidates.length > 0 && selectedIds.size === candidates.length

  const handleSelectAll = () => {
    if (allSelected) {
      setSelectedIds(new Set())
    } else {
      setSelectedIds(new Set(candidates.map((c) => c.id)))
    }
  }

  const toggleCandidate = (id: string) => {
    const next = new Set(selectedIds)
    if (next.has(id)) next.delete(id)
    else next.add(id)
    setSelectedIds(next)
  }

  const selectedCandidates = candidates.filter((c) => selectedIds.has(c.id))

  const handleSend = async () => {
    setSendError(null)
    setSendDetail(null)
    if (!user || user.role !== 'hr') {
      setSendError('Log in as an HR reviewer to send shortlist emails.')
      return
    }
    const missingEmail = selectedCandidates.filter((c) => !c.emailFromResume)
    if (missingEmail.length > 0) {
      setSendError(
        `${missingEmail.length} selected candidate(s) have no résumé email — deselect them or re-run bulk ingest.`
      )
      return
    }
    setSending(true)
    try {
      const res = await postShortlistEmail({
        decision_ids: selectedCandidates.map((c) => c.id),
        subject: subject.trim(),
        body: body.trim(),
        sender_id: user.id,
      })
      setEmailedCount((n) => n + res.sent)
      if (res.sent > 0) {
        setShowSuccess(true)
        setTimeout(() => setShowSuccess(false), 4000)
      }
      const parts: string[] = []
      if (res.sent) parts.push(`${res.sent} sent`)
      if (res.skipped) parts.push(`${res.skipped} skipped`)
      if (res.failed) parts.push(`${res.failed} failed`)
      setSendDetail(parts.join(' · ') || 'No messages dispatched.')
      if (res.failed > 0 || (res.sent === 0 && res.skipped > 0)) {
        const reasons = res.results
          .filter((r) => r.status !== 'SENT')
          .map((r) => `${r.decision_id.slice(0, 8)}…: ${r.reason ?? r.error ?? r.status}`)
          .join('; ')
        if (reasons) setSendError(reasons)
      }
      if (res.sent > 0) void reload()
    } catch (e) {
      setSendError(e instanceof Error ? e.message : 'Failed to send emails')
    } finally {
      setSending(false)
    }
  }

  const canSend =
    selectedCandidates.length > 0 &&
    user?.role === 'hr' &&
    selectedCandidates.every((c) => c.emailFromResume) &&
    !sending

  function sourceDotColor(src: string) {
    if (src.includes('HR')) return '#0D6EFD'
    if (src.includes('Supervisor')) return '#B45309'
    return '#15803D'
  }

  return (
    <AppShell>
      <div className="flex items-center justify-between mb-7">
        <div>
          <h1 className="font-sans font-semibold" style={{ fontSize: '22px', color: '#0D0D0D' }}>
            Shortlist & Email
          </h1>
          <p className="font-sans text-sm mt-1" style={{ color: '#6B6B6B' }}>
            Candidates derived from artefacts (GREEN PASS, supervisor APPROVE, HR override, or tech ACCEPT). For tech-approved
            rows, the reviewer id from Tech Review is shown below · <span className="font-mono text-xs">{apiBase()}</span>
          </p>
          {loadErr && (
            <p className="font-sans text-xs mt-2" style={{ color: '#B91C1C' }}>
              {loadErr}
            </p>
          )}
        </div>
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={() => void reload()}
            className="font-sans text-xs"
            style={{ color: '#0D6EFD', background: 'none', border: 'none', cursor: 'pointer' }}
          >
            Refresh
          </button>
          <span className="font-sans font-semibold text-sm" style={{ color: '#0D0D0D' }}>
            {candidates.length} accepted · {emailedCount} emailed
          </span>
        </div>
      </div>

      {user?.role !== 'hr' && (
        <p className="font-sans text-xs mb-4 px-3 py-2 rounded-md" style={{ backgroundColor: '#FEF3C7', color: '#92400E' }}>
          Log in as HR to send shortlist emails. Viewing the queue is available to all demo roles.
        </p>
      )}

      <div className="flex gap-6">
        <div style={{ width: '60%' }}>
          <div className="flex items-center justify-between mb-3">
            <h2 className="font-sans font-semibold text-[15px]" style={{ color: '#0D0D0D' }}>
              Accepted Candidates
            </h2>
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={allSelected}
                onChange={handleSelectAll}
                className="rounded"
                style={{ width: '16px', height: '16px', accentColor: '#0D6EFD' }}
              />
              <span className="font-sans text-xs" style={{ color: '#6B6B6B' }}>
                Select All
              </span>
            </label>
          </div>

          <div
            style={{
              backgroundColor: '#FFFFFF',
              border: '1px solid #E4E2DC',
              borderRadius: '8px',
            }}
          >
            {candidates.length === 0 && (
              <div className="px-4 py-8 font-sans text-sm text-center" style={{ color: '#9B9B9B' }}>
                No shortlisted candidates yet. Run the pipeline until you get GREEN, or approve / tech-accept via the
                other tabs.
              </div>
            )}
            {candidates.map((c, i) => {
              const isSelected = selectedIds.has(c.id)
              return (
                <div
                  key={c.id}
                  className="flex items-center gap-3 px-4"
                  style={{
                    height: '48px',
                    ...(i < candidates.length - 1 ? { borderBottom: '1px solid #E4E2DC' } : {}),
                    ...(isSelected ? { backgroundColor: '#F0FDF4' } : {}),
                  }}
                >
                  <input
                    type="checkbox"
                    checked={isSelected}
                    onChange={() => toggleCandidate(c.id)}
                    style={{ width: '16px', height: '16px', accentColor: '#0D6EFD' }}
                  />
                  <div className="flex-1 min-w-0">
                    <div className="font-sans font-medium text-sm" style={{ color: '#0D0D0D' }}>
                      {c.name}
                    </div>
                    <div className="font-sans text-xs" style={{ color: '#9B9B9B' }}>
                      {c.role}
                    </div>
                    {c.techReviewerId && (
                      <div className="font-sans text-[11px] mt-1" style={{ color: '#5B21B6' }}>
                        Technical review · <span className="font-mono">{c.techReviewerId}</span>
                        {c.techReviewedAtLabel ? (
                          <span style={{ color: '#9B9B9B' }}> · {c.techReviewedAtLabel}</span>
                        ) : null}
                      </div>
                    )}
                  </div>
                  <div className="flex items-center gap-2 mr-4">
                    <div
                      style={{
                        width: '8px',
                        height: '8px',
                        borderRadius: '2px',
                        backgroundColor: sourceDotColor(c.source),
                      }}
                    />
                    <span className="font-sans text-xs" style={{ color: sourceDotColor(c.source) }}>
                      {c.source}
                    </span>
                  </div>
                  <span
                    className="font-mono text-xs"
                    style={{ color: c.emailFromResume ? '#6B6B6B' : '#B45309' }}
                    title={c.emailFromResume ? 'Extracted from résumé' : 'No email on résumé — placeholder shown'}
                  >
                    {c.email}
                    {!c.emailFromResume ? ' · est.' : ''}
                  </span>
                </div>
              )
            })}
          </div>
        </div>

        <div style={{ width: '40%' }}>
          <div
            style={{
              backgroundColor: '#FFFFFF',
              border: '1px solid #E4E2DC',
              borderRadius: '12px',
              padding: '24px',
            }}
          >
            <h2 className="font-sans font-semibold text-[15px] mb-5" style={{ color: '#0D0D0D' }}>
              Email Template
            </h2>

            <div className="mb-4">
              <label className="font-sans text-xs block mb-1" style={{ color: '#9B9B9B' }}>
                From
              </label>
              <span className="font-mono text-xs" style={{ color: '#6B6B6B' }}>
                AgentGuard Recruitment Team · agentguard.hr@gmail.com
              </span>
            </div>

            <div className="mb-4">
              <label className="font-sans text-xs block mb-1" style={{ color: '#9B9B9B' }}>
                To
              </label>
              <div className="flex flex-wrap gap-2">
                {selectedCandidates.length === 0 ? (
                  <span className="font-sans text-xs italic" style={{ color: '#9B9B9B' }}>
                    Select candidates to add recipients
                  </span>
                ) : (
                  selectedCandidates.map((c) => (
                    <div
                      key={c.id}
                      className="flex items-center gap-1 px-2 py-1 rounded-md"
                      style={{
                        backgroundColor: '#F7F6F3',
                        border: '1px solid #E4E2DC',
                      }}
                    >
                      <span className="font-sans text-xs" style={{ color: '#0D0D0D' }}>
                        {c.name}
                      </span>
                      <button
                        type="button"
                        onClick={() => toggleCandidate(c.id)}
                        className="font-sans text-xs ml-1"
                        style={{
                          color: '#9B9B9B',
                          background: 'none',
                          border: 'none',
                          cursor: 'pointer',
                          padding: 0,
                        }}
                      >
                        ×
                      </button>
                    </div>
                  ))
                )}
              </div>
            </div>

            <div className="mb-4">
              <label className="font-sans text-xs block mb-1" style={{ color: '#9B9B9B' }}>
                Subject
              </label>
              <input
                type="text"
                value={subject}
                onChange={(e) => setSubject(e.target.value)}
                className="w-full font-sans text-sm px-3 rounded-md"
                style={{
                  border: '1px solid #E4E2DC',
                  backgroundColor: '#FFFFFF',
                  height: '36px',
                  outline: 'none',
                  color: '#0D0D0D',
                }}
              />
            </div>

            <div className="mb-4">
              <label className="font-sans text-xs block mb-1" style={{ color: '#9B9B9B' }}>
                Body
              </label>
              <textarea
                value={body}
                onChange={(e) => setBody(e.target.value)}
                className="w-full font-sans text-sm p-3 rounded-md"
                style={{
                  border: '1px solid #E4E2DC',
                  backgroundColor: '#FFFFFF',
                  height: '280px',
                  outline: 'none',
                  resize: 'vertical',
                  color: '#0D0D0D',
                  lineHeight: '1.6',
                }}
              />
            </div>

            <button
              type="button"
              onClick={() => void handleSend()}
              disabled={!canSend}
              className="w-full font-sans text-sm font-medium py-2.5 rounded-lg transition-opacity"
              style={{
                backgroundColor: !canSend ? '#E4E2DC' : '#0D6EFD',
                color: !canSend ? '#9B9B9B' : '#FFFFFF',
                border: 'none',
                cursor: !canSend ? 'not-allowed' : 'pointer',
              }}
            >
              {sending
                ? 'Sending…'
                : showSuccess
                  ? 'Emails Sent!'
                  : `Send ${selectedCandidates.length} Email${selectedCandidates.length !== 1 ? 's' : ''}`}
            </button>

            {sendError && (
              <p className="font-sans text-xs mt-2 text-center" style={{ color: '#B91C1C' }}>
                {sendError}
              </p>
            )}
            {sendDetail && !sendError && (
              <p className="font-sans text-xs mt-2 text-center" style={{ color: '#15803D' }}>
                {sendDetail}
              </p>
            )}
            {showSuccess && (
              <p className="font-sans text-xs mt-2 text-center" style={{ color: '#15803D' }}>
                Check server logs when ENVIRONMENT=development (mock). Set ENVIRONMENT=production for Gmail SMTP.
              </p>
            )}
          </div>
        </div>
      </div>
    </AppShell>
  )
}
