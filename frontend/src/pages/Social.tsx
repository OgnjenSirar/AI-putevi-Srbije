import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { Sparkles } from 'lucide-react'
import { api } from '../lib/api'
import { fmtDate } from '../lib/format'
import { Button, Chip, Empty, ErrorNote, Panel, Spinner, inputCls } from '../components/ui'

export type Post = {
  id: number
  created_at: string
  created_by: string
  brief: string
  template_code: string
  template_label: string
  fields: Record<string, string>
  fb_text: string
  ig_text: string
  alt_text: string
  image_prompt: string
  background: string
  background_is_ai: boolean
  images: Record<string, string>
  render_warnings: { tip: string; poruka: string }[]
  status: string
  approved_by: string
  approved_at: string | null
  published_at: string | null
  publish_log: { korak: string; metod: string; url: string; telo: Record<string, unknown>; odgovor: Record<string, unknown> }[]
  ai_meta: Record<string, unknown>
}

const STATUS: Record<string, { label: string; tone: 'neutral' | 'signal' | 'autoput' }> = {
  nacrt: { label: 'nacrt', tone: 'neutral' },
  odobreno: { label: 'odobreno', tone: 'signal' },
  objavljeno: { label: 'objavljeno', tone: 'autoput' },
}

const EXAMPLES = [
  'Radovi na autoputu A1 kod Ćuprije od 25. do 28. oktobra. Saobraćaj se odvija jednom trakom u smeru Niša. Planirajte više vremena za put.',
  'Upozorenje vozačima: zbog guste magle na deonici Pojate - Preševo vidljivost je mestimično ispod 50 metara. Vozite sporije i držite odstojanje.',
  'Podsetnik da se račun TAG uređaja može dopuniti preko portala i mobilne aplikacije, bez odlaska u korisnički centar.',
]

export default function SocialPage() {
  const nav = useNavigate()
  const { data, isLoading } = useQuery({ queryKey: ['posts'], queryFn: () => api.get<Post[]>('/api/social/posts') })
  const { data: meta } = useQuery({ queryKey: ['social-meta'], queryFn: () => api.get<{ imagegen: { status: string } }>('/api/social/templates') })
  const [brief, setBrief] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<unknown>(null)

  async function create() {
    setBusy(true)
    setError(null)
    try {
      const p = await api.post<Post>('/api/social/posts', { brief })
      nav(`/mreze/${p.id}`)
    } catch (e) {
      setError(e)
      setBusy(false)
    }
  }

  return (
    <div className="max-w-[1200px]">
      <h1 className="text-[28px] font-extrabold">Društvene mreže</h1>
      <p className="text-sivo text-sm max-w-2xl">
        Opišite šta treba objaviti. AI piše tekst za Facebook i Instagram i popunjava šablon, a slika se pravi iz šablona sa vizuelnim identitetom. Ništa se ne objavljuje bez odobrenja.
      </p>
      <Panel className="mt-5" title="Nova objava" actions={<Chip tone={meta?.imagegen.status === 'ok' ? 'autoput' : 'neutral'}>AI pozadine: {meta?.imagegen.status === 'ok' ? 'dostupne' : 'nedostupne'}</Chip>}>
        <textarea className={`${inputCls} min-h-28`} value={brief} onChange={(e) => setBrief(e.target.value)} placeholder="npr. Radovi na deonici, period, šta vozači treba da znaju" aria-label="Opis objave" />
        <div className="mt-2 flex flex-wrap gap-2">
          {EXAMPLES.map((ex, i) => (
            <button key={i} className="text-left text-[13px] px-3 py-1.5 rounded-full border border-linija hover:border-autoput max-w-full truncate" onClick={() => setBrief(ex)}>
              {ex.slice(0, 60)}...
            </button>
          ))}
        </div>
        <ErrorNote error={error} />
        <Button className="mt-3" variant="primary" icon={<Sparkles className="size-4" />} loading={busy} disabled={brief.trim().length < 10} onClick={create}>
          Pripremi objavu
        </Button>
      </Panel>
      <h2 className="mt-8 mb-3 text-lg font-semibold">Objave</h2>
      {isLoading ? (
        <Spinner />
      ) : !data?.length ? (
        <Empty title="Još nema objava" />
      ) : (
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {data.map((p) => (
            <Link key={p.id} to={`/mreze/${p.id}`} className="bg-papir border border-linija rounded-[10px] overflow-hidden hover:border-sivo">
              {p.images.portret ? <img src={p.images.portret} alt={p.alt_text} className="w-full aspect-[4/5] object-cover bg-beton" /> : <div className="aspect-[4/5] bg-beton" />}
              <div className="p-3">
                <div className="flex items-center justify-between gap-2">
                  <span className="font-medium truncate">{p.fields.naslov}</span>
                  <Chip tone={STATUS[p.status]?.tone}>{STATUS[p.status]?.label ?? p.status}</Chip>
                </div>
                <div className="text-[13px] text-sivo">{p.template_label}, {fmtDate(p.published_at ?? p.created_at)}</div>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  )
}
