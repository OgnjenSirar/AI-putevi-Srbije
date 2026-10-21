import { createContext, useContext, useEffect, useState, type ReactNode } from 'react'
import { api, getToken, setToken } from './api'

export type User = {
  id: number
  username: string
  full_name: string
  role: 'operater' | 'supervizor' | 'admin'
  org_unit: { id: number; code: string; name: string } | null
}

type Ctx = {
  user: User | null
  loading: boolean
  login: (username: string, password: string) => Promise<void>
  logout: () => void
}

const AuthContext = createContext<Ctx>({ user: null, loading: true, login: async () => {}, logout: () => {} })

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!getToken()) {
      setLoading(false)
      return
    }
    api
      .get<User>('/api/auth/me')
      .then(setUser)
      .catch(() => setToken(null))
      .finally(() => setLoading(false))
  }, [])

  async function login(username: string, password: string) {
    const r = await api.post<{ token: string; user: User }>('/api/auth/login', { username, password })
    setToken(r.token)
    setUser(r.user)
  }

  function logout() {
    // Brise i kolacic sesije kojim nginx stiti slike i Mailpit
    api.post('/api/auth/logout', {}).catch(() => undefined)
    setToken(null)
    setUser(null)
  }

  return <AuthContext.Provider value={{ user, loading, login, logout }}>{children}</AuthContext.Provider>
}

export const useAuth = () => useContext(AuthContext)
