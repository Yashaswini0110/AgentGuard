import AppShell from '@/components/AppShell'

export default function AgentsPage() {
  return (
    <AppShell>
      <h1 className="font-sans font-semibold" style={{ fontSize: '22px', color: '#0D0D0D' }}>
        Agents & integrations
      </h1>
      <p className="font-sans text-sm mt-2" style={{ color: '#6B6B6B', maxWidth: '560px' }}>
        Registry placeholder. Each adapter (for example <span className="font-mono text-xs">hiring_demo_v1</span>) declares
        its ingress contract; production systems register webhooks and subject schemas here.
      </p>
      <div className="mt-6 p-4 rounded-md" style={{ border: '1px solid #E4E2DC', background: '#fff' }}>
        <p className="font-mono text-xs">hiring_demo_v1 — active (Scenario Lab)</p>
        <p className="font-mono text-xs mt-2 text-muted-foreground">loan_demo_v1 — planned fixture only</p>
      </div>
    </AppShell>
  )
}
