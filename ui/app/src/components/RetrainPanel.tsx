import { useCallback, useEffect, useRef, useState } from 'react'
import { fetchDriftStatus, fetchRetrainStatus, postRetrain } from '@/lib/api'
import type { RetrainJobStatus } from '@/lib/api'

function StatusBadge({ status }: { status: RetrainJobStatus['status'] }) {
  const map: Record<RetrainJobStatus['status'], { bg: string; color: string }> = {
    IDLE:    { bg: '#F3F4F6', color: '#6B6B6B' },
    RUNNING: { bg: '#EFF6FF', color: '#0D6EFD' },
    DONE:    { bg: '#DCFCE7', color: '#15803D' },
    FAILED:  { bg: '#FEE2E2', color: '#B91C1C' },
  }
  const { bg, color } = map[status]
  return (
    <span
      className="font-mono text-xs px-2 py-0.5 rounded font-semibold"
      style={{ backgroundColor: bg, color }}
    >
      {status}
    </span>
  )
}

function AccuracyRow({ label, value }: { label: string; value: number | null }) {
  if (value === null) return null
  return (
    <div className="flex items-center justify-between py-1">
      <span className="font-sans text-sm" style={{ color: '#6B6B6B' }}>{label}</span>
      <span className="font-mono text-sm font-semibold" style={{ color: '#0D0D0D' }}>
        {(value * 100).toFixed(1)}%
      </span>
    </div>
  )
}

export default function RetrainPanel() {
  const [modelHash, setModelHash] = useState<string | null>(null)
  const [baselineRed, setBaselineRed] = useState<number | null>(null)
  const [job, setJob] = useState<RetrainJobStatus | null>(null)
  const [starting, setStarting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const stopPoll = useCallback(() => {
    if (pollRef.current !== null) {
      clearInterval(pollRef.current)
      pollRef.current = null
    }
  }, [])

  const pollStatus = useCallback(async () => {
    try {
      const s = await fetchRetrainStatus()
      setJob(s)
      if (s.model_version_hash) setModelHash(s.model_version_hash)
      if (s.status === 'DONE' || s.status === 'FAILED') {
        stopPoll()
      }
    } catch {
      // keep polling on transient errors
    }
  }, [stopPoll])

  useEffect(() => {
    // Load current model info and initial job status on mount
    const init = async () => {
      try {
        const [ds, s] = await Promise.all([
          fetchDriftStatus().catch(() => null),
          fetchRetrainStatus().catch(() => null),
        ])
        if (ds) setBaselineRed(ds.baseline_red_rate)
        if (s) {
          setJob(s)
          if (s.model_version_hash) setModelHash(s.model_version_hash)
          if (s.status === 'RUNNING') {
            pollRef.current = setInterval(() => void pollStatus(), 3_000)
          }
        }
      } catch {
        // non-fatal
      }
    }
    void init()
    return stopPoll
  }, [pollStatus, stopPoll])

  const handleStart = async () => {
    setError(null)
    setStarting(true)
    try {
      await postRetrain()
      // Immediately poll for status
      const s = await fetchRetrainStatus()
      setJob(s)
      stopPoll()
      pollRef.current = setInterval(() => void pollStatus(), 3_000)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to start retraining')
    } finally {
      setStarting(false)
    }
  }

  const isRunning = job?.status === 'RUNNING' || starting

  return (
    <div>
      {/* Current model info */}
      <div
        className="mb-6 p-4 rounded-lg"
        style={{ border: '1px solid #E4E2DC', backgroundColor: '#F7F6F3' }}
      >
        <p className="font-sans font-semibold text-sm mb-3" style={{ color: '#0D0D0D' }}>
          Current Model
        </p>
        <div className="flex items-center justify-between py-1">
          <span className="font-sans text-sm" style={{ color: '#6B6B6B' }}>Baseline RED rate</span>
          <span className="font-mono text-sm font-semibold" style={{ color: '#0D0D0D' }}>
            {baselineRed !== null ? `${(baselineRed * 100).toFixed(1)}%` : '—'}
          </span>
        </div>
        <div className="flex items-center justify-between py-1">
          <span className="font-sans text-sm" style={{ color: '#6B6B6B' }}>Model hash</span>
          <span
            className="font-mono text-xs"
            style={{ color: '#6B6B6B', maxWidth: '240px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}
            title={modelHash ?? undefined}
          >
            {modelHash ?? '—'}
          </span>
        </div>
      </div>

      {/* Start button */}
      <div className="flex items-center gap-4 mb-6">
        <button
          type="button"
          disabled={isRunning}
          onClick={() => void handleStart()}
          className="font-sans text-sm font-semibold px-5 py-2 rounded-md transition-opacity"
          style={{
            backgroundColor: isRunning ? '#9B9B9B' : '#0D6EFD',
            color: '#FFFFFF',
            border: 'none',
            cursor: isRunning ? 'not-allowed' : 'pointer',
            opacity: isRunning ? 0.7 : 1,
          }}
        >
          {starting ? 'Starting…' : isRunning ? 'Retraining…' : 'Start Retraining'}
        </button>
        {job && <StatusBadge status={job.status} />}
        {isRunning && (
          <span className="font-sans text-xs animate-pulse" style={{ color: '#0D6EFD' }}>
            Polling every 3s…
          </span>
        )}
      </div>

      {error && (
        <div
          className="mb-4 px-4 py-2 rounded font-sans text-sm"
          style={{ backgroundColor: '#FEE2E2', color: '#B91C1C', border: '1px solid #FCA5A5' }}
        >
          {error}
        </div>
      )}

      {/* Job result */}
      {job && job.status !== 'IDLE' && (
        <div
          className="p-4 rounded-lg"
          style={{ border: '1px solid #E4E2DC' }}
        >
          <p className="font-sans font-semibold text-sm mb-3" style={{ color: '#0D0D0D' }}>
            Last Job
          </p>
          <AccuracyRow label="Previous accuracy" value={job.old_accuracy} />
          <AccuracyRow label="New accuracy" value={job.new_accuracy} />
          {job.status === 'DONE' && (
            <div className="flex items-center justify-between py-1">
              <span className="font-sans text-sm" style={{ color: '#6B6B6B' }}>Model swapped</span>
              <span
                className="font-mono text-sm font-semibold"
                style={{ color: job.swapped ? '#15803D' : '#B45309' }}
              >
                {job.swapped ? 'Yes — live model updated' : 'No — incumbent retained'}
              </span>
            </div>
          )}
          {job.message && (
            <p
              className="font-sans text-xs mt-3 pt-3"
              style={{ color: job.status === 'FAILED' ? '#B91C1C' : '#6B6B6B', borderTop: '1px solid #E4E2DC' }}
            >
              {job.message}
            </p>
          )}
          {job.started_at && (
            <p className="font-sans text-xs mt-1" style={{ color: '#9B9B9B' }}>
              Started: {new Date(job.started_at).toLocaleString()}
              {job.finished_at && ` · Finished: ${new Date(job.finished_at).toLocaleString()}`}
            </p>
          )}
        </div>
      )}
    </div>
  )
}
