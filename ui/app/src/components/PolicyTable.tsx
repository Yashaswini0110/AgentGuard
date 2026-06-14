import { useCallback, useEffect, useState } from 'react'
import { fetchPolicies, patchPolicy } from '@/lib/api'
import type { PolicyRule } from '@/lib/api'
import { useDemoAuth } from '@/contexts/DemoAuthContext'

function SeverityBadge({ severity }: { severity: string | null }) {
  const color = severity === 'RED' ? '#B91C1C' : severity === 'YELLOW' ? '#B45309' : '#6B6B6B'
  return (
    <span
      className="font-mono text-xs px-2 py-0.5 rounded"
      style={{ backgroundColor: `${color}18`, color }}
    >
      {severity ?? '—'}
    </span>
  )
}

function ActiveBadge({ active }: { active: boolean }) {
  return (
    <span
      className="font-sans text-xs px-2 py-0.5 rounded font-medium"
      style={{
        backgroundColor: active ? '#DCFCE7' : '#F3F4F6',
        color: active ? '#15803D' : '#6B6B6B',
      }}
    >
      {active ? 'Active' : 'Inactive'}
    </span>
  )
}

export default function PolicyTable() {
  const { user } = useDemoAuth()
  const [policies, setPolicies] = useState<PolicyRule[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [toggling, setToggling] = useState<Set<string>>(new Set())
  const [toast, setToast] = useState<{ id: string; msg: string; ok: boolean } | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const rows = await fetchPolicies()
      setPolicies(rows)
    } catch (e) {
      const raw = e instanceof Error ? e.message : 'Failed to load policies'
      // Strip JSON body from fetch errors (e.g. "HTTP 404 Not Found — {...}") for cleaner display
      const clean = raw.replace(/\s*—\s*\{.*\}$/, '')
      setError(clean || 'Policies endpoint unreachable — check backend connection')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { void load() }, [load])

  const showToast = (msg: string, ok: boolean) => {
    const id = String(Date.now())
    setToast({ id, msg, ok })
    setTimeout(() => setToast((t) => (t?.id === id ? null : t)), 3500)
  }

  const handleToggle = async (policy: PolicyRule) => {
    const next = !policy.is_active
    setToggling((s) => new Set(s).add(policy.id))
    setPolicies((prev) =>
      prev.map((p) => (p.id === policy.id ? { ...p, is_active: next } : p))
    )
    try {
      const updated = await patchPolicy(policy.id, next, user?.id ?? 'ADMIN-01')
      setPolicies((prev) =>
        prev.map((p) => (p.id === updated.id ? updated : p))
      )
      showToast(
        `${policy.name} ${next ? 'activated' : 'deactivated'}`,
        true
      )
    } catch (e) {
      setPolicies((prev) =>
        prev.map((p) => (p.id === policy.id ? { ...p, is_active: !next } : p))
      )
      const raw = e instanceof Error ? e.message : 'error'
      const clean = raw.replace(/\s*—\s*\{.*\}$/, '')
      showToast(`Failed to update ${policy.name}: ${clean}`, false)
    } finally {
      setToggling((s) => {
        const n = new Set(s)
        n.delete(policy.id)
        return n
      })
    }
  }

  return (
    <div>
      {toast && (
        <div
          className="mb-4 px-4 py-2 rounded font-sans text-sm"
          style={{
            backgroundColor: toast.ok ? '#DCFCE7' : '#FEE2E2',
            color: toast.ok ? '#15803D' : '#B91C1C',
            border: `1px solid ${toast.ok ? '#86EFAC' : '#FCA5A5'}`,
          }}
        >
          {toast.msg}
        </div>
      )}

      <div className="flex items-center justify-between mb-4">
        <p className="font-sans text-sm" style={{ color: '#6B6B6B' }}>
          {policies.length} rule{policies.length !== 1 ? 's' : ''} ·{' '}
          {policies.filter((p) => p.is_active).length} active
        </p>
        <button
          type="button"
          onClick={() => void load()}
          className="font-sans text-sm font-medium"
          style={{ color: '#0D6EFD', background: 'none', border: 'none', cursor: 'pointer' }}
        >
          Refresh
        </button>
      </div>

      {loading && (
        <p className="font-sans text-sm py-8 text-center" style={{ color: '#9B9B9B' }}>
          Loading policies…
        </p>
      )}
      {error && (
        <p className="font-sans text-sm py-4" style={{ color: '#B91C1C' }}>
          {error}
        </p>
      )}

      {!loading && !error && (
        <div style={{ border: '1px solid #E4E2DC', borderRadius: '8px', overflow: 'hidden' }}>
          <table className="w-full">
            <thead>
              <tr style={{ backgroundColor: '#F7F6F3' }}>
                {['Rule Name', 'Severity', 'Source', 'Uploaded By', 'Status', 'Toggle'].map((h) => (
                  <th
                    key={h}
                    className="font-sans font-medium text-xs uppercase text-left px-4 py-3"
                    style={{ color: '#6B6B6B', letterSpacing: '0.06em' }}
                  >
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {policies.length === 0 && (
                <tr>
                  <td
                    colSpan={6}
                    className="px-4 py-8 font-sans text-sm text-center"
                    style={{ color: '#9B9B9B' }}
                  >
                    No policy rules found. Supabase may be unavailable — engine uses hardcoded defaults.
                  </td>
                </tr>
              )}
              {policies.map((p) => (
                <tr
                  key={p.id}
                  style={{
                    borderTop: '1px solid #E4E2DC',
                    opacity: p.is_active ? 1 : 0.55,
                  }}
                >
                  <td className="px-4 py-3 font-mono text-xs" style={{ color: '#0D0D0D' }}>
                    {p.name}
                  </td>
                  <td className="px-4 py-3">
                    <SeverityBadge severity={p.severity} />
                  </td>
                  <td className="px-4 py-3 font-sans text-xs" style={{ color: '#6B6B6B' }}>
                    {p.source ?? '—'}
                  </td>
                  <td className="px-4 py-3 font-sans text-xs" style={{ color: '#6B6B6B' }}>
                    {p.uploaded_by ?? '—'}
                  </td>
                  <td className="px-4 py-3">
                    <ActiveBadge active={p.is_active} />
                  </td>
                  <td className="px-4 py-3">
                    <button
                      type="button"
                      disabled={toggling.has(p.id)}
                      onClick={() => void handleToggle(p)}
                      className="font-sans text-xs px-3 py-1 rounded font-medium transition-opacity"
                      style={{
                        backgroundColor: p.is_active ? '#FEE2E2' : '#DCFCE7',
                        color: p.is_active ? '#B91C1C' : '#15803D',
                        border: 'none',
                        cursor: toggling.has(p.id) ? 'wait' : 'pointer',
                        opacity: toggling.has(p.id) ? 0.6 : 1,
                      }}
                    >
                      {toggling.has(p.id) ? '…' : p.is_active ? 'Deactivate' : 'Activate'}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
