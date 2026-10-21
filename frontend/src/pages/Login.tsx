import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../lib/auth'
import { Button, ErrorNote, Field, inputCls } from '../components/ui'

export default function LoginPage() {
  const { login } = useAuth()
  const nav = useNavigate()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<unknown>(null)
  const [busy, setBusy] = useState(false)

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
            <Field label="Lozinka">
              <input className={inputCls} type="password" value={password} onChange={(e) => setPassword(e.target.value)} autoComplete="current-password" />
            </Field>
            <Button variant="primary" className="w-full" loading={busy} type="submit">
              Prijavi se
            </Button>
            <ErrorNote error={error} />
          </form>
          <p className="mt-8 text-[13px] text-sivo">
            Pristup imaju samo korisnici sa nalogom. Nalog otvara administrator demoa.
          </p>
        </div>
      </div>
    </div>
  )
}
