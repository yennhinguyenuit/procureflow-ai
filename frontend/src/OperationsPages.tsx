import { useMemo, useState } from 'react'
import { ArrowDownToLine, ArrowUpRight, Building2, FileCheck2, Mail, Plus, Search, Upload } from 'lucide-react'
import { Badge, Button, categoryOf, displayDate, Empty, FieldTooltip, number, PageHeader, ProductCell, quantity, Select, shortMoney, unitOf } from './components'
import { reportUrl } from './api'
import type { PageProps } from './appTypes'
import type { InventoryRow } from './types'

function SearchField({value,setValue,placeholder}:{value:string;setValue:(value:string)=>void;placeholder:string}) {
  return <label className="table-search"><Search size={16}/><input value={value} onChange={event=>setValue(event.target.value)} placeholder={placeholder} aria-label={placeholder}/></label>
}
function SupplierFilter({data,value,onChange}:{data:PageProps['data'];value:string;onChange:(value:string)=>void}) {
  return <Select label="Filter by supplier" value={value} onChange={onChange}><option value="">All suppliers</option>{data.suppliers.map(item=><option key={item.name} value={item.name}>{item.name}</option>)}</Select>
}
function QuantityCell({value,row}:{value:number;row:InventoryRow}) {return <><strong>{number(value)}</strong><span className="cell-unit">{unitOf(row)}</span></>}

export function InventoryPage({data,date,openImport,openInventory}:PageProps) {
  const [search,setSearch]=useState(''),[supplier,setSupplier]=useState(''),[category,setCategory]=useState(''),[risk,setRisk]=useState(''),[sort,setSort]=useState('risk')
  const [view,setView]=useState('balances')
  const categories=[...new Set(data.inventory.map(categoryOf))].sort()
  const ranks:Record<string,number>={'Critical Stock':0,'Low Stock':1,'Data Quality Issue':2,'Normal':3}
  const rows=data.inventory.filter(row=>(!supplier||row.supplier===supplier)&&(!risk||row.risk===risk)&&(!category||categoryOf(row)===category)&&`${row.sku} ${row.product_name} ${row.supplier} ${categoryOf(row)} ${row.origin||''}`.toLowerCase().includes(search.toLowerCase())).sort((a,b)=>sort==='name'?a.product_name.localeCompare(b.product_name):sort==='on_hand'?unitOf(a).localeCompare(unitOf(b))||a.on_hand-b.on_hand:sort==='value'?b.estimated_cost_vnd-a.estimated_cost_vnd:ranks[a.risk]-ranks[b.risk]||a.product_name.localeCompare(b.product_name))
  return <>
    <PageHeader title="Inventory" description="Material balances, quality context, and replenishment calculations." eyebrow="MATERIAL CONTROL"><a className="button button-secondary" href={reportUrl(date,'replenishment.csv')}><ArrowDownToLine size={16}/>Export inventory</a><Button variant="primary" icon={<Upload size={16}/>} onClick={()=>openImport('inventory')}>Import data</Button></PageHeader>
    <div className="inventory-summary">
      <div><small>Tracked materials</small><strong>{data.inventory.length}<em>SKUs</em></strong></div>
      <div><small>With inbound stock</small><strong>{data.inventory.filter(row=>row.on_order>0).length}<em>materials</em></strong></div>
      <div><small>With reserved stock</small><strong>{data.inventory.filter(row=>row.reserved_qty>0).length}<em>materials</em></strong></div>
      <div><small>Recommended for ordering</small><strong>{data.inventory.filter(row=>row.quantity>0).length}<em>materials</em></strong></div>
    </div>
    <section className="panel inventory-panel">
      <div className="page-tabs"><button className={view==='balances'?'active':''} onClick={()=>setView('balances')}>Stock balances</button><button className={view==='replenishment'?'active':''} onClick={()=>setView('replenishment')}>Replenishment</button><span className="tab-context">{rows.length} materials</span></div>
      <div className="inventory-filters"><SearchField value={search} setValue={setSearch} placeholder="Search material, SKU, or origin"/><Select label="Filter by category" value={category} onChange={setCategory}><option value="">All categories</option>{categories.map(item=><option key={item}>{item}</option>)}</Select><SupplierFilter data={data} value={supplier} onChange={setSupplier}/><Select label="Filter stock status" value={risk} onChange={setRisk}><option value="">All stock statuses</option>{['Critical Stock','Low Stock','Normal','Data Quality Issue'].map(item=><option key={item}>{item}</option>)}</Select></div>
      <div className="table-subtoolbar"><span>{view==='balances'?'Current balances by material and unit of measure':'14-day demand average · 4-day review period'}</span><Select label="Sort materials" value={sort} onChange={setSort}><option value="risk">Sort: Stock risk</option><option value="name">Sort: Material name</option><option value="on_hand">On hand (within unit)</option><option value="value">Sort: Procurement value</option></Select></div>
      <div className="table-wrap"><table className={`material-table ${view==='balances'?'balance-view':'replenishment-view'}`}>
        <colgroup>{(view==='balances'?[29,17,12,12,12,12,6]:[29,12,12,10,10,13,14]).map((width,index)=><col style={{width:`${width}%`}} key={index}/>)}</colgroup>
        <thead><tr><th>Material</th>{view==='balances'?<><th>Stock status</th><th className="numeric">On hand</th><th className="numeric">On order</th><th className="numeric">Reserved <FieldTooltip label="Reserved" description="Stock allocated to existing demand. Reserved quantities reduce available stock and inventory position."/></th><th className="numeric">Available</th><th/></>:<><th className="numeric">Daily demand <FieldTooltip label="Daily demand" description="Recorded demand in the last 14 calendar days divided by 14. Missing days contribute zero; the policy uses the unrounded total."/></th><th className="numeric">Position <FieldTooltip label="Position" description="On-hand stock plus on-order stock minus reserved quantities, in the material base unit."/></th><th className="numeric">Reorder point <FieldTooltip label="Reorder point" description="Ceiling of demand during lead time plus safety stock. Positive demand at or below this point is evaluated for replenishment."/></th><th className="numeric">Target <FieldTooltip label="Target" description="Ceiling of demand during lead time plus four review days, then safety stock. Orders fill the positive target gap in full packs."/></th><th className="numeric">Order quantity</th><th className="numeric">Est. value</th></>}</tr></thead>
        <tbody>{rows.map(row=><tr key={row.sku}><td><ProductCell row={row} onClick={()=>openInventory(row)}/><span className="material-supplier">{row.supplier}</span><span className="material-meta">{categoryOf(row)} · {unitOf(row)}{view==='replenishment'?` · ${row.lead_time_days}d lead`:''}</span></td>{view==='balances'?<><td><Badge value={row.risk}/></td><td className="numeric"><QuantityCell value={row.on_hand} row={row}/></td><td className="numeric"><QuantityCell value={row.on_order} row={row}/></td><td className="numeric"><QuantityCell value={row.reserved_qty} row={row}/></td><td className={`numeric ${row.risk==='Critical Stock'?'critical-number':''}`}><QuantityCell value={row.available_stock} row={row}/></td><td><button className="row-link" onClick={()=>openInventory(row)} aria-label={`Open ${row.product_name}`}><ArrowUpRight size={15}/></button></td></>:<><td className="numeric"><QuantityCell value={row.avg_daily_demand} row={row}/></td><td className="numeric"><QuantityCell value={row.inventory_position} row={row}/></td><td className="numeric"><QuantityCell value={row.reorder_point} row={row}/></td><td className="numeric"><QuantityCell value={row.target_stock} row={row}/></td><td className="numeric recommended-quantity"><QuantityCell value={row.quantity} row={row}/></td><td className="numeric value-cell">{shortMoney(row.estimated_cost_vnd)}</td></>}</tr>)}</tbody>
      </table></div>
      {!rows.length&&<Empty title="No matching materials" description="Adjust the category, supplier, stock status, or search term."/>}
      <div className="panel-table-footer"><span>Showing {rows.length} of {data.inventory.length} materials</span><span>Open a material for source data and calculation details</span></div>
    </section>
  </>
}

export function RequestsPage({data,date,generating,generate,openRequest}:PageProps) {
  const [search,setSearch]=useState(''),[status,setStatus]=useState(''),[supplier,setSupplier]=useState('')
  const rows=data.proposals.filter(row=>(!status||row.status===status)&&(!supplier||row.supplier===supplier)&&`${row.id} ${row.sku} ${row.product_name} ${row.supplier}`.toLowerCase().includes(search.toLowerCase()))
  return <>
    <PageHeader title="Purchase requests" description="Review material requirements, saved policy evidence, and purchasing decisions." eyebrow="PURCHASING CONTROL"><a className="button button-secondary" href={reportUrl(date,'proposals.csv')}><ArrowDownToLine size={16}/>Export requests</a><Button variant="primary" icon={<Plus size={16}/>} loading={generating} onClick={generate}>Generate requests</Button></PageHeader>
    <div className="request-summary"><button className={!status?'active':''} onClick={()=>setStatus('')}><span>All requests</span><strong>{data.proposals.length}</strong></button>{['DRAFT','APPROVED','REJECTED'].map((value,index)=><button key={value} className={status===value?'active':''} onClick={()=>setStatus(value)}><span>{['Pending review','Approved','Rejected'][index]}</span><strong>{data.proposals.filter(row=>row.status===value).length}</strong></button>)}</div>
    <section className="panel"><div className="table-toolbar"><SearchField value={search} setValue={setSearch} placeholder="Search request, material, or SKU"/><div className="toolbar-right"><SupplierFilter data={data} value={supplier} onChange={setSupplier}/><Select label="Filter request status" value={status} onChange={setStatus}><option value="">All statuses</option><option value="DRAFT">Pending review</option><option value="APPROVED">Approved</option><option value="REJECTED">Rejected</option></Select></div></div>
      {rows.length?<div className="table-wrap"><table className="requests-table"><thead><tr><th>Request / material</th><th>Supplier</th><th>Status</th><th className="numeric">Quantity</th><th className="numeric">Est. value</th><th>Created</th><th/></tr></thead><tbody>{rows.map(row=>{const material=data.inventory.find(item=>item.sku===row.sku);const unit={unit_of_measure:row.unit_of_measure||material?.unit_of_measure};return <tr key={row.id}><td><span className="request-id">PR-{String(row.id).padStart(4,'0')}</span><ProductCell row={row} onClick={()=>openRequest(row)}/></td><td className="supplier-cell">{row.supplier}</td><td><Badge value={row.status}/></td><td className="numeric">{quantity(row.quantity,unit)}</td><td className="numeric strong">{shortMoney(row.estimated_cost_vnd)}</td><td className="date-cell">{displayDate(row.created_at,{day:'numeric',month:'short'})}</td><td><button className="review-button" onClick={()=>openRequest(row)}>{row.status==='DRAFT'?'Review':'Details'}<ArrowUpRight size={13}/></button></td></tr>})}</tbody></table></div>:<Empty icon={<FileCheck2 size={26}/>} title={data.proposals.length?'No requests match these filters':'No purchase requests yet'} description={data.proposals.length?'Adjust the status, supplier, or search term.':'Generate draft requests from current stock recommendations. Every draft requires a reviewer decision.'} action={!data.proposals.length?<Button variant="primary" icon={<Plus size={16}/>} loading={generating} onClick={generate}>Generate requests</Button>:undefined}/>}
      <div className="panel-table-footer"><span>{rows.length} requests</span><span>Saved cost and policy snapshot · Reviewer name and reason required</span></div>
    </section>
  </>
}

export function SuppliersPage({data,openImport,openInventory}:PageProps) {
  const [search,setSearch]=useState('')
  const suppliers=useMemo(()=>data.suppliers.filter(row=>`${row.name} ${row.contact_email||''}`.toLowerCase().includes(search.toLowerCase())),[data.suppliers,search])
  return <>
    <PageHeader title="Suppliers" description="Supplier assignments, reference lead times, and master-data completeness." eyebrow="SUPPLIER DIRECTORY"><Button variant="primary" icon={<Upload size={16}/>} onClick={()=>openImport('suppliers')}>Import suppliers</Button></PageHeader>
    <div className="section-search"><SearchField value={search} setValue={setSearch} placeholder="Search supplier or contact"/><span>{data.suppliers.length} supplier records</span></div>
    <div className="supplier-grid">{suppliers.map(supplier=>{const items=data.inventory.filter(row=>row.supplier===supplier.name);const pending=data.proposals.filter(row=>row.supplier===supplier.name&&row.status==='DRAFT');const completeness=Number(!!supplier.name)+Number(!!supplier.lead_time_days)+Number(!!supplier.contact_email);return <section className="panel supplier-card" key={supplier.name}>
      <div className="supplier-card-heading"><span className="supplier-avatar"><Building2 size={24} strokeWidth={1.4}/></span><span className={`badge ${completeness===3?'badge-green':'badge-neutral'}`}>{completeness}/3 fields complete</span></div>
      <h2>{supplier.name}</h2><div className="supplier-stats"><div><small>Assigned materials</small><strong>{items.length}</strong></div><div><small>Reference lead time</small><strong>{supplier.lead_time_days??'—'}<em>days</em></strong></div><div><small>Pending requests</small><strong>{pending.length}</strong></div></div>
      <div className="supplier-contact"><Mail size={15}/>{supplier.contact_email?<a href={`mailto:${supplier.contact_email}`}>{supplier.contact_email}</a>:<span>Contact email not provided</span>}</div>
      {completeness<3&&<div className="data-completeness-note">{!supplier.lead_time_days?'Reference lead time is missing. ':''}{!supplier.contact_email?'Add an approved contact through supplier import.':''}</div>}
      <div className="supplier-items"><span className="eyebrow">ASSIGNED MATERIALS</span>{items.map(row=><button key={row.sku} onClick={()=>openInventory(row)}><span>{row.product_name}<small>{row.sku} · {unitOf(row)}</small></span><ArrowUpRight size={14}/></button>)}{!items.length&&<p>No materials assigned.</p>}</div>
    </section>})}</div>
    {!suppliers.length&&<Empty title="No suppliers found" description="Adjust your search or import a validated supplier file."/>}
  </>
}
