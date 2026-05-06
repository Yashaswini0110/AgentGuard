import { useCallback, useEffect, useState } from 'react'
import AppShell from '@/components/AppShell'
import { apiBase, fetchRecentArtifacts } from '@/lib/api'
import { isShortlisted, placeholderEmail, shortlistSource } from '@/lib/artifactHelpers'

interface CandidateRow {
  id: string
  name: string
  role: string
  source: string
  email: string
}

export default function ShortlistPage() {
  const [candidates, setCandidates] = useState<CandidateRow[]>([])
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set())
  const [subject, setSubject] = useState('Interview Shortlisting — [Role] Position')
  const [body, setBody] = useState(
    `Dear Candidate,

Congratulations! We are pleased to inform you that you have been shortlisted for the next round of interviews.

Our AI governance system (AgentGuard v3) has reviewed your application alongside our hiring panel, and your profile has cleared all compliance and technical checks.

Next steps:
• A member of our recruitment team will contact you within 2 business days to schedule your interview.
• Please ensure your contact details are up to date.
• If you have any questions, reply to this email or reach out to hr@company.com.

We look forward to speaking with you.

Best regards,
HR Compliance Team
Company Inc.`
  )
  const [emailedCount, setEmailedCount] = useState(0)
  const [showSuccess, setShowSuccess] = useState(false)
  const [loadErr, setLoadErr] = useState<string | null>(null)

  const reload = useCallback(async () => {
    setLoadErr(null)
    try {
      const arts = await fetchRecentArtifacts(160)
      const rows: CandidateRow[] = arts
        .filter((a) => isShortlisted(a))
        .map((a) => ({
          id: a.decision_id,
          name: a.candidate_name ?? a.candidate_id ?? 'Unknown',
          role: 'Applicant',
          source: shortlistSource(a),
          email: placeholderEmail(a.candidate_name, a.decision_id),
        }))
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

  const handleSend = () => {
    setEmailedCount(selectedCandidates.length)
    setShowSuccess(true)
    setTimeout(() => setShowSuccess(false), 3000)
  }

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
            Candidates derived from artefacts (GREEN PASS, supervisor APPROVE, HR override, or tech ACCEPT) ·{' '}
            <span className="font-mono text-xs">{apiBase()}</span>
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
            {candidates.length} accepted · {emailedCount} emailed (demo)
          </span>
        </div>
      </div>

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
                  <div className="flex-1">
                    <div className="font-sans font-medium text-sm" style={{ color: '#0D0D0D' }}>
                      {c.name}
                    </div>
                    <div className="font-sans text-xs" style={{ color: '#9B9B9B' }}>
                      {c.role}
                    </div>
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
                  <span className="font-mono text-xs" style={{ color: '#6B6B6B' }}>
                    {c.email}
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
                HR Compliance · agentguard-hr@company.com
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
                  height: '240px',
                  outline: 'none',
                  resize: 'vertical',
                  color: '#0D0D0D',
                  lineHeight: '1.6',
                }}
              />
            </div>

            <button
              type="button"
              onClick={handleSend}
              disabled={selectedCandidates.length === 0}
              className="w-full font-sans text-sm font-medium py-2.5 rounded-lg transition-opacity"
              style={{
                backgroundColor: selectedCandidates.length === 0 ? '#E4E2DC' : '#0D6EFD',
                color: selectedCandidates.length === 0 ? '#9B9B9B' : '#FFFFFF',
                border: 'none',
                cursor: selectedCandidates.length === 0 ? 'not-allowed' : 'pointer',
              }}
            >
              {showSuccess ? 'Emails Sent!' : `Send ${selectedCandidates.length} Email${selectedCandidates.length !== 1 ? 's' : ''}`}
            </button>

            {showSuccess && (
              <p className="font-sans text-xs mt-2 text-center" style={{ color: '#15803D' }}>
                Demo only — no mail transport is wired yet.
              </p>
            )}
          </div>
        </div>
      </div>
    </AppShell>
  )
}
