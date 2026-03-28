export interface Prospect {
  name: string;
  category: string;
  /** Presente en respuestas de API (lista de prospectos) */
  id?: number;
  address?: string;
  city?: string;
  phone?: string;
  website?: string;
  rating?: number;
  reviews_count?: number;
  maps_url?: string;
  latitude?: number;
  longitude?: number;
  instagram_url?: string;
  instagram_handle?: string;
  ig_followers?: number;
  ig_bio?: string;
  ig_email?: string;
  ig_phone?: string;
  ig_website?: string;
  demo_url?: string;
  screenshot_path?: string;
  prompt_used?: string;
  lovable_account_used?: string;
  whatsapp_message?: string;
  status?: string;
  scraped_at?: string;
  is_contacted?: boolean;
  notes?: string;
  lead_score?: number;
  /** Solo mapa de clientes: id de ficha cliente */
  client_id?: number;
}

export interface ProspectFilters {
  status?: string;
  category?: string;
  city?: string;
  contacted?: string;
  has_instagram?: string;
  name?: string;
}

export interface CatalogItem {
  name: string;
  label: string;
  icon?: string;
}

export interface WhatsappTemplate {
  id: string;
  name: string;
  template: string;
}

export interface ClientPreferences {
  default_currency: string;
  quote_footer_note: string;
}

export interface AppSettings {
  default_city: string;
  default_scrape_limit: number;
  map_center_lat: number;
  map_center_lng: number;
  map_zoom: number;
  ig_min_delay: number;
  ig_max_delay: number;
  max_results_per_category: number;
  scraper_headless: boolean;
  whatsapp_min_delay: number;
  whatsapp_max_delay: number;
  whatsapp_max_daily: number;
  whatsapp_phone: string;
  lovable_timeout: number;
  lovable_headless: boolean;
  whatsapp_templates: WhatsappTemplate[];
  client_preferences?: ClientPreferences;
}

export interface Hexagon {
  boundary: number[][];
  count: number;
  processed_count: number;
  status: string;
}

export interface StatusInfo {
  label: string;
  class: string;
}

export type ModalType = "alert" | "prompt" | "category" | "edit" | "detail" | "add" | "scanner" | null;

export interface ClientMeeting {
  id: number;
  client_id: number;
  title: string;
  scheduled_at: string;
  duration_min: number;
  notes: string;
  status: string;
}

export interface Client {
  id: number;
  prospect_id: number | null;
  display_name: string;
  category: string;
  contact_email: string;
  phone: string;
  notes: string;
  stage: string;
  quote_amount: number | null;
  quote_currency: string;
  quote_pdf_path: string;
  estimated_delivery_at: string;
  quoted_at: string;
  contract_required: number;
  contract_skipped: number;
  contract_signed_at: string;
  contract_pdf_path: string;
  payment_status: string;
  github_repo_url: string;
  production_domain: string;
  drive_folder_url: string;
  staging_url: string;
  maps_url: string;
  latitude?: number;
  longitude?: number;
  created_at: string;
  updated_at: string;
  meetings?: ClientMeeting[];
}

export interface ClientMapMarker {
  id: number;
  display_name: string;
  category: string;
  stage: string;
  latitude: number;
  longitude: number;
  maps_url: string;
}

/** Respuesta de POST /clients/parse-maps-url */
export interface ParsedMapsUrl {
  latitude: number;
  longitude: number;
  resolved_url: string;
  suggested_display_name: string;
}
