import type { InventoryRow, Page, Proposal, Workspace } from './types'
export interface PageProps {
  data: Workspace; date: string; navigate: (page: Page) => void; refresh: () => Promise<void>;
  notify: (message: string, kind?: 'success' | 'error') => void;
  openImport: (dataset?: string) => void; openInventory: (row: InventoryRow) => void; openRequest: (row: Proposal) => void;
  generate: () => Promise<void>; generating: boolean;
}
