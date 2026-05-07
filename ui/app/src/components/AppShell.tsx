import { NavLink, useLocation } from 'react-router'
import { Shield } from 'lucide-react'

const navLinks = [
  { to: '/mission-control', label: 'Mission control' },
  { to: '/decisions', label: 'Decision stream' },
  { to: '/incidents', label: 'Incident queue' },
  { to: '/policies', label: 'Policies' },
  { to: '/artifacts', label: 'Artifacts' },
  { to: '/agents', label: 'Agents' },
  { to: '/scenario-lab', label: 'Scenario lab' },
]

export default function AppShell({ children }: { children: React.ReactNode }) {
  const location = useLocation()

  return (
    <div className="min-h-screen bg-ag-bg" style={{ backgroundColor: '#F7F6F3' }}>
      <header
        className="sticky top-0 z-50 flex flex-wrap items-center gap-y-2 justify-between px-6 border-b bg-white"
        style={{
          minHeight: '52px',
          borderColor: '#E4E2DC',
        }}
      >
        <div className="flex items-center gap-2 min-w-[140px]">
          <Shield size={16} color="#0D6EFD" />
          <span className="font-sans font-semibold text-sm" style={{ color: '#0D0D0D' }}>
            AgentGuard
          </span>
          <span className="font-mono text-[11px]" style={{ color: '#9B9B9B' }}>
            governance
          </span>
        </div>

        <nav className="flex flex-wrap items-center justify-center gap-x-2 gap-y-1 max-w-[900px]">
          {navLinks.map((link) => {
            const active = location.pathname === link.to || location.pathname.startsWith(link.to + '/')
            return (
              <NavLink
                key={link.to}
                to={link.to}
                className="font-sans font-medium text-xs px-2 py-1.5 rounded transition-colors whitespace-nowrap"
                style={{
                  color: active ? '#0D0D0D' : '#6B6B6B',
                  borderBottom: active ? '2px solid #0D0D0D' : '2px solid transparent',
                  textDecoration: 'none',
                }}
              >
                {link.label}
              </NavLink>
            )
          })}
        </nav>

        <div className="flex items-center gap-3 min-w-[160px] justify-end">
          <span className="font-sans text-xs" style={{ color: '#6B6B6B' }}>
            Governance operator
          </span>
          <div
            className="flex items-center justify-center rounded-full font-sans font-semibold text-[10px] px-2"
            style={{
              minWidth: '28px',
              height: '28px',
              backgroundColor: '#EFF6FF',
              color: '#0D6EFD',
            }}
            title="Demo role — map to SSO group in prod"
          >
            GOV
          </div>
        </div>
      </header>

      <main className="mx-auto px-6" style={{ maxWidth: '1200px', padding: '32px 24px' }}>
        {children}
      </main>
    </div>
  )
}
