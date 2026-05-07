import { useState } from 'react'
import { Navigate, useNavigate } from 'react-router'
import { Shield } from 'lucide-react'
import { DEMO_LOGIN_PASSWORD, DEMO_USERS } from '@/lib/demoAuth'
import { defaultRouteForRole } from '@/components/ProtectedRoute'
import { useDemoAuth } from '@/contexts/DemoAuthContext'

export default function LoginPage() {
  const { login, user } = useDemoAuth()
  const navigate = useNavigate()
  const [userId, setUserId] = useState(DEMO_USERS[0].id)
  const [password, setPassword] = useState(DEMO_LOGIN_PASSWORD)
  const [err, setErr] = useState<string | null>(null)

  if (user) {
    return <Navigate to={defaultRouteForRole(user.role)} replace />
  }

  const hrUsers = DEMO_USERS.filter((u) => u.role === 'hr')
  const techUsers = DEMO_USERS.filter((u) => u.role === 'tech')

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    setErr(null)
    const u = login(userId, password)
    if (!u) {
      setErr(`Invalid credentials. Demo password is “${DEMO_LOGIN_PASSWORD}”.`)
      return
    }
    navigate(defaultRouteForRole(u.role), { replace: true })
  }

  const grouped = [
    { title: 'HR', list: hrUsers },
    { title: 'Technical reviewers', list: techUsers },
  ]

  return (
    <div className="min-h-screen flex flex-col" style={{ backgroundColor: '#F7F6F3' }}>
      <header
        className="flex items-center gap-2 px-6"
        style={{ height: '52px', backgroundColor: '#FFFFFF', borderBottom: '1px solid #E4E2DC' }}
      >
        <Shield size={16} color="#0D6EFD" />
        <span className="font-sans font-semibold text-sm" style={{ color: '#0D0D0D' }}>
          AgentGuard
        </span>
        <span className="font-mono text-[11px]" style={{ color: '#9B9B9B' }}>
          v3 · demo login
        </span>
      </header>

      <div className="flex-1 flex items-center justify-center px-6 py-12">
        <div
          className="w-full max-w-md rounded-xl px-8 py-10"
          style={{
            backgroundColor: '#FFFFFF',
            border: '1px solid #E4E2DC',
            boxShadow: '0 1px 3px rgba(0,0,0,0.06)',
          }}
        >
          <h1 className="font-sans font-semibold text-lg" style={{ color: '#0D0D0D' }}>
            Sign in (demo users)
          </h1>
          <p className="font-sans text-sm mt-2" style={{ color: '#6B6B6B' }}>
            Choose a demo account and enter the shared password <span className="font-mono">{DEMO_LOGIN_PASSWORD}</span>.
            HR lands on Review Queue; technical reviewers land on Tech Review.
          </p>

          <form onSubmit={(e) => void handleSubmit(e)} className="mt-8 space-y-5">
            <div>
              <label className="font-sans text-xs block mb-2" style={{ color: '#9B9B9B' }}>
                Demo user
              </label>
              <select
                value={userId}
                onChange={(e) => setUserId(e.target.value)}
                className="w-full font-sans text-sm px-3 py-2.5 rounded-md"
                style={{ border: '1px solid #E4E2DC', backgroundColor: '#FFFFFF', color: '#0D0D0D' }}
              >
                {grouped.map((g) => (
                  <optgroup key={g.title} label={g.title}>
                    {g.list.map((u) => (
                      <option key={u.id} value={u.id}>
                        {u.label}
                      </option>
                    ))}
                  </optgroup>
                ))}
              </select>
            </div>

            <div>
              <label className="font-sans text-xs block mb-2" style={{ color: '#9B9B9B' }}>
                Password
              </label>
              <input
                type="password"
                autoComplete="current-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full font-sans text-sm px-3 py-2.5 rounded-md"
                style={{ border: '1px solid #E4E2DC', backgroundColor: '#FFFFFF', color: '#0D0D0D' }}
              />
            </div>

            {err && (
              <p className="font-sans text-xs" style={{ color: '#B91C1C' }}>
                {err}
              </p>
            )}

            <button
              type="submit"
              className="w-full font-sans text-sm font-medium py-2.5 rounded-lg"
              style={{ backgroundColor: '#0D6EFD', color: '#FFFFFF', border: 'none', cursor: 'pointer' }}
            >
              Continue
            </button>
          </form>
        </div>
      </div>
    </div>
  )
}
