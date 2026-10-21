export const STATUS_LABEL: Record<string, string> = {
  novo: 'Novo',
  u_obradi: 'U obradi',
  ceka_proveru: 'Čeka proveru',
  odgovoreno: 'Odgovoreno',
  zatvoreno: 'Zatvoreno',
}

export const PRIORITY_LABEL: Record<string, string> = {
  hitan: 'Hitan',
  visok: 'Visok',
  normalan: 'Normalan',
  nizak: 'Nizak',
}

export const PRIORITY_COLOR: Record<string, string> = {
  hitan: 'var(--color-stop)',
  visok: 'var(--color-signal)',
  normalan: 'var(--color-enp)',
  nizak: '#a7b0aa',
}

export const EDIT_LABEL: Record<string, string> = {
  bez_izmena: 'bez izmena',
  manje_izmene: 'uz manje izmene',
  vece_izmene: 'uz veće izmene',
  napisan_iznova: 'napisan iznova',
}

const months = ['jan', 'feb', 'mar', 'apr', 'maj', 'jun', 'jul', 'avg', 'sep', 'okt', 'nov', 'dec']

export function fmtDate(iso?: string | null, withTime = true): string {
  if (!iso) return ''
  const d = new Date(iso)
  const day = `${d.getDate()}. ${months[d.getMonth()]}`
  const year = d.getFullYear() !== new Date().getFullYear() ? ` ${d.getFullYear()}.` : ''
  if (!withTime) return day + year
  return `${day}${year} ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
}

export function relTime(iso?: string | null): string {
  if (!iso) return ''
  const diff = (Date.now() - new Date(iso).getTime()) / 1000
  if (diff < 60) return 'upravo'
  if (diff < 3600) return `pre ${Math.round(diff / 60)} min`
  if (diff < 86400) return `pre ${Math.round(diff / 3600)} h`
  return `pre ${Math.round(diff / 86400)} d`
}

/** Rok kao na putokazu: koliko je ostalo ili koliko kasni. */
export function dueText(iso?: string | null): { text: string; tone: 'stop' | 'signal' | 'muted' } {
  if (!iso) return { text: 'bez roka', tone: 'muted' }
  const h = (new Date(iso).getTime() - Date.now()) / 3600000
  if (h < 0) {
    const a = -h
    return { text: a < 48 ? `kasni ${Math.ceil(a)} h` : `kasni ${Math.round(a / 24)} d`, tone: 'stop' }
  }
  if (h < 24) return { text: `još ${Math.max(1, Math.round(h))} h`, tone: 'signal' }
  return { text: `još ${Math.round(h / 24)} d`, tone: 'muted' }
}

export function fmtNum(n?: number | null, digits = 0): string {
  if (n === null || n === undefined) return '-'
  return n.toLocaleString('sr-Latn-RS', { maximumFractionDigits: digits, minimumFractionDigits: digits })
}

export function fmtDuration(sec: number): string {
  const m = Math.floor(sec / 60)
  const s = sec % 60
  return m ? `${m} min ${s} s` : `${s} s`
}
