import { useEffect, useRef, useState } from 'react'
import { ArrowRight, ArrowUp, ArrowUpRight, Check, ChevronRight, ClipboardList, FileCheck2, History, LoaderCircle, MessageSquare, Plus, X } from 'lucide-react'
import { api } from './api'
import { displayDate, initials, InlineError, PageHeader, Select } from './components'
import type { ChatMessage, Conversation } from './types'
import type { PageProps } from './appTypes'

const prompts = {
  en:[['Critical stock review','Which materials have critical stock risk and what should I review first?'],['Pending purchase reviews','Summarize pending purchase requests and the evidence required for review.'],['Supplier lead-time exposure','How do supplier lead times affect current replenishment needs?'],['Material demand comparison','Compare recent material demand with the previous equal-length period.']],
  vi:[['Rà soát tồn kho nghiêm trọng','Nguyên liệu nào có rủi ro tồn kho nghiêm trọng và cần kiểm tra trước?'],['Đề nghị mua chờ duyệt','Tóm tắt các đề nghị mua đang chờ duyệt và thông tin cần kiểm tra.'],['Thời gian cung ứng','Thời gian cung ứng của nhà cung cấp ảnh hưởng thế nào đến nhu cầu bổ sung?'],['So sánh nhu cầu nguyên liệu','So sánh nhu cầu nguyên liệu gần đây với kỳ trước cùng độ dài.']],
}
function InlineText({text}:{text:string}) {return <>{text.split(/(\*\*[^*]+\*\*)/g).map((part,index)=>part.startsWith('**')?<strong key={index}>{part.slice(2,-2)}</strong>:part)}</>}
function Answer({text}:{text:string}) {return <div className="answer-text">{text.split('\n').map((line,index)=>line.trim()?<p key={index} className={/^[-*] /.test(line)?'answer-bullet':/^#{1,4} /.test(line)?'answer-heading':''}><InlineText text={line.replace(/^#{1,4} /,'').replace(/^[-*] /,'')}/></p>:<div className="answer-gap" key={index}/>)}</div>}

export default function AIWorkspace({data,date,openInventory,notify}:PageProps) {
  const [messages,setMessages]=useState<ChatMessage[]>([]),[conversations,setConversations]=useState<Conversation[]>([])
  const [conversation,setConversation]=useState<string|undefined>(),[input,setInput]=useState(''),[language,setLanguage]=useState<'en'|'vi'>('en')
  const [busy,setBusy]=useState(false),[loading,setLoading]=useState(false),[history,setHistory]=useState(false),[error,setError]=useState(''),[sku,setSku]=useState<string|undefined>()
  const bottom=useRef<HTMLDivElement>(null),inputRef=useRef<HTMLTextAreaElement>(null)
  const last=[...messages].reverse().find(message=>message.role==='assistant')?.metadata
  useEffect(()=>{
    api.conversations().then(setConversations).catch(()=>{})
    const prompt=sessionStorage.getItem('procureflow_prompt')
    if(prompt){setInput(prompt);setSku(sessionStorage.getItem('procureflow_sku')??undefined);sessionStorage.removeItem('procureflow_prompt');sessionStorage.removeItem('procureflow_sku');inputRef.current?.focus()}
  },[])
  useEffect(()=>{bottom.current?.scrollIntoView({behavior:'smooth',block:'nearest'})},[messages,busy])
  async function send(text=input) {
    if(!text.trim()||busy)return
    const value=text.trim(),optimisticId=`user-${Date.now()}`
    setInput('');setError('');setBusy(true)
    setMessages(previous=>[...previous,{id:optimisticId,role:'user',content:value,created_at:new Date().toISOString()}])
    try {
      const response=await api.chat(value,conversation,date,sku)
      setConversation(response.conversation_id)
      setMessages(previous=>[...previous,{id:response.message_id,role:'assistant',content:response.answer,metadata:response,created_at:response.created_at}])
      api.conversations().then(setConversations).catch(()=>{})
    } catch(error) {setMessages(previous=>previous.filter(message=>message.id!==optimisticId));setError((error as Error).message);setInput(value)}
    finally {setBusy(false)}
  }
  async function selectConversation(value:Conversation) {
    setLoading(true);setHistory(false);setError('')
    try {setMessages(await api.messages(value.id));setConversation(value.id);setSku(undefined);setInput('')}
    catch(error) {notify((error as Error).message,'error')}
    finally {setLoading(false)}
  }
  function startNew(){setMessages([]);setConversation(undefined);setSku(undefined);setInput('');setError('');setHistory(false);inputRef.current?.focus()}
  return <>
    <PageHeader title="Operational Assistant" description="Read-only analysis of material stock, demand, suppliers, and purchasing records." eyebrow="OPERATIONAL REVIEW"/>
    <div className="ai-workspace">
      <section className="panel chat-panel">
        <div className="chat-topbar"><div><ClipboardList size={17}/><strong>{conversation?'Saved conversation':'New operational review'}</strong></div><div><button className="icon-button" onClick={()=>setHistory(!history)} aria-label="Conversation history"><History size={17}/></button><button className="new-chat-button" onClick={startNew}><Plus size={15}/>New conversation</button></div></div>
        {history&&<div className="conversation-history"><div><strong>Conversation history</strong><button className="icon-button" onClick={()=>setHistory(false)} aria-label="Close history"><X size={16}/></button></div>{conversations.length?conversations.map(item=><button key={item.id} onClick={()=>selectConversation(item)}><MessageSquare size={16}/><span><strong>{item.title}</strong><small>{displayDate(item.updated_at,{day:'numeric',month:'short'})}</small></span><ChevronRight size={14}/></button>):<p>No conversations saved yet.</p>}</div>}
        <div className="chat-scroll">{loading?<div className="chat-loading"><LoaderCircle size={20} className="spin"/>Opening conversation…</div>:!messages.length?<div className="chat-empty"><span className="eyebrow">START A REVIEW</span><h2>What would you like to examine?</h2><p>Choose an operational question or enter your own in English or Vietnamese. Answers reference the available workspace records.</p><div className="suggestion-grid">{prompts[language].map(([title,text])=><button key={title} onClick={()=>send(text)}><strong>{title}</strong><ArrowRight size={15}/></button>)}</div><div className="assistant-scope"><FileCheck2 size={16}/><p>Analysis only. Purchase quantities come from the policy engine; approval and stock changes remain manual workflow actions.</p></div></div>:<div className="chat-messages">
          {messages.map(message=><article key={`${message.role}-${message.id}`} className={`chat-message ${message.role==='user'?'user-message':'assistant-message'}`}><span className={message.role==='user'?'message-user-avatar':'message-ai-avatar'}>{message.role==='user'?initials(data.settings.operator_name):<ClipboardList size={16}/>}</span><div className="message-content"><div className="message-author">{message.role==='user'?'You':'Operational Assistant'}<time>{new Date(message.created_at).toLocaleTimeString('en-GB',{timeZone:'Asia/Ho_Chi_Minh',hour:'2-digit',minute:'2-digit'})}</time></div>{message.role==='assistant'?<><Answer text={message.content}/><p className="answer-source-note">Verify source records before making a purchasing decision.</p></>:<p className="user-message-text">{message.content}</p>}</div></article>)}
          {busy&&<article className="chat-message assistant-message"><span className="message-ai-avatar"><ClipboardList size={16}/></span><div className="message-content"><div className="message-author">Operational Assistant</div><div className="thinking-state"><LoaderCircle size={14} className="spin"/><p>Reviewing relevant inventory and purchasing records…</p></div></div></article>}<div ref={bottom}/>
        </div>}</div>
        <div className="chat-composer-area"><InlineError error={error}/>{last?.suggestions?.length&&!busy&&messages.length>0&&<div className="followup-suggestions">{last.suggestions.slice(0,3).map(item=><button key={item} onClick={()=>send(item)}>{item}<ArrowRight size={12}/></button>)}</div>}
          <form className="chat-composer" onSubmit={event=>{event.preventDefault();send()}}><textarea ref={inputRef} aria-label="Message the Operational Assistant" placeholder={language==='vi'?'Hỏi về tồn kho, nhu cầu hoặc đề nghị mua…':'Ask about stock, recorded demand, or purchase requests…'} value={input} rows={2} onChange={event=>setInput(event.target.value)} onKeyDown={event=>{if(event.key==='Enter'&&!event.shiftKey){event.preventDefault();send()}}}/><div className="composer-bottom"><span>{sku?`Material: ${sku}`:`Window ending ${displayDate(date,{day:'numeric',month:'short'})}`}</span><div><Select label="Question language" value={language} onChange={value=>setLanguage(value as 'en'|'vi')}><option value="en">English</option><option value="vi">Tiếng Việt</option></Select><button type="submit" className="send-button" disabled={!input.trim()||busy} aria-label="Send message">{busy?<LoaderCircle size={17} className="spin"/>:<ArrowUp size={18}/>}</button></div></div></form><div className="composer-disclaimer">Enter to send · Shift + Enter for a new line</div>
        </div>
      </section>
      <aside className="ai-context">
        <section className="panel context-panel"><h3>Review context</h3><dl className="context-records"><div><dt>Materials</dt><dd>{data.inventory.length}</dd></div><div><dt>Demand observations</dt><dd>{data.sales.length}</dd></div><div><dt>Pending requests</dt><dd>{data.proposals.filter(row=>row.status==='DRAFT').length}</dd></div><div><dt>Suppliers</dt><dd>{data.suppliers.length}</dd></div></dl><p className="context-asof">Demand window ends {displayDate(date)}. Current stock balances are used.</p></section>
        <details className="panel source-panel technical-details"><summary>Source references <span>{last?.sources?.length||0}</span></summary>{last?.sources?.length?last.sources.map((source,index)=><button key={index} className="source-card" disabled={!source.sku} onClick={()=>{const row=data.inventory.find(item=>item.sku===source.sku);if(row)openInventory(row)}}><span className="source-number">{index+1}</span><span><strong>{source.label}</strong><small>{source.detail}</small></span>{source.sku&&<ArrowUpRight size={13}/>}</button>):<p className="context-placeholder">References appear after an answer is generated.</p>}</details>
        <details className="panel technical-details"><summary>Analysis steps <span>{last?.tools?.length||0}</span></summary><div className="tool-trace">{last?.tools?.length?last.tools.map((tool,index)=><div key={`${tool.name}-${index}`}><Check size={13}/><div><strong>{tool.label}</strong><p>{tool.detail}</p></div></div>):<p className="context-placeholder">No analysis steps recorded yet.</p>}</div></details>
        <details className="panel technical-details"><summary>Execution details</summary><dl className="engine-details"><div><dt>Provider</dt><dd>{data.agent.provider}</dd></div><div><dt>Response mode</dt><dd>{last?.mode||data.agent.mode}</dd></div><div><dt>Model / engine</dt><dd>{last?.model||data.agent.model||'Workspace tools'}</dd></div></dl><p>{data.agent.message}</p><p>Conversations are stored locally. The assistant has no purchasing or approval tools.</p></details>
      </aside>
    </div>
  </>
}
