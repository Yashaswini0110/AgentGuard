import { NavLink, useLocation } from 'react-router'
import { Shield } from 'lucide-react'

const navLinks = [
  { to: '/dashboard', label: 'Dashboard' },
  { to: '/run', label: 'Run pipeline' },
  { to: '/review', label: 'Review Queue' },
  { to: '/tech-review', label: 'Tech Review' },
  { to: '/shortlist', label: 'Shortlist & Email' },
]

export default function AppShell({ children }: { children: React.ReactNode }) {
  const location = useLocation()
  const isActive = (path: string) => location.pathname === path

  return (
    <div className="min-h-screen bg-ag-bg" style={{ backgroundColor: '#F7F6F3' }}>
      {/* Top navigation bar */}
      <header
        className="sticky top-0 z-50 flex items-center justify-between px-6"
        style={{
          height: '52px',
          backgroundColor: '#FFFFFF',
          borderBottom: '1px solid #E4E2DC',
        }}
      >
        {/* Left: Logo */}
        <div className="flex items-center gap-2">
          <Shield size={16} color="#0D6EFD" />
          <span className="font-sans font-semibold text-sm" style={{ color: '#0D0D0D' }}>
            AgentGuard
          </span>
          <span className="font-mono text-[11px]" style={{ color: '#9B9B9B' }}>
            v3
          </span>
        </div>

        {/* Center: Navigation */}
        <nav className="flex items-center h-full">
          {navLinks.map((link, i) => (
            <div key={link.to} className="flex items-center h-full">
              {i === 1 && (
                <div
                  className="mx-4"
                  style={{ width: '1px', height: '16px', backgroundColor: '#E4E2DC' }}
                />
              )}
              <NavLink
                to={link.to}
                className="flex items-center h-full px-3 font-sans font-medium text-sm transition-colors"
                style={{
                  color: isActive(link.to) ? '#0D0D0D' : '#6B6B6B',
                  borderBottom: isActive(link.to) ? '2px solid #0D0D0D' : '2px solid transparent',
                  textDecoration: 'none',
                }}
              >
                {link.label}
              </NavLink>
            </div>
          ))}
        </nav>

        {/* Right: User */}
        <div className="flex items-center gap-3">
          <span className="font-sans text-xs" style={{ color: '#6B6B6B' }}>
            HR Compliance Officer
          </span>
          <div
            className="flex items-center justify-center rounded-full font-sans font-semibold text-xs"
            style={{
              width: '28px',
              height: '28px',
              backgroundColor: '#EFF6FF',
              color: '#0D6EFD',
            }}
          >
            HR
          </div>
        </div>
      </header>

      {/* Page content area */}
      <main className="mx-auto px-6" style={{ maxWidth: '1200px', padding: '32px 24px' }}>
        {children}
      </main>
    </div>
  )
}
