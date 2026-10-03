export interface ConsentDocument {
  id: number;
  purpose_code: string;
  version: string;
  title: string;
  body_markdown: string;
  sha256: string;
  effective_from: string;
  active: boolean;
  created_at: string;
}

export interface ConsentRecord {
  id: number;
  user_id?: number | null;
  upload_id?: number | null;
  order_id?: number | null;
  purpose_code: string;
  document_id: number;
  document_sha256: string;
  action: 'granted' | 'withdrawn';
  ip?: string | null;
  user_agent?: string | null;
  created_at: string;
  document_title?: string | null;
  document_version?: string | null;
}

export interface TakedownRequest {
  id: number;
  upload_id: number;
  claimant_name: string;
  claimant_email: string;
  reason: string;
  details: string;
  status: 'PENDING' | 'INVESTIGATING' | 'ACTIONED' | 'DISMISSED';
  admin_notes?: string | null;
  created_at: string;
}

export interface DeletionRequest {
  id: number;
  user_id: number;
  status: 'PENDING' | 'APPROVED' | 'REJECTED';
  reason?: string | null;
  admin_notes?: string | null;
  created_at: string;
  processed_at?: string | null;
}

export interface DataExport {
  user_profile: Record<string, any>;
  uploads: Array<Record<string, any>>;
  orders_and_licenses: Array<Record<string, any>>;
  consent_history: ConsentRecord[];
  exported_at: string;
}

export interface ConsentReport {
  total_active_documents: number;
  total_records: number;
  grants_by_purpose: Record<string, number>;
  withdrawals_by_purpose: Record<string, number>;
  uploads_with_ai_training: number;
  uploads_awaiting_moderation: number;
  pending_takedowns: number;
  pending_deletions: number;
}
