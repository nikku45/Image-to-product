export interface HealthResponse {
  status: string;
  environment: string;
  gemini_configured: boolean;
  serpapi_configured: boolean;
}

export interface ImageAnalysis {
  product_category: string;
  brand: string | null;
  model: string | null;
  color: string | null;
  visible_text: string[];
  identifying_attributes: string[];
  uncertainties: string[];
  search_queries: string[];
}

export interface ProductCandidate {
  asin: string;
  title: string;
  product_url: string;
  image_url: string | null;
  price_amount: number | null;
  currency: string | null;
  seller_count: number | null;
  seller_count_type: string | null;
  match_score: number;
  match_confidence: "high" | "medium" | "low";
  match_signals?: Record<string, unknown>;
  source: string;
  retrieved_at: string;
}

export interface ProductMatchResponse {
  search_id: string;
  status: "pending" | "processing" | "completed" | "failed";
  analysis: ImageAnalysis | null;
  candidates: ProductCandidate[];
  total_candidates: number;
  total_sellers: number;
  selected_asin?: string | null;
  error_code?: string | null;
  error_message?: string | null;
}

export interface ApiError {
  error: {
    code: string;
    message: string;
    details?: unknown;
  };
}
