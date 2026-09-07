import { mockStore } from "./mock-store";

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
  private fallbackToMock = false;
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
    this.fallbackToMock = false;
  }

  public isMockMode(): boolean {
    if (this.fallbackToMock) return true;
    if (typeof window !== "undefined") {
      const explicit = localStorage.getItem("tp_force_mock");
      if (explicit === "true") return true;
      if (explicit === "false") return false;

      // On GitHub Pages or static host without an explicit HTTPS/remote API URL, default to mock mode
      const isGitHubPages = window.location.hostname.includes("github.io");
      const apiBase = this.getApiBase();
      if (isGitHubPages && apiBase.includes("localhost")) {
        return true;
      }
    }
    return false;
  }

  public setMockMode(enabled: boolean): void {
    if (typeof window !== "undefined") {
      localStorage.setItem("tp_force_mock", enabled ? "true" : "false");
    }
    this.fallbackToMock = enabled;
  }

  public resetDemoData(): void {
    mockStore.resetToDefaults();
  }

  private getToken(): string | null {
    if (typeof window === "undefined") return null;
    return localStorage.getItem("tp_token");
  }

  private async ensureToken(): Promise<string | null> {
    if (typeof window === "undefined") return null;
    let token = localStorage.getItem("tp_token");
    if (!token) {
      const demoEmails = [
        "estimator@amandlacivils.co.za",
        "estimator@amandla.co.za",
      ];
      for (const email of demoEmails) {
        try {
          const loginRes = await fetch(`${this.getApiBase()}/auth/login`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ email }),
          });
          if (loginRes.ok) {
            const authData = await loginRes.json();
            token = authData.access_token;
            if (token) {
              localStorage.setItem("tp_token", token);
              localStorage.setItem("tp_session", JSON.stringify(authData));
              break;
            }
          }
        } catch {}
      }
    }
    return token;
  }

  private async request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    if (this.isMockMode()) {
      throw new Error("MOCK_MODE");
    }

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
    } catch (networkErr: any) {
      console.warn(
        `[Tenderpreneur API] Unable to reach backend at ${apiBase}. Switching to in-browser demo engine:`,
        networkErr.message
      );
      this.fallbackToMock = true;
      throw new Error("MOCK_FALLBACK");
    }

    if (response.status === 401 && typeof window !== "undefined") {
      localStorage.removeItem("tp_token");
      token = await this.ensureToken();
      if (token) {
        headers["Authorization"] = `Bearer ${token}`;
        try {
          response = await fetch(`${apiBase}${endpoint}`, {
            ...options,
            headers,
          });
        } catch (networkErr: any) {
          this.fallbackToMock = true;
          throw new Error("MOCK_FALLBACK");
        }
      }
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
  async login(email: string): Promise<AuthSession> {
    if (this.isMockMode()) return mockStore.login(email);
    try {
      const res = await this.request<AuthSession>("/auth/login", {
        method: "POST",
        body: JSON.stringify({ email }),
      });
      if (typeof window !== "undefined") {
        localStorage.setItem("tp_token", res.access_token);
        localStorage.setItem("tp_session", JSON.stringify(res));
      }
      return res;
    } catch {
      return mockStore.login(email);
    }
  }

  async getMe(): Promise<AuthSession> {
    if (this.isMockMode()) return mockStore.getMe();
    try {
      return await this.request<AuthSession>("/auth/me");
    } catch {
      return mockStore.getMe();
    }
  }

  async getDemoTenants(): Promise<UserDTO[]> {
    if (this.isMockMode()) return mockStore.getDemoTenants();
    try {
      return await this.request<UserDTO[]>("/auth/demo-tenants");
    } catch {
      return mockStore.getDemoTenants();
    }
  }

  // BoQs
  async listBoQs(): Promise<BoQSummaryDTO[]> {
    if (this.isMockMode()) return mockStore.listBoQs();
    try {
      return await this.request<BoQSummaryDTO[]>("/boqs");
    } catch {
      return mockStore.listBoQs();
    }
  }

  async getBoQ(id: string): Promise<BoQDetailDTO> {
    if (this.isMockMode()) return mockStore.getBoQ(id);
    try {
      return await this.request<BoQDetailDTO>(`/boqs/${id}`);
    } catch {
      return mockStore.getBoQ(id);
    }
  }

  async createBoQ(data: { title: string; tender_reference?: string; region: string }): Promise<BoQDetailDTO> {
    if (this.isMockMode()) return mockStore.createBoQ(data);
    try {
      return await this.request<BoQDetailDTO>("/boqs", {
        method: "POST",
        body: JSON.stringify(data),
      });
    } catch {
      return mockStore.createBoQ(data);
    }
  }

  async deleteBoQ(id: string): Promise<void> {
    if (this.isMockMode()) return mockStore.deleteBoQ(id);
    try {
      await this.request(`/boqs/${id}`, { method: "DELETE" });
    } catch {
      await mockStore.deleteBoQ(id);
    }
  }

  async uploadBoQDocument(boqId: string, file: File): Promise<any> {
    if (this.isMockMode()) return mockStore.uploadBoQDocument(boqId, file);
    try {
      const formData = new FormData();
      formData.append("file", file);
      return await this.request(`/boqs/${boqId}/documents`, {
        method: "POST",
        body: formData,
      });
    } catch {
      return mockStore.uploadBoQDocument(boqId, file);
    }
  }

  async parseBoQ(boqId: string, pastedText?: string): Promise<BoQDetailDTO> {
    if (this.isMockMode()) return mockStore.parseBoQ(boqId, pastedText);
    try {
      return await this.request<BoQDetailDTO>(`/boqs/${boqId}/parse`, {
        method: "POST",
        body: JSON.stringify({ pasted_text: pastedText }),
      });
    } catch {
      return mockStore.parseBoQ(boqId, pastedText);
    }
  }

  async addLineItem(boqId: string, item: any): Promise<LineItemDTO> {
    if (this.isMockMode()) return mockStore.addLineItem(boqId, item);
    try {
      return await this.request<LineItemDTO>(`/boqs/${boqId}/line-items`, {
        method: "POST",
        body: JSON.stringify(item),
      });
    } catch {
      return mockStore.addLineItem(boqId, item);
    }
  }

  async updateLineItem(boqId: string, itemId: string, item: Partial<LineItemDTO>): Promise<LineItemDTO> {
    if (this.isMockMode()) return mockStore.updateLineItem(boqId, itemId, item);
    try {
      return await this.request<LineItemDTO>(`/boqs/${boqId}/line-items/${itemId}`, {
        method: "PATCH",
        body: JSON.stringify(item),
      });
    } catch {
      return mockStore.updateLineItem(boqId, itemId, item);
    }
  }

  async deleteLineItem(boqId: string, itemId: string): Promise<void> {
    if (this.isMockMode()) return mockStore.deleteLineItem(boqId, itemId);
    try {
      await this.request(`/boqs/${boqId}/line-items/${itemId}`, { method: "DELETE" });
    } catch {
      await mockStore.deleteLineItem(boqId, itemId);
    }
  }

  async bulkDeleteLineItems(boqId: string, lineItemIds: string[]): Promise<{ deleted_count: number }> {
    if (this.isMockMode()) return mockStore.bulkDeleteLineItems(boqId, lineItemIds);
    try {
      return await this.request<{ deleted_count: number }>(`/boqs/${boqId}/line-items/bulk-delete`, {
        method: "POST",
        body: JSON.stringify({ line_item_ids: lineItemIds }),
      });
    } catch {
      return mockStore.bulkDeleteLineItems(boqId, lineItemIds);
    }
  }

  async restoreLineItem(boqId: string, itemId: string): Promise<LineItemDTO> {
    if (this.isMockMode()) return mockStore.restoreLineItem(boqId, itemId);
    try {
      return await this.request<LineItemDTO>(`/boqs/${boqId}/line-items/${itemId}/restore`, {
        method: "POST",
        body: JSON.stringify({}),
      });
    } catch {
      return mockStore.restoreLineItem(boqId, itemId);
    }
  }

  async getParserFeedbackSummary(): Promise<any> {
    if (this.isMockMode()) return mockStore.getParserFeedbackSummary();
    try {
      return await this.request("/boqs/parser/feedback-summary");
    } catch {
      return mockStore.getParserFeedbackSummary();
    }
  }

  // Sourcing & Quotes
  async createQuoteRequest(lineItemId: string, responseDeadline: string): Promise<QuoteRequestDTO> {
    if (this.isMockMode()) return mockStore.createQuoteRequest(lineItemId, responseDeadline);
    try {
      return await this.request<QuoteRequestDTO>("/quote-requests", {
        method: "POST",
        body: JSON.stringify({ line_item_id: lineItemId, response_deadline: responseDeadline }),
      });
    } catch {
      return mockStore.createQuoteRequest(lineItemId, responseDeadline);
    }
  }

  async broadcastQuoteRequest(requestId: string): Promise<QuoteRequestDTO> {
    if (this.isMockMode()) return mockStore.broadcastQuoteRequest(requestId);
    try {
      return await this.request<QuoteRequestDTO>(`/quote-requests/${requestId}/broadcast`, {
        method: "POST",
        body: JSON.stringify({}),
      });
    } catch {
      return mockStore.broadcastQuoteRequest(requestId);
    }
  }

  async validateBroadcastSafety(boqId: string, lineItemIds: string[]): Promise<BroadcastSafetyValidationDTO> {
    if (this.isMockMode()) return mockStore.validateBroadcastSafety(boqId, lineItemIds);
    try {
      return await this.request<BroadcastSafetyValidationDTO>(`/boqs/${boqId}/validate-broadcast`, {
        method: "POST",
        body: JSON.stringify({ line_item_ids: lineItemIds }),
      });
    } catch {
      return mockStore.validateBroadcastSafety(boqId, lineItemIds);
    }
  }

  async getQuoteComparison(boqId: string): Promise<BoQComparisonDTO> {
    if (this.isMockMode()) return mockStore.getQuoteComparison(boqId);
    try {
      return await this.request<BoQComparisonDTO>(`/boqs/${boqId}/quote-comparison`);
    } catch {
      return mockStore.getQuoteComparison(boqId);
    }
  }

  async selectQuote(requestId: string, quoteId: string): Promise<LineItemComparisonDTO> {
    if (this.isMockMode()) return mockStore.selectQuote(requestId, quoteId);
    try {
      return await this.request<LineItemComparisonDTO>(`/quote-requests/${requestId}/select`, {
        method: "POST",
        body: JSON.stringify({ quote_id: quoteId }),
      });
    } catch {
      return mockStore.selectQuote(requestId, quoteId);
    }
  }

  async autoSelectBestQuotes(boqId: string): Promise<{ selected_count: number; total_priced_minor: number; message: string }> {
    if (this.isMockMode()) return mockStore.autoSelectBestQuotes(boqId);
    try {
      return await this.request<{ selected_count: number; total_priced_minor: number; message: string }>(
        `/boqs/${boqId}/auto-select-best-quotes`,
        { method: "POST", body: JSON.stringify({}) }
      );
    } catch {
      return mockStore.autoSelectBestQuotes(boqId);
    }
  }

  async overridePrice(boqId: string, itemId: string, priceMinor: number, reason: string): Promise<LineItemComparisonDTO> {
    if (this.isMockMode()) return mockStore.overridePrice(boqId, itemId, priceMinor, reason);
    try {
      return await this.request<LineItemComparisonDTO>(`/boqs/${boqId}/line-items/${itemId}/price-override`, {
        method: "POST",
        body: JSON.stringify({ price_minor: priceMinor, reason, currency: "ZAR" }),
      });
    } catch {
      return mockStore.overridePrice(boqId, itemId, priceMinor, reason);
    }
  }

  // Supplier Portal
  async getSupplierQuoteRequests(): Promise<QuoteRequestDTO[]> {
    if (this.isMockMode()) return mockStore.getSupplierQuoteRequests();
    try {
      return await this.request<QuoteRequestDTO[]>("/suppliers/quote-requests");
    } catch {
      return mockStore.getSupplierQuoteRequests();
    }
  }

  async getSupplierQuoteRequest(requestId: string): Promise<QuoteRequestDTO> {
    if (this.isMockMode()) return mockStore.getSupplierQuoteRequest(requestId);
    try {
      return await this.request<QuoteRequestDTO>(`/suppliers/quote-requests/${requestId}`);
    } catch {
      return mockStore.getSupplierQuoteRequest(requestId);
    }
  }

  async submitSupplierQuote(
    requestId: string,
    unitPriceMinor: number,
    leadTimeDays?: number,
    notes?: string
  ): Promise<QuoteDTO> {
    if (this.isMockMode()) return mockStore.submitSupplierQuote(requestId, unitPriceMinor, leadTimeDays, notes);
    try {
      return await this.request<QuoteDTO>(`/quote-requests/${requestId}/quotes`, {
        method: "POST",
        body: JSON.stringify({
          unit_price_minor: unitPriceMinor,
          lead_time_days: leadTimeDays,
          notes,
          currency: "ZAR",
        }),
      });
    } catch {
      return mockStore.submitSupplierQuote(requestId, unitPriceMinor, leadTimeDays, notes);
    }
  }

  // Exports & Audit
  async getAuditTrail(boqId: string): Promise<AuditEventDTO[]> {
    if (this.isMockMode()) return mockStore.getAuditTrail(boqId);
    try {
      return await this.request<AuditEventDTO[]>(`/boqs/${boqId}/audit`);
    } catch {
      return mockStore.getAuditTrail(boqId);
    }
  }

  async createExport(boqId: string, format: "xlsx" | "pdf"): Promise<{ download_url: string; filename: string }> {
    if (this.isMockMode()) return mockStore.createExport(boqId, format);
    try {
      return await this.request<{ download_url: string; filename: string }>(`/boqs/${boqId}/exports`, {
        method: "POST",
        body: JSON.stringify({ format }),
      });
    } catch {
      return mockStore.createExport(boqId, format);
    }
  }

  // Simulation
  async simulateBoqQuotes(boqId: string): Promise<{ total_quotes: number; message: string }> {
    if (this.isMockMode()) return mockStore.simulateBoqQuotes(boqId);
    try {
      return await this.request<{ total_quotes: number; message: string }>(`/boqs/${boqId}/simulate-quotes`, {
        method: "POST",
      });
    } catch {
      return mockStore.simulateBoqQuotes(boqId);
    }
  }

  async simulateRequestQuotes(requestId: string): Promise<{ quotes_count: number; message: string }> {
    if (this.isMockMode()) return mockStore.simulateRequestQuotes(requestId);
    try {
      return await this.request<{ quotes_count: number; message: string }>(
        `/quote-requests/${requestId}/simulate-responses`,
        { method: "POST" }
      );
    } catch {
      return mockStore.simulateRequestQuotes(requestId);
    }
  }
}

export const api = new ApiClient();
