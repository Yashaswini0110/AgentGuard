import { useEffect, useState } from 'react'
import { fetchResumeUrl } from '@/lib/api'

interface Props {
  decisionId: string
  candidateName?: string
  onClose: () => void
}

/**
 * Full-screen modal that renders the candidate's resume inline using the
 * Supabase signed URL returned by GET /resumes/{decision_id}/url.
 *
 * The PDF is loaded directly from Supabase Storage (Content-Disposition:
 * inline) — FastAPI never streams the bytes, so this stays fast even on
 * the free tier.
 */
export function ResumeViewer({ decisionId, candidateName, onClose }: Props) {
  const [url, setUrl] = useState<string | null>(null)
  const [filename, setFilename] = useState<string>('')
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState<boolean>(true)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError(null)
    setUrl(null)

    fetchResumeUrl(decisionId)
      .then((info) => {
        if (cancelled) return
        setUrl(info.url)
        setFilename(info.original_name || 'resume.pdf')
      })
      .catch((e: unknown) => {
        if (cancelled) return
        setError(e instanceof Error ? e.message : 'Failed to load resume')
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })

    return () => {
      cancelled = true
    }
  }, [decisionId])

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])

  return (
    <div
      onClick={onClose}
      style={{
        position: 'fixed',
        inset: 0,
        zIndex: 50,
        backgroundColor: 'rgba(0, 0, 0, 0.65)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '24px',
      }}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        style={{
          width: '90vw',
          maxWidth: '1100px',
          height: '90vh',
          backgroundColor: '#FFFFFF',
          borderRadius: '12px',
          overflow: 'hidden',
          boxShadow: '0 20px 60px rgba(0,0,0,0.35)',
          display: 'flex',
          flexDirection: 'column',
        }}
      >
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            padding: '12px 16px',
            borderBottom: '1px solid #E4E2DC',
            backgroundColor: '#F7F6F3',
          }}
        >
          <div style={{ display: 'flex', flexDirection: 'column', minWidth: 0 }}>
            <span
              className="font-sans font-medium text-sm"
              style={{
                color: '#0D0D0D',
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                whiteSpace: 'nowrap',
              }}
            >
              {candidateName ? `${candidateName} · ` : ''}
              {loading ? 'Loading resume…' : filename || 'Candidate resume'}
            </span>
            <span className="font-mono text-[11px]" style={{ color: '#9B9B9B' }}>
              decision_id: {decisionId}
            </span>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="font-sans text-xs font-medium px-3 py-1.5 rounded-md"
            style={{
              border: '1px solid #E4E2DC',
              backgroundColor: '#FFFFFF',
              color: '#0D0D0D',
              cursor: 'pointer',
            }}
          >
            Close (Esc)
          </button>
        </div>

        <div style={{ flex: 1, position: 'relative', backgroundColor: '#F1EFE9' }}>
          {loading && (
            <div
              className="font-sans text-sm"
              style={{
                position: 'absolute',
                inset: 0,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: '#6B6B6B',
              }}
            >
              Generating signed URL…
            </div>
          )}
          {error && !loading && (
            <div
              className="font-sans text-sm"
              style={{
                position: 'absolute',
                inset: 0,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: '#B91C1C',
                padding: '24px',
                textAlign: 'center',
              }}
            >
              {error}
            </div>
          )}
          {url && !error && (
            <iframe
              src={url}
              title="Candidate resume"
              style={{ width: '100%', height: '100%', border: 'none' }}
            />
          )}
        </div>
      </div>
    </div>
  )
}
