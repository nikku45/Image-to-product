import {
  HealthResponse,
  ProductMatchResponse,
  ApiError,
} from "@/types/product";

const BASE_URL =
  process.env.NEXT_PUBLIC_BACKEND_URL?.replace(/\/+$/, "") ||
  "http://localhost:8000";

export class ApiClientError extends Error {
  code: string;
  status: number;
  details?: unknown;

  constructor(message: string, code = "UNKNOWN_ERROR", status = 500, details?: unknown) {
    super(message);
    this.name = "ApiClientError";
    this.code = code;
    this.status = status;
    this.details = details;
  }
}

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    let errorCode = `HTTP_${response.status}`;
    let errorMessage = `API request failed with status ${response.status}`;
    let errorDetails: unknown = undefined;

    try {
      const data: ApiError = await response.json();
      if (data.error) {
        errorCode = data.error.code || errorCode;
        errorMessage = data.error.message || errorMessage;
        errorDetails = data.error.details;
      }
    } catch {
      // Body was not JSON; use default error message
    }

    throw new ApiClientError(errorMessage, errorCode, response.status, errorDetails);
  }

  return response.json() as Promise<T>;
}

export const api = {
  /**
   * Health check endpoint
   */
  async getHealth(): Promise<HealthResponse> {
    const res = await fetch(`${BASE_URL}/api/health`, {
      method: "GET",
      headers: { Accept: "application/json" },
      cache: "no-store",
    });
    return handleResponse<HealthResponse>(res);
  },

  /**
   * Submit an image for analysis and Amazon.in candidate matching
   */
  async createProductMatch(file: File): Promise<ProductMatchResponse> {
    const formData = new FormData();
    formData.append("image", file);

    const res = await fetch(`${BASE_URL}/api/product-matches`, {
      method: "POST",
      body: formData,
    });
    return handleResponse<ProductMatchResponse>(res);
  },

  /**
   * Retrieve search result by search_id
   */
  async getProductMatch(searchId: string): Promise<ProductMatchResponse> {
    const res = await fetch(`${BASE_URL}/api/product-matches/${encodeURIComponent(searchId)}`, {
      method: "GET",
      headers: { Accept: "application/json" },
      cache: "no-store",
    });
    return handleResponse<ProductMatchResponse>(res);
  },

  /**
   * Confirm the matching ASIN for a search
   */
  async confirmCandidate(searchId: string, asin: string): Promise<{ success: boolean; confirmed_asin: string }> {
    const res = await fetch(
      `${BASE_URL}/api/product-matches/${encodeURIComponent(searchId)}/confirm`,
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Accept: "application/json",
        },
        body: JSON.stringify({ asin }),
      }
    );
    return handleResponse<{ success: boolean; confirmed_asin: string }>(res);
  },
};
