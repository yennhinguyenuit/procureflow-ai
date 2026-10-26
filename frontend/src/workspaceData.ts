import type { Audit, Workspace } from './types'

export const actionLabels: Record<string,string> = {
  DEMO_SEEDED:'Workspace initialized',DATA_IMPORTED:'Data imported',CREATED:'Request created',
  APPROVED:'Request approved',REJECTED:'Request rejected',EXCEPTION_RECORDED:'Exception recorded',
  EXCEPTIONS_RESOLVED:'Exception resolved',SETTINGS_UPDATED:'Settings updated',
}
export function parseEvidence(value?: string): Record<string,unknown> {
  try {return value ? JSON.parse(value) : {}} catch {return {}}
}
export function affectedSkus(event: Audit, data: Workspace): string[] {
  const records = (value: Record<string,unknown>) => Array.isArray(value.records) ? value.records as Record<string,unknown>[] : []
  const before=parseEvidence(event.before_json),after=parseEvidence(event.after_json)
  const skus=[...records(before),...records(after)].map(row=>String(row.sku||'')).filter(Boolean)
  if (typeof after.sku==='string') skus.push(after.sku)
  const proposal=data.proposals.find(row=>row.id===event.proposal_id)
  if (proposal) skus.push(proposal.sku)
  return [...new Set(skus)]
}
export function stockChanges(data: Workspace) {
  const changes:{key:string;sku:string;actor:string;created_at:string;before?:number;after:number;field:string}[]=[]
  for (const event of data.audit) {
    const before=parseEvidence(event.before_json),after=parseEvidence(event.after_json)
    const previous=Array.isArray(before.records)?before.records as Record<string,unknown>[]:[]
    const next=Array.isArray(after.records)?after.records as Record<string,unknown>[]:[]
    for (const row of next) {
      if (typeof row.sku!=='string') continue
      const old=previous.find(item=>item.sku===row.sku)
      for (const field of ['on_hand','on_order','reserved_qty']) {
        if (typeof row[field]==='number'&&old?.[field]!==row[field]) changes.push({key:`${event.id}:${row.sku}:${field}`,sku:row.sku,actor:event.actor,created_at:event.created_at,before:typeof old?.[field]==='number'?old[field] as number:undefined,after:row[field] as number,field})
      }
    }
    if (event.action==='APPROVED'&&typeof after.on_order==='number') {
      const proposal=data.proposals.find(row=>row.id===event.proposal_id)
      if (proposal) changes.push({key:`${event.id}:approval`,sku:proposal.sku,actor:event.actor,created_at:event.created_at,before:typeof before.on_order==='number'?before.on_order:undefined,after:after.on_order,field:'on_order'})
    }
  }
  return changes
}
