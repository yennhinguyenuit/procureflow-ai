import { useState } from 'react'
import { ArrowDownToLine, ArrowRight, ArrowUpRight, Clock3, FileCheck2, Package, Plus, TriangleAlert, Wallet } from 'lucide-react'
import { Badge, Button, categoryOf, compact, displayDate, Empty, money, number, PageHeader, ProductCell, quantity, Select, shortMoney, unitOf } from './components'
import { DemandChart, getDemand, HealthChart, inventoryUnits, preferredUnit } from './Charts'
import { reportUrl } from './api'
import { actionLabels, stockChanges } from './workspaceData'
import type { PageProps } from './appTypes'

export default function Overview({data,date,navigate,openInventory,openRequest,generate,generating}: PageProps) {
  const [days,setDays]=useState(30)
  const [demandUnit,setDemandUnit]=useState(()=>preferredUnit(data.inventory))
  const low=data.inventory.filter(row=>row.risk==='Low Stock').length
  const critical=data.inventory.filter(row=>row.risk==='Critical Stock').length
  const pending=data.proposals.filter(row=>row.status==='DRAFT').length
  const recommendations=data.inventory.filter(row=>row.quantity>0)
  const value=recommendations.reduce((sum,row)=>sum+row.estimated_cost_vnd,0)
  const priorities=[...data.inventory].filter(row=>row.risk!=='Normal').sort((a,b)=>(a.risk==='Critical Stock'?0:1)-(b.risk==='Critical Stock'?0:1)||b.estimated_cost_vnd-a.estimated_cost_vnd)
  const demand=getDemand(data,days,date,new Set(data.inventory.filter(row=>unitOf(row)===demandUnit).map(row=>row.sku)))
  const recentStock=stockChanges(data).slice(0,4)
  const procurement=data.audit.filter(row=>['CREATED','APPROVED','REJECTED'].includes(row.action)).slice(0,4)
  return <>
    <PageHeader title="Operations overview" description="Inventory readiness, purchasing priorities, and recent decisions." eyebrow="PROCUREMENT OPERATIONS">
      <a className="button button-secondary" href={reportUrl(date)}><ArrowDownToLine size={16}/>Export report</a>
      <Button variant="primary" icon={<Plus size={16}/>} loading={generating} onClick={generate}>Generate requests</Button>
    </PageHeader>
    <div className="assessment-note"><span>Demand window ending <strong>{displayDate(date)}</strong></span><span>Replenishment uses current inventory balances</span></div>
    <div className="kpi-grid five-kpis">
      <article className="kpi-card"><div className="kpi-label">Total SKUs<Package size={16}/></div><strong className="kpi-value">{data.inventory.length}</strong><p className="kpi-context">Across {data.suppliers.length} suppliers</p></article>
      <article className="kpi-card"><div className="kpi-label">Low-stock items<Clock3 size={16}/></div><strong className="kpi-value">{low}</strong><p className="kpi-context">Reorder review required</p></article>
      <article className="kpi-card"><div className="kpi-label">Critical-stock items<TriangleAlert size={16}/></div><strong className="kpi-value critical-number">{critical}</strong><p className="kpi-context">Physical availability risk</p></article>
      <article className="kpi-card"><div className="kpi-label">Pending requests<FileCheck2 size={16}/></div><strong className="kpi-value">{pending}</strong><p className="kpi-context">Awaiting a review decision</p></article>
      <article className="kpi-card"><div className="kpi-label">Estimated procurement<Wallet size={16}/></div><strong className="kpi-value" title={money(value)}>{compact(value)}<span className="kpi-unit">VND</span></strong><p className="kpi-context">{recommendations.length} recommended materials</p></article>
    </div>
    <div className="overview-charts">
      <section className="panel"><div className="panel-header"><div><h2>Material demand</h2><p>Recorded usage and withdrawals · {demandUnit}</p></div><div className="chart-controls"><Select label="Demand unit" value={demandUnit} onChange={setDemandUnit}>{inventoryUnits(data.inventory).map(unit=><option key={unit}>{unit}</option>)}</Select><div className="segmented">{[14,30,84].map(value=><button key={value} className={value===days?'selected':''} onClick={()=>setDays(value)}>{value}d</button>)}</div></div></div><div className="chart-stat"><strong>{number(demand.reduce((sum,row)=>sum+row.units,0))}</strong><span>{demandUnit} in selected period</span></div><DemandChart data={demand} unit={demandUnit}/></section>
      <section className="panel"><div className="panel-header"><div><h2>Stock classification</h2><p>Current policy assessment</p></div><button className="icon-button" onClick={()=>navigate('inventory')} aria-label="View inventory classification"><ArrowUpRight size={17}/></button></div><HealthChart rows={data.inventory}/><div className="panel-footnote">Inbound coverage can reduce buying needs while physical-stock risk remains.</div></section>
    </div>
    <section className="panel priorities-panel"><div className="panel-header"><div><h2>Replenishment priorities <span className="count-pill">{priorities.length}</span></h2><p>Review physical availability and the next recommended purchase.</p></div><button className="text-button" onClick={()=>navigate('inventory')}>View inventory<ArrowRight size={14}/></button></div>{priorities.length?<div className="table-wrap"><table className="priority-table"><thead><tr><th>Material</th><th>Stock status</th><th className="numeric">Available</th><th className="numeric">Recommended</th><th className="numeric">Estimated value</th></tr></thead><tbody>{priorities.slice(0,5).map(row=><tr key={row.sku}><td><ProductCell row={row} onClick={()=>openInventory(row)}/><span className="material-meta">{categoryOf(row)}</span></td><td><Badge value={row.risk}/></td><td className="numeric">{quantity(row.available_stock,row)}</td><td className="numeric strong">{quantity(row.quantity,row)}</td><td className="numeric">{shortMoney(row.estimated_cost_vnd)}</td></tr>)}</tbody></table></div>:<Empty title="No stock risks identified" description="Current materials are within the policy assessment. Continue reviewing recorded demand and incoming deliveries."/>}<div className="panel-table-footer"><span>Rule-based quantities · Human approval required</span><span>Full-pack order rounding</span></div></section>
    <div className="overview-activity-grid">
      <section className="panel"><div className="panel-header"><div><h2>Recent stock changes</h2><p>Persisted adjustments and approved inbound quantities</p></div><button className="text-button" onClick={()=>navigate('activity')}>View history<ArrowRight size={14}/></button></div><div className="compact-event-list">{recentStock.length?recentStock.map(event=>{const material=data.inventory.find(row=>row.sku===event.sku);return <article key={event.key}><span className="event-icon"><Package size={16}/></span><div><button onClick={()=>{if(material)openInventory(material)}} className="event-title">{material?.product_name||event.sku}</button><p>{event.field==='on_hand'?'On hand':event.field==='on_order'?'On order':'Reserved'}: {event.before===undefined?'—':number(event.before)} → {number(event.after)} {material?unitOf(material):'unit'}</p><small>{event.actor} · {displayDate(event.created_at,{day:'numeric',month:'short',hour:'2-digit',minute:'2-digit'})}</small></div></article>}):<div className="compact-empty"><Package size={20}/><p>No inventory adjustments recorded.</p></div>}</div></section>
      <section className="panel"><div className="panel-header"><div><h2>Procurement activity</h2><p>Recent request creation and review decisions</p></div><button className="text-button" onClick={()=>navigate('requests')}>View requests<ArrowRight size={14}/></button></div><div className="compact-event-list">{procurement.length?procurement.map(event=><article key={event.id}><span className="event-icon"><FileCheck2 size={16}/></span><div><button className="event-title" onClick={()=>{const request=data.proposals.find(row=>row.id===event.proposal_id);if(request)openRequest(request)}}>{actionLabels[event.action]} · PR-{String(event.proposal_id).padStart(4,'0')}</button><p>{event.actor}</p><small>{displayDate(event.created_at,{day:'numeric',month:'short',hour:'2-digit',minute:'2-digit'})}</small></div><Badge value={event.action==='CREATED'?'DRAFT':event.action}/></article>):<div className="compact-empty"><FileCheck2 size={20}/><p>No purchase requests created yet.</p></div>}</div></section>
    </div>
  </>
}
