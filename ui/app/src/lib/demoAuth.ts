/** Demo-only auth — not for production. */

export type DemoRole = 'hr' | 'tech'

export interface DemoSessionUser {
  id: string
  label: string
  role: DemoRole
}

const STORAGE_KEY = 'agentguard_demo_session_v1'

export const DEMO_LOGIN_PASSWORD = 'demo'

/** One HR plus three tech reviewers; IDs are persisted on artifacts as reviewer_id */
export const DEMO_USERS: DemoSessionUser[] = [
  { id: 'HR-COMPLIANCE-01', label: 'Jordan Chen (HR Compliance)', role: 'hr' },
  { id: 'TECH-REVIEWER-01', label: 'Alex Kumar (Technical)', role: 'tech' },
  { id: 'TECH-REVIEWER-02', label: 'Sam Rivera (Technical)', role: 'tech' },
  { id: 'TECH-REVIEWER-03', label: 'Riley Patel (Technical)', role: 'tech' },
]

export function findDemoUser(userId: string): DemoSessionUser | undefined {
  return DEMO_USERS.find((u) => u.id === userId)
}

export function readDemoSession(): DemoSessionUser | null {
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY)
    if (!raw) return null
    const parsed = JSON.parse(raw) as Partial<DemoSessionUser>
    if (
      parsed &&
      typeof parsed.id === 'string' &&
      typeof parsed.label === 'string' &&
      (parsed.role === 'hr' || parsed.role === 'tech')
    ) {
      const canon = findDemoUser(parsed.id)
      if (canon && canon.role === parsed.role) return canon
    }
    return null
  } catch {
    return null
  }
}

export function writeDemoSession(user: DemoSessionUser): void {
  sessionStorage.setItem(STORAGE_KEY, JSON.stringify(user))
}

export function clearDemoSession(): void {
  sessionStorage.removeItem(STORAGE_KEY)
}

export function verifyDemoLogin(userId: string, password: string): DemoSessionUser | null {
  if (password.trim() !== DEMO_LOGIN_PASSWORD) return null
  const u = findDemoUser(userId)
  return u ?? null
}
