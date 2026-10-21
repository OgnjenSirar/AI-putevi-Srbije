import { useState, type ReactNode } from 'react'
import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { BarChart3, BookOpen, Inbox, LogOut, Mail, Megaphone, Menu, Settings, Users, X } from 'lucide-react'
import { api } from '../lib/api'
import { useAuth } from '../lib/auth'

type Status = { effective_mode: string; llm_model: string; services: Record<string, boolean | object> }

const NAV: { to: string; label: string; icon: ReactNode; roles?: string[] }[] = [
  { to: '/predmeti', label: 'Predmeti', icon: <Inbox className="size-[18px]" /> },
  { to: '/posta', label: 'Pošta', icon: <Mail className="size-[18px]" /> },
  { to: '/korisnici', label: 'Korisnici', icon: <Users className="size-[18px]" /> },
  { to: '/znanje', label: 'Znanje službe', icon: <BookOpen className="size-[18px]" /> },
  { to: '/mreze', label: 'Društvene mreže', icon: <Megaphone className="size-[18px]" /> },
  { to: '/izvestaji', label: 'Izveštaji', icon: <BarChart3 className="size-[18px]" /> },
  { to: '/administracija', label: 'Administracija', icon: <Settings className="size-[18px]" /> },
]

const ROLE: Record<string, string> = { operater: 'operater', supervizor: 'supervizor', admin: 'administrator' }

export default function Layout() {
  const { user, logout } = useAuth()
  const nav = useNavigate()
  const [open, setOpen] = useState(false)
  const { data: status } = useQuery({ queryKey: ['status'], queryFn: () => api.get<Status>('/api/admin/status'), refetchInterval: 30000 })
  const live = status?.effective_mode === 'live'

  const sidebar = (
    <div className="flex h-full flex-col bg-autoput text-white">
      <div className="px-5 pt-5 pb-6">
        <div className="font-display text-[22px] font-extrabold leading-none">Korisnički centar</div>
        <div className="mt-1.5 text-[12.5px] text-white/70">Elektronska naplata putarine</div>
      </div>
      <nav className="flex-1 px-3 space-y-0.5" aria-label="Glavna navigacija">
        {NAV.map((n) => (
          <NavLink
            key={n.to}
            to={n.to}
            onClick={() => setOpen(false)}
            className={({ isActive }) =>
              `flex items-center gap-3 rounded-[7px] px-3 py-2.5 font-display text-[15px] ${isActive ? 'bg-white text-autoput font-semibold' : 'text-white/90 hover:bg-white/10'}`
            }
          >
            {n.icon}
            {n.label}
          </NavLink>
        ))}
      </nav>
      <div className="px-4 py-3 mx-3 mb-3 rounded-[8px] bg-autoput-deep text-[12.5px]">
        <div className="flex items-center gap-2">
          <span className={`size-2 rounded-full ${live ? 'bg-[#7ee2a8]' : 'bg-signal'}`} />
          {status ? (live ? `AI aktivan (${status.llm_model})` : 'AI u rezervnom režimu') : 'Provera AI servisa'}
        </div>
        <div className="mt-1 text-white/60">Demo, svi podaci su izmišljeni</div>
      </div>
      <div className="border-t border-white/15 px-5 py-4 flex items-center justify-between gap-2">
        <div className="min-w-0">
          <div className="truncate font-medium">{user?.full_name}</div>
          <div className="text-[12.5px] text-white/70">
            {ROLE[user?.role ?? '']}
            {user?.org_unit ? `, ${user.org_unit.code}` : ''}
          </div>
        </div>
        <button
          className="p-2 rounded hover:bg-white/10"
          aria-label="Odjava"
          title="Odjava"
          onClick={() => {
            logout()
            nav('/prijava')
          }}
        >
          <LogOut className="size-[18px]" />
        </button>
      </div>
    </div>
  )

  return (
    <div className="min-h-full lg:grid lg:grid-cols-[236px_1fr]">
      <aside className="hidden lg:block sticky top-0 h-screen">{sidebar}</aside>
      <div className="lg:hidden flex items-center justify-between bg-autoput text-white px-4 h-14 sticky top-0 z-40">
        <span className="font-display font-extrabold">Korisnički centar</span>
        <button aria-label={open ? 'Zatvori meni' : 'Otvori meni'} onClick={() => setOpen(!open)} className="p-2">
          {open ? <X /> : <Menu />}
        </button>
      </div>
      {open && <div className="lg:hidden fixed inset-0 top-14 z-30">{sidebar}</div>}
      <main className="min-w-0 p-4 lg:p-7">
        <Outlet />
      </main>
    </div>
  )
}
