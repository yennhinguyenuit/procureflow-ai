import { useEffect, useId, useRef, useState } from 'react'
import type { ButtonHTMLAttributes, ReactNode } from 'react'
import { ArrowUpRight, Check, ChevronDown, Info, LoaderCircle, Package, X } from 'lucide-react'
import type { InventoryRow, Risk } from './types'

export const number = (value: number) => new Intl.NumberFormat('en-US', { maximumFractionDigits: 1 }).format(value ?? 0)
export const compact = (value: number) => new Intl.NumberFormat('en-US', { notation: 'compact', maximumFractionDigits: 1 }).format(value ?? 0)
export const money = (value: number) => `${new Intl.NumberFormat('en-US', {maximumFractionDigits: 0}).format(value ?? 0)} VND`
export const shortMoney = (value: number) => `${compact(value)} VND`
export const unitOf = (row: {unit_of_measure?: string}) => row.unit_of_measure?.trim() || 'unit'
export const categoryOf = (row: {category?: string}) => row.category?.trim() || 'Unclassified'
export const quantity = (value: number, row: {unit_of_measure?: string}) => `${number(value)} ${unitOf(row)}`
export const displayDate = (value: string, options?: Intl.DateTimeFormatOptions) => new Date(value.length === 10 ? `${value}T12:00:00` : value).toLocaleDateString('en-GB', {timeZone:'Asia/Ho_Chi_Minh', ...(options ?? {day: 'numeric', month: 'short', year: 'numeric'})})
export const businessDate = (value: string) => new Date(value).toLocaleDateString('en-CA', {timeZone:'Asia/Ho_Chi_Minh'})
export const initials = (value: string) => value.replace(/_/g, ' ').split(/\s+/).filter(Boolean).slice(0, 2).map(item => item[0]).join('').toUpperCase()

export function Brand({compact: small}: {compact?: boolean}) {
  const asset = import.meta.env.VITE_AUTHORIZED_BRAND_ASSET || ''
  const authorized = import.meta.env.VITE_BRAND_ASSET_AUTHORIZED === 'true' && /^\/brand\/[A-Za-z0-9][A-Za-z0-9._-]*\.(svg|png|webp)$/.test(asset)
  return <div className="brand">{authorized && <img className="authorized-brand-asset" src={asset} alt="Authorized workspace brand"/>}<span className="brand-mark" aria-hidden="true">P<span>F</span></span>{!small && <span>ProcureFlow</span>}</div>
}

export function Button({children, icon, loading, variant = 'secondary', className = '', ...props}: ButtonHTMLAttributes<HTMLButtonElement> & {icon?: ReactNode; loading?: boolean; variant?: 'primary' | 'secondary' | 'ghost' | 'danger'; children: ReactNode}) {
  return <button className={`button button-${variant} ${className}`} {...props} disabled={props.disabled || loading}>{loading ? <LoaderCircle size={16} className="spin"/> : icon}{children}</button>
}

export function Badge({value}: {value: string}) {
  const colors: Record<string, string> = {'Critical Stock':'red','Low Stock':'amber','Normal':'green','Data Quality Issue':'neutral','DRAFT':'amber','APPROVED':'green','REJECTED':'neutral','OPEN':'amber','RESOLVED':'green'}
  const labels: Record<string, string> = {'Critical Stock':'Critical','Low Stock':'Low stock','Normal':'Healthy','Data Quality Issue':'Needs data','DRAFT':'Pending review','APPROVED':'Approved','REJECTED':'Rejected','OPEN':'Open','RESOLVED':'Resolved'}
  return <span className={`badge badge-${colors[value] ?? 'neutral'}`}><span className="badge-dot"/>{labels[value] ?? value}</span>
}

export function ProductAvatar({sku, size = ''}: {sku: string; size?: string}) {
  return <span className={`product-avatar product-${sku.split('-')[0].toLowerCase()} ${size}`}><Package size={size === 'large' ? 24 : 17} strokeWidth={1.7}/></span>
}
export function ProductCell({row, onClick}: {row: Pick<InventoryRow, 'sku' | 'product_name'>; onClick?: () => void}) {
  const content = <><ProductAvatar sku={row.sku}/><span className="product-name"><strong>{row.product_name}</strong><small>{row.sku}</small></span></>
  return onClick ? <button className="product-cell product-button" onClick={onClick}>{content}</button> : <div className="product-cell">{content}</div>
}

export function Empty({title, description, action, icon}: {title: string; description: string; action?: ReactNode; icon?: ReactNode}) {
  return <div className="empty-state"><span className="empty-icon">{icon ?? <Package size={25}/>}</span><h3>{title}</h3><p>{description}</p>{action}</div>
}

export function Modal({title, description, children, onClose, drawer = false}: {title: string; description?: string; children: ReactNode; onClose: () => void; drawer?: boolean}) {
  const ref = useRef<HTMLDivElement>(null)
  const close = useRef(onClose); close.current = onClose
  useEffect(() => {
    const previous = document.activeElement as HTMLElement | null
    const oldOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    const timer = window.setTimeout(() => ref.current?.querySelector<HTMLElement>('button, input, select, textarea')?.focus(), 30)
    function handle(event: KeyboardEvent) {
      if (event.key === 'Escape') close.current()
      if (event.key === 'Tab') {
        const elements = Array.from(ref.current?.querySelectorAll<HTMLElement>('button:not(:disabled), a[href], input:not(:disabled), select, textarea, [tabindex="0"]') ?? [])
        const first = elements[0]; const last = elements[elements.length - 1]
        if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last?.focus() }
        else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first?.focus() }
      }
    }
    document.addEventListener('keydown', handle)
    return () => { clearTimeout(timer); document.removeEventListener('keydown', handle); document.body.style.overflow = oldOverflow; previous?.focus() }
  }, [])
  return <div className={`modal-overlay ${drawer ? 'drawer-overlay' : ''}`} onMouseDown={event => {if (event.target === event.currentTarget) onClose()}}><div className={drawer ? 'drawer' : 'modal'} role="dialog" aria-modal="true" aria-labelledby="dialog-title" ref={ref}><div className="modal-heading"><div><span className="eyebrow">PROCUREFLOW WORKSPACE</span><h2 id="dialog-title">{title}</h2>{description && <p>{description}</p>}</div><button className="icon-button" onClick={onClose} aria-label="Close dialog"><X size={20}/></button></div>{children}</div></div>
}

export function Select({label, value, onChange, children}: {label: string; value: string; onChange: (value: string) => void; children: ReactNode}) {
  return <label className="filter-select"><span className="sr-only">{label}</span><select aria-label={label} value={value} onChange={event => onChange(event.target.value)}>{children}</select><ChevronDown size={14}/></label>
}

export function PageHeader({title, description, children, eyebrow}: {title: string; description: string; children?: ReactNode; eyebrow?: string}) {
  return <div className="page-heading"><div>{eyebrow && <span className="eyebrow">{eyebrow}</span>}<h1>{title}</h1><p>{description}</p></div><div className="page-actions">{children}</div></div>
}

export function InlineError({error}: {error: string}) { return error ? <div className="inline-error" role="alert">{error}</div> : null }
export function FieldTooltip({label,description}:{label:string;description:string}) {
  const [open,setOpen]=useState(false)
  const id=useId()
  return <span className="field-tooltip" onMouseEnter={()=>setOpen(true)} onMouseLeave={()=>setOpen(false)}><button type="button" aria-label={`About ${label}`} aria-describedby={open?id:undefined} onFocus={()=>setOpen(true)} onBlur={()=>setOpen(false)} onClick={()=>setOpen(!open)} onKeyDown={event=>{if(event.key==='Escape'){event.stopPropagation();setOpen(false)}}}><Info size={12}/></button>{open&&<span id={id} role="tooltip" className="field-tooltip-bubble">{description}</span>}</span>
}
export function RiskNote({risk}: {risk: Risk}) { return <Badge value={risk}/> }
export function RowLink({onClick, label}: {onClick: () => void; label: string}) { return <button className="row-link" aria-label={label} onClick={onClick}><ArrowUpRight size={16}/></button> }
export function Saved({children}: {children: ReactNode}) { return <span className="saved-label"><Check size={13}/>{children}</span> }
