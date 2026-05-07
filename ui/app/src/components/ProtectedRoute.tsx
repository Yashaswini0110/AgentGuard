import type { ReactNode } from 'react'
import { Navigate, useLocation } from 'react-router'
import type { DemoRole } from '@/lib/demoAuth'
import { useDemoAuth } from '@/contexts/DemoAuthContext'

export function defaultRouteForRole(role: DemoRole): string {
  return role === 'hr' ? '/review' : '/tech-review'
}

export default function ProtectedRoute({
  children,
  roles,
}: {
  children: ReactNode
  roles?: DemoRole[]
}) {
  const { user } = useDemoAuth()
  const location = useLocation()

  if (!user) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />
  }

  if (roles && !roles.includes(user.role)) {
    return <Navigate to={defaultRouteForRole(user.role)} replace />
  }

  return <>{children}</>
}
