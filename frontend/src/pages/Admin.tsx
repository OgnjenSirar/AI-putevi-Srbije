import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { ExternalLink, RotateCcw } from 'lucide-react'
import { api } from '../lib/api'
import { useAuth } from '../lib/auth'
import { useCodebooks, useUnits } from '../lib/hooks'
import { PRIORITY_LABEL } from '../lib/format'
import { Button, Chip, ErrorNote, Field, Modal, Panel, Spinner, Tabs, inputCls } from '../components/ui'

type Status = {
  ai_mode: string
  effective_mode: string
  llm_model: string
  services: Record<string, boolean | Record<string, unknown>>
  jobs: Record<string, number>
  langfuse_ui: string
  mailpit_ui: string
}

const SERVICES: [string, string, string][] = [
  ['llm', 'Jezički model (Gemma 4)', 'analiza, predlozi odgovora, tekst objava'],
  ['embed', 'Embedding model (BGE-M3)', 'semantička pretraga znanja službe'],
  ['rerank', 'Reranker (bge-reranker-v2-m3)', 'preraspoređivanje rezultata pretrage'],
  ['imagegen', 'Generisanje slika (FLUX.2 klein 4B)', 'AI pozadine za objave'],
  ['langfuse', 'Langfuse', 'tragovi AI poziva i kvalitet'],
  ['smtp', 'SMTP (Mailpit u demou)', 'slanje odgovora korisnicima'],
]

export default function AdminPage() {
  const [tab, setTab] = useState<'status' | 'nalozi' | 'jedinice' | 'sifarnici' | 'podesavanja' | 'demo'>('status')
  return (
    <div className="max-w-[1200px]">
      <h1 className="text-[28px] font-extrabold">Administracija</h1>
      <div className="mt-4">
        <Tabs
          value={tab}
          onChange={setTab}
          items={[
            { value: 'status', label: 'Stanje sistema' },
            { value: 'nalozi', label: 'Nalozi i uloge' },
            { value: 'jedinice', label: 'Organizacione jedinice' },
            { value: 'sifarnici', label: 'Šifarnici' },
            { value: 'podesavanja', label: 'Podešavanja' },
            { value: 'demo', label: 'Demo' },
          ]}
        />
      </div>
      <div className="mt-5">
        {tab === 'status' && <SystemStatus />}
        {tab === 'nalozi' && <Users />}
        {tab === 'jedinice' && <Units />}
        {tab === 'sifarnici' && <Codebooks />}
        {tab === 'podesavanja' && <SettingsTab />}
        {tab === 'demo' && <Demo />}
      </div>
    </div>
  )
}

function SystemStatus() {
  const { data, isLoading } = useQuery({ queryKey: ['status-full'], queryFn: () => api.get<Status>('/api/admin/status'), refetchInterval: 10000 })
  if (isLoading || !data) return <Spinner />
  const ig = data.services.imagegen_detail as Record<string, unknown> | undefined
  return (
    <div className="grid lg:grid-cols-[minmax(0,1fr)_340px] gap-5 items-start">
      <Panel title="AI servisi">
        <ul className="divide-y divide-linija">
          {SERVICES.map(([k, label, desc]) => {
            const ok = data.services[k] === true
            return (
              <li key={k} className="py-2.5 flex items-center justify-between gap-3">
                <div>
                  <div className="font-medium text-sm">{label}</div>
                  <div className="text-[13px] text-sivo">{desc}</div>
                  {k === 'llm' && <div className="text-[12.5px] text-sivo">model: {data.llm_model}</div>}
                  {k === 'imagegen' && ig && <div className="text-[12.5px] text-sivo">stanje: {String(ig.status)}{ig.u_memoriji === false ? ' (model se učitava pri prvom zahtevu)' : ''}{ig.gpu_free_gb ? `, slobodno ${String(ig.gpu_free_gb)} od ${String(ig.gpu_total_gb)} GB GPU memorije` : ''}</div>}
                </div>
                <Chip tone={ok ? 'autoput' : 'stop'}>{ok ? 'radi' : 'nedostupan'}</Chip>
              </li>
            )
          })}
        </ul>
      </Panel>
      <div className="space-y-5">
        <Panel title="AI režim">
          <p className="text-sm">
            {data.effective_mode === 'live'
              ? `Predlozi se prave pomoću modela ${data.llm_model}.`
              : 'Jezički model nije dostupan, pa sistem koristi rezervni režim zasnovan na pravilima. Rad službe se nastavlja bez prekida.'}
          </p>
          <div className="mt-2 text-[13px] text-sivo">Podešeni režim: {data.ai_mode}</div>
        </Panel>
        <Panel title="Red poslova">
          <dl className="grid grid-cols-2 gap-y-1 text-sm">
            {Object.entries(data.jobs).map(([k, v]) => (
              <div key={k} className="contents"><dt className="text-sivo">{({ done: 'završeno', queued: 'u redu', running: 'u toku', failed: 'neuspelo' } as Record<string, string>)[k] ?? k}</dt><dd className="num text-right">{v}</dd></div>
            ))}
          </dl>
        </Panel>
        <Panel title="Alati">
          <div className="space-y-2 text-sm">
            {data.langfuse_ui && <a className="flex items-center gap-1.5 text-enp hover:underline" href={data.langfuse_ui} target="_blank" rel="noreferrer">Langfuse, tragovi AI poziva <ExternalLink className="size-3.5" /></a>}
            <a className="flex items-center gap-1.5 text-enp hover:underline" href={data.mailpit_ui} target="_blank" rel="noreferrer">Mailpit, poslati odgovori <ExternalLink className="size-3.5" /></a>
          </div>
        </Panel>
      </div>
    </div>
  )
}

type U = { id: number; username: string; full_name: string; role: string; org_unit_id: number | null; active: boolean }

function Users() {
  const qc = useQueryClient()
  const { user } = useAuth()
  const { data } = useQuery({ queryKey: ['users'], queryFn: () => api.get<U[]>('/api/admin/users') })
  const units = useUnits().data
  const [edit, setEdit] = useState<(U & { password: string }) | null>(null)
  const [error, setError] = useState<unknown>(null)
  const isAdmin = user?.role === 'admin'
  return (
    <Panel title="Nalozi" actions={isAdmin && <Button size="sm" onClick={() => setEdit({ id: 0, username: '', full_name: '', role: 'operater', org_unit_id: units?.[0]?.id ?? null, active: true, password: '' })}>Novi nalog</Button>} pad={false}>
      {!isAdmin && <p className="px-4 text-[13px] text-sivo">Izmene naloga može da radi samo administrator.</p>}
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left text-[13px] text-sivo border-y border-linija">
            <th className="px-4 py-2 font-medium">Ime</th>
            <th className="px-3 py-2 font-medium">Korisničko ime</th>
            <th className="px-3 py-2 font-medium">Uloga</th>
            <th className="px-3 py-2 font-medium">Jedinica</th>
            <th className="px-4 py-2" />
          </tr>
        </thead>
        <tbody className="divide-y divide-linija">
          {data?.map((u) => (
            <tr key={u.id} className={u.active ? '' : 'text-sivo'}>
              <td className="px-4 py-2">{u.full_name}</td>
              <td className="px-3 py-2 num">{u.username}</td>
              <td className="px-3 py-2">{u.role}</td>
              <td className="px-3 py-2">{units?.find((x) => x.id === u.org_unit_id)?.code ?? '-'}</td>
              <td className="px-4 py-2 text-right">{isAdmin && <Button size="sm" onClick={() => setEdit({ ...u, password: '' })}>Izmeni</Button>}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <Modal open={!!edit} onClose={() => setEdit(null)} title={edit?.id ? 'Izmena naloga' : 'Novi nalog'}>
        {edit && (
          <div className="space-y-3">
            <Field label="Ime i prezime"><input className={inputCls} value={edit.full_name} onChange={(e) => setEdit({ ...edit, full_name: e.target.value })} /></Field>
            <Field label="Korisničko ime"><input className={inputCls} value={edit.username} disabled={!!edit.id} onChange={(e) => setEdit({ ...edit, username: e.target.value })} /></Field>
            <div className="grid grid-cols-2 gap-3">
              <Field label="Uloga">
                <select className={inputCls} value={edit.role} onChange={(e) => setEdit({ ...edit, role: e.target.value })}>
                  <option value="operater">operater</option>
                  <option value="supervizor">supervizor</option>
                  <option value="admin">admin</option>
                </select>
              </Field>
              <Field label="Jedinica">
                <select className={inputCls} value={edit.org_unit_id ?? ''} onChange={(e) => setEdit({ ...edit, org_unit_id: e.target.value ? Number(e.target.value) : null })}>
                  <option value="">bez jedinice</option>
                  {units?.map((x) => <option key={x.id} value={x.id}>{x.code}</option>)}
                </select>
              </Field>
            </div>
            <Field label={edit.id ? 'Nova lozinka (opciono)' : 'Lozinka'}><input className={inputCls} type="password" value={edit.password} onChange={(e) => setEdit({ ...edit, password: e.target.value })} /></Field>
            <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={edit.active} onChange={(e) => setEdit({ ...edit, active: e.target.checked })} /> Nalog aktivan</label>
            <ErrorNote error={error} />
            <div className="flex justify-end gap-2">
              <Button onClick={() => setEdit(null)}>Otkaži</Button>
              <Button variant="primary" onClick={async () => {
                try {
                  if (edit.id) await api.put(`/api/admin/users/${edit.id}`, edit)
                  else await api.post('/api/admin/users', edit)
                  qc.invalidateQueries({ queryKey: ['users'] })
                  setEdit(null)
                } catch (e) { setError(e) }
              }}>Sačuvaj</Button>
            </div>
          </div>
        )}
      </Modal>
    </Panel>
  )
}

function Units() {
  const qc = useQueryClient()
  const { data } = useUnits()
  const [edit, setEdit] = useState<{ id: number; code: string; name: string; description: string; email: string; active: boolean } | null>(null)
  return (
    <Panel title="Organizacione jedinice" actions={<Button size="sm" onClick={() => setEdit({ id: 0, code: '', name: '', description: '', email: '', active: true })}>Nova jedinica</Button>} pad={false}>
      <table className="w-full text-sm">
        <tbody className="divide-y divide-linija border-t border-linija">
          {data?.map((u) => (
            <tr key={u.id}>
              <td className="px-4 py-2.5 num font-semibold w-20">{u.code}</td>
              <td className="px-3 py-2.5"><div>{u.name}</div><div className="text-[13px] text-sivo">{u.description}</div></td>
              <td className="px-3 py-2.5 text-[13px]">{u.email}</td>
              <td className="px-4 py-2.5 text-right"><Button size="sm" onClick={() => setEdit(u)}>Izmeni</Button></td>
            </tr>
          ))}
        </tbody>
      </table>
      <Modal open={!!edit} onClose={() => setEdit(null)} title={edit?.id ? 'Izmena jedinice' : 'Nova jedinica'}>
        {edit && (
          <div className="space-y-3">
            <Field label="Šifra"><input className={inputCls} value={edit.code} onChange={(e) => setEdit({ ...edit, code: e.target.value })} /></Field>
            <Field label="Naziv"><input className={inputCls} value={edit.name} onChange={(e) => setEdit({ ...edit, name: e.target.value })} /></Field>
            <Field label="Opis nadležnosti" hint="AI koristi opis kada predlaže nadležnu jedinicu"><textarea className={inputCls} value={edit.description} onChange={(e) => setEdit({ ...edit, description: e.target.value })} /></Field>
            <Field label="Mejl"><input className={inputCls} value={edit.email} onChange={(e) => setEdit({ ...edit, email: e.target.value })} /></Field>
            <div className="flex justify-end gap-2">
              <Button onClick={() => setEdit(null)}>Otkaži</Button>
              <Button variant="primary" onClick={async () => {
                if (edit.id) await api.put(`/api/admin/units/${edit.id}`, edit)
                else await api.post('/api/admin/units', edit)
                qc.invalidateQueries({ queryKey: ['units'] })
                setEdit(null)
              }}>Sačuvaj</Button>
            </div>
          </div>
        )}
      </Modal>
    </Panel>
  )
}

function Codebooks() {
  const qc = useQueryClient()
  const { data } = useCodebooks()
  const units = useUnits().data
  const [edit, setEdit] = useState<{ id: number; label: string; data: Record<string, unknown>; active: boolean } | null>(null)
  if (!data) return <Spinner />
  return (
    <div className="space-y-5">
      <Panel title="Kategorije obraćanja" pad={false}>
        <p className="px-4 text-[13px] text-sivo mb-2">Uobičajena jedinica, prioritet i rok po kategoriji. AI ih koristi kao polaznu tačku, a rok se računa automatski.</p>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-[13px] text-sivo border-y border-linija">
                <th className="px-4 py-2 font-medium">Kategorija</th>
                <th className="px-3 py-2 font-medium">Jedinica</th>
                <th className="px-3 py-2 font-medium">Prioritet</th>
                <th className="px-3 py-2 font-medium text-right">Rok (dana)</th>
                <th className="px-3 py-2 font-medium">Provera</th>
                <th className="px-4 py-2" />
              </tr>
            </thead>
            <tbody className="divide-y divide-linija">
              {data.kategorija?.map((c) => (
                <tr key={c.id}>
                  <td className="px-4 py-2">{c.label}</td>
                  <td className="px-3 py-2 num">{String(c.data.unit)}</td>
                  <td className="px-3 py-2">{PRIORITY_LABEL[String(c.data.priority)]}</td>
                  <td className="px-3 py-2 num text-right">{String(c.data.due_days)}</td>
                  <td className="px-3 py-2">{c.data.needs_check ? 'da' : 'ne'}</td>
                  <td className="px-4 py-2 text-right"><Button size="sm" onClick={() => setEdit(c)}>Izmeni</Button></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Panel>
      <Panel title="Tipovi provere u naplatnom sistemu">
        <div className="flex flex-wrap gap-2">{data.provera?.map((p) => <Chip key={p.id} tone="enp">{p.label}</Chip>)}</div>
      </Panel>
      <Modal open={!!edit} onClose={() => setEdit(null)} title="Izmena kategorije">
        {edit && (
          <div className="space-y-3">
            <Field label="Naziv"><input className={inputCls} value={edit.label} onChange={(e) => setEdit({ ...edit, label: e.target.value })} /></Field>
            <div className="grid grid-cols-2 gap-3">
              <Field label="Jedinica">
                <select className={inputCls} value={String(edit.data.unit)} onChange={(e) => setEdit({ ...edit, data: { ...edit.data, unit: e.target.value } })}>
                  {units?.map((u) => <option key={u.id} value={u.code}>{u.code}</option>)}
                </select>
              </Field>
              <Field label="Prioritet">
                <select className={inputCls} value={String(edit.data.priority)} onChange={(e) => setEdit({ ...edit, data: { ...edit.data, priority: e.target.value } })}>
                  {Object.entries(PRIORITY_LABEL).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
                </select>
              </Field>
            </div>
            <Field label="Rok (dana)"><input className={inputCls} type="number" value={Number(edit.data.due_days)} onChange={(e) => setEdit({ ...edit, data: { ...edit.data, due_days: Number(e.target.value) } })} /></Field>
            <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={!!edit.data.needs_check} onChange={(e) => setEdit({ ...edit, data: { ...edit.data, needs_check: e.target.checked } })} /> Uvek potrebna provera u naplatnom sistemu</label>
            <div className="flex justify-end gap-2">
              <Button onClick={() => setEdit(null)}>Otkaži</Button>
              <Button variant="primary" onClick={async () => { await api.put(`/api/admin/codebooks/${edit.id}`, edit); qc.invalidateQueries({ queryKey: ['codebooks'] }); setEdit(null) }}>Sačuvaj</Button>
            </div>
          </div>
        )}
      </Modal>
    </div>
  )
}

type S = { key: string; label: string; value: Record<string, unknown> }

function SettingsTab() {
  const qc = useQueryClient()
  const { data } = useQuery({ queryKey: ['settings'], queryFn: () => api.get<S[]>('/api/admin/settings') })
  const [drafts, setDrafts] = useState<Record<string, string>>({})
  const [saved, setSaved] = useState('')
  if (!data) return <Spinner />
  return (
    <Panel title="Podešavanja sistema">
      <ul className="divide-y divide-linija">
        {data.map((s) => {
          const raw = drafts[s.key] ?? JSON.stringify(s.value.value !== undefined ? s.value.value : s.value)
          return (
            <li key={s.key} className="py-3 grid md:grid-cols-[260px_minmax(0,1fr)_auto] gap-3 items-start">
              <div>
                <div className="text-sm font-medium">{s.label}</div>
                <div className="num text-[12.5px] text-sivo">{s.key}</div>
              </div>
              <textarea className={`${inputCls} font-mono text-[13px] min-h-10`} value={raw} onChange={(e) => setDrafts({ ...drafts, [s.key]: e.target.value })} aria-label={s.label} />
              <Button size="sm" disabled={drafts[s.key] === undefined} onClick={async () => {
                try {
                  const parsed = JSON.parse(raw)
                  const value = s.value.value !== undefined ? { ...s.value, value: parsed } : parsed
                  await api.put(`/api/admin/settings/${s.key}`, { value })
                  const n = { ...drafts }
                  delete n[s.key]
                  setDrafts(n)
                  setSaved(s.label)
                  qc.invalidateQueries({ queryKey: ['settings'] })
                } catch {
                  setSaved(`Neispravan format za: ${s.label}`)
                }
              }}>Sačuvaj</Button>
            </li>
          )
        })}
      </ul>
      {saved && <p className="mt-2 text-sm text-autoput">Sačuvano: {saved}</p>}
    </Panel>
  )
}

function Demo() {
  const qc = useQueryClient()
  const [busy, setBusy] = useState(false)
  const [msg, setMsg] = useState('')
  return (
    <Panel title="Vraćanje demoa na početno stanje">
      <p className="text-sm max-w-2xl">Briše sve izmene i ponovo puni bazu izmišljenim podacima: korisnicima, istorijom od 150 zatvorenih predmeta i novim mejlovima koje AI zatim obrađuje.</p>
      <Button className="mt-3" variant="danger" icon={<RotateCcw className="size-4" />} loading={busy} onClick={async () => {
        if (!window.confirm('Vratiti demo na početno stanje? Sve izmene će biti obrisane.')) return
        setBusy(true)
        try {
          await api.post('/api/admin/reset')
          qc.invalidateQueries()
          setMsg('Demo je vraćen na početno stanje. AI obrađuje nove mejlove.')
        } finally {
          setBusy(false)
        }
      }}>Vrati demo na početno stanje</Button>
      {msg && <p className="mt-3 text-sm text-autoput">{msg}</p>}
    </Panel>
  )
}
