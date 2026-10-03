export type Role = 'contributor' | 'agency' | 'admin';

export interface ContributorProfile {
  id: number;
  display_name: string;
  reputation_score: number;
}

export interface AgencyProfile {
  id: number;
  company_name: string;
}

export interface User {
  id: number;
  email: string;
  role: Role;
  status: 'active' | 'suspended';
  contributor_profile?: ContributorProfile;
  agency_profile?: AgencyProfile;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface Subcategory {
  id: number;
  parent_id: number | null;
  slug: string;
  name: string;
  base_price_paise: number;
  active: boolean;
  version: number;
  published_count: number;
}

export interface CategoryTree {
  id: number;
  slug: string;
  name: string;
  base_price_paise: number;
  active: boolean;
  version: number;
  published_count: number;
  subcategories: Subcategory[];
}

export type UploadStatus = 'uploaded' | 'processing' | 'analyzed' | 'published' | 'rejected' | 'flagged' | 'unpublished' | 'held_uncategorized';
export type DataType = 'image' | 'tabular';

export interface UploadFile {
  id: number;
  data_type: DataType;
  mime: string;
  size: number;
  width?: number;
  height?: number;
  phash?: string;
  exif_stripped: boolean;
  row_count?: number;
  column_schema?: any;
  content_hash?: string;
  signature_hash?: string;
}

export interface GemmaClassificationOutput {
  primary_category: string;
  subcategory?: string | null;
  secondary_categories: string[];
  confidence: number;
  tags: string[];
  reasoning: string;
  suggested_new_category?: string | null;
}

export interface AIAnalysis {
  id: number;
  upload_id: number;
  model_name: string;
  config_version: string;
  taxonomy_version: number;
  classification_output: GemmaClassificationOutput;
  quality: number;
  authenticity: number;
  uniqueness: number;
  metadata_accuracy: number;
  reputation: number;
  total_score: number;
  explanation: string;
  tips: string[];
  degraded: boolean;
  ai_min_price?: number;
  ai_max_price?: number;
  suggested_price?: number;
}

export interface ListingContributor {
  id: number;
  display_name: string;
  reputation_score: number;
}

export interface ListingCategory {
  id: number;
  slug: string;
  name: string;
  base_price_paise: number;
}

export interface ListingItem {
  id: number;
  upload_id: number;
  title: string;
  description: string;
  status: 'active' | 'inactive';
  data_type: DataType;
  price_paise: number;
  trust_score: number;
  category?: ListingCategory;
  subcategory?: ListingCategory;
  tags: string[];
  contributor?: ListingContributor;
  ai_training_allowed: boolean;
  size: number;
  published_at: string;
  created_at: string;
}

export interface ListingDetail {
  id: number;
  upload_id: number;
  title: string;
  description: string;
  status: 'active' | 'inactive';
  data_type: DataType;
  price_paise: number;
  ai_min_price?: number;
  ai_max_price?: number;
  category?: ListingCategory;
  subcategory?: ListingCategory;
  tags: string[];
  contributor?: ListingContributor;
  ai_training_allowed: boolean;
  ai_analysis?: AIAnalysis;
  file_metadata: {
    mime?: string;
    size?: number;
    width?: number;
    height?: number;
    row_count?: number;
    column_schema?: any;
    exif_stripped?: boolean;
  };
  published_at: string;
  created_at: string;
}

export interface Upload {
  id: number;
  contributor_id: number;
  title: string;
  description: string;
  status: UploadStatus;
  category_id?: number;
  subcategory_id?: number;
  category_source: string;
  category_confidence?: number;
  tags: string[];
  price_paise?: number;
  ai_min_price?: number;
  ai_max_price?: number;
  ai_training_allowed: boolean;
  consent_version: string;
  consent_at: string;
  created_at: string;
  file_info?: UploadFile;
}

export interface License {
  id: number;
  order_id: number;
  terms_version: string;
  type: string;
  created_at: string;
}

export interface Order {
  id: number;
  buyer_id: number;
  listing_id: number;
  amount_paise: number;
  status: 'created' | 'awaiting_payment' | 'paid' | 'failed' | 'cancelled' | 'refunded';
  created_at: string;
  listing?: ListingItem;
  license?: License;
}

export interface MockCheckoutInfo {
  order_id: number;
  listing_id: number;
  listing_title: string;
  contributor_name: string;
  amount_paise: number;
  currency: string;
  status: string;
  provider_ref: string;
  ai_training_allowed: boolean;
}

export interface ListingPagination {
  items: ListingItem[];
  total: number;
  page: number;
  limit: number;
  total_pages: number;
}

export interface Wallet {
  user_id: number;
  pending_balance_paise: number;
  available_balance_paise: number;
  updated_at: string;
}

export interface SaleItem {
  order_id: number;
  upload_id: number;
  dataset_title: string;
  data_type: DataType;
  total_amount_paise: number;
  contributor_share_paise: number;
  buyer_email: string;
  created_at: string;
}

export interface PayoutRequest {
  id: number;
  user_id: number;
  amount_paise: number;
  status: 'requested' | 'completed' | 'rejected';
  method?: string;
  destination?: string;
  created_at: string;
  processed_at?: string;
}

export interface ContributorEarningsSummary {
  wallet: Wallet;
  lifetime_earnings_paise: number;
  lifetime_withdrawn_paise: number;
  sales_count: number;
  recent_sales: SaleItem[];
  payout_requests: PayoutRequest[];
}

export interface ModerationItem {
  id: number;
  contributor_id: number;
  contributor_email: string;
  contributor_name: string;
  title: string;
  description: string;
  status: UploadStatus;
  category_id?: number;
  category_name?: string;
  subcategory_id?: number;
  subcategory_name?: string;
  category_source: string;
  category_confidence?: number;
  price_paise?: number;
  data_type: string;
  flags_count: number;
  open_flags: Array<{ id: number; reason: string; source: string; created_at: string }>;
  ai_total_score?: number;
  created_at: string;
}

export interface CategoryDistribution {
  category_id: number;
  category_name: string;
  category_slug: string;
  uploads_count: number;
  published_count: number;
  base_price_paise: number;
}

export interface PlatformAnalytics {
  gmv_paise: number;
  platform_revenue_paise: number;
  contributor_payouts_paise: number;
  total_contributors: number;
  total_agencies: number;
  total_uploads: number;
  total_active_listings: number;
  total_orders_paid: number;
  total_licenses_issued: number;
  category_distribution: CategoryDistribution[];
}

export interface AuditLogEntry {
  id: number;
  actor_id?: number;
  actor_email?: string;
  action: string;
  entity: string;
  entity_id: string;
  meta?: any;
  created_at: string;
}

export interface AuditLogPagination {
  items: AuditLogEntry[];
  total: number;
  page: number;
  limit: number;
  total_pages: number;
}




