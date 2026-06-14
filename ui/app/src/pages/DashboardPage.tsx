import { useCallback, useEffect, useRef, useState } from 'react'
import { Link } from 'react-router'
import { ArrowRight } from 'lucide-react'
import AppShell from '@/components/AppShell'
import { StatusDot } from '@/components/StatusDot'
import { apiBase, fetchDrift, fetchDriftStatus, fetchHealth, fetchRecentArtifacts } from '@/lib/api'
import type { DriftStatus } from '@/lib/api'
import {
  dashboardRowStatus,
  formatArtifactTime,
  shortHash,
} from '@/lib/artifactHelpers'
import type { AgentGuardArtifact } from '@/types/agentguard'

function StatusBadge({ status }: { status: 'APPROVED' | 'REVIEW' | 'BLOCKED' | 'OPEN' | 'RESOLVED' }) {
  const map: Record<string, { color: 'green' | 'amber' | 'red' | 'purple'; text: string }> = {
    APPROVED: { color: 'green', text: 'APPROVED' },
    REVIEW: { color: 'amber', text: 'REVIEW' },
    BLOCKED: { color: 'red', text: 'BLOCKED' },
    OPEN: { color: 'red', text: 'OPEN' },
    RESOLVED: { color: 'green', text: 'RESOLVED' },
  }
  const { color, text } = map[status]
  return <StatusDot color={color} label={text} />
}

export default function DashboardPage() {
  const [healthOk, setHealthOk] = useState<boolean | null>(null)
  const [version, setVersion] = useState<string>('—')
  const [drift, setDrift] = useState<{
    green_pct: number
    yellow_pct: number
    red_pct: number
    total: number
    alert?: boolean
  } | null>(null)
  const [driftStatus, setDriftStatus] = useState<DriftStatus | null>(null)
  const [artifacts, setArtifacts] = useState<AgentGuardArtifact[]>([])
  const [loadError, setLoadError] = useState<string | null>(null)
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const refreshDriftStatus = useCallback(async () => {
    try {
      const ds = await fetchDriftStatus()
      setDriftStatus(ds)
    } catch {
      // non-fatal — banner stays hidden if endpoint unreachable
    }
  }, [])

  const refresh = useCallback(async () => {
    setLoadError(null)
    try {
      const [h, d, arts] = await Promise.all([
        fetchHealth().catch(() => null),
        fetchDrift(),
        fetchRecentArtifacts(48),
      ])
      if (h) {
        setHealthOk(true)
        setVersion(h.version ?? '3.x')
      } else {
        setHealthOk(false)
      }
      setDrift({
        green_pct: Number(d.green_pct ?? 0),
        yellow_pct: Number(d.yellow_pct ?? 0),
        red_pct: Number(d.red_pct ?? 0),
        total: Number(d.total ?? d.artifacts_analysed ?? 0),
        alert: Boolean(d.alert),
      })
      setArtifacts(arts)
    } catch (e) {
      setHealthOk(false)
      setLoadError(e instanceof Error ? e.message : 'Failed to load dashboard')
    }
  }, [])

  useEffect(() => {
    const init = async () => {
      await refresh()
      await refreshDriftStatus()
    }
    void init()
    pollRef.current = setInterval(() => void refreshDriftStatus(), 30_000)
    return () => {
      if (pollRef.current !== null) clearInterval(pollRef.current)
    }
  }, [refresh, refreshDriftStatus])

  const recentSlice = artifacts.slice(0, 12)
  const policyPassPct =
    artifacts.length === 0
      ? 100
      : Math.round(
          (artifacts.filter((a) => a.policy_result === 'PASS').length / artifacts.length) * 100
        )

  const blockedCount = artifacts.filter(
    (a) => a.policy_result === 'BLOCK' || a.routing_classification === 'RED'
  ).length
  const reviewCount = artifacts.filter((a) => a.routing_classification === 'YELLOW').length

  const incidents = artifacts
    .filter((a) => a.servicenow_ticket_id)
    .slice(0, 12)
    .map((a) => ({
      id: a.servicenow_ticket_id as string,
      status: 'OPEN' as const,
      candidate: a.candidate_name ?? a.candidate_id ?? 'Unknown',
      time: formatArtifactTime(a.timestamp),
    }))

  return (
    <AppShell>
      <div className="flex items-center justify-between mb-7">
        <div>
          <h1 className="font-sans font-semibold" style={{ fontSize: '22px', color: '#0D0D0D' }}>
            Dashboard
          </h1>
          <p className="font-sans text-sm mt-1" style={{ color: '#6B6B6B' }}>
            Live data from{' '}
            <span className="font-mono text-xs">{apiBase()}</span>
            {' · '}
            {healthOk === null && 'Connecting…'}
            {healthOk === true && (
              <>
                API <span style={{ color: '#15803D' }}>ok</span> v{version}
              </>
            )}
            {healthOk === false && (
              <>
                API <span style={{ color: '#B91C1C' }}>unreachable</span>
              </>
            )}
          </p>
          {loadError && (
            <p className="font-sans text-xs mt-2" style={{ color: '#B91C1C' }}>
              {loadError}
            </p>
          )}
        </div>
        <Link
          to="/run"
          className="inline-flex items-center gap-1 font-sans text-sm font-medium px-4 py-2 rounded-md transition-opacity hover:opacity-90"
          style={{ backgroundColor: '#0D6EFD', color: '#FFFFFF', textDecoration: 'none' }}
        >
          Run pipeline <ArrowRight size={14} />
        </Link>
      </div>

      {/* Drift alert banner — only visible when is_drifting */}
      {driftStatus?.is_drifting && (
        <div
          className="flex items-start gap-3 px-4 py-3 rounded-lg mb-5 font-sans text-sm"
          style={{
            backgroundColor: '#FEF3C7',
            border: '1px solid #FCD34D',
            color: '#92400E',
          }}
        >
          <span style={{ fontSize: '16px', lineHeight: '1.4' }}>⚠</span>
          <div>
            <span className="font-semibold">Drift alert — RED rate elevated</span>
            <span style={{ marginLeft: '8px' }}>
              {(driftStatus.current_red_rate * 100).toFixed(1)}% current vs {(driftStatus.baseline_red_rate * 100).toFixed(1)}% baseline
              {' · '}
              {driftStatus.days_exceeded} of {driftStatus.days_required} consecutive days exceeded threshold
              {' · '}
              {driftStatus.total_decisions} decisions in {driftStatus.window_days}-day window
            </span>
          </div>
        </div>
      )}

      {/* Stat row */}
      <div className="flex" style={{ borderBottom: '1px solid #E4E2DC', paddingBottom: '28px' }}>
        {[
          {
            value: String(driftStatus?.total_decisions ?? drift?.total ?? artifacts.length),
            label: 'Decisions in window',
            delta: driftStatus?.is_drifting
              ? `Drift alert — ${driftStatus.days_exceeded}/${driftStatus.days_required} days RED > threshold`
              : drift?.alert
                ? 'Drift alert: RED >20%'
                : 'From /drift/status · 7-day window',
            deltaColor: (driftStatus?.is_drifting || drift?.alert) ? '#B91C1C' : '#6B6B6B',
          },
          {
            value: String(blockedCount),
            label: 'Blocked / RED',
            delta: `${artifacts.length ? Math.round((blockedCount / artifacts.length) * 100) : 0}% of loaded batch`,
            deltaColor: '#6B6B6B',
          },
          {
            value: String(reviewCount),
            label: 'YELLOW (review)',
            delta: `${artifacts.length ? Math.round((reviewCount / artifacts.length) * 100) : 0}% of loaded batch`,
            deltaColor: '#6B6B6B',
          },
          {
            value: '~50ms',
            label: 'Router target',
            delta: `${policyPassPct}% policy pass (${artifacts.length || 0} loaded)`,
            deltaColor: '#15803D',
          },
        ].map((stat, i) => (
          <div key={stat.label} className="flex items-center">
            <div className="px-8">
              <div className="font-sans font-semibold" style={{ fontSize: '36px', color: '#0D0D0D' }}>
                {stat.value}
              </div>
              <div
                className="font-sans text-xs uppercase mt-1"
                style={{ color: '#6B6B6B', letterSpacing: '0.06em' }}
              >
                {stat.label}
              </div>
              <div className="font-sans text-xs mt-1" style={{ color: stat.deltaColor }}>
                {stat.delta}
              </div>
            </div>
            {i < 3 && <div style={{ width: '1px', height: '40px', backgroundColor: '#E4E2DC' }} />}
          </div>
        ))}
      </div>

      {/* Pipeline panel */}
      <div
        className="mt-7"
        style={{
          backgroundColor: '#FFFFFF',
          border: '1px solid #E4E2DC',
          borderRadius: '8px',
          padding: '20px',
        }}
      >
        <h2 className="font-sans font-semibold text-[15px]" style={{ color: '#0D0D0D' }}>
          Decision Pipeline
        </h2>
        <p className="font-sans text-xs mt-1" style={{ color: '#9B9B9B' }}>
          Routing mix from GET /drift (last artefacts on disk)
          {(driftStatus?.is_drifting || drift?.alert) ? ' · ⚠ Elevated RED share' : ''}
          {driftStatus && (
            <span style={{ marginLeft: '8px', color: driftStatus.is_drifting ? '#B91C1C' : '#15803D' }}>
              · 7d RED rate: {(driftStatus.current_red_rate * 100).toFixed(1)}% (baseline {(driftStatus.baseline_red_rate * 100).toFixed(1)}%)
            </span>
          )}
        </p>

        <div className="flex items-center gap-4 mt-5">
          <div
            className="flex-1"
            style={{ border: '1px solid #E4E2DC', borderRadius: '12px', padding: '16px 20px' }}
          >
            <p className="font-mono text-xs uppercase" style={{ color: '#9B9B9B' }}>
              POLICY ENGINE
            </p>
            <p className="font-sans font-semibold text-xl mt-2" style={{ color: '#0D0D0D' }}>
              &lt; 5ms · {policyPassPct}% pass
            </p>
            <p className="font-sans text-xs mt-1" style={{ color: '#6B6B6B' }}>
              Loaded batch: PASS vs BLOCK artefacts
            </p>
          </div>
          <span className="font-mono text-lg" style={{ color: '#9B9B9B' }}>
            →
          </span>
          <div
            className="flex-1"
            style={{ border: '1px solid #E4E2DC', borderRadius: '12px', padding: '16px 20px' }}
          >
            <p className="font-mono text-xs uppercase" style={{ color: '#9B9B9B' }}>
              RISK ROUTER
            </p>
            <p className="font-sans font-semibold text-xl mt-2" style={{ color: '#0D0D0D' }}>
              sklearn · SHAP
            </p>
            <p className="font-sans text-xs mt-1" style={{ color: '#6B6B6B' }}>
              Live model from artifacts/
            </p>
          </div>
          <span className="font-mono text-lg" style={{ color: '#9B9B9B' }}>
            →
          </span>
          <div
            className="flex-1"
            style={{ border: '1px solid #E4E2DC', borderRadius: '12px', padding: '16px 20px' }}
          >
            <p className="font-mono text-xs uppercase" style={{ color: '#9B9B9B' }}>
              EXECUTION
            </p>
            <div className="flex flex-col gap-1 mt-2">
              <div className="flex items-center gap-2">
                <div style={{ width: '8px', height: '8px', borderRadius: '2px', backgroundColor: '#15803D' }} />
                <span className="font-sans text-sm" style={{ color: '#15803D' }}>
                  GREEN · {drift?.green_pct ?? 0}%
                </span>
              </div>
              <div className="flex items-center gap-2">
                <div style={{ width: '8px', height: '8px', borderRadius: '2px', backgroundColor: '#B45309' }} />
                <span className="font-sans text-sm" style={{ color: '#B45309' }}>
                  YELLOW · {drift?.yellow_pct ?? 0}%
                </span>
              </div>
              <div className="flex items-center gap-2">
                <div style={{ width: '8px', height: '8px', borderRadius: '2px', backgroundColor: '#B91C1C' }} />
                <span className="font-sans text-sm" style={{ color: '#B91C1C' }}>
                  RED · {drift?.red_pct ?? 0}%
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Recent Decisions */}
      <div
        className="mt-7"
        style={{ backgroundColor: '#FFFFFF', border: '1px solid #E4E2DC', borderRadius: '8px' }}
      >
        <div className="flex items-center justify-between px-5 py-4">
          <h2 className="font-sans font-semibold text-[15px]" style={{ color: '#0D0D0D' }}>
            Recent Decisions
          </h2>
          <button
            type="button"
            onClick={() => void refresh()}
            className="font-sans text-sm font-medium"
            style={{ color: '#0D6EFD', background: 'none', border: 'none', cursor: 'pointer' }}
          >
            Refresh
          </button>
        </div>
        <table className="w-full">
          <thead>
            <tr style={{ backgroundColor: '#F7F6F3' }}>
              {['STATUS', 'CANDIDATE', 'POLICY RESULT', 'CONFIDENCE', 'ROUTING', 'TIMESTAMP'].map((h) => (
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
            {recentSlice.length === 0 && (
              <tr>
                <td colSpan={6} className="px-5 py-8 font-sans text-sm text-center" style={{ color: '#9B9B9B' }}>
                  No artifacts yet. Run the pipeline once to populate{' '}
                  <span className="font-mono">artifacts/</span>.
                </td>
              </tr>
            )}
            {recentSlice.map((row) => {
              const st = dashboardRowStatus(row)
              const conf = row.confidence_score
              const pol =
                row.policy_result === 'BLOCK'
                  ? `BLOCK · ${row.policy_rule_cited ?? 'RULE'}`
                  : 'PASS'
              return (
                <tr key={row.decision_id} style={{ borderTop: '1px solid #E4E2DC' }}>
                  <td className="px-5 py-3">
                    <StatusBadge status={st === 'BLOCKED' ? 'BLOCKED' : st === 'REVIEW' ? 'REVIEW' : 'APPROVED'} />
                  </td>
                  <td className="px-5 py-3 font-sans font-medium text-sm" style={{ color: '#0D0D0D' }}>
                    {row.candidate_name ?? row.candidate_id ?? 'Unknown'}
                  </td>
                  <td
                    className="px-5 py-3 font-mono text-xs"
                    style={{ color: row.policy_result === 'PASS' ? '#15803D' : '#B91C1C' }}
                  >
                    {pol}
                  </td>
                  <td className="px-5 py-3 font-mono text-xs" style={{ color: '#6B6B6B' }}>
                    {typeof conf === 'number' ? conf.toFixed(2) : '—'}
                  </td>
                  <td className="px-5 py-3 font-mono text-xs" style={{ color: '#6B6B6B' }}>
                    {row.routing_classification ?? '—'}
                  </td>
                  <td className="px-5 py-3 font-sans text-xs" style={{ color: '#9B9B9B' }}>
                    {formatArtifactTime(row.timestamp)}
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>

      {/* ServiceNow */}
      <div
        className="mt-5"
        style={{ backgroundColor: '#FFFFFF', border: '1px solid #E4E2DC', borderRadius: '8px' }}
      >
        <div className="flex items-center justify-between px-5 py-4">
          <h2 className="font-sans font-semibold text-[15px]" style={{ color: '#0D0D0D' }}>
            ServiceNow Incidents (from artifacts)
          </h2>
          <div className="flex items-center gap-2">
            <div style={{ width: '8px', height: '8px', borderRadius: '2px', backgroundColor: '#B91C1C' }} />
            <span className="font-sans text-sm font-semibold" style={{ color: '#B91C1C' }}>
              {incidents.length} recorded
            </span>
          </div>
        </div>
        <table className="w-full">
          <thead>
            <tr style={{ backgroundColor: '#F7F6F3' }}>
              {['INC ID', 'STATUS', 'CANDIDATE', 'CREATED'].map((h) => (
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
            {incidents.length === 0 ? (
              <tr>
                <td colSpan={4} className="px-5 py-6 font-sans text-sm text-center" style={{ color: '#9B9B9B' }}>
                  No ServiceNow ticket IDs stored on recent artifacts (mock incidents use INC… in development).
                </td>
              </tr>
            ) : (
              incidents.map((inc) => (
                <tr key={inc.id + inc.candidate} style={{ borderTop: '1px solid #E4E2DC' }}>
                  <td className="px-5 py-3 font-mono text-xs" style={{ color: '#0D0D0D' }}>
                    {inc.id}
                  </td>
                  <td className="px-5 py-3">
                    <StatusBadge status={inc.status} />
                  </td>
                  <td className="px-5 py-3 font-sans text-sm" style={{ color: '#0D0D0D' }}>
                    {inc.candidate}
                  </td>
                  <td className="px-5 py-3 font-sans text-xs" style={{ color: '#9B9B9B' }}>
                    {inc.time}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      <div className="mt-8 font-mono text-[11px]" style={{ color: '#9B9B9B' }}>
        Tip: Artifact hashes are abbreviated here. Full value:{' '}
        <span style={{ color: '#6B6B6B' }}>{recentSlice[0] ? shortHash(recentSlice[0].artifact_hash, 18, 6) : '—'}</span>
      </div>
    </AppShell>
  )
}
