import { useState } from 'react'
import AppShell from '@/components/AppShell'
import PolicyTable from '@/components/PolicyTable'
import RetrainPanel from '@/components/RetrainPanel'

type Tab = 'policies' | 'retraining'

const TABS: { id: Tab; label: string }[] = [
  { id: 'policies', label: 'Policy Rules' },
  { id: 'retraining', label: 'Model Retraining' },
]

export default function AdminPage() {
  const [tab, setTab] = useState<Tab>('policies')

  return (
    <AppShell>
      <div className="mb-7">
        <h1 className="font-sans font-semibold" style={{ fontSize: '22px', color: '#0D0D0D' }}>
          Admin
        </h1>
        <p className="font-sans text-sm mt-1" style={{ color: '#6B6B6B' }}>
          Governance operations — policy management and model retraining.
        </p>
      </div>

      {/* Tab bar */}
      <div
        className="flex"
        style={{ borderBottom: '1px solid #E4E2DC', marginBottom: '28px' }}
      >
        {TABS.map((t) => (
          <button
            key={t.id}
            type="button"
            onClick={() => setTab(t.id)}
            className="font-sans font-medium text-sm px-4 py-2 transition-colors"
            style={{
              color: tab === t.id ? '#0D0D0D' : '#6B6B6B',
              background: 'none',
              border: 'none',
              borderBottom: tab === t.id ? '2px solid #0D0D0D' : '2px solid transparent',
              cursor: 'pointer',
              marginBottom: '-1px',
            }}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* Panel */}
      <div
        style={{
          backgroundColor: '#FFFFFF',
          border: '1px solid #E4E2DC',
          borderRadius: '8px',
          padding: '24px',
        }}
      >
        {tab === 'policies' && (
          <>
            <div className="mb-5">
              <h2 className="font-sans font-semibold text-[15px]" style={{ color: '#0D0D0D' }}>
                Policy Rules
              </h2>
              <p className="font-sans text-xs mt-1" style={{ color: '#9B9B9B' }}>
                Upload a regulation or policy PDF to extract enforceable rules into Supabase.
                Active rules are enforced by Layer 1 in real time — toggles take effect immediately.
                Extracted rules land inactive; activate them after review.
              </p>
            </div>
            <PolicyTable />
          </>
        )}

        {tab === 'retraining' && (
          <>
            <div className="mb-5">
              <h2 className="font-sans font-semibold text-[15px]" style={{ color: '#0D0D0D' }}>
                Model Retraining
              </h2>
              <p className="font-sans text-xs mt-1" style={{ color: '#9B9B9B' }}>
                Retrain the Layer 2 risk router on accumulated decision artifacts + the synthetic baseline.
                The live model is only swapped if the new model matches or beats incumbent accuracy.
              </p>
            </div>
            <RetrainPanel />
          </>
        )}
      </div>
    </AppShell>
  )
}
