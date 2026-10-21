import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { ArrowLeft, Mail, Phone } from 'lucide-react'
import { api } from '../lib/api'
import { fmtDate, fmtDuration } from '../lib/format'
import type { Customer, PhoneContact } from '../lib/types'
import { Button, Chip, Field, Panel, Spinner, StatusBadge, inputCls } from '../components/ui'
import PhoneLogModal from '../components/PhoneLogModal'

type TimelineItem =
  | { type: 'predmet'; at: string; id: number; number: string; title: string; status: string; channel: string; category_label: string }
  | { type: 'poziv'; at: string; id: number; title: string; note: string; staff: string; duration_sec: number }

type Detail = Customer & { timeline: TimelineItem[]; phone_contacts: PhoneContact[]; merged_records: { id: number; full_name: string; email: string }[] }

export default function CustomerDetailPage() {
  const { id } = useParams()
  const qc = useQueryClient()
  const { data: c, isLoading } = useQuery({ queryKey: ['customer', id], queryFn: () => api.get<Detail>(`/api/customers/${id}`) })
  const [phoneOpen, setPhoneOpen] = useState(false)
  const [edit, setEdit] = useState(false)
  const [form, setForm] = useState({ full_name: '', email: '', phone: '', city: '', address: '', note: '' })

  if (isLoading || !c) return <Spinner />

  return (
    <div className="max-w-[1200px]">
      <Link to="/korisnici" className="inline-flex items-center gap-1.5 text-sm text-sivo hover:text-grafit">
        <ArrowLeft className="size-4" /> Korisnici
      </Link>
      <div className="mt-2 flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-[26px] font-extrabold">{c.full_name}</h1>
          <div className="text-sm text-sivo">
            {c.customer_type === 'pravno' ? `Pravno lice${c.company ? `, ${c.company}` : ''}${c.pib ? `, PIB ${c.pib}` : ''}` : 'Fizičko lice'}
            {c.merged_into_id && <span className="text-stop">, zapis je spojen sa #{c.merged_into_id}</span>}
          </div>
        </div>
        <div className="flex gap-2">
          <Button icon={<Phone className="size-4" />} onClick={() => setPhoneOpen(true)}>Evidentiraj poziv</Button>
          <Button onClick={() => { setForm({ full_name: c.full_name, email: c.email, phone: c.phone, city: c.city, address: c.address, note: c.note }); setEdit(true) }}>Izmeni podatke</Button>
        </div>
      </div>

      <div className="mt-6 grid lg:grid-cols-[340px_minmax(0,1fr)] gap-5 items-start">
        <div className="space-y-5">
          <Panel title="Podaci">
            {edit ? (
              <div className="space-y-2.5">
                {(['full_name', 'email', 'phone', 'city', 'address'] as const).map((k) => (
                  <Field key={k} label={{ full_name: 'Ime', email: 'Mejl', phone: 'Telefon', city: 'Mesto', address: 'Adresa' }[k]}>
                    <input className={inputCls} value={form[k]} onChange={(e) => setForm({ ...form, [k]: e.target.value })} />
                  </Field>
                ))}
                <Field label="Napomena"><textarea className={inputCls} value={form.note} onChange={(e) => setForm({ ...form, note: e.target.value })} /></Field>
                <div className="flex gap-2">
                  <Button size="sm" variant="primary" onClick={async () => { await api.put(`/api/customers/${c.id}`, form); setEdit(false); qc.invalidateQueries({ queryKey: ['customer', id] }) }}>Sačuvaj</Button>
                  <Button size="sm" onClick={() => setEdit(false)}>Otkaži</Button>
                </div>
              </div>
            ) : (
              <dl className="grid grid-cols-[80px_1fr] gap-y-1.5 text-sm">
                <dt className="text-sivo">Mejl</dt><dd className="break-all">{c.email || '-'}</dd>
                <dt className="text-sivo">Telefon</dt><dd>{c.phone || '-'}</dd>
                <dt className="text-sivo">Mesto</dt><dd>{c.city || '-'}</dd>
                <dt className="text-sivo">Adresa</dt><dd>{c.address || '-'}</dd>
                <dt className="text-sivo">Od</dt><dd>{fmtDate(c.created_at, false)}</dd>
                {c.note && (<><dt className="text-sivo">Napomena</dt><dd className="whitespace-pre-wrap">{c.note}</dd></>)}
              </dl>
            )}
            {c.source === 'automatski' && <p className="mt-3 text-[13px] text-signal-ink">Zapis je kreiran automatski iz dolaznog mejla.</p>}
          </Panel>
          <Panel title="Vozila i TAG uređaji">
            {c.vehicles.length ? (
              <ul className="space-y-2">
                {c.vehicles.map((v) => (
                  <li key={v.id} className="rounded-[7px] border border-linija px-3 py-2">
                    <div className="num font-semibold">{v.plate}</div>
                    <div className="text-[13px] text-sivo">Kategorija {v.category}{v.tag_number ? `, ${v.tag_number}` : ', bez TAG-a'}</div>
                    {v.tag_number && <div className="num text-[13px]">Stanje računa: {v.account_balance.toLocaleString('sr-Latn-RS')} din (demo)</div>}
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-sm text-sivo">Nema evidentiranih vozila.</p>
            )}
          </Panel>
          {c.merged_records.length > 0 && (
            <Panel title="Spojeni zapisi">
              {c.merged_records.map((m) => (
                <div key={m.id} className="text-sm">#{m.id} {m.full_name} <span className="text-sivo">{m.email}</span></div>
              ))}
            </Panel>
          )}
        </div>
        <Panel title={`Sva obraćanja i pozivi (${c.timeline.length})`}>
          <ol className="divide-y divide-linija">
            {c.timeline.map((t) => (
              <li key={`${t.type}-${t.id}`} className="py-3 flex gap-3">
                <span className="mt-0.5 text-sivo">{t.type === 'poziv' ? <Phone className="size-4" /> : <Mail className="size-4" />}</span>
                <div className="flex-1 min-w-0">
                  {t.type === 'predmet' ? (
                    <>
                      <div className="flex flex-wrap items-center gap-2">
                        <Link to={`/predmeti/${t.id}`} className="font-medium hover:underline">{t.title}</Link>
                        <StatusBadge status={t.status} />
                      </div>
                      <div className="text-[13px] text-sivo"><span className="num">{t.number}</span>, {t.category_label}</div>
                    </>
                  ) : (
                    <>
                      <div className="font-medium">{t.title} <Chip>poziv</Chip></div>
                      <div className="text-[13px] text-sivo">{t.staff}, {fmtDuration(t.duration_sec)}</div>
                      {t.note && <div className="text-[13.5px] mt-0.5">{t.note}</div>}
                    </>
                  )}
                </div>
                <time className="text-[13px] text-sivo shrink-0">{fmtDate(t.at)}</time>
              </li>
            ))}
          </ol>
        </Panel>
      </div>
      <PhoneLogModal open={phoneOpen} onClose={() => { setPhoneOpen(false); qc.invalidateQueries({ queryKey: ['customer', id] }) }} customer={c} />
    </div>
  )
}
