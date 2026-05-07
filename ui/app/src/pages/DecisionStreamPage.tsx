import { Link } from 'react-router'
import { useCallback, useEffect, useState } from 'react'
import AppShell from '@/components/AppShell'
import { fetchDecisionStream } from '@/lib/api'
import { formatArtifactTime } from '@/lib/artifactHelpers'
import type { AgentGuardArtifact } from '@/types/agentguard'

export default function DecisionStreamPage() {
  const [rows, setRows] = useState<AgentGuardArtifact[]>([])
  const [err, setErr] = useState<string | null>(null)
  const [offset, setOffset] = useState(0)

  const load = useCallback(async (next: number) => {
    setErr(null)
    try {
      const data = await fetchDecisionStream(30, next)
      setRows(data.artifacts)
      setOffset(next)
    } catch (e) {
      setErr(e instanceof Error ? e.message : 'Failed')
    }
  }, [])

  useEffect(() => {
    void load(0)
  }, [load])

  return (
    <AppShell>
      <div className="flex items-center justify-between mb-7">
        <div>
          <h1 className="font-sans font-semibold" style={{ fontSize: '22px', color: '#0D0D0D' }}>
            Decision stream
          </h1>
          <p className="font-sans text-sm mt-1" style={{ color: '#6B6B6B' }}>
            Paginated evaluations from <span className="font-mono text-xs">GET /v2/decisions/stream</span>. Click a row
            to investigate.
          </p>
          {err && (
            <p className="font-sans text-xs mt-2" style={{ color: '#B91C1C' }}>
              {err}
            </p>
          )}
        </div>
        <button
          type="button"
          className="font-sans text-sm"
          style={{ color: '#0D6EFD', background: 'none', border: 'none', cursor: 'pointer' }}
          onClick={() => void load(offset)}
        >
          Refresh
        </button>
      </div>

      <div style={{ backgroundColor: '#FFFFFF', border: '1px solid #E4E2DC', borderRadius: '8px' }}>
        <table className="w-full">
          <thead>
            <tr style={{ backgroundColor: '#F7F6F3' }}>
              {['TRACE', 'ROUTING', 'POLICY', 'SUBJECT', 'TIME'].map((h) => (
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
            {rows.length === 0 && (
              <tr>
                <td colSpan={5} className="px-5 py-8 text-center font-sans text-sm" style={{ color: '#9B9B9B' }}>
                  No artifacts yet — run Scenario lab to enqueue a governed decision.
                </td>
              </tr>
            )}
            {rows.map((row) => (
              <tr key={row.decision_id} style={{ borderTop: '1px solid #E4E2DC' }}>
                <td className="px-5 py-3 font-mono text-xs">
                  <Link to={`/investigate/${row.decision_id}`} style={{ color: '#0D6EFD', textDecoration: 'none' }}>
                    {(row as AgentGuardArtifact & { trace_id?: string }).trace_id ?? row.decision_id}
                  </Link>
                </td>
                <td className="px-5 py-3 font-mono text-xs" style={{ color: '#6B6B6B' }}>
                  {row.routing_classification ?? '—'}
                </td>
                <td className="px-5 py-3 font-mono text-xs">{row.policy_result}</td>
                <td className="px-5 py-3 font-sans text-sm">{row.candidate_name ?? row.candidate_id ?? '—'}</td>
                <td className="px-5 py-3 font-sans text-xs" style={{ color: '#9B9B9B' }}>
                  {formatArtifactTime(row.timestamp)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </AppShell>
  )
}
