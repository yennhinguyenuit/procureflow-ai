export type Page = 'overview' | 'inventory' | 'requests' | 'suppliers' | 'ai' | 'analytics' | 'activity' | 'settings'
export type Risk = 'Critical Stock' | 'Low Stock' | 'Normal' | 'Data Quality Issue'
export interface InventoryRow {
  sku: string; product_name: string; supplier: string; on_hand: number; on_order: number; reserved_qty: number;
  available_stock: number; safety_stock: number; lead_time_days: number; pack_size: number; unit_cost_vnd: number;
  avg_daily_demand: number; inventory_position: number; reorder_point: number; target_stock: number;
  quantity: number; estimated_cost_vnd: number; risk: Risk; demand_change_pct: number | null;
  sales_days_observed: number; data_quality_issue?: string; units_last_window: number;
}
export interface Proposal {
  id: number; sku: string; product_name: string; supplier: string; quantity: number; estimated_cost_vnd: number;
  unit_cost_vnd: number; status: 'DRAFT' | 'APPROVED' | 'REJECTED'; reason: string;
  created_at: string; decided_at?: string; decided_by?: string; comment?: string;
  avg_daily_demand: number; inventory_position: number; reorder_point: number; target_stock: number;
}
export interface Supplier { name: string; lead_time_days: number | null; contact_email: string | null }
export interface Audit { id: number; proposal_id?: number; action: string; actor: string; comment?: string; before_json?: string; after_json?: string; created_at: string }
export interface Exception { id: number; sku?: string; exception_type: string; severity: string; message: string; status: string; created_at: string }
export interface Snapshot { id: number; snapshot_date: string; sku: string; on_hand: number; on_order: number; reserved_qty: number; source: string; created_at: string }
export interface AgentStatus { provider: string; mode: 'local_model' | 'local_tools'; available: boolean; model: string; endpoint?: string; message: string }
export interface Settings { operator_name: string; workspace_name: string }
export interface Workspace {
  as_of: string; inventory: InventoryRow[]; proposals: Proposal[]; suppliers: Supplier[]; audit: Audit[];
  approvals: Record<string, unknown>[]; exceptions: Exception[]; sales: { sale_date: string; sku: string; units: number }[];
  snapshots: Snapshot[]; settings: Settings; agent: AgentStatus;
}
export interface Tool { name: string; label: string; detail: string }
export interface Source { sku?: string; label: string; detail: string }
export interface ChatResponse { conversation_id: string; message_id: number | string; answer: string; mode: string; model: string; tools: Tool[]; sources: Source[]; suggestions: string[]; created_at: string }
export interface Conversation { id: string; title: string; created_at: string; updated_at: string }
export interface ChatMessage { id: string | number; role: string; content: string; metadata?: Partial<ChatResponse> | null; created_at: string }
