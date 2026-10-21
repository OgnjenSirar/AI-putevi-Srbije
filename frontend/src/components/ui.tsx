import { useEffect, type ButtonHTMLAttributes, type ReactNode } from 'react'
import { Loader2, X } from 'lucide-react'
import { PRIORITY_COLOR, PRIORITY_LABEL, STATUS_LABEL, dueText } from '../lib/format'

type BtnProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: 'primary' | 'secondary' | 'ghost' | 'danger' | 'signal'
  size?: 'sm' | 'md'
  loading?: boolean
  icon?: ReactNode
}

export function Button({ variant = 'secondary', size = 'md', loading, icon, children, className = '', disabled, ...rest }: BtnProps) {
  const base = 'inline-flex items-center justify-center gap-2 rounded-[7px] font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed whitespace-nowrap'
  const sizes = { sm: 'h-8 px-3 text-[13px]', md: 'h-10 px-4 text-sm' }
  const variants = {
    primary: 'bg-autoput text-white hover:bg-autoput-deep',
    secondary: 'bg-papir text-grafit border border-linija hover:border-sivo',
    ghost: 'text-grafit hover:bg-black/5',
    danger: 'bg-stop text-white hover:brightness-95',
    signal: 'bg-signal text-grafit hover:brightness-95',
  }
  return (
    <button className={`${base} ${sizes[size]} ${variants[variant]} ${className}`} disabled={disabled || loading} {...rest}>
      {loading ? <Loader2 className="size-4 animate-spin" aria-hidden /> : icon}
      {children}
    </button>
  )
}

export function Panel({ children, className = '', title, actions, pad = true }: { children: ReactNode; className?: string; title?: ReactNode; actions?: ReactNode; pad?: boolean }) {
  return (
    <section className={`bg-papir border border-linija rounded-[10px] ${className}`}>
      {(title || actions) && (
        <header className="flex items-center justify-between gap-3 px-4 pt-3.5 pb-2">
          <h2 className="text-[15px] font-semibold">{title}</h2>
          {actions}
        </header>
      )}
      <div className={pad ? 'px-4 pb-4 pt-1' : ''}>{children}</div>
    </section>
  )
}

export function PriorityStripe({ priority }: { priority: string }) {
  return <span className="block w-1.5 self-stretch rounded-full" style={{ background: PRIORITY_COLOR[priority] }} title={`Prioritet: ${PRIORITY_LABEL[priority]}`} />
}

export function PriorityBadge({ priority }: { priority: string }) {
  return (
    <span className="inline-flex items-center gap-1.5 text-[13px]">
      <span className="size-2.5 rounded-full" style={{ background: PRIORITY_COLOR[priority] }} />
      {PRIORITY_LABEL[priority] ?? priority}
    </span>
  )
}

export function StatusBadge({ status }: { status: string }) {
  const tone: Record<string, string> = {
    novo: 'bg-enp-soft text-enp',
    u_obradi: 'bg-autoput-soft text-autoput',
    ceka_proveru: 'bg-signal-soft text-signal-ink',
    odgovoreno: 'bg-black/5 text-sivo',
    zatvoreno: 'bg-black/5 text-sivo',
  }
  return <span className={`inline-block rounded-full px-2.5 py-0.5 text-[12.5px] font-medium ${tone[status] ?? 'bg-black/5'}`}>{STATUS_LABEL[status] ?? status}</span>
}

export function DueChip({ due, closed }: { due?: string | null; closed?: boolean }) {
  if (closed) return <span className="text-sivo text-[13px]">završeno</span>
  const d = dueText(due)
  const tone = { stop: 'text-stop font-semibold', signal: 'text-signal-ink font-semibold', muted: 'text-sivo' }[d.tone]
  return <span className={`num text-[13px] ${tone}`}>{d.text}</span>
}

export function Chip({ children, tone = 'neutral' }: { children: ReactNode; tone?: 'neutral' | 'enp' | 'signal' | 'stop' | 'autoput' }) {
  const t = {
    neutral: 'bg-black/5 text-grafit',
    enp: 'bg-enp-soft text-enp',
    signal: 'bg-signal-soft text-signal-ink',
    stop: 'bg-stop-soft text-stop',
    autoput: 'bg-autoput-soft text-autoput',
  }[tone]
  return <span className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-[12.5px] font-medium ${t}`}>{children}</span>
}

export function Spinner({ label }: { label?: string }) {
  return (
    <div className="flex items-center gap-2 text-sivo text-sm p-6">
      <Loader2 className="size-4 animate-spin" aria-hidden /> {label ?? 'Učitavanje'}
    </div>
  )
}

export function Empty({ title, children }: { title: string; children?: ReactNode }) {
  return (
    <div className="p-10 text-center">
      <p className="font-display font-semibold text-lg">{title}</p>
      {children && <div className="text-sivo mt-1 text-sm">{children}</div>}
    </div>
  )
}

export function Field({ label, children, hint }: { label: string; children: ReactNode; hint?: ReactNode }) {
  return (
    <label className="block">
      <span className="block text-[13px] font-medium text-sivo mb-1">{label}</span>
      {children}
      {hint && <span className="block text-[12.5px] text-sivo mt-1">{hint}</span>}
    </label>
  )
}

export const selectAutoCls = 'rounded-[7px] border border-linija bg-papir px-3 py-2 text-sm outline-none focus:border-enp'
export const inputCls = `w-full ${selectAutoCls}`

export function Tabs<T extends string>({ value, onChange, items }: { value: T; onChange: (v: T) => void; items: { value: T; label: ReactNode }[] }) {
  return (
    <div role="tablist" className="flex gap-1 border-b border-linija overflow-x-auto scroll-thin">
      {items.map((it) => (
        <button
          key={it.value}
          role="tab"
          aria-selected={value === it.value}
          onClick={() => onChange(it.value)}
          className={`px-3.5 py-2 text-sm whitespace-nowrap border-b-[3px] -mb-px ${value === it.value ? 'border-autoput font-semibold text-grafit' : 'border-transparent text-sivo hover:text-grafit'}`}
        >
          {it.label}
        </button>
      ))}
    </div>
  )
}

export function Modal({ open, onClose, title, children, wide }: { open: boolean; onClose: () => void; title: string; children: ReactNode; wide?: boolean }) {
  useEffect(() => {
    if (!open) return
    const h = (e: KeyboardEvent) => e.key === 'Escape' && onClose()
    window.addEventListener('keydown', h)
    return () => window.removeEventListener('keydown', h)
  }, [open, onClose])
  if (!open) return null
  return (
    <div className="fixed inset-0 z-50 bg-black/40 flex items-start justify-center p-4 overflow-y-auto" onMouseDown={onClose}>
      <div
        role="dialog"
        aria-modal="true"
        aria-label={title}
        className={`bg-papir rounded-[12px] w-full ${wide ? 'max-w-4xl' : 'max-w-lg'} mt-10 shadow-xl`}
        onMouseDown={(e) => e.stopPropagation()}
      >
        <header className="flex items-center justify-between px-5 py-4 border-b border-linija">
          <h2 className="font-semibold text-lg">{title}</h2>
          <button onClick={onClose} aria-label="Zatvori" className="p-1 rounded hover:bg-black/5">
            <X className="size-5" />
          </button>
        </header>
        <div className="p-5">{children}</div>
      </div>
    </div>
  )
}

export function Stat({ label, value, sub, tone }: { label: string; value: ReactNode; sub?: ReactNode; tone?: 'stop' | 'signal' }) {
  return (
    <div className="px-4 py-3">
      <div className={`num text-[28px] leading-tight font-extrabold ${tone === 'stop' ? 'text-stop' : tone === 'signal' ? 'text-signal-ink' : ''}`}>{value}</div>
      <div className="text-[13px] text-sivo">{label}</div>
      {sub && <div className="text-[12.5px] text-sivo mt-0.5">{sub}</div>}
    </div>
  )
}

export function ErrorNote({ error }: { error: unknown }) {
  if (!error) return null
  return <p className="text-stop text-sm mt-2">{error instanceof Error ? error.message : String(error)}</p>
}
