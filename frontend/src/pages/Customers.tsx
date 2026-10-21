import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Search } from 'lucide-react'
import { api } from '../lib/api'
import type { Customer } from '../lib/types'
import { Button, Chip, Empty, Modal, Panel, Spinner, inputCls } from '../components/ui'

type Dup = { primary_id: number; duplicate_id: number; score: number; reasons: string[]; primary: Customer; duplicate: Customer }

export default function CustomersPage() {
  const [q, setQ] = useState('')
  const { data, isLoading } = useQuery({ queryKey: ['customers', q], queryFn: () => api.get<Customer[]>(`/api/customers?q=${encodeURIComponent(q)}`) })
  const { data: dups } = useQuery({ queryKey: ['duplicates'], queryFn: () => api.get<Dup[]>('/api/customers/duplicates') })
  const [review, setReview] = useState<Dup | null>(null)

  return (
    <div className="max-w-[1200px]">
      <h1 className="text-[28px] font-extrabold">Korisnici</h1>
      <p className="text-sivo text-sm">Jedinstven pregled korisnika, njihovih vozila, obraćanja i poziva.</p>

      {!!dups?.length && (
        <Panel className="mt-5" title={`Mogući dupli zapisi (${dups.length})`}>
          <p className="text-[13.5px] text-sivo mb-3">Sistem je pronašao zapise koji verovatno pripadaju istoj osobi. Spajanje se radi tek kad ga operater potvrdi.</p>
          <ul className="divide-y divide-linija">
            {dups.map((d) => (
              <li key={`${d.primary_id}-${d.duplicate_id}`} className="py-2.5 flex flex-wrap items-center justify-between gap-3">
                <div className="text-sm">
                  <b>{d.primary.full_name}</b> i <b>{d.duplicate.full_name}</b>
                  <div className="text-[13px] text-sivo">{d.reasons.join(', ')}</div>
                </div>
                <div className="flex items-center gap-3">
                  <span className="num text-sm">{Math.round(d.score * 100)}%</span>
                  <Button size="sm" onClick={() => setReview(d)}>Pregledaj</Button>
                </div>
              </li>
            ))}
          </ul>
        </Panel>
      )}

      <div className="mt-5 relative max-w-md">
        <Search className="size-4 absolute left-3 top-1/2 -translate-y-1/2 text-sivo" />
        <input className={`${inputCls} pl-9`} placeholder="Ime, firma, mejl, telefon, tablica ili TAG" value={q} onChange={(e) => setQ(e.target.value)} aria-label="Pretraga korisnika" />
      </div>
      <div className="mt-3 bg-papir border border-linija rounded-[10px] overflow-x-auto">
        {isLoading ? (
          <Spinner />
        ) : !data?.length ? (
          <Empty title="Nema korisnika za ovu pretragu" />
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-[13px] text-sivo border-b border-linija">
                <th className="px-4 py-2.5 font-medium">Korisnik</th>
                <th className="px-4 py-2.5 font-medium">Kontakt</th>
                <th className="px-4 py-2.5 font-medium">Vozila</th>
                <th className="px-4 py-2.5 font-medium text-right">Obraćanja</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-linija">
              {data.map((c) => (
                <tr key={c.id} className="hover:bg-beton/50">
                  <td className="px-4 py-2.5">
                    <Link to={`/korisnici/${c.id}`} className="font-medium hover:underline">{c.full_name}</Link>
                    {c.company && <div className="text-[13px] text-sivo">{c.company}</div>}
                    <div className="flex gap-1.5 mt-0.5">
                      {c.source === 'automatski' && <Chip tone="signal">iz mejla</Chip>}
                      {c.possible_duplicate && <Chip tone="enp">mogući duplikat</Chip>}
                    </div>
                  </td>
                  <td className="px-4 py-2.5 text-[13px]">
                    <div>{c.email}</div>
                    <div className="text-sivo">{c.phone}</div>
                  </td>
                  <td className="px-4 py-2.5 num text-[13px]">{c.vehicles.map((v) => v.plate).join(', ') || '-'}</td>
                  <td className="px-4 py-2.5 num text-right">{c.case_count}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
      {review && <MergeModal d={review} onClose={() => setReview(null)} />}
    </div>
  )
}

function MergeModal({ d, onClose }: { d: Dup; onClose: () => void }) {
  const qc = useQueryClient()
  const [busy, setBusy] = useState(false)
  const col = (c: Customer, label: string) => (
    <div className="rounded-[8px] border border-linija p-3 text-sm">
      <div className="text-[13px] text-sivo">{label}</div>
      <div className="font-semibold mt-1">{c.full_name}</div>
      <div>{c.email}</div>
      <div>{c.phone || '-'}</div>
      <div>{c.city}</div>
      <div className="num mt-1">{c.vehicles.map((v) => `${v.plate}${v.tag_number ? ` (${v.tag_number})` : ''}`).join(', ') || 'bez vozila'}</div>
    </div>
  )
  return (
    <Modal open onClose={onClose} title="Spajanje zapisa" wide>
      <p className="text-sm mb-3">Podudaranja: {d.reasons.join(', ')}. Predmeti, vozila i pozivi duplikata prelaze na glavni zapis, a duplikat ostaje u evidenciji izmena.</p>
      <div className="grid sm:grid-cols-2 gap-3">
        {col(d.primary, 'Glavni zapis')}
        {col(d.duplicate, 'Duplikat')}
      </div>
      <div className="mt-4 flex justify-end gap-2">
        <Button onClick={onClose}>Nije ista osoba</Button>
        <Button
          variant="primary"
          loading={busy}
          onClick={async () => {
            setBusy(true)
            await api.post('/api/customers/merge', { primary_id: d.primary_id, duplicate_id: d.duplicate_id })
            qc.invalidateQueries()
            onClose()
          }}
        >
          Spoji zapise
        </Button>
      </div>
    </Modal>
  )
}
