import { ArrowDownToLine, ArrowRight, ArrowUpRight, Boxes, CheckCheck, ChevronRight, CircleCheck, Clock3, FileCheck2, Layers3, Package, Plus, ShieldCheck, Sparkles, TriangleAlert, Wallet } from 'lucide-react'
import { useState } from 'react'
import { Badge, Button, compact, displayDate, money, number, PageHeader, ProductCell, RowLink, shortMoney } from './components'
import { DemandChart, getDemand, HealthChart } from './Charts'
import { reportUrl } from './api'
import type { PageProps } from './appTypes'

export default function Overview(props: PageProps) {
  const {data,date,navigate,openInventory,generate,generating} = props
  const [days,setDays] = useState(30)
  const critical = data.inventory.filter(row => row.risk === 'Critical Stock').length
  const low = data.inventory.filter(row => row.risk === 'Low Stock').length
  const quality = data.inventory.filter(row => row.risk === 'Data Quality Issue').length
  const needs = data.inventory.filter(row => row.quantity > 0)
  const pending = data.proposals.filter(row => row.status === 'DRAFT')
  const priorities = [...data.inventory].filter(row => row.risk !== 'Normal').sort((a,b)=> (a.risk==='Critical Stock'?-1:1)-(b.risk==='Critical Stock'?-1:1) || b.estimated_cost_vnd-a.estimated_cost_vnd)
  const spend=needs.reduce((sum,row)=>sum+row.estimated_cost_vnd,0)
  const demand=getDemand(data,days,date)
  const sales=demand.reduce((sum,row)=>sum+row.units,0)
  const openExceptions=data.exceptions.filter(row=>row.status==='OPEN')
  const healthy=data.inventory.filter(row=>row.risk==='Normal').length
  return <>
    <PageHeader title="Operations overview" description="Everything you need to keep your supply moving."><a className="button button-secondary" href={reportUrl(date)}><ArrowDownToLine size={16}/>Export report</a><Button variant="primary" icon={<Plus size={17}/>} loading={generating} onClick={generate}>Generate requests</Button></PageHeader>
    <div className="overview-welcome"><span><span className="live-dot"/>Workspace up to date</span><span>Assessment for {displayDate(date, {day:'numeric',month:'long',year:'numeric'})}<span className="welcome-divider"/>Current inventory balances</span></div>
    <div className="kpi-grid">
      <div className="kpi-card"><div className="kpi-label">Total inventory items<span className="kpi-icon teal"><Boxes size={19}/></span></div><div className="kpi-value">{number(data.inventory.length)}<span className="kpi-unit">SKUs</span></div><div className="kpi-context"><span className="small-dot teal-dot"/>Across {data.suppliers.length} suppliers<span className="kpi-mini">Active inventory</span></div></div>
      <div className="kpi-card"><div className="kpi-label">Items needing attention<span className="kpi-icon coral"><TriangleAlert size={18}/></span></div><div className="kpi-value">{critical+low+quality}<span className="kpi-unit">items</span></div><div className="kpi-context"><span className="attention-count">{critical} critical</span><span className="context-separator">·</span>{quality?`${quality} data issues`:`${low} low stock`}</div></div>
      <div className="kpi-card"><div className="kpi-label">Pending purchase requests<span className="kpi-icon violet"><FileCheck2 size={19}/></span></div><div className="kpi-value">{pending.length}<span className="kpi-unit">requests</span></div><div className="kpi-context"><Clock3 size={13}/>{pending.length ? 'Waiting for human review' : 'Your approval queue is clear'}</div></div>
      <div className="kpi-card"><div className="kpi-label">Recommended procurement<span className="kpi-icon blue"><Wallet size={18}/></span></div><div className="kpi-value currency-value" title={money(spend)}>{compact(spend)}<span className="kpi-unit">VND</span></div><div className="kpi-context">For {needs.length} item{needs.length===1?'':'s'} requiring replenishment</div></div>
    </div>
    <div className="overview-charts">
      <section className="panel demand-panel"><div className="panel-header"><div><h2>Demand at a glance</h2><p>Daily sales across your tracked inventory</p></div><div className="segmented">{[14,30,84].map(value=><button key={value} className={value===days?'selected':''} onClick={()=>setDays(value)}>{value} days</button>)}</div></div><div className="chart-stat"><strong>{number(sales)}</strong><span>units sold</span><span className="chart-series-label"><span className="legend-dot"/>Daily demand</span></div><DemandChart data={demand}/><div className="chart-footnote"><ShieldCheck size={13}/>Recorded sales history · rule-based demand calculation</div></section>
      <section className="panel health-panel"><div className="panel-header"><div><h2>Inventory health</h2><p>Know where to focus next</p></div><span className="subtle-icon"><Layers3 size={17}/></span></div><HealthChart rows={data.inventory}/><div className="health-footer"><span><span className="live-dot"/>{healthy} of {data.inventory.length} items healthy</span><button onClick={()=>navigate('inventory')} aria-label="View all inventory health"><ArrowUpRight size={17}/></button></div></section>
    </div>
    <div className="overview-bottom">
      <section className="panel attention-panel"><div className="panel-header"><div><h2>Needs your attention <span className="count-pill">{priorities.length}</span></h2><p>Review stock risks before they affect operations</p></div><button className="text-button" onClick={()=>navigate('inventory')}>View inventory<ArrowRight size={14}/></button></div><div className="table-wrap"><table><thead><tr><th>Item</th><th className="numeric">Available</th><th>Status</th><th className="numeric">Suggested order</th><th/></tr></thead><tbody>{priorities.slice(0,4).map(row=><tr key={row.sku}><td><ProductCell row={row} onClick={()=>openInventory(row)}/></td><td className="numeric"><strong>{number(row.available_stock)}</strong><small className="cell-caption">units available</small></td><td><Badge value={row.risk}/></td><td className="numeric"><strong>{number(row.quantity)} <span className="muted">units</span></strong><small className="cell-caption">{shortMoney(row.estimated_cost_vnd)}</small></td><td><RowLink onClick={()=>openInventory(row)} label={`Review ${row.product_name}`}/></td></tr>)}</tbody></table>{!priorities.length && <div className="compact-empty"><CircleCheck size={23}/><span>Your inventory is in a healthy place.</span></div>}</div><div className="panel-table-footer"><span><span className="legend-dot amber-dot"/>Recommendations require your review</span><span>Quantities calculated by Python</span></div></section>
      <div className="overview-aside"><section className="assistant-card"><div className="assistant-card-top"><span className="assistant-orb"><Sparkles size={21}/></span><span className="local-pill"><span/>Runs locally</span></div><h2>A little clarity.<br/>A better next step.</h2><p>Ask your AI workspace what needs attention, and see the data behind every answer.</p><button onClick={()=>navigate('ai')}>Explore AI workspace<ArrowUpRight size={16}/></button><div className="assistant-card-bottom"><ShieldCheck size={13}/>Your business data stays here</div></section><section className="next-step-card"><span className="next-step-icon">{pending.length ? <FileCheck2 size={18}/> : <CheckCheck size={18}/>}</span><div><strong>{pending.length ? `${pending.length} requests to review` : openExceptions.length ? `${openExceptions.length} open exceptions` : 'Ready for your next move'}</strong><p>{pending.length ? 'A quick review keeps things moving.' : openExceptions.length ? 'Resolve data issues before ordering.' : 'Create drafts from your stock recommendations.'}</p></div><button aria-label={pending.length?'Review pending requests':'Open purchase requests'} onClick={()=>navigate(pending.length?'requests':openExceptions.length?'activity':'requests')}><ChevronRight size={19}/></button></section></div>
    </div>
    <div className="overview-bottom-note"><span><ShieldCheck size={14}/>Every recommendation is explainable. Every decision is traceable.</span><button className="text-button" onClick={()=>navigate('activity')}>View activity<ArrowRight size={13}/></button></div>
  </>
}

