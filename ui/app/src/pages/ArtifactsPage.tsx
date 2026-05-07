import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router'
import AppShell from '@/components/AppShell'
import { fetchRecentArtifacts } from '@/lib/api'
import { formatArtifactTime, shortHash } from '@/lib/artifactHelpers'
import type { AgentGuardArtifact } from '@/types/agentguard'

export default function ArtifactsPage() {
  const [rows, setRows] = useState<AgentGuardArtifact[]>([])
  const [err, setErr] = useState<string | null>(null)

  const reload = useCallback(async () => {
    setErr(null)
    try {
      const r = await fetchRecentArtifacts(80)
      setRows(r)
    } catch (e) {
      setErr(e instanceof Error ? e.message : 'Failed')
    }
  }, [])

  useEffect(() => {
    void reload()
  }, [reload])

  return (
    <AppShell>
      <div className="flex justify-between items-start mb-6">
        <div>
          <h1 className="font-sans font-semibold" style={{ fontSize: '22px', color: '#0D0D0D' }}>
            Artifacts & audit
          </h1>
          <p className="font-sans text-sm mt-1" style={{ color: '#6B6B6B' }}>
            Immutable envelopes written by the artifact engine (<span className="font-mono text-xs">GET /artifacts/recent</span>
            ).
          </p>
          {err && (
            <p className="text-xs mt-2" style={{ color: '#B91C1C' }}>
              {err}
            </p>
          )}
        </div>
        <button
          type="button"
          style={{ color: '#0D6EFD', background: 'none', border: 'none', cursor: 'pointer' }}
          className="text-sm font-sans"
          onClick={() => void reload()}
        >
          Refresh
        </button>
      </div>
      <div style={{ border: '1px solid #E4E2DC', borderRadius: '8px', overflow: 'hidden' }}>
        <table className="w-full">
          <thead style={{ background: '#F7F6F3' }}>
            <tr>
              <th className="text-left px-4 py-2 font-sans text-xs text-muted-foreground">DECISION</th>
              <th className="text-left px-4 py-2 font-sans text-xs text-muted-foreground">HASH</th>
              <th className="text-left px-4 py-2 font-sans text-xs text-muted-foreground">TIME</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((a) => (
              <tr key={a.decision_id} style={{ borderTop: '1px solid #E4E2DC' }}>
                <td className="px-4 py-2">
                  <Link to={`/investigate/${a.decision_id}`} className="font-mono text-xs" style={{ color: '#0D6EFD' }}>
                    {a.decision_id}
                  </Link>
                </td>
                <td className="px-4 py-2 font-mono text-xs">{shortHash(a.artifact_hash)}</td>
                <td className="px-4 py-2 font-sans text-xs" style={{ color: '#9B9B9B' }}>
                  {formatArtifactTime(a.timestamp)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </AppShell>
  )
}
