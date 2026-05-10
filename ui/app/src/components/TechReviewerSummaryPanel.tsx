import { useCallback, useState } from 'react'
import { ChevronUp, Loader2, RefreshCw, Sparkles } from 'lucide-react'
import { postReviewerSummary } from '@/lib/api'
import type { ReviewerResumeContext, ReviewerSummary } from '@/lib/api'

const panelStyle = {
  backgroundColor: '#F7F6F3',
  border: '1px solid #E4E2DC',
  borderRadius: '10px',
} as const

function isGreenRouting(route: string) {
  return String(route || '')
    .trim()
    .toUpperCase() === 'GREEN'
}

function BulletList({
  title,
  items,
  accent,
}: {
  title: string
  items: string[]
  accent: string
}) {
  if (!items.length) return null
  return (
    <div className="mt-3">
      <p className="font-sans font-semibold text-xs uppercase tracking-wide" style={{ color: '#6B6B6B' }}>
        {title}
      </p>
      <ul className="mt-1.5 list-disc pl-4 font-sans text-sm space-y-1" style={{ color: '#0D0D0D' }}>
        {items.map((x, i) => (
          <li key={`${title}-${i}-${x.slice(0, 24)}`} style={{ color: accent }}>
            {x}
          </li>
        ))}
      </ul>
    </div>
  )
}

/**
 * AI Technical Review — one instance per candidate card.
 * State is strictly local (expanded / loading / summary / jd / error) and scoped by React instance;
 * parent should set key={decisionId} so remounts track the correct dossier.
 */
export default function TechReviewerSummaryPanel({
  decisionId,
  routingClassification,
}: {
  decisionId: string
  routingClassification: string
}) {
  const [expanded, setExpanded] = useState(false)
  const [jd, setJd] = useState('')
  const [loading, setLoading] = useState(false)
  const [summary, setSummary] = useState<ReviewerSummary | null>(null)
  const [resumeCtx, setResumeCtx] = useState<ReviewerResumeContext | null>(null)
  const [err, setErr] = useState<string | null>(null)

  const green = isGreenRouting(routingClassification)

  const runGenerate = useCallback(async () => {
    if (green) return
    setErr(null)
    setLoading(true)
    try {
      const res = await postReviewerSummary(decisionId, jd.trim() || undefined)
      if (!res.ok) {
        setSummary(null)
        setResumeCtx(null)
        setErr(res.error || 'Unable to generate summary.')
        return
      }
      setSummary(res.summary ?? null)
      setResumeCtx(res.resume_context ?? null)
    } catch (e) {
      setSummary(null)
      setResumeCtx(null)
      setErr(e instanceof Error ? e.message : 'Request failed.')
    } finally {
      setLoading(false)
    }
  }, [decisionId, jd, green])

  const handleCollapsedPrimary = () => {
    if (green) return
    setExpanded(true)
    if (!summary && !loading) void runGenerate()
  }

  const handleCollapsedRegenerate = () => {
    if (green) return
    setExpanded(true)
    void runGenerate()
  }

  const handleCollapse = () => {
    setExpanded(false)
  }

  return (
    <div
      data-ai-review-card
      data-decision-id={decisionId}
      style={panelStyle}
      className="mt-4 overflow-hidden"
    >
      {/* ——— Collapsed row: always-visible CTA per candidate ——— */}
      {!expanded && (
        <div className="px-4 py-3 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <Sparkles size={16} style={{ color: '#7C3AED', flexShrink: 0 }} />
              <span className="font-sans font-semibold text-sm" style={{ color: '#0D0D0D' }}>
                AI Technical Review
              </span>
              <span className="font-mono text-[10px] hidden sm:inline" style={{ color: '#9B9B9B' }}>
                {decisionId.slice(0, 8)}…
              </span>
            </div>
            <p className="font-sans text-[11px] mt-1 leading-snug" style={{ color: '#6B6B6B' }}>
              Advisory narrative only — does not change routing or policy. On-demand per candidate.
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2 shrink-0">
            {green ? (
              <span className="font-sans text-xs px-3 py-2 rounded-md" style={{ color: '#9B9B9B', border: '1px solid #E4E2DC' }}>
                Not available for GREEN routing
              </span>
            ) : (
              <>
                <button
                  type="button"
                  disabled={loading}
                  onClick={() => void handleCollapsedPrimary()}
                  className="inline-flex items-center justify-center gap-2 font-sans text-sm font-semibold px-4 py-2.5 rounded-lg shadow-sm transition-opacity hover:opacity-92"
                  style={{
                    backgroundColor: '#7C3AED',
                    color: '#FFFFFF',
                    border: 'none',
                    cursor: loading ? 'wait' : 'pointer',
                    minWidth: '180px',
                  }}
                >
                  {loading ? <Loader2 size={16} className="animate-spin" /> : <Sparkles size={16} />}
                  {loading ? 'Generating…' : summary ? 'View AI review' : 'Evaluate with AI'}
                </button>
                {summary && !loading && (
                  <button
                    type="button"
                    onClick={() => void handleCollapsedRegenerate()}
                    className="inline-flex items-center gap-2 font-sans text-xs font-semibold px-3 py-2 rounded-lg transition-opacity hover:opacity-90"
                    style={{
                      backgroundColor: '#FFFFFF',
                      color: '#7C3AED',
                      border: '1px solid #7C3AED',
                      cursor: 'pointer',
                    }}
                  >
                    <RefreshCw size={14} />
                    Regenerate
                  </button>
                )}
              </>
            )}
          </div>
        </div>
      )}

      {/* ——— Expanded: detail + toolbar ——— */}
      {expanded && (
        <div style={{ borderTop: '1px solid #E4E2DC' }}>
          <div
            className="px-4 py-3 flex flex-wrap items-center justify-between gap-2"
            style={{ backgroundColor: '#EFECE7' }}
          >
            <div className="flex items-center gap-2 min-w-0">
              <Sparkles size={16} style={{ color: '#7C3AED', flexShrink: 0 }} />
              <span className="font-sans font-semibold text-sm truncate" style={{ color: '#0D0D0D' }}>
                AI Technical Review
              </span>
              <span className="font-mono text-[10px] truncate" style={{ color: '#9B9B9B' }} title={decisionId}>
                {decisionId}
              </span>
            </div>
            <div className="flex flex-wrap gap-2">
              <button
                type="button"
                disabled={loading || green}
                onClick={() => void runGenerate()}
                className="inline-flex items-center gap-1.5 font-sans text-xs font-semibold px-3 py-2 rounded-md transition-opacity hover:opacity-90"
                style={{
                  backgroundColor: '#7C3AED',
                  color: '#FFFFFF',
                  border: 'none',
                  cursor: loading || green ? 'wait' : 'pointer',
                }}
              >
                {loading ? <Loader2 size={14} className="animate-spin" /> : <RefreshCw size={14} />}
                {loading ? 'Generating…' : 'Refresh AI review'}
              </button>
              <button
                type="button"
                disabled={loading}
                onClick={handleCollapse}
                className="inline-flex items-center gap-1.5 font-sans text-xs font-semibold px-3 py-2 rounded-md transition-opacity hover:opacity-90"
                style={{
                  backgroundColor: '#FFFFFF',
                  color: '#0D0D0D',
                  border: '1px solid #E4E2DC',
                  cursor: 'pointer',
                }}
              >
                <ChevronUp size={14} />
                Collapse
              </button>
            </div>
          </div>

          <div className="px-4 pb-4 pt-3">
            {green ? (
              <p className="font-sans text-xs" style={{ color: '#9B9B9B' }}>
                Not available for GREEN routing (lightweight path).
              </p>
            ) : (
              <>
                <label className="block font-sans text-[11px] font-medium uppercase tracking-wide" style={{ color: '#6B6B6B' }}>
                  Job description excerpt (optional)
                </label>
                <textarea
                  className="mt-1 w-full font-sans text-xs p-2 rounded-md"
                  style={{ border: '1px solid #E4E2DC', backgroundColor: '#FFFFFF', minHeight: '72px', resize: 'vertical' }}
                  placeholder="Paste role summary for stronger alignment (not stored on artifact)."
                  value={jd}
                  disabled={loading}
                  onChange={(e) => setJd(e.target.value)}
                />
                <p className="font-sans text-[11px] mt-2 font-mono" style={{ color: '#9B9B9B' }}>
                  POST /reviewer-summary/{decisionId.slice(0, 8)}…
                </p>
              </>
            )}

            {loading && (
              <div
                className="mt-4 flex items-center gap-3 p-4 rounded-lg"
                style={{ backgroundColor: '#FFFFFF', border: '1px dashed #C4B8A8' }}
              >
                <Loader2 size={22} className="animate-spin" style={{ color: '#7C3AED' }} />
                <div>
                  <p className="font-sans font-semibold text-sm" style={{ color: '#0D0D0D' }}>
                    Reading résumé & generating AI review…
                  </p>
                  <p className="font-sans text-xs mt-0.5" style={{ color: '#6B6B6B' }}>
                    Only this candidate is loading; others stay interactive.
                  </p>
                </div>
              </div>
            )}

            {err && !loading && (
              <p className="font-sans text-xs mt-3" style={{ color: '#B91C1C' }}>
                {err}
              </p>
            )}

            {summary && !loading && (
              <div className="mt-4 p-4 rounded-lg" style={{ backgroundColor: '#FFFFFF', border: '1px solid #E4E2DC' }}>
                {resumeCtx && !resumeCtx.resume_grounded && (
                  <div
                    className="mb-4 p-3 rounded-md font-sans text-xs leading-relaxed"
                    style={{ backgroundColor: '#FFFBEB', border: '1px solid #FCD34D', color: '#78350F' }}
                  >
                    Résumé text was not loaded from storage (e.g. pre-Supabase decision or missing upload). The overview
                    below may be limited — paste a JD above and treat technical claims cautiously.
                  </div>
                )}
                {resumeCtx?.resume_grounded && (
                  <p className="font-sans text-[11px] mb-4 font-mono" style={{ color: '#15803D' }}>
                    Grounded in résumé excerpt ({resumeCtx.resume_chars_used.toLocaleString()} chars
                    {resumeCtx.resume_source ? ` · ${resumeCtx.resume_source}` : ''})
                  </p>
                )}
                <Section label="👤 Candidate overview">{summary.candidate_overview}</Section>
                <Section label="🛠 Technical skills & stack">{summary.technical_skills_stack}</Section>
                <Section label="📁 Projects & experience">{summary.projects_and_experience}</Section>
                <Section label="🎯 Job alignment">{summary.job_alignment}</Section>
                <BulletList title="⚠ Skill gaps / concerns" items={summary.skill_gaps_concerns} accent="#B45309" />
                <Section label="🧠 Technical opinion">{summary.technical_opinion}</Section>
                <div className="mt-4 p-3 rounded-md" style={{ backgroundColor: '#F7F6F3' }}>
                  <p className="font-sans font-semibold text-xs" style={{ color: '#7C3AED' }}>
                    Suggested reviewer action
                  </p>
                  <p className="font-sans text-sm mt-1" style={{ color: '#0D0D0D' }}>
                    {summary.suggested_action}
                  </p>
                </div>
                <div
                  className="mt-4 p-3 rounded-md"
                  style={{ backgroundColor: '#F0F0ED', border: '1px solid #E4E2DC' }}
                >
                  <p className="font-sans font-semibold text-xs" style={{ color: '#6B6B6B' }}>
                    🛡 Governance notes (secondary)
                  </p>
                  <p className="font-sans text-xs mt-2 leading-relaxed" style={{ color: '#4B5563' }}>
                    {summary.governance_notes}
                  </p>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

function Section({ label, children }: { label: string; children: string }) {
  if (!children?.trim()) return null
  return (
    <div className="mt-3 first:mt-0">
      <p className="font-sans font-semibold text-xs" style={{ color: '#7C3AED' }}>
        {label}
      </p>
      <p className="font-sans text-sm mt-1 leading-relaxed" style={{ color: '#1a1a1a' }}>
        {children}
      </p>
    </div>
  )
}
