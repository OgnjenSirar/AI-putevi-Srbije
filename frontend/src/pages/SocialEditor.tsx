import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { AlertTriangle, ArrowLeft, Check, ImagePlus, Send, Sparkles, Upload } from 'lucide-react'
import { api } from '../lib/api'
import { fmtDate } from '../lib/format'
import { Button, Chip, ErrorNote, Field, Panel, Spinner, Tabs, inputCls } from '../components/ui'
import type { Post } from './Social'

type TplDef = { code: string; label: string; fields: { key: string; label: string; type: 'text' | 'choice'; max?: number; options?: string[] }[] }
type Meta = { templates: TplDef[]; formats: Record<string, { w: number; h: number; label: string }>; imagegen: { status: string; error?: string } }

export default function SocialEditorPage() {
  const { id } = useParams()
  const qc = useQueryClient()
  const { data: p, isLoading } = useQuery({ queryKey: ['post', id], queryFn: () => api.get<Post>(`/api/social/posts/${id}`) })
  const { data: meta } = useQuery({ queryKey: ['social-meta'], queryFn: () => api.get<Meta>('/api/social/templates') })
  const [fmt, setFmt] = useState('portret')
  const [form, setForm] = useState<{ template_code: string; fields: Record<string, string>; fb_text: string; ig_text: string; alt_text: string; image_prompt: string } | null>(null)
  const [busy, setBusy] = useState<string | null>(null)
  const [error, setError] = useState<unknown>(null)

  useEffect(() => {
    if (p) setForm({ template_code: p.template_code, fields: { ...p.fields }, fb_text: p.fb_text, ig_text: p.ig_text, alt_text: p.alt_text, image_prompt: p.image_prompt })
  }, [p?.id, p?.status, p?.images?.portret])

  if (isLoading || !p || !form || !meta) return <Spinner />
  const tpl = meta.templates.find((t) => t.code === form.template_code)!
  const published = p.status === 'objavljeno'
  const dirty = JSON.stringify(form) !== JSON.stringify({ template_code: p.template_code, fields: p.fields, fb_text: p.fb_text, ig_text: p.ig_text, alt_text: p.alt_text, image_prompt: p.image_prompt })

  async function run(name: string, fn: () => Promise<unknown>) {
    setBusy(name)
    setError(null)
    try {
      const r = await fn()
      if (r && typeof r === 'object' && 'id' in r) qc.setQueryData(['post', id], r)
      qc.invalidateQueries({ queryKey: ['posts'] })
    } catch (e) {
      setError(e)
    } finally {
      setBusy(null)
    }
  }

  const save = (extra: Record<string, unknown> = {}) => run('save', () => api.put(`/api/social/posts/${p.id}`, { ...form, ...extra }))

  return (
    <div className="max-w-[1300px]">
      <Link to="/mreze" className="inline-flex items-center gap-1.5 text-sm text-sivo hover:text-grafit">
        <ArrowLeft className="size-4" /> Društvene mreže
      </Link>
      <div className="mt-2 flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-[26px] font-extrabold">{p.fields.naslov || 'Objava'}</h1>
          <div className="text-sm text-sivo">
            {p.created_by}, {fmtDate(p.created_at)}
            {p.ai_meta?.mode === 'mock' && ', tekst iz rezervnog režima'}
          </div>
        </div>
        <div className="flex flex-wrap gap-2">
          {!published && p.status !== 'odobreno' && (
            <Button icon={<Check className="size-4" />} disabled={dirty} loading={busy === 'approve'} onClick={() => run('approve', () => api.post(`/api/social/posts/${p.id}/approve`))}>
              Odobri objavu
            </Button>
          )}
          {p.status === 'odobreno' && (
            <Button variant="primary" icon={<Send className="size-4" />} loading={busy === 'publish'} onClick={() => run('publish', () => api.post(`/api/social/posts/${p.id}/publish`))}>
              Objavi na Facebook i Instagram
            </Button>
          )}
          {published && <Chip tone="autoput">objavljeno {fmtDate(p.published_at)}</Chip>}
        </div>
      </div>
      {p.status === 'odobreno' && <p className="mt-2 text-[13px] text-sivo">Odobrio {p.approved_by}. Objava je u demou simulirana: sistem pravi tačne pozive Meta Graph API-ja, ali ih ne šalje.</p>}
      <ErrorNote error={error} />

      <div className="mt-5 grid lg:grid-cols-[minmax(0,460px)_minmax(0,1fr)] gap-5 items-start">
        <div className="space-y-4 lg:sticky lg:top-5">
          <Tabs value={fmt} onChange={setFmt} items={Object.entries(meta.formats).map(([k, v]) => ({ value: k, label: k === 'kvadrat' ? 'Kvadrat' : k === 'portret' ? 'Portret' : 'Story' }))} />
          <div className="bg-papir border border-linija rounded-[10px] p-3">
            {p.images[fmt] ? <img src={p.images[fmt]} alt={p.alt_text} className="w-full rounded-[6px]" /> : <div className="aspect-[4/5] bg-beton rounded" />}
            <div className="mt-2 text-[12.5px] text-sivo">{meta.formats[fmt]?.label}, {meta.formats[fmt]?.w} x {meta.formats[fmt]?.h} px</div>
          </div>
          {p.render_warnings?.length > 0 && (
            <ul className="space-y-1">
              {p.render_warnings.map((w, i) => (
                <li key={i} className={`flex gap-2 text-[13px] ${w.tip === 'preliv' ? 'text-stop' : 'text-signal-ink'}`}>
                  <AlertTriangle className="size-4 shrink-0 mt-0.5" /> {w.poruka}
                </li>
              ))}
            </ul>
          )}
          {!published && (
            <Panel title="Pozadina">
              <p className="text-[13px] text-sivo">Tekst na slici uvek ispisuje šablon. AI generiše samo pozadinu bez teksta, a slika se označava kao AI sadržaj.</p>
              <Field label="Opis pozadine za AI (engleski)">
                <textarea className={`${inputCls} min-h-16 mt-1`} value={form.image_prompt} onChange={(e) => setForm({ ...form, image_prompt: e.target.value })} />
              </Field>
              <div className="mt-2 flex flex-wrap gap-2">
                <Button size="sm" variant="signal" icon={<Sparkles className="size-3.5" />} disabled={meta.imagegen.status !== 'ok'} loading={busy === 'bg'} onClick={() => run('bg', () => api.post(`/api/social/posts/${p.id}/background`, { prompt: form.image_prompt }))}>
                  Generiši AI pozadinu
                </Button>
                <label className="inline-flex items-center gap-2 h-8 px-3 text-[13px] rounded-[7px] border border-linija bg-papir cursor-pointer hover:border-sivo">
                  <Upload className="size-3.5" /> Sopstvena fotografija
                  <input type="file" accept="image/*" className="sr-only" onChange={(e) => {
                    const f = e.target.files?.[0]
                    if (!f) return
                    const fd = new FormData()
                    fd.append('file', f)
                    run('upload', () => api.form(`/api/social/posts/${p.id}/background-upload`, fd))
                  }} />
                </label>
                {p.background && <Button size="sm" variant="ghost" onClick={() => save({ remove_background: true })}>Ukloni pozadinu</Button>}
              </div>
              {meta.imagegen.status !== 'ok' && <p className="mt-2 text-[12.5px] text-sivo">Servis za generisanje slika trenutno nije dostupan ({meta.imagegen.status}).</p>}
              {busy === 'bg' && <p className="mt-2 text-[13px] text-signal-ink">Generisanje traje nekoliko sekundi.</p>}
            </Panel>
          )}
        </div>

        <div className="space-y-5">
          <Panel title="Sadržaj slike">
            <Field label="Šablon">
              <select className={inputCls} value={form.template_code} disabled={published} onChange={(e) => setForm({ ...form, template_code: e.target.value })}>
                {meta.templates.map((t) => <option key={t.code} value={t.code}>{t.label}</option>)}
              </select>
            </Field>
            <div className="mt-3 space-y-3">
              {tpl.fields.map((f) =>
                f.type === 'choice' ? (
                  <Field key={f.key} label={f.label}>
                    <select className={inputCls} disabled={published} value={form.fields[f.key] ?? ''} onChange={(e) => setForm({ ...form, fields: { ...form.fields, [f.key]: e.target.value } })}>
                      {f.options?.map((o) => <option key={o} value={o}>{o}</option>)}
                    </select>
                  </Field>
                ) : (
                  <Field key={f.key} label={f.label} hint={<span className={(form.fields[f.key]?.length ?? 0) > (f.max ?? 999) ? 'text-stop' : ''}>{form.fields[f.key]?.length ?? 0} / {f.max} znakova</span>}>
                    <input className={inputCls} disabled={published} value={form.fields[f.key] ?? ''} onChange={(e) => setForm({ ...form, fields: { ...form.fields, [f.key]: e.target.value } })} />
                  </Field>
                ),
              )}
            </div>
          </Panel>
          <Panel title="Tekst objave">
            <div className="space-y-3">
              <Field label="Facebook" hint={`${form.fb_text.length} znakova`}>
                <textarea className={`${inputCls} min-h-28`} disabled={published} value={form.fb_text} onChange={(e) => setForm({ ...form, fb_text: e.target.value })} />
              </Field>
              <Field label="Instagram" hint={`${form.ig_text.length} znakova`}>
                <textarea className={`${inputCls} min-h-24`} disabled={published} value={form.ig_text} onChange={(e) => setForm({ ...form, ig_text: e.target.value })} />
              </Field>
              <Field label="Alternativni tekst slike (za slabovide)">
                <input className={inputCls} disabled={published} value={form.alt_text} onChange={(e) => setForm({ ...form, alt_text: e.target.value })} />
              </Field>
            </div>
            {!published && (
              <div className="mt-4 flex items-center gap-3">
                <Button variant="primary" icon={<ImagePlus className="size-4" />} disabled={!dirty} loading={busy === 'save'} onClick={() => save()}>
                  Sačuvaj i osveži sliku
                </Button>
                {dirty && <span className="text-[13px] text-signal-ink">Izmene nisu sačuvane. Odobrenje je moguće posle čuvanja.</span>}
              </div>
            )}
          </Panel>
          {p.publish_log?.length > 0 && (
            <Panel title="Pozivi Meta Graph API (simulacija)">
              <p className="text-[13px] text-sivo mb-3">Ovo su tačni zahtevi koje bi produkcija poslala. Token se čuva u sefu za tajne i nikad se ne prikazuje.</p>
              <ol className="space-y-2">
                {p.publish_log.map((l, i) => (
                  <li key={i}>
                    <details className="rounded-[8px] border border-linija">
                      <summary className="cursor-pointer px-3 py-2 text-sm">
                        <span className="num font-semibold mr-2">{l.metod}</span>{l.korak}
                      </summary>
                      <div className="px-3 pb-3 text-[12.5px]">
                        <div className="num break-all text-enp">{l.url}</div>
                        <pre className="mt-2 bg-beton/70 rounded p-2 overflow-x-auto">{JSON.stringify(l.telo, null, 2)}</pre>
                        <div className="mt-1 text-sivo">Odgovor</div>
                        <pre className="bg-beton/70 rounded p-2 overflow-x-auto">{JSON.stringify(l.odgovor, null, 2)}</pre>
                      </div>
                    </details>
                  </li>
                ))}
              </ol>
            </Panel>
          )}
        </div>
      </div>
    </div>
  )
}
