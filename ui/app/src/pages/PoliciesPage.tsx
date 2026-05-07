import AppShell from '@/components/AppShell'

const RULES = [
  { id: 'EMOTION_SCORE_IN_HIRING_PROHIBITED', reg: 'EU AI Act Art. 5(1)(f)' },
  { id: 'SURNAME_PROXY_CASTE_RELIGION', reg: 'India Constitution Art. 15' },
  { id: 'INSTITUTION_TIER_PROXY_SOCIOECONOMIC', reg: 'India DPDP Act 2023' },
  { id: 'MATERNITY_DISCRIMINATION_PROXY', reg: 'Maternity Benefit Act 1961' },
  { id: 'TRIBAL_IDENTITY_PROXY', reg: 'India Constitution Art. 15' },
  { id: 'PROMPT_INJECTION_DETECTED', reg: 'AgentGuard Security Policy v1.0' },
]

export default function PoliciesPage() {
  return (
    <AppShell>
      <div className="mb-6">
        <h1 className="font-sans font-semibold" style={{ fontSize: '22px', color: '#0D0D0D' }}>
          Published policy catalog
        </h1>
        <p className="font-sans text-sm mt-1" style={{ color: '#6B6B6B' }}>
          Deterministic Layer‑1 rules enforced before risk routing. Mirrors <span className="font-mono text-xs">core/policy_engine.py</span>.
        </p>
      </div>
      <div style={{ backgroundColor: '#FFFFFF', border: '1px solid #E4E2DC', borderRadius: '8px' }}>
        <table className="w-full">
          <thead>
            <tr style={{ backgroundColor: '#F7F6F3' }}>
              {['RULE', 'REGULATION ANCHOR'].map((h) => (
                <th
                  key={h}
                  className="font-sans font-medium text-xs uppercase text-left px-5 py-3"
                  style={{ color: '#6B6B6B' }}
                >
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {RULES.map((r) => (
              <tr key={r.id} style={{ borderTop: '1px solid #E4E2DC' }}>
                <td className="px-5 py-3 font-mono text-xs">{r.id}</td>
                <td className="px-5 py-3 font-sans text-sm" style={{ color: '#6B6B6B' }}>
                  {r.reg}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </AppShell>
  )
}
