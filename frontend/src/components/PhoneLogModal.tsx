import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '../lib/api'
import { useUnits } from '../lib/hooks'
import type { Customer } from '../lib/types'
import { Button, ErrorNote, Field, Modal, inputCls } from './ui'

export default function PhoneLogModal({ open, onClose, customer }: { open: boolean; onClose: () => void; customer?: Customer }) {
  const nav = useNavigate()
  const qc = useQueryClient()
  const { data: units } = useUnits()
  const [q, setQ] = useState('')
  const [picked, setPicked] = useState<Customer | null>(customer ?? null)
  const [topic, setTopic] = useState('')
  const [note, setNote] = useState('')
  const [minutes, setMinutes] = useState('3')
  const [openCase, setOpenCase] = useState(false)
  const [unitId, setUnitId] = useState<number | ''>('')
  const [priority, setPriority] = useState('normalan')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<unknown>(null)
  const { data: found } = useQuery({
    queryKey: ['cust-search', q],
    queryFn: () => api.get<Customer[]>(`/api/customers?q=${encodeURIComponent(q)}`),
    enabled: open && !customer && q.length >= 2,
  })

  async function save() {
    if (!topic.trim()) {
      setError(new Error('Unesite temu poziva'))
      return
    }
    setBusy(true)
    setError(null)
    try {
      const r = await api.post<{ case_id: number | null }>('/api/phone-contacts', {
        customer_id: picked?.id ?? null,
        phone: picked?.phone ?? '',
        topic,
        note,
        duration_sec: Math.round(Number(minutes || 0) * 60),
        open_case: openCase,
        org_unit_id: unitId || null,
        priority,
      })
      qc.invalidateQueries()
      onClose()
      if (r.case_id) nav(`/predmeti/${r.case_id}`)
    } catch (e) {
      setError(e)
    } finally {
      setBusy(false)
    }
  }

  return (
    <Modal open={open} onClose={onClose} title="Evidencija telefonskog poziva">
      <div className="space-y-4">
        {customer ? (
          <p className="text-sm">
            Korisnik: <b>{customer.full_name}</b>
          </p>
        ) : (
          <Field label="Korisnik" hint={picked ? `Izabran: ${picked.full_name}` : 'Pretražite po imenu, telefonu, tablici ili TAG-u'}>
            <input className={inputCls} value={q} onChange={(e) => setQ(e.target.value)} placeholder="npr. Petrović ili BG 123-AB" />
            {found && q.length >= 2 && !picked && (
              <ul className="mt-1 border border-linija rounded-[7px] max-h-40 overflow-auto">
                {found.slice(0, 8).map((c) => (
                  <li key={c.id}>
                    <button type="button" className="w-full text-left px-3 py-1.5 text-sm hover:bg-beton" onClick={() => setPicked(c)}>
                      {c.full_name} <span className="text-sivo">{c.phone}</span>
                    </button>
                  </li>
                ))}
                {!found.length && <li className="px-3 py-1.5 text-sm text-sivo">Nema rezultata, poziv se može evidentirati i bez korisnika.</li>}
              </ul>
            )}
          </Field>
        )}
        <Field label="Tema poziva">
          <input className={inputCls} value={topic} onChange={(e) => setTopic(e.target.value)} placeholder="npr. TAG nije očitan" />
        </Field>
        <Field label="Beleška">
          <textarea className={`${inputCls} min-h-24`} value={note} onChange={(e) => setNote(e.target.value)} />
        </Field>
        <Field label="Trajanje (min)">
          <input className={`${inputCls} w-28`} type="number" min="0" value={minutes} onChange={(e) => setMinutes(e.target.value)} />
        </Field>
        <label className="flex items-center gap-2 text-sm">
          <input type="checkbox" checked={openCase} onChange={(e) => setOpenCase(e.target.checked)} /> Otvori predmet za dalju obradu
        </label>
        {openCase && (
          <div className="grid grid-cols-2 gap-3">
            <Field label="Jedinica">
              <select className={inputCls} value={unitId} onChange={(e) => setUnitId(e.target.value ? Number(e.target.value) : '')}>
                <option value="">Korisnički centar</option>
                {units?.map((u) => (
                  <option key={u.id} value={u.id}>
                    {u.code}, {u.name}
                  </option>
                ))}
              </select>
            </Field>
            <Field label="Prioritet">
              <select className={inputCls} value={priority} onChange={(e) => setPriority(e.target.value)}>
                <option value="hitan">Hitan</option>
                <option value="visok">Visok</option>
                <option value="normalan">Normalan</option>
                <option value="nizak">Nizak</option>
              </select>
            </Field>
          </div>
        )}
        <ErrorNote error={error} />
        <div className="flex justify-end gap-2">
          <Button onClick={onClose}>Otkaži</Button>
          <Button variant="primary" onClick={save} loading={busy}>
            Sačuvaj poziv
          </Button>
        </div>
      </div>
    </Modal>
  )
}
