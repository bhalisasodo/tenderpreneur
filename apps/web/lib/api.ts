export interface UserDTO {
  id: string;
  email: string;
  name: string;
  role: string;
  organisation_id: string;
  organisation?: OrganisationDTO;
}

export interface OrganisationDTO {
  id: string;
  type: "contractor" | "supplier";
  legal_name: string;
  trading_name?: string;
  email: string;
  phone?: string;
  region: string;
}

export interface AuthSession {
  access_token: string;
  token_type: string;
  user: UserDTO;
  organisation: OrganisationDTO;
  supplier_approval_status?: SupplierProfileStatus;
}

export type SupplierProfileStatus = "pending" | "approved" | "rejected" | "suspended";

export interface SupplierProfileDTO {
  id: string;
  organisation_id: string;
  categories: string[];
  service_regions: string[];
  compliance_flags: Record<string, any>;
  preferred_contact_method: string;
  status: SupplierProfileStatus;
  active: boolean;
  created_at?: string;
  updated_at?: string;
}

export interface SupplierReviewDTO {
  id: string;
  organisation_id: string;
  legal_name: string;
  trading_name?: string;
  email: string;
  phone?: string;
  region: string;
  categories: string[];
  service_regions: string[];
  approval_status: SupplierProfileStatus;
  status: SupplierProfileStatus;
  active: boolean;
}

export interface LineItemDTO {
  id: string;
  boq_id: string;
  source_row_reference?: string;
  description: string;
  unit: string;
  quantity: number;
  category: string;
  benchmark_min_minor?: number;
  benchmark_max_minor?: number;
  benchmark_source?: string;
  final_price_minor?: number;
  pricing_status: string;
  parsing_confidence?: number;
  review_status?: "accepted" | "needs_review" | "excluded";
  exclusion_reason?: string;
}

export interface BoQSummaryDTO {
  id: string;
  contractor_organisation_id: string;
  title: string;
  tender_reference?: string;
  tender_deadline?: string;
  region: string;
  status: string;
  line_item_count: number;
  total_priced_minor: number;
  created_at: string;
}

export interface BoQDetailDTO extends BoQSummaryDTO {
  source_document_id?: string;
  line_items: LineItemDTO[];
}

export interface QuoteDTO {
  id: string;
  quote_request_id: string;
  supplier_organisation_id: string;
  supplier_name?: string;
  unit_price_minor: number;
  total_price_minor: number;
  currency: string;
  lead_time_days?: number;
  notes?: string;
  is_selected: boolean;
  submitted_at: string;
}

export interface QuoteRequestDTO {
  id: string;
  line_item_id: string;
  line_item_description?: string;
  line_item_quantity?: number;
  line_item_unit?: string;
  line_item_category?: string;
  boq_id?: string;
  boq_title?: string;
  boq_region?: string;
  response_deadline: string;
  status: string;
  is_expired: boolean;
  quotes: QuoteDTO[];
  supplier_count: number;
}

export interface LineItemComparisonDTO {
  line_item_id: string;
  description: string;
  unit: string;
  quantity: number;
  category: string;
  benchmark_min_minor?: number;
  benchmark_max_minor?: number;
  final_price_minor?: number;
  pricing_status: string;
  quote_request_id?: string;
  response_deadline?: string;
  is_deadline_passed: boolean;
  quotes: QuoteDTO[];
  lowest_quote?: QuoteDTO;
  fastest_quote?: QuoteDTO;
  selected_quote?: QuoteDTO;
}

export interface BoQComparisonDTO {
  boq_id: string;
  title: string;
  region: string;
  tender_deadline?: string;
  line_items: LineItemComparisonDTO[];
  total_estimated_minor: number;
  total_priced_minor: number;
}

export interface AuditEventDTO {
  id: string;
  organisation_id: string;
  actor_name?: string;
  entity_type: string;
  entity_id: string;
  action: string;
  before_json?: Record<string, any>;
  after_json?: Record<string, any>;
  metadata_json?: Record<string, any>;
  created_at: string;
}

export interface CorruptedItemDTO {
  id: string;
  line_item_id?: string;
  description: string;
  reason: string;
  corruption_ratio: number;
}

export interface BroadcastSafetyValidationDTO {
  is_safe: boolean;
  safe?: boolean;
  total_items: number;
  valid_items_count: number;
  corrupted_items_count: number;
  corrupted_items: CorruptedItemDTO[];
  message: string;
}

class ApiClient {
  private customApiBase: string | null = null;

  public getApiBase(): string {
    if (typeof window !== "undefined") {
      const stored = localStorage.getItem("tp_custom_api_url");
      if (stored) return stored;
    }
    return process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";
  }

  public setApiBase(url: string | null): void {
    if (typeof window !== "undefined") {
      if (url) {
        localStorage.setItem("tp_custom_api_url", url);
      } else {
        localStorage.removeItem("tp_custom_api_url");
      }
    }
    this.customApiBase = url;
  }

  private getToken(): string | null {
    if (typeof window === "undefined") return null;
    return localStorage.getItem("tp_token");
  }

  private async ensureToken(): Promise<string | null> {
    if (typeof window === "undefined") return null;
    let token = localStorage.getItem("tp_token");
    if (!token) {
      if (typeof window !== "undefined" && window.location.search) {
        try {
          const urlParams = new URLSearchParams(window.location.search);
          const urlToken = urlParams.get("access_token");
          if (urlToken) {
            localStorage.setItem("tp_token", urlToken);
            return urlToken;
          }
        } catch {}
      }
    }
    return token;
  }

  private async request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    const apiBase = this.getApiBase();
    let token = await this.ensureToken();

    const headers: Record<string, string> = {
      ...(options.headers as Record<string, string>),
    };

    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }

    if (!(options.body instanceof FormData) && !headers["Content-Type"]) {
      headers["Content-Type"] = "application/json";
    }

    let response: Response;
    try {
      // Use AbortController to quickly timeout if server is not reachable
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 4000);

      response = await fetch(`${apiBase}${endpoint}`, {
        ...options,
        headers,
        signal: controller.signal,
      });
      clearTimeout(timeoutId);
    } catch {
      throw new Error(`Unable to reach the BoQPro API at ${apiBase}. Check your connection and try again.`);
    }

    if (response.status === 401 && typeof window !== "undefined") {
      localStorage.removeItem("tp_token");
      localStorage.removeItem("tp_session");
      window.dispatchEvent(new Event("boqpro:session-expired"));
    }

    if (!response.ok) {
      let errorData = { code: "ERROR", message: "Request failed" };
      try {
        const json = await response.json();
        if (json.detail) {
          errorData = typeof json.detail === "object" ? json.detail : { code: "ERROR", message: json.detail };
        } else if (json.error) {
          errorData = json.error;
        }
      } catch {
        errorData = { code: `HTTP_${response.status}`, message: response.statusText };
      }
      throw new Error(errorData.message || "An error occurred");
    }

    if (response.status === 204) {
      return {} as T;
    }

    return response.json();
  }

  // Auth
  async login(email: string, password: string): Promise<AuthSession> {
    const res = await this.request<AuthSession>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });
    if (typeof window !== "undefined") {
      localStorage.setItem("tp_token", res.access_token);
      localStorage.setItem("tp_session", JSON.stringify(res));
    }
    return res;
  }

  async register(payload: {
    organisation_type: "contractor" | "supplier";
    legal_name: string;
    trading_name?: string;
    email: string;
    phone?: string;
    region: string;
    name: string;
    password: string;
    supplier_categories?: string[];
    supplier_service_regions?: string[];
    preferred_contact_method?: "email" | "whatsapp" | "sms";
  }): Promise<AuthSession> {
    const res = await this.request<AuthSession>("/auth/register", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    if (typeof window !== "undefined") {
      localStorage.setItem("tp_token", res.access_token);
      localStorage.setItem("tp_session", JSON.stringify(res));
    }
    return res;
  }

  async getSupplierProfile(): Promise<SupplierProfileDTO> {
    return this.request<SupplierProfileDTO>("/suppliers/profile");
  }

  async updateSupplierProfile(payload: Partial<SupplierProfileDTO>): Promise<SupplierProfileDTO> {
    return this.request<SupplierProfileDTO>("/suppliers/profile", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  }

  async listSupplierReviewQueue(): Promise<SupplierReviewDTO[]> {
    return this.request<SupplierReviewDTO[]>("/suppliers/review");
  }

  async approveSupplier(organisationId: string, reason: string): Promise<SupplierReviewDTO> {
    return this.request<SupplierReviewDTO>(`/suppliers/${organisationId}/approve`, {
      method: "POST",
      body: JSON.stringify({ reason }),
    });
  }

  async suspendSupplier(organisationId: string, reason: string): Promise<SupplierReviewDTO> {
    return this.request<SupplierReviewDTO>(`/suppliers/${organisationId}/suspend`, {
      method: "POST",
      body: JSON.stringify({ reason }),
    });
  }

  async getMe(): Promise<AuthSession> {
    const session = await this.request<AuthSession>("/auth/me");
    if (typeof window !== "undefined") {
      localStorage.setItem("tp_token", session.access_token);
      localStorage.setItem("tp_session", JSON.stringify(session));
    }
    return session;
  }

  logout(): void {
    if (typeof window !== "undefined") {
      localStorage.removeItem("tp_token");
      localStorage.removeItem("tp_session");
      window.dispatchEvent(new Event("boqpro:session-changed"));
    }
  }

  // BoQs
  async listBoQs(): Promise<BoQSummaryDTO[]> {
    return this.request<BoQSummaryDTO[]>("/boqs");
  }

  async getBoQ(id: string): Promise<BoQDetailDTO> {
    return this.request<BoQDetailDTO>(`/boqs/${id}`);
  }

  async createBoQ(data: { title: string; tender_reference?: string; region: string }): Promise<BoQDetailDTO> {
    return this.request<BoQDetailDTO>("/boqs", {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  async deleteBoQ(id: string): Promise<void> {
    await this.request(`/boqs/${id}`, { method: "DELETE" });
  }

  async uploadBoQDocument(boqId: string, file: File): Promise<any> {
    const formData = new FormData();
    formData.append("file", file);
    return this.request(`/boqs/${boqId}/documents`, {
      method: "POST",
      body: formData,
    });
  }

  async parseBoQ(boqId: string, pastedText?: string): Promise<BoQDetailDTO> {
    return this.request<BoQDetailDTO>(`/boqs/${boqId}/parse`, {
      method: "POST",
      body: JSON.stringify({ pasted_text: pastedText }),
    });
  }

  async addLineItem(boqId: string, item: any): Promise<LineItemDTO> {
    return this.request<LineItemDTO>(`/boqs/${boqId}/line-items`, {
      method: "POST",
      body: JSON.stringify(item),
    });
  }

  async updateLineItem(boqId: string, itemId: string, item: Partial<LineItemDTO>): Promise<LineItemDTO> {
    return this.request<LineItemDTO>(`/boqs/${boqId}/line-items/${itemId}`, {
      method: "PATCH",
      body: JSON.stringify(item),
    });
  }

  async deleteLineItem(boqId: string, itemId: string): Promise<void> {
    await this.request(`/boqs/${boqId}/line-items/${itemId}`, { method: "DELETE" });
  }

  async bulkDeleteLineItems(boqId: string, lineItemIds: string[]): Promise<{ deleted_count: number }> {
    return this.request<{ deleted_count: number }>(`/boqs/${boqId}/line-items/bulk-delete`, {
      method: "POST",
      body: JSON.stringify({ line_item_ids: lineItemIds }),
    });
  }

  async restoreLineItem(boqId: string, itemId: string): Promise<LineItemDTO> {
    return this.request<LineItemDTO>(`/boqs/${boqId}/line-items/${itemId}/restore`, {
      method: "POST",
      body: JSON.stringify({}),
    });
  }

  async getParserFeedbackSummary(): Promise<any> {
    return this.request("/boqs/parser/feedback-summary");
  }

  // Sourcing & Quotes
  async createQuoteRequest(lineItemId: string, responseDeadline: string): Promise<QuoteRequestDTO> {
    return this.request<QuoteRequestDTO>("/quote-requests", {
      method: "POST",
      body: JSON.stringify({ line_item_id: lineItemId, response_deadline: responseDeadline }),
    });
  }

  async broadcastQuoteRequest(requestId: string): Promise<QuoteRequestDTO> {
    return this.request<QuoteRequestDTO>(`/quote-requests/${requestId}/broadcast`, {
      method: "POST",
      body: JSON.stringify({}),
    });
  }

  async validateBroadcastSafety(boqId: string, lineItemIds: string[]): Promise<BroadcastSafetyValidationDTO> {
    return this.request<BroadcastSafetyValidationDTO>(`/boqs/${boqId}/validate-broadcast`, {
      method: "POST",
      body: JSON.stringify({ line_item_ids: lineItemIds }),
    });
  }

  async getQuoteComparison(boqId: string): Promise<BoQComparisonDTO> {
    return this.request<BoQComparisonDTO>(`/boqs/${boqId}/quote-comparison`);
  }

  async selectQuote(requestId: string, quoteId: string): Promise<LineItemComparisonDTO> {
    return this.request<LineItemComparisonDTO>(`/quote-requests/${requestId}/select`, {
      method: "POST",
      body: JSON.stringify({ quote_id: quoteId }),
    });
  }

  async autoSelectBestQuotes(boqId: string): Promise<{ selected_count: number; total_priced_minor: number; message: string }> {
    return this.request<{ selected_count: number; total_priced_minor: number; message: string }>(
        `/boqs/${boqId}/auto-select-best-quotes`,
        { method: "POST", body: JSON.stringify({}) }
      );
  }

  async overridePrice(boqId: string, itemId: string, priceMinor: number, reason: string): Promise<LineItemComparisonDTO> {
    return this.request<LineItemComparisonDTO>(`/boqs/${boqId}/line-items/${itemId}/price-override`, {
      method: "POST",
      body: JSON.stringify({ price_minor: priceMinor, reason, currency: "ZAR" }),
    });
  }

  // Supplier Portal
  async getSupplierQuoteRequests(): Promise<QuoteRequestDTO[]> {
    return this.request<QuoteRequestDTO[]>("/suppliers/quote-requests");
  }

  async getSupplierQuoteRequest(requestId: string): Promise<QuoteRequestDTO> {
    return this.request<QuoteRequestDTO>(`/suppliers/quote-requests/${requestId}`);
  }

  async submitSupplierQuote(
    requestId: string,
    unitPriceMinor: number,
    leadTimeDays?: number,
    notes?: string
  ): Promise<QuoteDTO> {
    return this.request<QuoteDTO>(`/quote-requests/${requestId}/quotes`, {
      method: "POST",
      body: JSON.stringify({
        unit_price_minor: unitPriceMinor,
        lead_time_days: leadTimeDays,
        notes,
        currency: "ZAR",
      }),
    });
  }

  // Exports & Audit
  async getAuditTrail(boqId: string): Promise<AuditEventDTO[]> {
    return this.request<AuditEventDTO[]>(`/boqs/${boqId}/audit`);
  }

  async createExport(boqId: string, format: "xlsx" | "pdf"): Promise<{ download_url: string; filename: string }> {
    return this.request<{ download_url: string; filename: string }>(`/boqs/${boqId}/exports`, {
      method: "POST",
      body: JSON.stringify({ format }),
    });
  }

}

export const api = new ApiClient();
