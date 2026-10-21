import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { api } from '../lib/api'
import { useAuth, type User } from '../lib/auth'
import { Button, ErrorNote, Field, inputCls } from '../components/ui'

const ROLE: Record<string, string> = { operater: 'Operater', supervizor: 'Supervizor', admin: 'Administrator' }

export default function LoginPage() {
  const { login } = useAuth()
  const nav = useNavigate()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<unknown>(null)
  const [busy, setBusy] = useState(false)
  const { data: users } = useQuery({ queryKey: ['demo-users'], queryFn: () => api.get<User[]>('/api/auth/demo-users') })

  async function go(u: string, p: string) {
    setBusy(true)
    setError(null)
    try {
      await login(u, p)
      nav('/predmeti')
    } catch (e) {
      setError(e)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="min-h-full grid lg:grid-cols-[1.1fr_1fr]">
      <div className="bg-autoput text-white p-8 lg:p-14 flex flex-col justify-between relative overflow-hidden">
        <div>
          <div className="inline-block border-[3px] border-white rounded-[10px] px-5 py-3">
            <div className="font-display text-[34px] lg:text-[44px] font-extrabold leading-none">Korisnički centar</div>
            <div className="font-display text-lg mt-2 text-white/85">Elektronska naplata putarine</div>
          </div>
          <p className="mt-8 max-w-md text-white/85 text-[15.5px]">
            Demo sistema za obradu obraćanja korisnika, sa AI predlozima koje operater uvek pregleda pre slanja.
          </p>
        </div>
        <div className="mt-10 flex items-center gap-4 text-white/75 text-sm">
          <svg width="120" height="10" aria-hidden>
            {[0, 1, 2, 3].map((i) => (
              <rect key={i} x={i * 32} y="2" width="20" height="6" rx="1" fill="#F2A900" />
            ))}
          </svg>
          Svi podaci u demou su izmišljeni.
        </div>
      </div>
      <div className="p-6 lg:p-14 flex items-center">
        <div className="w-full max-w-md">
          <h1 className="text-2xl font-extrabold">Prijava</h1>
          <form
            className="mt-6 space-y-4"
            onSubmit={(e) => {
              e.preventDefault()
              go(username, password)
            }}
          >
            <Field label="Korisničko ime">
              <input className={inputCls} value={username} onChange={(e) => setUsername(e.target.value)} autoComplete="username" />
            </Field>
            <Field label="Lozinka" hint="Za sve demo naloge lozinka je demo">
              <input className={inputCls} type="password" value={password} onChange={(e) => setPassword(e.target.value)} autoComplete="current-password" />
            </Field>
            <Button variant="primary" className="w-full" loading={busy} type="submit">
              Prijavi se
            </Button>
            <ErrorNote error={error} />
          </form>
          <div className="mt-8">
            <p className="text-sm font-medium text-sivo">Brza prijava</p>
            <div className="mt-2 grid sm:grid-cols-2 gap-2">
              {users?.map((u) => (
                <button
                  key={u.id}
                  onClick={() => go(u.username, 'demo')}
                  className="text-left rounded-[8px] border border-linija bg-papir px-3 py-2 hover:border-autoput"
                >
                  <div className="font-medium text-sm">{u.full_name}</div>
                  <div className="text-[12.5px] text-sivo">
                    {ROLE[u.role]}
                    {u.org_unit ? `, ${u.org_unit.code}` : ''}
                  </div>
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
