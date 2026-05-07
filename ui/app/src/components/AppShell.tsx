import { NavLink, useLocation, useNavigate } from 'react-router'
import { Shield, LogOut } from 'lucide-react'
import { useDemoAuth } from '@/contexts/DemoAuthContext'
import type { DemoRole } from '@/lib/demoAuth'

const NAV_HR: { to: string; label: string }[] = [
  { to: '/dashboard', label: 'Dashboard' },
  { to: '/run', label: 'Run pipeline' },
  { to: '/bulk-rank', label: 'Bulk rank' },
  { to: '/review', label: 'Review Queue' },
  { to: '/shortlist', label: 'Shortlist & Email' },
]

const NAV_TECH: { to: string; label: string }[] = [{ to: '/tech-review', label: 'Tech Review' }]

function initials(label: string, role: DemoRole) {
  const parts = label.trim().split(/\s+/)
  if (parts.length >= 2) {
    return (parts[0][0] + parts[1][0]).toUpperCase()
  }
  return role === 'hr' ? 'HR' : 'T'
}

export default function AppShell({ children }: { children: React.ReactNode }) {
  const location = useLocation()
  const navigate = useNavigate()
  const { user, logout } = useDemoAuth()
  const isActive = (path: string) => location.pathname === path

  const navLinks = user?.role === 'tech' ? NAV_TECH : NAV_HR

  const handleLogout = () => {
    logout()
    navigate('/login', { replace: true })
  }

  return (
    <div className="min-h-screen bg-ag-bg" style={{ backgroundColor: '#F7F6F3' }}>
      <header
        className="sticky top-0 z-50 flex items-center justify-between px-6"
        style={{
          height: '52px',
          backgroundColor: '#FFFFFF',
          borderBottom: '1px solid #E4E2DC',
        }}
      >
        <div className="flex items-center gap-2">
          <Shield size={16} color="#0D6EFD" />
          <span className="font-sans font-semibold text-sm" style={{ color: '#0D0D0D' }}>
            AgentGuard
          </span>
          <span className="font-mono text-[11px]" style={{ color: '#9B9B9B' }}>
            v3
          </span>
        </div>

        <nav className="flex items-center h-full">
          {navLinks.map((link, i) => (
            <div key={link.to} className="flex items-center h-full">
              {user?.role === 'hr' && i === 1 && (
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

        <div className="flex items-center gap-3">
          {user && (
            <>
              <span
                className="font-sans text-xs max-w-[200px] truncate hidden sm:inline"
                style={{ color: '#6B6B6B' }}
                title={user.label}
              >
                {user.label}
              </span>
              <div
                className="flex items-center justify-center rounded-full font-sans font-semibold text-xs"
                style={{
                  width: '28px',
                  height: '28px',
                  backgroundColor: user.role === 'hr' ? '#EFF6FF' : '#F5F3FF',
                  color: user.role === 'hr' ? '#0D6EFD' : '#5B21B6',
                }}
                title={user.role === 'hr' ? 'HR' : 'Technical reviewer'}
              >
                {initials(user.label, user.role)}
              </div>
              <button
                type="button"
                onClick={() => handleLogout()}
                className="flex items-center gap-1 font-sans text-xs px-2 py-1 rounded-md transition-colors"
                style={{ color: '#6B6B6B', border: '1px solid #E4E2DC', background: '#FFFFFF' }}
                title="Sign out"
              >
                <LogOut size={14} />
                <span className="hidden sm:inline">Out</span>
              </button>
            </>
          )}
        </div>
      </header>

      <main className="mx-auto px-6" style={{ maxWidth: '1200px', padding: '32px 24px' }}>
        {children}
      </main>
    </div>
  )
}
