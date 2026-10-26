import { Area, AreaChart, Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import type { InventoryRow, Workspace } from './types'
import { compact, displayDate, money, number, unitOf } from './components'

export const riskColors: Record<string,string> = {'Normal':'#74806C','Low Stock':'#B2935B','Critical Stock':'#AE6658','Data Quality Issue':'#8A8580'}
const axis = {fontSize:11,fill:'#8B847B'}
const tooltip = {border:'1px solid #E7E1D8',borderRadius:6,boxShadow:'0 6px 20px #25231f08',fontSize:12,background:'#fff'}
export const inventoryUnits = (rows: InventoryRow[]) => [...new Set(rows.map(unitOf))].sort()
export const preferredUnit = (rows: InventoryRow[]) => inventoryUnits(rows).includes('kg') ? 'kg' : inventoryUnits(rows)[0] || 'unit'

export function getDemand(data: Workspace, days: number, end: string, skus?: Set<string>) {
  const startDate=new Date(`${end}T12:00:00`);startDate.setDate(startDate.getDate()-days+1)
  const start=startDate.toISOString().slice(0,10)
  const daily=new Map<string,number>()
  for (const row of data.sales) if (row.sale_date>=start&&row.sale_date<=end&&(!skus||skus.has(row.sku))) daily.set(row.sale_date,(daily.get(row.sale_date)??0)+row.units)
  return [...daily].sort(([a],[b])=>a.localeCompare(b)).map(([date,units])=>({date,units}))
}

export function DemandChart({data,unit='unit'}:{data:{date:string;units:number}[];unit?:string}) {
  if (!data.length) return <div className="chart-empty">No recorded demand in this period.</div>
  return <div className="chart-canvas"><ResponsiveContainer width="100%" height="100%"><AreaChart data={data} margin={{left:-12,right:12,top:16,bottom:4}}>
    <CartesianGrid vertical={false} stroke="#EEE9E2" strokeDasharray="3 4"/>
    <XAxis dataKey="date" tickFormatter={value=>displayDate(value,{day:'numeric',month:'short'})} axisLine={false} tickLine={false} minTickGap={35} tick={axis} dy={10}/>
    <YAxis axisLine={false} tickLine={false} tick={axis} tickFormatter={compact}/>
    <Tooltip contentStyle={tooltip} labelFormatter={value=>displayDate(String(value))} formatter={value=>[`${number(Number(value))} ${unit}`,'Recorded demand']} cursor={{stroke:'#B9A58F',strokeDasharray:'4 4'}}/>
    <Area isAnimationActive={false} type="monotone" dataKey="units" stroke="#77583F" strokeWidth={2} fill="#A58763" fillOpacity={.1} activeDot={{r:4,stroke:'white',strokeWidth:2}}/>
  </AreaChart></ResponsiveContainer></div>
}

export function HealthChart({rows}:{rows:InventoryRow[]}) {
  return <div className="risk-distribution">{Object.entries(riskColors).map(([risk,color])=>{
    const count=rows.filter(row=>row.risk===risk).length
    return <div className="risk-distribution-row" key={risk}><div><span className="legend-dot" style={{background:color}}/><span>{risk==='Normal'?'Healthy stock':risk==='Data Quality Issue'?'Data quality':risk}</span><strong>{count}</strong></div><div className="risk-track"><span style={{width:`${rows.length?count/rows.length*100:0}%`,background:color}}/></div></div>
  })}<div className="risk-distribution-total">{rows.length} materials assessed</div></div>
}

export function StockChart({data,unit='unit'}:{data:{date:string;on_hand:number;on_order:number}[];unit?:string}) {
  if (!data.length) return <div className="chart-empty">No inventory snapshots in this period.</div>
  return <div className="chart-canvas"><ResponsiveContainer width="100%" height="100%"><AreaChart data={data} margin={{left:-12,right:12,top:16,bottom:4}}>
    <CartesianGrid vertical={false} stroke="#EEE9E2" strokeDasharray="3 4"/><XAxis dataKey="date" tickFormatter={value=>displayDate(value,{day:'numeric',month:'short'})} axisLine={false} tickLine={false} minTickGap={30} tick={axis} dy={10}/><YAxis axisLine={false} tickLine={false} tick={axis} tickFormatter={compact}/><Tooltip contentStyle={tooltip} formatter={(value,name)=>[`${number(Number(value))} ${unit}`,name]}/>
    <Area isAnimationActive={false} type="monotone" dataKey="on_hand" name="On hand" stroke="#77583F" strokeWidth={2} fill="#A58763" fillOpacity={.08}/><Area isAnimationActive={false} type="monotone" dataKey="on_order" name="On order" stroke="#A6A095" strokeWidth={1.6} fill="#A6A095" fillOpacity={.03}/>
  </AreaChart></ResponsiveContainer></div>
}

export function SupplierChart({rows}:{rows:InventoryRow[]}) {
  const suppliers=[...new Set(rows.map(row=>row.supplier))].map(supplier=>{const items=rows.filter(row=>row.supplier===supplier);return {supplier:supplier.replace('Demo supplier ',''),lead:items.reduce((sum,row)=>sum+row.lead_time_days,0)/items.length}})
  return <div className="chart-canvas"><ResponsiveContainer width="100%" height="100%"><BarChart data={suppliers} margin={{left:-20,right:16,top:20,bottom:20}}><CartesianGrid vertical={false} stroke="#EEE9E2"/><XAxis dataKey="supplier" axisLine={false} tickLine={false} tick={axis} tickFormatter={value=>value.length>14?`${value.slice(0,13)}…`:value}/><YAxis axisLine={false} tickLine={false} tick={axis}/><Tooltip contentStyle={tooltip} formatter={value=>[`${number(Number(value))} days`,'Mean product lead time']}/><Bar isAnimationActive={false} dataKey="lead" fill="#B09B82" radius={[3,3,0,0]} maxBarSize={45}/></BarChart></ResponsiveContainer></div>
}

export function MaterialValueChart({rows}:{rows:InventoryRow[]}) {
  const values=[...rows].filter(row=>row.estimated_cost_vnd>0).sort((a,b)=>b.estimated_cost_vnd-a.estimated_cost_vnd).slice(0,7).map(row=>({sku:row.sku,name:row.product_name,value:row.estimated_cost_vnd}))
  if (!values.length) return <div className="chart-empty">No replenishment value is currently recommended.</div>
  return <div className="chart-canvas"><ResponsiveContainer width="100%" height="100%"><BarChart data={values} layout="vertical" margin={{left:8,right:25,top:8,bottom:4}}><CartesianGrid horizontal={false} stroke="#EEE9E2"/><XAxis type="number" axisLine={false} tickLine={false} tick={axis} tickFormatter={compact}/><YAxis dataKey="sku" type="category" width={84} axisLine={false} tickLine={false} tick={axis}/><Tooltip contentStyle={tooltip} labelFormatter={value=>values.find(row=>row.sku===value)?.name||value} formatter={value=>[money(Number(value)),'Recommended value']}/><Bar isAnimationActive={false} dataKey="value" fill="#8F7051" radius={[0,3,3,0]} maxBarSize={22}/></BarChart></ResponsiveContainer></div>
}
