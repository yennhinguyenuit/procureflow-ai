import type { Workspace, Settings, ChatResponse, Conversation, ChatMessage } from './types'

export async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`/api${path}`, { ...options, headers: { ...(options?.body instanceof FormData ? {} : { 'Content-Type': 'application/json' }), ...options?.headers } })
  if (!response.ok) {
    let message = `Request failed (${response.status}). Please try again.`
    try { const error = await response.json(); message = typeof error.detail === 'string' ? error.detail : typeof error.message === 'string' ? error.message : JSON.stringify(error.detail ?? error) } catch { /* Preserve a useful HTTP error. */ }
    throw new Error(message)
  }
  return response.json() as Promise<T>
}
export const api = {
  workspace: (date?: string) => request<Workspace>(`/workspace${date ? `?as_of=${date}` : ''}`),
  generate: (as_of: string, actor: string) => request<{created: number; message: string}>('/requests/generate', {method: 'POST', body: JSON.stringify({as_of, actor})}),
  decide: (id: number, decision: string, actor: string, comment: string) => request<{message: string}>(`/requests/${id}/decision`, {method: 'POST', body: JSON.stringify({decision, actor, comment})}),
  inventory: (sku: string, values: {on_hand: number; on_order: number; reserved_qty: number; actor: string; as_of: string}) => request<{message: string}>(`/inventory/${encodeURIComponent(sku)}`, {method: 'PATCH', body: JSON.stringify(values)}),
  import: (dataset: string, as_of: string, file: File, actor: string) => { const body = new FormData(); body.append('file', file); body.append('actor', actor); return request<{imported: number; message: string}>(`/import/${dataset}?as_of=${as_of}`, {method: 'POST', body}) },
  settings: (settings: Settings) => request<Settings>('/settings', {method: 'PATCH', body: JSON.stringify(settings)}),
  conversations: () => request<Conversation[]>('/agent/conversations'),
  messages: (id: string) => request<ChatMessage[]>(`/agent/conversations/${encodeURIComponent(id)}/messages`),
  chat: (message: string, conversation_id?: string, as_of?: string, sku?: string) => request<ChatResponse>('/agent/chat', {method: 'POST', body: JSON.stringify({message, conversation_id, as_of, sku})}),
}
export const reportUrl = (date: string, dataset = 'workbook.xlsx') => `/api/reports/${dataset}?as_of=${date}`
