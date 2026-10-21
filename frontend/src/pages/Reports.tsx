import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Bar, BarChart, CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { Download } from 'lucide-react'
import { api, download } from '../lib/api'
import { fmtDate, fmtNum } from '../lib/format'
import { Button, Panel, Spinner, Stat, Tabs } from '../components/ui'

type Summary = {
  rad: {
    kpi: Record<string, number | null>
    po_danima: { datum: string; primljeno: number; zatvoreno: number }[]
    po_kategorijama: { kategorija: string; broj: number }[]
    po_jedinicama: { jedinica: string; naziv: string; primljeno: number; zatvoreno: number; otvoreno_sada: number; prekoraceno_sada: number; prosek_odgovora_h: number | null }[]
  }
  ai: {
    predloga: number
    potvrdjeno_rasporeda: number
    zavrseno_odgovora: number
    tacnost_jedinice: number | null
    tacnost_prioriteta: number | null
    izmene: { klasa: string; naziv: string; broj: number; procenat: number }[]
    prosecna_izmena: number | null
    matrica: { predlog: string; konacno: string; broj: number }[]
    po_kategorijama: { kategorija: string; ukupno: number; jedinica_procenat: number | null; tekst_procenat: number | null }[]
    nedeljno: { nedelja: string; ukupno: number; korisceno: number; procenat: number }[]
    obrasci: { sifra: string; broj: number }[]
  }
  trosak: {
    cene: { ulaz_1m: number; izlaz_1m: number; slika: number; valuta: string; napomena: string }
    ukupno: { poziva: number; ulaz: number; izlaz: number; trosak: number; po_predmetu: number | null; predmeta: number; rezervni_rezim: number }
    po_funkciji: { funkcija: string; naziv: string; poziva: number; ulaz: number; izlaz: number; trosak: number; prosecno_ms: number; greske: number }[]
    po_danima: { datum: string; ulaz: number; izlaz: number; trosak: number }[]
  }
}

type Audit = { id: number; at: string; actor: string; entity: string; entity_id: string; action: string; summary: string }

// Validirane boje grafika (scripts/validate_palette.js): plava i tamnozlatna za dve serije,
// zelena skala (tamnije = manje izmena) za udeo izmena predloga.
const C_IN = '#1b5fa8'
const C_OUT = '#d98b00'
const EDIT_RAMP: Record<string, string> = { bez_izmena: '#0b5d3b', manje_izmene: '#2f8a5c', vece_izmene: '#6fb88f', napisan_iznova: '#b5dcc4' }
const axis = { fontSize: 12, fill: '#5e6b64' }
const shortDay = (d: string) => `${Number(d.slice(8, 10))}.${Number(d.slice(5, 7))}.`

export default function ReportsPage() {
  const [days, setDays] = useState(30)
  const [tab, setTab] = useState<'rad' | 'ai' | 'trosak' | 'izmene'>('rad')
  const [busy, setBusy] = useState<string | null>(null)
  const { data, isLoading } = useQuery({ queryKey: ['reports', days], queryFn: () => api.get<Summary>(`/api/reports/summary?days=${days}`) })

  async function exp(fmt: string) {
    setBusy(fmt)
    try {
      await download(`/api/reports/export/${fmt}?days=${days}`, `izvestaj-korisnicki-centar-${days}d.${fmt}`)
    } finally {
      setBusy(null)
    }
  }

  return (
    <div className="max-w-[1300px]">
      <h1 className="text-[28px] font-extrabold">Izveštaji</h1>
      <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
        <div className="flex gap-1 bg-papir border border-linija rounded-[8px] p-1" role="group" aria-label="Period">
          {[7, 30, 60].map((d) => (
            <button key={d} onClick={() => setDays(d)} aria-pressed={days === d} className={`h-8 px-3 rounded-[6px] text-sm ${days === d ? 'bg-grafit text-white' : 'hover:bg-black/5'}`}>
              {d} dana
            </button>
          ))}
        </div>
        <div className="flex gap-2">
          {[['xlsx', 'Excel'], ['docx', 'Word'], ['pdf', 'PDF']].map(([f, l]) => (
            <Button key={f} size="sm" icon={<Download className="size-3.5" />} loading={busy === f} onClick={() => exp(f)}>{l}</Button>
          ))}
        </div>
      </div>
      <div className="mt-4">
        <Tabs value={tab} onChange={setTab} items={[{ value: 'rad', label: 'Rad službe' }, { value: 'ai', label: 'AI predlozi' }, { value: 'trosak', label: 'Trošak AI' }, { value: 'izmene', label: 'Evidencija izmena' }]} />
      </div>
      <div className="mt-5">
        {tab === 'izmene' ? <AuditLog /> : isLoading || !data ? <Spinner /> : tab === 'rad' ? <Work d={data} /> : tab === 'ai' ? <AI d={data} /> : <Cost d={data} />}
      </div>
    </div>
  )
}

function KpiRow({ children }: { children: React.ReactNode }) {
  return <div className="bg-papir border border-linija rounded-[10px] grid grid-cols-2 md:grid-cols-4 divide-x divide-y md:divide-y-0 divide-linija">{children}</div>
}

function Work({ d }: { d: Summary }) {
  const k = d.rad.kpi
  const maxCat = Math.max(...d.rad.po_kategorijama.map((c) => c.broj), 1)
  return (
    <div className="space-y-5">
      <KpiRow>
        <Stat label="primljeno predmeta" value={fmtNum(k.primljeno)} sub={`${fmtNum(k.odvojena_posta)} mejlova odvojeno kao spam ili tehnička pošta`} />
        <Stat label="prosečno do prvog odgovora" value={`${fmtNum(k.prosek_prvog_odgovora_h, 1)} h`} />
        <Stat label="odgovoreno u roku" value={`${fmtNum(k.u_roku_procenat, 1)}%`} />
        <Stat label="otvoreno, od toga kasni" value={<>{fmtNum(k.otvoreno_sada)} <span className={k.prekoraceno_sada ? 'text-stop' : 'text-sivo'}>/ {fmtNum(k.prekoraceno_sada)}</span></>} sub={`${fmtNum(k.telefonski_kontakti)} telefonskih kontakata`} />
      </KpiRow>
      <Panel title="Primljeni i zatvoreni predmeti po danima">
        <div className="h-64">
          <ResponsiveContainer>
            <LineChart data={d.rad.po_danima} margin={{ top: 8, right: 12, left: -16, bottom: 0 }}>
              <CartesianGrid stroke="#e7eae5" vertical={false} />
              <XAxis dataKey="datum" tickFormatter={shortDay} tick={axis} tickLine={false} axisLine={{ stroke: '#d5dad2' }} minTickGap={24} />
              <YAxis allowDecimals={false} tick={axis} tickLine={false} axisLine={false} />
              <Tooltip labelFormatter={(l) => fmtDate(String(l), false)} />
              <Legend iconType="plainline" wrapperStyle={{ fontSize: 13 }} />
              <Line type="linear" dataKey="primljeno" name="Primljeno" stroke={C_IN} strokeWidth={2} dot={false} activeDot={{ r: 5 }} />
              <Line type="linear" dataKey="zatvoreno" name="Zatvoreno" stroke={C_OUT} strokeWidth={2} dot={false} activeDot={{ r: 5 }} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </Panel>
      <div className="grid lg:grid-cols-2 gap-5 items-start">
        <Panel title="Po jedinicama" pad={false}>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-[13px] text-sivo border-y border-linija">
                  <th className="px-3 py-2 font-medium">Jedinica</th>
                  <th className="px-2 py-2 font-medium text-right">Primljeno</th>
                  <th className="px-2 py-2 font-medium text-right">Zatvoreno</th>
                  <th className="px-2 py-2 font-medium text-right">Otvoreno</th>
                  <th className="px-2 py-2 font-medium text-right">Kasni</th>
                  <th className="px-3 py-2 font-medium text-right">Prosek h</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-linija">
                {d.rad.po_jedinicama.map((u) => (
                  <tr key={u.jedinica}>
                    <td className="px-3 py-2" title={u.naziv}><b className="num">{u.jedinica}</b><span className="block text-sivo text-[12.5px] truncate max-w-[150px]">{u.naziv}</span></td>
                    <td className="px-2 py-2 num text-right">{u.primljeno}</td>
                    <td className="px-2 py-2 num text-right">{u.zatvoreno}</td>
                    <td className="px-2 py-2 num text-right">{u.otvoreno_sada}</td>
                    <td className={`px-2 py-2 num text-right ${u.prekoraceno_sada ? 'text-stop font-semibold' : ''}`}>{u.prekoraceno_sada}</td>
                    <td className="px-3 py-2 num text-right">{fmtNum(u.prosek_odgovora_h, 1)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Panel>
        <Panel title="Teme obraćanja">
          <ul className="space-y-2">
            {d.rad.po_kategorijama.slice(0, 12).map((c) => (
              <li key={c.kategorija} className="grid grid-cols-[minmax(0,1fr)_120px_32px] items-center gap-3 text-sm">
                <span className="truncate">{c.kategorija}</span>
                <span className="h-2 rounded-r bg-enp" style={{ width: `${(c.broj / maxCat) * 100}%` }} />
                <span className="num text-right">{c.broj}</span>
              </li>
            ))}
          </ul>
        </Panel>
      </div>
    </div>
  )
}

function AI({ d }: { d: Summary }) {
  const a = d.ai
  const used = a.izmene.filter((x) => x.klasa === 'bez_izmena' || x.klasa === 'manje_izmene').reduce((s, x) => s + x.procenat, 0)
  return (
    <div className="space-y-5">
      <KpiRow>
        <Stat label="tačan predlog jedinice" value={`${fmtNum(a.tacnost_jedinice, 1)}%`} sub={`od ${a.potvrdjeno_rasporeda} potvrđenih rasporeda`} />
        <Stat label="tačan predlog prioriteta" value={`${fmtNum(a.tacnost_prioriteta, 1)}%`} />
        <Stat label="odgovora iz predloga bez većih izmena" value={`${fmtNum(used, 1)}%`} sub={`od ${a.zavrseno_odgovora} poslatih odgovora`} />
        <Stat label="prosečan obim izmene teksta" value={a.prosecna_izmena === null ? '-' : `${Math.round(a.prosecna_izmena * 100)}%`} sub="normalizovana Levenshtein razlika" />
      </KpiRow>
      <Panel title="Kako operateri koriste predloge odgovora">
        <div className="flex h-7 rounded-[6px] overflow-hidden gap-[2px] bg-papir">
          {a.izmene.filter((x) => x.procenat > 0).map((x) => (
            <div key={x.klasa} title={`${x.naziv}: ${x.procenat}% (${x.broj})`} style={{ width: `${x.procenat}%`, background: EDIT_RAMP[x.klasa] }} />
          ))}
        </div>
        <ul className="mt-3 flex flex-wrap gap-x-6 gap-y-1 text-sm">
          {a.izmene.map((x) => (
            <li key={x.klasa} className="inline-flex items-center gap-2">
              <span className="size-3 rounded-sm" style={{ background: EDIT_RAMP[x.klasa] }} />
              {x.naziv} <span className="num font-semibold">{x.procenat}%</span> <span className="text-sivo">({x.broj})</span>
            </li>
          ))}
        </ul>
      </Panel>
      <div className="grid lg:grid-cols-2 gap-5 items-start">
        <Panel title="Udeo odgovora bez većih izmena, po nedeljama">
          <div className="h-56">
            <ResponsiveContainer>
              <LineChart data={a.nedeljno} margin={{ top: 8, right: 12, left: -16, bottom: 0 }}>
                <CartesianGrid stroke="#e7eae5" vertical={false} />
                <XAxis dataKey="nedelja" tick={axis} tickLine={false} axisLine={{ stroke: '#d5dad2' }} />
                <YAxis domain={[0, 100]} tick={axis} tickLine={false} axisLine={false} unit="%" />
                <Tooltip formatter={(v) => [`${v}%`, 'Bez većih izmena']} />
                <Line type="linear" dataKey="procenat" stroke="#0b5d3b" strokeWidth={2} dot={{ r: 4 }} activeDot={{ r: 6 }} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </Panel>
        <Panel title="Predlog jedinice i konačna odluka">
          <p className="text-[13px] text-sivo mb-2">Redovi gde se predlog razlikuje od odluke operatera pokazuju gde AI greši.</p>
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-[13px] text-sivo border-b border-linija">
                <th className="py-1.5 font-medium">AI predlog</th>
                <th className="py-1.5 font-medium">Konačno</th>
                <th className="py-1.5 font-medium text-right">Broj</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-linija">
              {a.matrica.map((m) => (
                <tr key={`${m.predlog}-${m.konacno}`} className={m.predlog !== m.konacno ? 'text-stop' : ''}>
                  <td className="py-1.5 num">{m.predlog}</td>
                  <td className="py-1.5 num">{m.konacno}</td>
                  <td className="py-1.5 num text-right">{m.broj}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </Panel>
      </div>
      <Panel title="Po kategorijama" pad={false}>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-[13px] text-sivo border-y border-linija">
                <th className="px-4 py-2 font-medium">Kategorija</th>
                <th className="px-3 py-2 font-medium text-right">Predloga</th>
                <th className="px-3 py-2 font-medium text-right">Tačna jedinica</th>
                <th className="px-4 py-2 font-medium text-right">Odgovor bez većih izmena</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-linija">
              {a.po_kategorijama.map((c) => (
                <tr key={c.kategorija}>
                  <td className="px-4 py-2">{c.kategorija}</td>
                  <td className="px-3 py-2 num text-right">{c.ukupno}</td>
                  <td className="px-3 py-2 num text-right">{c.jedinica_procenat === null ? '-' : `${c.jedinica_procenat}%`}</td>
                  <td className="px-4 py-2 num text-right">{c.tekst_procenat === null ? '-' : `${c.tekst_procenat}%`}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Panel>
    </div>
  )
}

function Cost({ d }: { d: Summary }) {
  const t = d.trosak
  return (
    <div className="space-y-5">
      <KpiRow>
        <Stat label={`ukupan trošak (${t.cene.valuta}, interna cena)`} value={fmtNum(t.ukupno.trosak, 2)} />
        <Stat label="po obrađenom predmetu" value={fmtNum(t.ukupno.po_predmetu, 2)} sub={`${t.ukupno.predmeta} predmeta`} />
        <Stat label="tokena (ulaz / izlaz)" value={<span className="text-[22px]">{fmtNum(t.ukupno.ulaz)} / {fmtNum(t.ukupno.izlaz)}</span>} />
        <Stat label="AI poziva" value={fmtNum(t.ukupno.poziva)} sub={t.ukupno.rezervni_rezim ? `${t.ukupno.rezervni_rezim} u rezervnom režimu` : undefined} />
      </KpiRow>
      <Panel title={`Trošak po danima (${t.cene.valuta})`}>
        <div className="h-60">
          <ResponsiveContainer>
            <BarChart data={t.po_danima} margin={{ top: 8, right: 12, left: -10, bottom: 0 }}>
              <CartesianGrid stroke="#e7eae5" vertical={false} />
              <XAxis dataKey="datum" tickFormatter={shortDay} tick={axis} tickLine={false} axisLine={{ stroke: '#d5dad2' }} minTickGap={20} />
              <YAxis tick={axis} tickLine={false} axisLine={false} />
              <Tooltip labelFormatter={(l) => fmtDate(String(l), false)} formatter={(v) => [`${fmtNum(Number(v), 2)} ${t.cene.valuta}`, 'Trošak']} />
              <Bar dataKey="trosak" fill={C_IN} radius={[4, 4, 0, 0]} maxBarSize={22} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </Panel>
      <Panel title="Po funkcijama" pad={false}>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-[13px] text-sivo border-y border-linija">
                <th className="px-4 py-2 font-medium">Funkcija</th>
                <th className="px-3 py-2 font-medium text-right">Poziva</th>
                <th className="px-3 py-2 font-medium text-right">Ulaz</th>
                <th className="px-3 py-2 font-medium text-right">Izlaz</th>
                <th className="px-3 py-2 font-medium text-right">Trošak</th>
                <th className="px-4 py-2 font-medium text-right">Prosečno trajanje</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-linija">
              {t.po_funkciji.map((f) => (
                <tr key={f.funkcija}>
                  <td className="px-4 py-2">{f.naziv}{f.greske ? <span className="text-stop text-[13px]">, {f.greske} grešaka</span> : null}</td>
                  <td className="px-3 py-2 num text-right">{fmtNum(f.poziva)}</td>
                  <td className="px-3 py-2 num text-right">{fmtNum(f.ulaz)}</td>
                  <td className="px-3 py-2 num text-right">{fmtNum(f.izlaz)}</td>
                  <td className="px-3 py-2 num text-right">{fmtNum(f.trosak, 2)}</td>
                  <td className="px-4 py-2 num text-right">{fmtNum(f.prosecno_ms / 1000, 1)} s</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Panel>
      <p className="text-[13px] text-sivo max-w-3xl">
        {t.cene.napomena} Trenutne cene: {fmtNum(t.cene.ulaz_1m, 2)} {t.cene.valuta} za milion ulaznih tokena, {fmtNum(t.cene.izlaz_1m, 2)} za milion izlaznih, {fmtNum(t.cene.slika, 2)} po slici.
      </p>
    </div>
  )
}

function AuditLog() {
  const { data, isLoading } = useQuery({ queryKey: ['audit'], queryFn: () => api.get<Audit[]>('/api/reports/audit') })
  if (isLoading) return <Spinner />
  return (
    <Panel title="Evidencija izmena podataka" pad={false}>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-[13px] text-sivo border-y border-linija">
              <th className="px-4 py-2 font-medium">Vreme</th>
              <th className="px-3 py-2 font-medium">Ko</th>
              <th className="px-3 py-2 font-medium">Šta</th>
              <th className="px-4 py-2 font-medium">Opis</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-linija">
            {data?.map((r) => (
              <tr key={r.id}>
                <td className="px-4 py-2 whitespace-nowrap text-[13px]">{fmtDate(r.at)}</td>
                <td className="px-3 py-2 whitespace-nowrap">{r.actor}</td>
                <td className="px-3 py-2 whitespace-nowrap text-[13px]">{r.entity}, {r.action}</td>
                <td className="px-4 py-2">{r.summary}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Panel>
  )
}
