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

export type ModalType = "alert" | "prompt" | "category" | "edit" | "detail" | "scanner" | null;
