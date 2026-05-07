import { createContext, useCallback, useContext, useMemo, useState } from 'react'
import type { DemoSessionUser } from '@/lib/demoAuth'
import {
  clearDemoSession,
  readDemoSession,
  verifyDemoLogin,
  writeDemoSession,
} from '@/lib/demoAuth'

type DemoAuthState = {
  user: DemoSessionUser | null
  login: (userId: string, password: string) => DemoSessionUser | null
  logout: () => void
}

const DemoAuthContext = createContext<DemoAuthState | null>(null)

export function DemoAuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<DemoSessionUser | null>(() => readDemoSession())

  const login = useCallback((userId: string, password: string) => {
    const u = verifyDemoLogin(userId, password)
    if (u) {
      writeDemoSession(u)
      setUser(u)
    }
    return u
  }, [])

  const logout = useCallback(() => {
    clearDemoSession()
    setUser(null)
  }, [])

  const value = useMemo(() => ({ user, login, logout }), [user, login, logout])

  return <DemoAuthContext.Provider value={value}>{children}</DemoAuthContext.Provider>
}

export function useDemoAuth(): DemoAuthState {
  const ctx = useContext(DemoAuthContext)
  if (!ctx) throw new Error('useDemoAuth must be used within DemoAuthProvider')
  return ctx
}
