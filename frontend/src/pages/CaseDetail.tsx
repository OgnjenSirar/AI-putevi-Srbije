import { useEffect, useMemo, useRef, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { AlertTriangle, ArrowLeft, Bot, CheckCircle2, Info, Loader2, Paperclip, Phone, RefreshCw, Send, ShieldAlert, Sparkles } from 'lucide-react'
import { api } from '../lib/api'
import { useAuth } from '../lib/auth'
import { useCategories, useUnits } from '../lib/hooks'
import { EDIT_LABEL, PRIORITY_LABEL, fmtDate, fmtDuration, relTime } from '../lib/format'
import type { CaseDetail, EmailMsg, Suggestion } from '../lib/types'
import { Button, Chip, DueChip, ErrorNote, Field, Modal, Panel, PriorityBadge, Spinner, StatusBadge, inputCls } from '../components/ui'

export default function CaseDetailPage() {
  const { id } = useParams()
  const qc = useQueryClient()
  const { user } = useAuth()
  const { data: c, isLoading } = useQuery({
    queryKey: ['case', id],
    queryFn: () => api.get<CaseDetail>(`/api/cases/${id}`),
    refetchInterval: (q) => (q.state.data && ['pending', 'processing'].includes(q.state.data.ai_status) ? 3000 : false),
  })
  const [forwardOpen, setForwardOpen] = useState(false)
  const refresh = () => {
    qc.invalidateQueries({ queryKey: ['case', id] })
    qc.invalidateQueries({ queryKey: ['cases'] })
  }

  if (isLoading || !c) return <Spinner />
  const closed = c.status === 'zatvoreno'
  const mine = c.assigned_to?.id === user?.id

  return (
    <div className="max-w-[1400px]">
      <Link to="/predmeti" className="inline-flex items-center gap-1.5 text-sm text-sivo hover:text-grafit">
        <ArrowLeft className="size-4" /> Predmeti
      </Link>
      <header className="mt-2 flex flex-wrap items-start justify-between gap-4">
        <div className="min-w-0">
          <div className="num text-[15px] font-semibold text-autoput">{c.number}</div>
          <h1 className="text-[26px] font-extrabold leading-tight">{c.subject}</h1>
          <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-2 text-sm">
            <StatusBadge status={c.status} />
            <PriorityBadge priority={c.priority} />
            <span className="inline-flex items-center gap-1.5 text-sivo">
              Rok <DueChip due={c.due_at} closed={closed || c.status === 'odgovoreno'} />
            </span>
            <span className="text-sivo">{c.channel === 'telefon' ? 'telefon' : 'e-pošta'}, otvoren {fmtDate(c.created_at)}</span>
            {c.script === 'cyrillic' && <Chip>ćirilica</Chip>}
            {c.language !== 'sr' && <Chip tone="enp">jezik: {c.language}</Chip>}
            <span className="text-sivo">Obrađuje: {c.assigned_to?.name ?? 'niko'}</span>
          </div>
        </div>
        <div className="flex flex-wrap gap-2">
          {!mine && !closed && (
            <Button variant="primary" onClick={async () => { await api.post(`/api/cases/${c.id}/assign`); refresh() }}>
              Preuzmi predmet
            </Button>
          )}
          {!closed && <Button onClick={() => setForwardOpen(true)}>Prosledi</Button>}
          {!closed ? (
            <Button onClick={async () => { await api.post(`/api/cases/${c.id}/status`, { status: 'zatvoreno' }); refresh() }}>Zatvori bez odgovora</Button>
          ) : (
            <Button onClick={async () => { await api.post(`/api/cases/${c.id}/status`, { status: 'u_obradi', note: 'Predmet ponovo otvoren.' }); refresh() }}>Ponovo otvori</Button>
          )}
        </div>
      </header>

      <div className="mt-6 grid xl:grid-cols-[minmax(0,1fr)_400px] gap-5 items-start">
        <div className="space-y-5 min-w-0">
          <Thread emails={c.emails} />
          {!closed && <ReplyBox c={c} onSent={refresh} />}
          <Timeline c={c} onNote={refresh} />
        </div>
        <aside className="space-y-5">
          <RoutingPanel c={c} onChange={refresh} />
          {(c.needs_billing_check || c.suggestion?.billing_check?.potrebna) && <BillingPanel c={c} onChange={refresh} />}
          <CustomerPanel c={c} />
          {c.suggestion && <AiDetails s={c.suggestion} count={c.suggestion_count} caseId={c.id} onReanalyze={refresh} />}
        </aside>
      </div>
      <ForwardModal open={forwardOpen} onClose={() => setForwardOpen(false)} caseId={c.id} onDone={refresh} />
    </div>
  )
}

// ------------------------------------------------------------------ prepiska

function Thread({ emails }: { emails: EmailMsg[] }) {
  return (
    <Panel title={`Prepiska (${emails.length})`}>
      <ol className="space-y-4">
        {emails.map((e) => (
          <MessageItem key={e.id} e={e} />
        ))}
        {!emails.length && <p className="text-sivo text-sm">Predmet nema poruka, otvoren je iz telefonskog poziva.</p>}
      </ol>
    </Panel>
  )
}

function MessageItem({ e }: { e: EmailMsg }) {
  const [full, setFull] = useState(false)
  const hasQuote = e.body_clean && e.body_clean.trim() !== e.body.trim()
  const out = e.direction === 'out'
  return (
    <li className={`rounded-[8px] border ${out ? 'border-autoput/30 bg-autoput-soft/40 ml-6' : 'border-linija mr-6'}`}>
      <div className="flex flex-wrap items-baseline justify-between gap-2 px-4 pt-3">
        <div className="text-sm">
          <span className="font-semibold">{out ? 'Korisnički centar' : e.from_name || e.from_addr}</span>{' '}
          <span className="text-sivo">{out ? `za ${e.to_addr}` : `<${e.from_addr}>`}</span>
        </div>
        <time className="text-[13px] text-sivo" dateTime={e.received_at}>{fmtDate(e.received_at)}</time>
      </div>
      <div className="px-4 text-[13px] text-sivo">{e.subject}</div>
      <div className="prose-mail px-4 py-3">{full || !hasQuote ? e.body : e.body_clean}</div>
      {hasQuote && (
        <button className="px-4 pb-2 text-[13px] text-enp hover:underline" onClick={() => setFull(!full)}>
          {full ? 'Sakrij citiranu prepisku' : 'Prikaži citiranu prepisku'}
        </button>
      )}
      {e.attachments?.length > 0 && (
        <div className="px-4 pb-3 space-y-2">
          {e.attachments.map((a) => (
            <details key={a.name} className="rounded-[7px] bg-beton/70 px-3 py-2 text-sm">
              <summary className="cursor-pointer inline-flex items-center gap-2">
                <Paperclip className="size-3.5" /> {a.name} <span className="text-sivo">({Math.max(1, Math.round(a.size / 1024))} KB)</span>
              </summary>
              {a.text && (
                <div className="mt-2">
                  <div className="text-[12.5px] text-sivo">Tekst izdvojen iz priloga, dostupan AI analizi:</div>
                  <pre className="prose-mail text-[13px] mt-1">{a.text}</pre>
                </div>
              )}
            </details>
          ))}
        </div>
      )}
    </li>
  )
}

// ------------------------------------------------------------------ odgovor

function countChecks(t: string) {
  return (t.match(/\[PROVERA:[^\]]*\]/g) ?? []).length
}

function ReplyBox({ c, onSent }: { c: CaseDetail; onSent: () => void }) {
  const s = c.suggestion
  const usable = s && !s.finalized_at
  const [text, setText] = useState(usable ? s.draft : '')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<unknown>(null)
  const [result, setResult] = useState<string | null>(null)
  useEffect(() => {
    if (s && !s.finalized_at) setText(s.draft)
  }, [s?.id])
  const taRef = useRef<HTMLTextAreaElement>(null)
  useEffect(() => {
    const el = taRef.current
    if (!el) return
    el.style.height = 'auto'
    el.style.height = `${Math.min(900, Math.max(300, el.scrollHeight + 4))}px`
  }, [text])
  const edited = usable && text.trim() !== s.draft.trim()
  const checks = countChecks(text)
  const aiBusy = ['pending', 'processing'].includes(c.ai_status)

  async function send(close: boolean) {
    if (checks > 0 && !window.confirm(`U odgovoru je ostalo ${checks} oznaka [PROVERA]. Poslati ipak?`)) return
    setBusy(true)
    setError(null)
    try {
      const r = await api.post<{ sent: boolean; metrics: { edit_ratio: number; edit_class: string } | null }>(`/api/cases/${c.id}/reply`, {
        text,
        suggestion_id: usable ? s.id : null,
        close,
      })
      setResult(
        (r.sent ? 'Odgovor je poslat.' : 'Odgovor je sačuvan, ali SMTP server nije dostupan.') +
          (r.metrics ? ` AI predlog korišćen ${EDIT_LABEL[r.metrics.edit_class]} (${Math.round(r.metrics.edit_ratio * 100)}% izmena).` : ''),
      )
      onSent()
    } catch (e) {
      setError(e)
    } finally {
      setBusy(false)
    }
  }

  return (
    <Panel
      title="Odgovor korisniku"
      actions={
        usable && edited ? (
          <button className="text-[13px] text-enp hover:underline" onClick={() => setText(s.draft)}>
            Vrati AI predlog
          </button>
        ) : null
      }
    >
      {aiBusy && (
        <p className="mb-3 inline-flex items-center gap-2 text-sm text-signal-ink">
          <Loader2 className="size-4 animate-spin" /> AI priprema predlog odgovora
        </p>
      )}
      {usable && (
        <div className="mb-3 space-y-1.5">
          <div className="flex flex-wrap items-center gap-2 text-[13px] text-sivo">
            <Sparkles className="size-4 text-signal-ink" />
            Predlog AI na osnovu obrazaca{' '}
            {s.sources.filter((x) => x.koriscen).map((x) => (
              <Chip key={x.code} tone="signal">{x.code}</Chip>
            ))}
            {!s.sources.some((x) => x.koriscen) && <span>bez obrasca</span>}
          </div>
          <Warnings items={s.warnings} />
          {s.operator_note && <p className="text-[13px] text-sivo">Napomena za operatera: {s.operator_note}</p>}
        </div>
      )}
      <div className={`rounded-[8px] ${usable && !edited ? 'lane-proposed bg-signal-soft/40' : edited ? 'lane-confirmed' : ''}`}>
        <textarea
          ref={taRef}
          className={`${inputCls} min-h-[300px] font-sans leading-relaxed text-[14.5px] border-l-0 rounded-l-none`}
          value={text}
          onChange={(e) => setText(e.target.value)}
          aria-label="Tekst odgovora"
          placeholder="Napišite odgovor korisniku"
        />
      </div>
      <div className="mt-2 flex flex-wrap items-center justify-between gap-3">
        <span className={`text-[13px] ${checks ? 'text-stop font-medium' : 'text-sivo'}`}>
          {checks ? `Zamenite ${checks} ${checks === 1 ? 'oznaku' : 'oznake'} [PROVERA] podatkom iz naplatnog sistema` : usable ? (edited ? 'Predlog je izmenjen' : 'Predlog nije menjan') : ''}
        </span>
        <div className="flex gap-2">
          <Button onClick={() => send(false)} loading={busy} disabled={!text.trim()}>
            Pošalji, ostavi otvoren
          </Button>
          <Button variant="primary" icon={<Send className="size-4" />} onClick={() => send(true)} loading={busy} disabled={!text.trim()}>
            Pošalji i zatvori
          </Button>
        </div>
      </div>
      {result && (
        <p className="mt-3 inline-flex items-center gap-2 text-sm text-autoput">
          <CheckCircle2 className="size-4" /> {result}
        </p>
      )}
      <ErrorNote error={error} />
    </Panel>
  )
}

function Warnings({ items }: { items: Suggestion['warnings'] }) {
  if (!items?.length) return null
  return (
    <ul className="space-y-1">
      {items.map((w, i) => (
        <li key={i} className={`flex items-start gap-2 text-[13px] ${w.nivo === 'upozorenje' || w.nivo === 'vazno' ? 'text-stop' : 'text-sivo'}`}>
          {w.nivo === 'info' ? <Info className="size-4 shrink-0 mt-0.5" /> : <AlertTriangle className="size-4 shrink-0 mt-0.5" />}
          {w.poruka}
        </li>
      ))}
    </ul>
  )
}

// ------------------------------------------------------------------ raspored

function RoutingPanel({ c, onChange }: { c: CaseDetail; onChange: () => void }) {
  const { data: units } = useUnits()
  const cats = useCategories()
  const s = c.suggestion
  const [unit, setUnit] = useState<number | ''>(c.org_unit?.id ?? '')
  const [prio, setPrio] = useState(c.priority)
  const [cat, setCat] = useState(c.category)
  const [busy, setBusy] = useState(false)
  useEffect(() => {
    setUnit(c.org_unit?.id ?? '')
    setPrio(c.priority)
    setCat(c.category)
  }, [c.org_unit?.id, c.priority, c.category])
  const changed = unit !== (c.org_unit?.id ?? '') || prio !== c.priority || cat !== c.category
  const aiBusy = ['pending', 'processing'].includes(c.ai_status)

  async function save() {
    if (!unit) return
    setBusy(true)
    try {
      await api.post(`/api/cases/${c.id}/routing`, { org_unit_id: unit, priority: prio, category: cat })
      onChange()
    } finally {
      setBusy(false)
    }
  }

  return (
    <Panel title="Razvrstavanje" actions={c.routing_confirmed ? <Chip tone="autoput">potvrđeno</Chip> : s ? <Chip tone="signal">AI predlog</Chip> : null}>
      {aiBusy && !s ? (
        <p className="text-sm text-sivo inline-flex items-center gap-2"><Loader2 className="size-4 animate-spin" /> AI analizira obraćanje</p>
      ) : (
        <div className={`pl-3 ${c.routing_confirmed ? 'lane-confirmed' : 'lane-proposed'}`}>
          {s && (
            <div className="mb-3">
              <p className="text-[13.5px]">{s.reasoning}</p>
              <div className="mt-2 flex items-center gap-2 text-[12.5px] text-sivo">
                <span>Pouzdanost</span>
                <span className="h-1.5 w-24 rounded-full bg-black/10 overflow-hidden">
                  <span className="block h-full bg-signal" style={{ width: `${Math.round(s.confidence * 100)}%` }} />
                </span>
                <span className="num">{Math.round(s.confidence * 100)}%</span>
              </div>
              {s.rule_overrides?.map((o) => (
                <p key={o.pravilo} className="mt-2 flex gap-2 text-[13px] text-stop">
                  <ShieldAlert className="size-4 shrink-0 mt-0.5" /> {o.poruka}
                </p>
              ))}
            </div>
          )}
          <div className="space-y-2.5">
            <Field label="Kategorija">
              <select className={inputCls} value={cat} onChange={(e) => setCat(e.target.value)} disabled={c.status === 'zatvoreno'}>
                {cats.map((x) => (
                  <option key={x.code} value={x.code}>{x.label}</option>
                ))}
              </select>
            </Field>
            <Field label={s?.suggested_unit && s.suggested_unit.id !== unit ? `Nadležna jedinica (AI predlog: ${s.suggested_unit.code})` : 'Nadležna jedinica'}>
              <select className={inputCls} value={unit} onChange={(e) => setUnit(Number(e.target.value))} disabled={c.status === 'zatvoreno'}>
                {units?.map((u) => (
                  <option key={u.id} value={u.id}>{u.code}, {u.name}</option>
                ))}
              </select>
            </Field>
            <Field label={s && s.suggested_priority !== prio ? `Prioritet (AI predlog: ${PRIORITY_LABEL[s.suggested_priority]})` : 'Prioritet'}>
              <select className={inputCls} value={prio} onChange={(e) => setPrio(e.target.value)} disabled={c.status === 'zatvoreno'}>
                {Object.entries(PRIORITY_LABEL).map(([k, v]) => (
                  <option key={k} value={k}>{v}</option>
                ))}
              </select>
            </Field>
          </div>
          {c.status !== 'zatvoreno' && (!c.routing_confirmed || changed) && (
            <Button className="mt-3 w-full" variant={changed ? 'secondary' : 'primary'} onClick={save} loading={busy}>
              {changed ? 'Sačuvaj izmenu rasporeda' : 'Potvrdi AI predlog'}
            </Button>
          )}
        </div>
      )}
    </Panel>
  )
}

// ------------------------------------------------------------------ provera

const ENT_LABEL: Record<string, string> = { tablice: 'Tablice', tagovi: 'TAG', datumi: 'Datumi', iznosi: 'Iznosi', naplatne_stanice: 'Stanice', telefoni: 'Telefon' }

function BillingPanel({ c, onChange }: { c: CaseDetail; onChange: () => void }) {
  const bc = { ...(c.suggestion?.billing_check ?? {}), ...(c.billing_check ?? {}) }
  const ent = c.suggestion?.entities ?? {}
  const [result, setResult] = useState('')
  const [busy, setBusy] = useState(false)
  const done = bc.status === 'obavljena'
  const vehicles = c.customer_full?.vehicles ?? []

  async function save(waiting: boolean) {
    setBusy(true)
    try {
      await api.post(`/api/cases/${c.id}/billing-check`, { result: waiting ? result || 'Prosleđeno službi naplate.' : result, waiting })
      setResult('')
      onChange()
    } finally {
      setBusy(false)
    }
  }

  return (
    <Panel title="Provera u naplatnom sistemu" actions={done ? <Chip tone="autoput">obavljena</Chip> : bc.status === 'zatrazena' ? <Chip tone="signal">zatražena</Chip> : <Chip tone="enp">potrebna</Chip>}>
      {bc.sta_proveriti && <p className="text-[13.5px]">{bc.sta_proveriti}</p>}
      <dl className="mt-3 grid grid-cols-[84px_1fr] gap-x-3 gap-y-1.5 text-[13px]">
        {Object.entries(ENT_LABEL).map(([k, label]) => {
          const v = ent[k]
          if (!Array.isArray(v) || !v.length) return null
          return (
            <div key={k} className="contents">
              <dt className="text-sivo">{label}</dt>
              <dd className="num">{v.join(', ')}</dd>
            </div>
          )
        })}
      </dl>
      {vehicles.length > 0 && (
        <div className="mt-3 rounded-[7px] bg-beton/70 px-3 py-2 text-[13px]">
          <div className="text-sivo mb-1">Iz evidencije korisnika (demo podaci)</div>
          {vehicles.map((v) => (
            <div key={v.id} className="num flex justify-between gap-2">
              <span>{v.plate}, kat. {v.category}{v.tag_number ? `, ${v.tag_number}` : ''}</span>
              {v.tag_number && <span>{v.account_balance.toLocaleString('sr-Latn-RS')} din</span>}
            </div>
          ))}
        </div>
      )}
      {done ? (
        <p className="mt-3 text-[13.5px]">
          <span className="text-sivo">Rezultat ({bc.proverio}):</span> {bc.rezultat}
        </p>
      ) : c.status !== 'zatvoreno' ? (
        <div className="mt-3 space-y-2">
          <textarea className={`${inputCls} min-h-20`} placeholder="Rezultat provere, npr. TAG aktivan, prolazak evidentiran kao gotovinski" value={result} onChange={(e) => setResult(e.target.value)} />
          <div className="flex gap-2">
            <Button size="sm" variant="primary" disabled={!result.trim()} loading={busy} onClick={() => save(false)}>Sačuvaj rezultat</Button>
            {bc.status !== 'zatrazena' && <Button size="sm" loading={busy} onClick={() => save(true)}>Zatraži proveru od službe</Button>}
          </div>
        </div>
      ) : null}
    </Panel>
  )
}

// ------------------------------------------------------------------ korisnik

function CustomerPanel({ c }: { c: CaseDetail }) {
  const cu = c.customer_full
  if (!cu) return null
  return (
    <Panel title="Korisnik" actions={<Link to={`/korisnici/${cu.id}`} className="text-[13px] text-enp hover:underline">Ceo pregled</Link>}>
      <div className="font-semibold">{cu.full_name}</div>
      {cu.company && <div className="text-sm">{cu.company}{cu.pib ? `, PIB ${cu.pib}` : ''}</div>}
      <div className="text-[13px] text-sivo mt-1">{[cu.email, cu.phone, cu.city].filter(Boolean).join(', ')}</div>
      {cu.source === 'automatski' && <p className="mt-2 text-[12.5px] text-signal-ink">Zapis je kreiran automatski iz mejla, proverite podatke.</p>}
      {c.other_cases.length > 0 && (
        <div className="mt-3">
          <div className="text-[13px] text-sivo mb-1">Ranija obraćanja ({c.other_cases.length})</div>
          <ul className="space-y-1">
            {c.other_cases.slice(0, 5).map((o) => (
              <li key={o.id} className="text-[13px] flex justify-between gap-2">
                <Link to={`/predmeti/${o.id}`} className="truncate hover:underline">{o.category_label || o.subject}</Link>
                <span className="text-sivo shrink-0">{fmtDate(o.created_at, false)}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
      {c.phone_contacts.length > 0 && (
        <div className="mt-3">
          <div className="text-[13px] text-sivo mb-1">Telefonski kontakti ({c.phone_contacts.length})</div>
          <ul className="space-y-1.5">
            {c.phone_contacts.slice(0, 3).map((p) => (
              <li key={p.id} className="text-[13px]">
                <span className="inline-flex items-center gap-1.5"><Phone className="size-3.5" /> {p.topic}</span>
                <span className="text-sivo">, {relTime(p.started_at)}, {fmtDuration(p.duration_sec)}</span>
                {p.note && <div className="text-sivo">{p.note}</div>}
              </li>
            ))}
          </ul>
        </div>
      )}
    </Panel>
  )
}

// ------------------------------------------------------------------ AI detalji

function AiDetails({ s, count, caseId, onReanalyze }: { s: Suggestion; count: number; caseId: number; onReanalyze: () => void }) {
  const { data: cfg } = useQuery({ queryKey: ['config'], queryFn: () => api.get<{ langfuse_ui: string }>('/api/config'), staleTime: 300000 })
  const [busy, setBusy] = useState(false)
  return (
    <Panel title="Kako je nastao predlog" actions={<Bot className="size-4 text-sivo" />}>
      <dl className="grid grid-cols-[110px_1fr] gap-x-3 gap-y-1 text-[13px]">
        <dt className="text-sivo">Model</dt>
        <dd>{s.mode === 'live' ? s.model : 'rezervni režim (pravila)'}</dd>
        <dt className="text-sivo">Verzija prompta</dt>
        <dd className="num">{s.prompt_version}</dd>
        <dt className="text-sivo">Verzija znanja</dt>
        <dd className="num">{s.kb_version}</dd>
        <dt className="text-sivo">Predloga</dt>
        <dd>{count}</dd>
      </dl>
      <div className="mt-3 text-[13px] text-sivo">Pronađeni obrasci (hibridna pretraga)</div>
      <ul className="mt-1 space-y-1">
        {s.sources.map((x) => (
          <li key={x.code} className="text-[13px] flex items-baseline justify-between gap-2">
            <span className={x.koriscen ? 'font-medium' : ''}>
              <span className="num">{x.code}</span> {x.title}
            </span>
            <span className="text-sivo shrink-0">{x.metode.join(', ')}</span>
          </li>
        ))}
      </ul>
      <div className="mt-4 flex flex-wrap gap-2">
        <Button size="sm" icon={<RefreshCw className="size-3.5" />} loading={busy} onClick={async () => { setBusy(true); await api.post(`/api/cases/${caseId}/reanalyze`); setBusy(false); onReanalyze() }}>
          Nova AI analiza
        </Button>
        {cfg?.langfuse_ui && (
          <a className="inline-flex items-center h-8 px-3 text-[13px] rounded-[7px] border border-linija hover:border-sivo" href={cfg.langfuse_ui} target="_blank" rel="noreferrer">
            Tragovi u Langfuse
          </a>
        )}
      </div>
    </Panel>
  )
}

// ------------------------------------------------------------------ istorijat

const EV_LABEL: Record<string, string> = {
  kreiran: 'Otvoren', ai_analiza: 'AI analiza', korisnik: 'Korisnik', preuzet: 'Preuzet', dodeljen: 'Dodeljen', raspored: 'Raspored',
  prosledjen: 'Prosleđen', interna_napomena: 'Interna napomena', provera: 'Provera', odgovor_poslat: 'Odgovor', zatvoren: 'Zatvoren',
  status: 'Status', nova_poruka: 'Nova poruka', ai_ponovo: 'AI', ai_greska: 'Greška AI',
}

function Timeline({ c, onNote }: { c: CaseDetail; onNote: () => void }) {
  const [note, setNote] = useState('')
  const [busy, setBusy] = useState(false)
  const events = useMemo(() => [...c.events].reverse(), [c.events])
  return (
    <Panel title="Istorijat i interna komunikacija">
      <div className="flex gap-2">
        <input className={inputCls} placeholder="Interna napomena za kolege (korisnik je ne vidi)" value={note} onChange={(e) => setNote(e.target.value)} />
        <Button loading={busy} disabled={!note.trim()} onClick={async () => { setBusy(true); await api.post(`/api/cases/${c.id}/note`, { text: note }); setNote(''); setBusy(false); onNote() }}>
          Dodaj
        </Button>
      </div>
      <ol className="mt-4 relative border-l-2 border-linija ml-1.5 space-y-3">
        {events.map((e) => (
          <li key={e.id} className="pl-4 relative">
            <span className={`absolute -left-[7px] top-1.5 size-3 rounded-full border-2 border-papir ${e.actor === 'AI' ? 'bg-signal' : e.type === 'interna_napomena' ? 'bg-enp' : 'bg-autoput'}`} />
            <div className="text-[13px] text-sivo">
              <span className="font-medium text-grafit">{EV_LABEL[e.type] ?? e.type}</span>, {e.actor}, {fmtDate(e.at)}
            </div>
            <div className={`text-[14px] ${e.type === 'interna_napomena' ? 'bg-enp-soft/60 rounded px-2 py-1 mt-0.5' : ''}`}>{e.text}</div>
          </li>
        ))}
      </ol>
    </Panel>
  )
}

function ForwardModal({ open, onClose, caseId, onDone }: { open: boolean; onClose: () => void; caseId: number; onDone: () => void }) {
  const { data: units } = useUnits()
  const [unit, setUnit] = useState<number | ''>('')
  const [note, setNote] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<unknown>(null)
  return (
    <Modal open={open} onClose={onClose} title="Prosleđivanje predmeta">
      <div className="space-y-4">
        <Field label="Jedinica">
          <select className={inputCls} value={unit} onChange={(e) => setUnit(Number(e.target.value))}>
            <option value="">Izaberite jedinicu</option>
            {units?.map((u) => (
              <option key={u.id} value={u.id}>{u.code}, {u.name}</option>
            ))}
          </select>
        </Field>
        <Field label="Napomena za jedinicu">
          <textarea className={`${inputCls} min-h-24`} value={note} onChange={(e) => setNote(e.target.value)} />
        </Field>
        <ErrorNote error={error} />
        <div className="flex justify-end gap-2">
          <Button onClick={onClose}>Otkaži</Button>
          <Button
            variant="primary"
            disabled={!unit}
            loading={busy}
            onClick={async () => {
              setBusy(true)
              try {
                await api.post(`/api/cases/${caseId}/forward`, { org_unit_id: unit, note })
                onDone()
                onClose()
              } catch (e) {
                setError(e)
              } finally {
                setBusy(false)
              }
            }}
          >
            Prosledi
          </Button>
        </div>
      </div>
    </Modal>
  )
}
