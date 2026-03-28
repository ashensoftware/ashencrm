export interface Prospect {
  name: string;
  category: string;
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
