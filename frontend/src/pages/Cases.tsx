import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { Loader2, Phone, Search, ShieldAlert } from 'lucide-react'
import { api } from '../lib/api'
import { useUnits } from '../lib/hooks'
import { relTime } from '../lib/format'
import type { CaseRow } from '../lib/types'
import { DueChip, Empty, PriorityStripe, Spinner, StatusBadge, inputCls, selectAutoCls } from '../components/ui'
import PhoneLogModal from '../components/PhoneLogModal'

type ListResp = { items: CaseRow[]; counts: Record<string, number> }

const VIEWS = [
  { key: 'otvoreni', label: 'Otvoreni', count: 'otvoreni', params: { status: 'otvoreni' } },
  { key: 'moji', label: 'Moji', count: 'moji', params: { status: 'otvoreni', mine: 'true' } },
  { key: 'kasne', label: 'Kasne', count: 'prekoraceni', params: { sla: 'prekoracen' } },
  { key: 'uskoro', label: 'Rok ističe za 24 h', count: 'uskoro', params: { sla: 'uskoro' } },
  { key: 'zatvoreni', label: 'Zatvoreni', count: '', params: { status: 'zatvoreno' } },
] as const

export default function CasesPage() {
  const { data: units } = useUnits()
  const [view, setView] = useState<(typeof VIEWS)[number]['key']>('otvoreni')
  const [unit, setUnit] = useState('')
  const [priority, setPriority] = useState('')
  const [q, setQ] = useState('')
  const [phoneOpen, setPhoneOpen] = useState(false)
  const v = VIEWS.find((x) => x.key === view)!
  const params = new URLSearchParams({ ...v.params, unit, priority, q } as Record<string, string>)
  const { data, isLoading } = useQuery({
    queryKey: ['cases', params.toString()],
    queryFn: () => api.get<ListResp>(`/api/cases?${params}`),
    refetchInterval: (query) => ((query.state.data?.counts.ai_u_obradi ?? 0) + (query.state.data?.counts.na_cekanju_mejlovi ?? 0) > 0 ? 4000 : 20000),
  })
  const pending = (data?.counts.ai_u_obradi ?? 0) + (data?.counts.na_cekanju_mejlovi ?? 0)

  return (
    <div className="max-w-[1400px]">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-[28px] font-extrabold">Predmeti</h1>
          <p className="text-sivo text-sm">Obraćanja korisnika, razvrstana po prioritetu i roku.</p>
        </div>
        <div className="flex items-center gap-3">
          {pending > 0 && (
            <span className="inline-flex items-center gap-2 text-sm text-signal-ink bg-signal-soft rounded-full px-3 py-1">
              <Loader2 className="size-4 animate-spin" /> AI obrađuje {pending} {pending === 1 ? 'obraćanje' : 'obraćanja'}
            </span>
          )}
          <button onClick={() => setPhoneOpen(true)} className="inline-flex items-center gap-2 h-10 px-4 rounded-[7px] border border-linija bg-papir text-sm hover:border-sivo">
            <Phone className="size-4" /> Evidentiraj poziv
          </button>
        </div>
      </div>

      <div className="mt-5 flex flex-wrap gap-2" role="tablist" aria-label="Prikaz">
        {VIEWS.map((x) => {
          const n = x.count ? data?.counts[x.count] : undefined
          const active = view === x.key
          return (
            <button
              key={x.key}
              role="tab"
              aria-selected={active}
              onClick={() => setView(x.key)}
              className={`h-9 rounded-full px-4 text-sm border ${active ? 'bg-grafit text-white border-grafit' : 'bg-papir border-linija hover:border-sivo'} ${x.key === 'kasne' && n ? (active ? '' : 'text-stop border-stop/40') : ''}`}
            >
              {x.label}
              {n !== undefined && <span className="num ml-2 font-semibold">{n}</span>}
            </button>
          )
        })}
      </div>

      <div className="mt-4 flex flex-wrap gap-2">
        <div className="relative flex-1 min-w-[220px] max-w-md">
          <Search className="size-4 absolute left-3 top-1/2 -translate-y-1/2 text-sivo" />
          <input className={`${inputCls} pl-9`} placeholder="Broj predmeta, naslov, korisnik ili mejl" value={q} onChange={(e) => setQ(e.target.value)} aria-label="Pretraga" />
        </div>
        <select className={selectAutoCls} value={unit} onChange={(e) => setUnit(e.target.value)} aria-label="Jedinica">
          <option value="">Sve jedinice</option>
          {units?.map((u) => (
            <option key={u.id} value={u.code}>
              {u.code}, {u.name}
            </option>
          ))}
        </select>
        <select className={selectAutoCls} value={priority} onChange={(e) => setPriority(e.target.value)} aria-label="Prioritet">
          <option value="">Svi prioriteti</option>
          <option value="hitan">Hitan</option>
          <option value="visok">Visok</option>
          <option value="normalan">Normalan</option>
          <option value="nizak">Nizak</option>
        </select>
      </div>

      <div className="mt-4 bg-papir border border-linija rounded-[10px] overflow-hidden">
        {isLoading ? (
          <Spinner />
        ) : !data?.items.length ? (
          <Empty title="Nema predmeta u ovom prikazu">Promenite filter ili sačekajte nova obraćanja.</Empty>
        ) : (
          <ul className="divide-y divide-linija">
            {data.items.map((c) => (
              <li key={c.id}>
                <Link to={`/predmeti/${c.id}`} className="flex gap-3 px-3 py-3 hover:bg-beton/60 focus-visible:bg-beton/60">
                  <PriorityStripe priority={c.priority} />
                  <div className="flex-1 min-w-0 grid md:grid-cols-[minmax(0,1fr)_200px_190px_110px] gap-x-4 gap-y-1 items-center">
                    <div className="min-w-0">
                      <div className="flex items-center gap-2 text-[13px] text-sivo">
                        <span className="num font-semibold text-grafit">{c.number}</span>
                        <span>{relTime(c.created_at)}</span>
                        {c.channel === 'telefon' && <Phone className="size-3.5" aria-label="Telefon" />}
                        {c.script === 'cyrillic' && <span className="text-[12px] border border-linija rounded px-1">ćirilica</span>}
                        {c.language !== 'sr' && <span className="text-[12px] border border-linija rounded px-1 uppercase">{c.language}</span>}
                      </div>
                      <div className="font-medium truncate">{c.subject}</div>
                      <div className="text-[13px] text-sivo truncate">{c.customer?.name}{c.snippet ? `: ${c.snippet}` : ''}</div>
                    </div>
                    <div className="text-[13px] min-w-0">
                      {c.ai_status === 'pending' || c.ai_status === 'processing' ? (
                        <span className="inline-flex items-center gap-1.5 text-sivo"><Loader2 className="size-3.5 animate-spin" /> AI analiza</span>
                      ) : (
                        <div className={`pl-2 ${c.routing_confirmed ? 'lane-confirmed' : 'lane-proposed'}`} title={c.routing_confirmed ? 'Raspored potvrđen' : 'AI predlog, nije potvrđen'}>
                          <div className="truncate">{c.category_label}</div>
                          <div className="text-sivo">{c.org_unit?.code ?? 'bez jedinice'}</div>
                        </div>
                      )}
                    </div>
                    <div className="flex items-center gap-2 flex-wrap">
                      <StatusBadge status={c.status} />
                      {c.needs_billing_check && c.billing_status !== 'obavljena' && (
                        <span className="inline-flex items-center gap-1 text-[12.5px] text-enp" title="Potrebna provera u naplatnom sistemu">
                          <ShieldAlert className="size-3.5" /> provera
                        </span>
                      )}
                    </div>
                    <div className="md:text-right">
                      <DueChip due={c.due_at} closed={c.status === 'zatvoreno' || c.status === 'odgovoreno'} />
                      <div className="text-[12.5px] text-sivo truncate">{c.assigned_to?.name ?? 'nepreuzet'}</div>
                    </div>
                  </div>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </div>
      <p className="mt-3 text-[12.5px] text-sivo">
        Isprekidana linija označava AI predlog rasporeda koji operater još nije potvrdio, puna linija potvrđen raspored.
      </p>
      <PhoneLogModal open={phoneOpen} onClose={() => setPhoneOpen(false)} />
    </div>
  )
}
