import { useEffect, useRef, useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { History, Plus, Search } from 'lucide-react'
import { api } from '../lib/api'
import { useCategories, useUnits } from '../lib/hooks'
import { fmtDate } from '../lib/format'
import { Button, Chip, Empty, ErrorNote, Field, Modal, Panel, Spinner, Tabs, inputCls } from '../components/ui'

type Tpl = { id: number; code: string; title: string; category: string; org_unit: { id: number; code: string } | null; body: string; tags: string[]; active: boolean; version: number; updated_by: string; updated_at: string; indexed: boolean; variables: string[] }
type TplDetail = Tpl & { preview: string; unknown_variables: string[]; versions: { version: number; title: string; body: string; changed_by: string; changed_at: string; change_note: string }[] }
type Var = { id: number; key: string; label: string; value: string; group: string; owner: string; version: number; verified_at: string; updated_at: string; stale: boolean; used_in: string[]; history: { value: string; changed_by: string; changed_at: string; change_note: string }[] }

const GROUPS: Record<string, string> = { cene: 'Cene', rokovi: 'Rokovi', kontakti: 'Kontakti', lokacije: 'Lokacije', pravila: 'Pravila', linkovi: 'Linkovi', ostalo: 'Ostalo' }

export default function KnowledgePage() {
  const [tab, setTab] = useState<'obrasci' | 'promenljive' | 'pretraga'>('obrasci')
  return (
    <div className="max-w-[1300px]">
      <h1 className="text-[28px] font-extrabold">Znanje službe</h1>
      <p className="text-sivo text-sm max-w-2xl">
        Obrasci odgovora i promenljivi podaci na kojima AI zasniva predloge. Cene, rokove i kontakte AI ne piše sam, već ih sistem upisuje iz ove evidencije.
      </p>
      <div className="mt-4">
        <Tabs value={tab} onChange={setTab} items={[{ value: 'obrasci', label: 'Obrasci odgovora' }, { value: 'promenljive', label: 'Promenljivi podaci' }, { value: 'pretraga', label: 'Provera pretrage' }]} />
      </div>
      <div className="mt-5">{tab === 'obrasci' ? <Templates /> : tab === 'promenljive' ? <Variables /> : <SearchTest />}</div>
    </div>
  )
}

function Templates() {
  const { data, isLoading } = useQuery({ queryKey: ['templates'], queryFn: () => api.get<Tpl[]>('/api/knowledge/templates') })
  const [sel, setSel] = useState<number | 'novi' | null>(null)
  useEffect(() => {
    if (sel === null && data?.length) setSel(data[0].id)
  }, [data, sel])
  if (isLoading) return <Spinner />
  return (
    <div className="grid lg:grid-cols-[320px_minmax(0,1fr)] gap-5 items-start">
      <div className="bg-papir border border-linija rounded-[10px] overflow-hidden">
        <div className="p-2 border-b border-linija">
          <Button size="sm" className="w-full" icon={<Plus className="size-4" />} onClick={() => setSel('novi')}>Novi obrazac</Button>
        </div>
        <ul className="max-h-[70vh] overflow-auto scroll-thin divide-y divide-linija">
          {data?.map((t) => (
            <li key={t.id}>
              <button onClick={() => setSel(t.id)} className={`w-full text-left px-3 py-2.5 ${sel === t.id ? 'bg-autoput-soft' : 'hover:bg-beton/60'}`}>
                <div className="flex items-center justify-between gap-2">
                  <span className="num text-[13px] font-semibold">{t.code}</span>
                  <span className="text-[12px] text-sivo">v{t.version}{!t.active ? ', neaktivan' : ''}</span>
                </div>
                <div className="text-sm">{t.title}</div>
              </button>
            </li>
          ))}
        </ul>
      </div>
      {sel === 'novi' ? <TemplateEditor key="novi" onSaved={(id) => setSel(id)} /> : sel ? <TemplateEditor key={sel} id={sel} onSaved={() => {}} /> : null}
    </div>
  )
}

function TemplateEditor({ id, onSaved }: { id?: number; onSaved: (id: number) => void }) {
  const qc = useQueryClient()
  const units = useUnits().data
  const cats = useCategories()
  const vars = useQuery({ queryKey: ['variables'], queryFn: () => api.get<Var[]>('/api/knowledge/variables') }).data
  const { data } = useQuery({ queryKey: ['template', id], queryFn: () => api.get<TplDetail>(`/api/knowledge/templates/${id}`), enabled: !!id })
  const [f, setF] = useState({ code: '', title: '', category: 'opste_informacije', org_unit_id: 1 as number | null, body: '', tags: '', active: true, change_note: '' })
  const [error, setError] = useState<unknown>(null)
  const [busy, setBusy] = useState(false)
  const [showVersion, setShowVersion] = useState<TplDetail['versions'][number] | null>(null)
  const ta = useRef<HTMLTextAreaElement>(null)
  useEffect(() => {
    if (data) setF({ code: data.code, title: data.title, category: data.category, org_unit_id: data.org_unit?.id ?? null, body: data.body, tags: data.tags.join(', '), active: data.active, change_note: '' })
  }, [data])

  function insertVar(key: string) {
    const el = ta.current
    const token = `{{${key}}}`
    if (!el) return setF({ ...f, body: f.body + token })
    const s = el.selectionStart
    const nb = f.body.slice(0, s) + token + f.body.slice(el.selectionEnd)
    setF({ ...f, body: nb })
    requestAnimationFrame(() => { el.focus(); el.selectionStart = el.selectionEnd = s + token.length })
  }

  async function save() {
    setBusy(true)
    setError(null)
    try {
      const payload = { ...f, tags: f.tags.split(',').map((x) => x.trim()).filter(Boolean) }
      const r = id ? await api.put<{ id: number }>(`/api/knowledge/templates/${id}`, payload) : await api.post<{ id: number }>('/api/knowledge/templates', payload)
      qc.invalidateQueries({ queryKey: ['templates'] })
      qc.invalidateQueries({ queryKey: ['template', r.id] })
      onSaved(r.id)
      setF((x) => ({ ...x, change_note: '' }))
    } catch (e) {
      setError(e)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="grid xl:grid-cols-[minmax(0,1fr)_330px] gap-5 items-start">
      <Panel title={id ? `Obrazac ${data?.code ?? ''}` : 'Novi obrazac'} actions={data && <span className="text-[13px] text-sivo">verzija {data.version}, {data.updated_by}, {fmtDate(data.updated_at)}</span>}>
        <div className="grid sm:grid-cols-[140px_1fr] gap-3">
          <Field label="Šifra"><input className={inputCls} value={f.code} disabled={!!id} onChange={(e) => setF({ ...f, code: e.target.value })} /></Field>
          <Field label="Naslov"><input className={inputCls} value={f.title} onChange={(e) => setF({ ...f, title: e.target.value })} /></Field>
        </div>
        <div className="mt-3 grid sm:grid-cols-2 gap-3">
          <Field label="Kategorija">
            <select className={inputCls} value={f.category} onChange={(e) => setF({ ...f, category: e.target.value })}>
              {cats.map((c) => <option key={c.code} value={c.code}>{c.label}</option>)}
            </select>
          </Field>
          <Field label="Jedinica">
            <select className={inputCls} value={f.org_unit_id ?? ''} onChange={(e) => setF({ ...f, org_unit_id: Number(e.target.value) })}>
              {units?.map((u) => <option key={u.id} value={u.id}>{u.code}, {u.name}</option>)}
            </select>
          </Field>
        </div>
        <div className="mt-3">
          <Field label="Tekst obrasca" hint="Promenljive se pišu kao {{var.kljuc}}. Oznaka [PROVERA: ...] označava podatak iz naplatnog sistema koji operater popunjava.">
            <textarea ref={ta} className={`${inputCls} min-h-[260px] leading-relaxed`} value={f.body} onChange={(e) => setF({ ...f, body: e.target.value })} />
          </Field>
        </div>
        <div className="mt-3 grid sm:grid-cols-2 gap-3">
          <Field label="Oznake za pretragu (odvojene zarezom)"><input className={inputCls} value={f.tags} onChange={(e) => setF({ ...f, tags: e.target.value })} /></Field>
          <Field label="Napomena o izmeni"><input className={inputCls} value={f.change_note} onChange={(e) => setF({ ...f, change_note: e.target.value })} placeholder="npr. usklađeno sa novim cenovnikom" /></Field>
        </div>
        <label className="mt-3 flex items-center gap-2 text-sm"><input type="checkbox" checked={f.active} onChange={(e) => setF({ ...f, active: e.target.checked })} /> Aktivan (koristi se u predlozima)</label>
        <ErrorNote error={error} />
        <div className="mt-4 flex gap-2">
          <Button variant="primary" loading={busy} onClick={save} disabled={!f.code || !f.title || !f.body}>{id ? 'Sačuvaj novu verziju' : 'Sačuvaj obrazac'}</Button>
        </div>
        {data && (
          <div className="mt-5">
            <div className="text-[13px] text-sivo mb-1">Pregled sa trenutnim vrednostima promenljivih</div>
            <div className="prose-mail rounded-[8px] bg-beton/60 p-3 text-[14px]">{data.preview}</div>
            {data.unknown_variables.length > 0 && <p className="mt-2 text-[13px] text-stop">Nepoznate promenljive: {data.unknown_variables.join(', ')}</p>}
          </div>
        )}
      </Panel>
      <div className="space-y-5">
        <Panel title="Ubaci promenljivu">
          <div className="max-h-72 overflow-auto scroll-thin space-y-0.5">
            {[['korisnik.ime', 'Ime korisnika'], ['predmet.broj', 'Broj predmeta']].map(([k, l]) => (
              <button key={k} className="w-full text-left text-[13px] px-2 py-1 rounded hover:bg-beton" onClick={() => insertVar(k)}>
                <span className="num">{`{{${k}}}`}</span> <span className="text-sivo">{l}</span>
              </button>
            ))}
            {vars?.map((v) => (
              <button key={v.id} className="w-full text-left text-[13px] px-2 py-1 rounded hover:bg-beton" onClick={() => insertVar(`var.${v.key}`)} title={v.value}>
                <span className="num">{v.key}</span> <span className="text-sivo">{v.label}</span>
              </button>
            ))}
          </div>
        </Panel>
        {data && (
          <Panel title="Istorija izmena" actions={<History className="size-4 text-sivo" />}>
            <ul className="space-y-2">
              {data.versions.map((v) => (
                <li key={v.version} className="text-[13px]">
                  <button className="text-left hover:underline" onClick={() => setShowVersion(v)}>
                    <b>v{v.version}</b> {v.changed_by}, {fmtDate(v.changed_at)}
                  </button>
                  {v.change_note && <div className="text-sivo">{v.change_note}</div>}
                </li>
              ))}
            </ul>
          </Panel>
        )}
      </div>
      <Modal open={!!showVersion} onClose={() => setShowVersion(null)} title={`Verzija ${showVersion?.version}`} wide>
        <div className="prose-mail text-[14px]">{showVersion?.body}</div>
      </Modal>
    </div>
  )
}

function Variables() {
  const qc = useQueryClient()
  const { data, isLoading } = useQuery({ queryKey: ['variables'], queryFn: () => api.get<Var[]>('/api/knowledge/variables') })
  const [edit, setEdit] = useState<Var | null>(null)
  const [val, setVal] = useState('')
  const [note, setNote] = useState('')
  const [busy, setBusy] = useState(false)
  if (isLoading) return <Spinner />
  const groups = Object.keys(GROUPS).filter((g) => data?.some((v) => v.group === g))
  return (
    <div className="space-y-5">
      {groups.map((g) => (
        <Panel key={g} title={GROUPS[g]} pad={false}>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-[13px] text-sivo border-y border-linija">
                  <th className="px-4 py-2 font-medium">Podatak</th>
                  <th className="px-4 py-2 font-medium">Vrednost</th>
                  <th className="px-4 py-2 font-medium">Vlasnik</th>
                  <th className="px-4 py-2 font-medium">Potvrđeno</th>
                  <th className="px-4 py-2" />
                </tr>
              </thead>
              <tbody className="divide-y divide-linija">
                {data?.filter((v) => v.group === g).map((v) => (
                  <tr key={v.id}>
                    <td className="px-4 py-2.5">
                      <div>{v.label}</div>
                      <div className="num text-[12.5px] text-sivo">{v.key}{v.used_in.length ? `, u obrascima ${v.used_in.join(', ')}` : ''}</div>
                    </td>
                    <td className="px-4 py-2.5 max-w-sm">{v.value}</td>
                    <td className="px-4 py-2.5 text-[13px] text-sivo">{v.owner}</td>
                    <td className="px-4 py-2.5 text-[13px]">
                      {fmtDate(v.verified_at, false)}
                      {v.stale && <div><Chip tone="signal">potvrditi</Chip></div>}
                    </td>
                    <td className="px-4 py-2.5 text-right">
                      <Button size="sm" onClick={() => { setEdit(v); setVal(v.value); setNote('') }}>Izmeni</Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Panel>
      ))}
      <Modal open={!!edit} onClose={() => setEdit(null)} title={edit?.label ?? ''}>
        {edit && (
          <div className="space-y-4">
            <Field label="Vrednost"><textarea className={`${inputCls} min-h-20`} value={val} onChange={(e) => setVal(e.target.value)} /></Field>
            <Field label="Napomena o izmeni"><input className={inputCls} value={note} onChange={(e) => setNote(e.target.value)} placeholder="npr. novi cenovnik od 1. novembra" /></Field>
            <p className="text-[13px] text-sivo">Nova vrednost se odmah koristi u svim novim predlozima odgovora{edit.used_in.length ? ` (obrasci ${edit.used_in.join(', ')})` : ''}. Čuvanje bez izmene vrednosti beleži da je podatak ponovo potvrđen.</p>
            <div>
              <div className="text-[13px] text-sivo mb-1">Istorija</div>
              <ul className="text-[13px] space-y-1">
                {edit.history.map((h, i) => (
                  <li key={i}><b>{h.value}</b> <span className="text-sivo">{h.changed_by}, {fmtDate(h.changed_at, false)}{h.change_note ? `, ${h.change_note}` : ''}</span></li>
                ))}
              </ul>
            </div>
            <div className="flex justify-end gap-2">
              <Button onClick={() => setEdit(null)}>Otkaži</Button>
              <Button variant="primary" loading={busy} onClick={async () => {
                setBusy(true)
                await api.put(`/api/knowledge/variables/${edit.id}`, { key: edit.key, label: edit.label, value: val, group: edit.group, owner: edit.owner, change_note: note })
                setBusy(false)
                setEdit(null)
                qc.invalidateQueries({ queryKey: ['variables'] })
              }}>Sačuvaj</Button>
            </div>
          </div>
        )}
      </Modal>
    </div>
  )
}

function SearchTest() {
  const [q, setQ] = useState('rampa se nije podigla iako imam tag')
  const [res, setRes] = useState<{ embeddings: boolean; results: { code: string; title: string; score: number; metode: string[] }[] } | null>(null)
  const [busy, setBusy] = useState(false)
  return (
    <Panel title="Kako AI pronalazi obrasce">
      <p className="text-sm text-sivo">Unesite tekst kao da je pitanje korisnika. Pretraga kombinuje tekstualno poklapanje, semantičku sličnost (BGE-M3) i preraspoređivanje (reranker).</p>
      <div className="mt-3 flex gap-2">
        <input className={inputCls} value={q} onChange={(e) => setQ(e.target.value)} aria-label="Upit" />
        <Button variant="primary" icon={<Search className="size-4" />} loading={busy} onClick={async () => { setBusy(true); setRes(await api.post('/api/knowledge/search', { query: q })); setBusy(false) }}>Pretraži</Button>
      </div>
      {res && (
        <div className="mt-4">
          {!res.embeddings && <p className="text-[13px] text-signal-ink mb-2">Servis za semantičku pretragu trenutno nije dostupan, rezultati su samo iz tekstualne pretrage.</p>}
          {res.results.length ? (
            <ol className="divide-y divide-linija">
              {res.results.map((r) => (
                <li key={r.code} className="py-2 flex items-center justify-between gap-3 text-sm">
                  <span><span className="num font-semibold">{r.code}</span> {r.title}</span>
                  <span className="text-sivo text-[13px]">{r.metode.join(', ')} <span className="num">{r.score.toFixed(3)}</span></span>
                </li>
              ))}
            </ol>
          ) : (
            <Empty title="Nema pogodaka" />
          )}
        </div>
      )}
    </Panel>
  )
}
