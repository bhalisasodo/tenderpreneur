/**
 * In-Browser Mock Store & Simulation Engine for BoQPro
 * Provides complete local persistence (localStorage) and realistic South African
 * tender data so the static GitHub Pages deployment works out-of-the-box without
 * requiring a live server.
 */

import type {
  AuditEventDTO,
  AuthSession,
  BoQComparisonDTO,
  BoQDetailDTO,
  BoQSummaryDTO,
  LineItemComparisonDTO,
  LineItemDTO,
  OrganisationDTO,
  QuoteDTO,
  QuoteRequestDTO,
  UserDTO,
} from "./api";

function generateId(): string {
  if (typeof crypto !== "undefined" && crypto.randomUUID) {
    return crypto.randomUUID();
  }
  return "id-" + Math.random().toString(36).substring(2, 11) + "-" + Date.now();
}

interface MockStorageState {
  users: UserDTO[];
  organisations: OrganisationDTO[];
  boqs: BoQDetailDTO[];
  quoteRequests: QuoteRequestDTO[];
  quotes: QuoteDTO[];
  auditEvents: AuditEventDTO[];
  supplierProfiles: Record<string, { categories: string[]; regions: string[] }>;
}

const STORAGE_KEY = "boqpro_mock_db_v1";
const LEGACY_STORAGE_KEY = "tenderpreneur_mock_db_v2";

export class MockStore {
  private state: MockStorageState;

  constructor() {
    this.state = this.loadState();
  }

  private getInitialState(): MockStorageState {
    const contractorOrgId = "org-amandla-civils";
    const contractorUserId = "user-sipho-ndlovu";

    const contractorOrg: OrganisationDTO = {
      id: contractorOrgId,
      type: "contractor",
      legal_name: "Amandla Infrastructure & Civil Contractors (Pty) Ltd",
      trading_name: "Amandla Civils",
      email: "estimator@amandlacivils.co.za",
      phone: "+27 31 555 0192",
      region: "KwaZulu-Natal",
    };

    const contractorUser: UserDTO = {
      id: contractorUserId,
      email: "estimator@amandlacivils.co.za",
      name: "Sipho Ndlovu",
      role: "admin",
      organisation_id: contractorOrgId,
      organisation: contractorOrg,
    };

    const suppliers: Array<{ org: OrganisationDTO; user: UserDTO; cats: string[]; regions: string[] }> = [
      {
        org: {
          id: "org-durban-builders",
          type: "supplier",
          legal_name: "Durban Building Supplies & Cement CC",
          trading_name: "Durban Builders Hub",
          email: "sales@durbanbuilders.co.za",
          phone: "+27 82 441 9021",
          region: "KwaZulu-Natal",
        },
        user: {
          id: "user-durban-rep",
          email: "sales@durbanbuilders.co.za",
          name: "Durban Builders Representative",
          role: "admin",
          organisation_id: "org-durban-builders",
        },
        cats: ["building-materials", "concrete", "earthworks"],
        regions: ["KwaZulu-Natal", "Eastern Cape"],
      },
      {
        org: {
          id: "org-afriready-concrete",
          type: "supplier",
          legal_name: "AfriReady Concrete & Aggregate Solutions",
          trading_name: "AfriReady Concrete",
          email: "orders@afriready.co.za",
          phone: "+27 83 992 1104",
          region: "KwaZulu-Natal",
        },
        user: {
          id: "user-afriready-rep",
          email: "orders@afriready.co.za",
          name: "AfriReady Concrete Representative",
          role: "admin",
          organisation_id: "org-afriready-concrete",
        },
        cats: ["concrete", "earthworks"],
        regions: ["KwaZulu-Natal", "Gauteng"],
      },
      {
        org: {
          id: "org-natal-roofing",
          type: "supplier",
          legal_name: "Natal Roofing & Timber Fabricators (Pty) Ltd",
          trading_name: "Natal Roof Trusses",
          email: "quotes@natalroofing.co.za",
          phone: "+27 84 330 8820",
          region: "KwaZulu-Natal",
        },
        user: {
          id: "user-natal-rep",
          email: "quotes@natalroofing.co.za",
          name: "Natal Roof Trusses Representative",
          role: "admin",
          organisation_id: "org-natal-roofing",
        },
        cats: ["roofing", "building-materials"],
        regions: ["KwaZulu-Natal"],
      },
      {
        org: {
          id: "org-protec-safety",
          type: "supplier",
          legal_name: "Protec Safety & PPE Supplies SA",
          trading_name: "Protec Safety Direct",
          email: "sales@protecsafety.co.za",
          phone: "+27 11 889 0044",
          region: "Gauteng",
        },
        user: {
          id: "user-protec-rep",
          email: "sales@protecsafety.co.za",
          name: "Protec Safety Direct Representative",
          role: "admin",
          organisation_id: "org-protec-safety",
        },
        cats: ["ppe", "general-building"],
        regions: ["Gauteng", "KwaZulu-Natal", "Western Cape", "National"],
      },
    ];

    const allOrgs: OrganisationDTO[] = [contractorOrg, ...suppliers.map((s) => s.org)];
    const allUsers: UserDTO[] = [
      contractorUser,
      ...suppliers.map((s) => {
        const u = { ...s.user, organisation: s.org };
        return u;
      }),
    ];

    const supplierProfiles: Record<string, { categories: string[]; regions: string[] }> = {};
    for (const s of suppliers) {
      supplierProfiles[s.org.id] = { categories: s.cats, regions: s.regions };
    }

    // Seed BoQ: Umlazi High School Science Wing Upgrade
    const demoBoqId = "demo";
    const now = new Date();
    const deadline = new Date(now.getTime() + 14 * 24 * 60 * 60 * 1000).toISOString();
    const createdAt = new Date(now.getTime() - 2 * 24 * 60 * 60 * 1000).toISOString();

    const lineItems: LineItemDTO[] = [
      {
        id: "item-101",
        boq_id: demoBoqId,
        source_row_reference: "1.01",
        description: "Excavation in earth for foundation trenches not exceeding 2.0m deep",
        unit: "m3",
        quantity: 320,
        category: "earthworks",
        benchmark_min_minor: 6500,
        benchmark_max_minor: 11000,
        benchmark_source: "SA Industry Rate Guide 2026",
        pricing_status: "quoted",
        parsing_confidence: 0.98,
        review_status: "accepted",
      },
      {
        id: "item-102",
        boq_id: demoBoqId,
        source_row_reference: "1.02",
        description: "Supply and place 25MPa ready-mix concrete in foundation footings & slab",
        unit: "m3",
        quantity: 115,
        category: "concrete",
        benchmark_min_minor: 185000,
        benchmark_max_minor: 240000,
        benchmark_source: "SA Industry Rate Guide 2026",
        pricing_status: "selected",
        final_price_minor: 195000,
        parsing_confidence: 0.96,
        review_status: "accepted",
      },
      {
        id: "item-103",
        boq_id: demoBoqId,
        source_row_reference: "1.03",
        description: "Standard clay stock bricks (NFP) in 1:4 cement mortar for load-bearing walls",
        unit: "no",
        quantity: 35000,
        category: "building-materials",
        benchmark_min_minor: 320,
        benchmark_max_minor: 450,
        benchmark_source: "SA Industry Rate Guide 2026",
        pricing_status: "quoted",
        parsing_confidence: 0.95,
        review_status: "accepted",
      },
      {
        id: "item-104",
        boq_id: demoBoqId,
        source_row_reference: "1.04",
        description: "50kg All-Purpose Portland Cement CEM II 42.5N bags",
        unit: "no",
        quantity: 500,
        category: "building-materials",
        benchmark_min_minor: 9200,
        benchmark_max_minor: 12500,
        benchmark_source: "SA Industry Rate Guide 2026",
        pricing_status: "selected",
        final_price_minor: 9600,
        parsing_confidence: 0.99,
        review_status: "accepted",
      },
      {
        id: "item-105",
        boq_id: demoBoqId,
        source_row_reference: "1.05",
        description: "Treated timber roof trusses designed and fabricated to engineer specs",
        unit: "m2",
        quantity: 240,
        category: "roofing",
        benchmark_min_minor: 26000,
        benchmark_max_minor: 42000,
        benchmark_source: "SA Industry Rate Guide 2026",
        pricing_status: "quoted",
        parsing_confidence: 0.92,
        review_status: "accepted",
      },
      {
        id: "item-106",
        boq_id: demoBoqId,
        source_row_reference: "1.06",
        description: "0.5mm IBR Chromadek roof sheeting with sealants and fixings",
        unit: "m2",
        quantity: 290,
        category: "roofing",
        benchmark_min_minor: 18000,
        benchmark_max_minor: 31000,
        benchmark_source: "SA Industry Rate Guide 2026",
        pricing_status: "needs_review",
        parsing_confidence: 0.74,
        review_status: "needs_review",
        exclusion_reason: "Check sheeting gauge & color code with spec",
      },
      {
        id: "item-107",
        boq_id: demoBoqId,
        source_row_reference: "1.07",
        description: "Personal Protective Equipment (PPE) site kits: hardhats, vests, boots",
        unit: "no",
        quantity: 25,
        category: "ppe",
        benchmark_min_minor: 15000,
        benchmark_max_minor: 35000,
        benchmark_source: "SA Industry Rate Guide 2026",
        pricing_status: "selected",
        final_price_minor: 16500,
        parsing_confidence: 0.97,
        review_status: "accepted",
      },
    ];

    const demoBoq: BoQDetailDTO = {
      id: demoBoqId,
      contractor_organisation_id: contractorOrgId,
      title: "KZN Dept of Education - Umlazi High School Science Wing Upgrade",
      tender_reference: "DOE-KZN-2026-088",
      tender_deadline: deadline,
      region: "KwaZulu-Natal",
      status: "in_sourcing",
      line_item_count: lineItems.length,
      total_priced_minor: 115 * 195000 + 500 * 9600 + 25 * 16500, // selected items
      created_at: createdAt,
      line_items: lineItems,
    };

    // Pre-create Quote Requests and Quotes
    const quoteRequests: QuoteRequestDTO[] = [];
    const quotes: QuoteDTO[] = [];
    const rfqDeadline = new Date(now.getTime() + 48 * 60 * 60 * 1000).toISOString();

    // RFQ for Concrete (item-102)
    const reqConcreteId = "req-102";
    const quoteAfriReady: QuoteDTO = {
      id: "quote-102-1",
      quote_request_id: reqConcreteId,
      supplier_organisation_id: "org-afriready-concrete",
      supplier_name: "AfriReady Concrete",
      unit_price_minor: 195000,
      total_price_minor: 115 * 195000,
      currency: "ZAR",
      lead_time_days: 2,
      notes: "Delivery included from Durban South batching plant. SABS 25MPa certified.",
      is_selected: true,
      submitted_at: new Date(now.getTime() - 4 * 60 * 60 * 1000).toISOString(),
    };

    const quoteDurbanHub: QuoteDTO = {
      id: "quote-102-2",
      quote_request_id: reqConcreteId,
      supplier_organisation_id: "org-durban-builders",
      supplier_name: "Durban Builders Hub",
      unit_price_minor: 215000,
      total_price_minor: 115 * 215000,
      currency: "ZAR",
      lead_time_days: 1,
      notes: "24h delivery guarantee with pump truck service available.",
      is_selected: false,
      submitted_at: new Date(now.getTime() - 6 * 60 * 60 * 1000).toISOString(),
    };

    quotes.push(quoteAfriReady, quoteDurbanHub);
    quoteRequests.push({
      id: reqConcreteId,
      line_item_id: "item-102",
      line_item_description: lineItems[1].description,
      line_item_quantity: lineItems[1].quantity,
      line_item_unit: lineItems[1].unit,
      line_item_category: lineItems[1].category,
      boq_id: demoBoqId,
      boq_title: demoBoq.title,
      boq_region: demoBoq.region,
      response_deadline: rfqDeadline,
      status: "open",
      is_expired: false,
      quotes: [quoteAfriReady, quoteDurbanHub],
      supplier_count: 2,
    });

    // RFQ for Earthworks (item-101)
    const reqEarthId = "req-101";
    const quoteEarth1: QuoteDTO = {
      id: "quote-101-1",
      quote_request_id: reqEarthId,
      supplier_organisation_id: "org-afriready-concrete",
      supplier_name: "AfriReady Concrete",
      unit_price_minor: 7800,
      total_price_minor: 320 * 7800,
      currency: "ZAR",
      lead_time_days: 3,
      notes: "Includes TLB and operator for 4 days.",
      is_selected: false,
      submitted_at: new Date(now.getTime() - 8 * 60 * 60 * 1000).toISOString(),
    };
    quotes.push(quoteEarth1);
    quoteRequests.push({
      id: reqEarthId,
      line_item_id: "item-101",
      line_item_description: lineItems[0].description,
      line_item_quantity: lineItems[0].quantity,
      line_item_unit: lineItems[0].unit,
      line_item_category: lineItems[0].category,
      boq_id: demoBoqId,
      boq_title: demoBoq.title,
      boq_region: demoBoq.region,
      response_deadline: rfqDeadline,
      status: "open",
      is_expired: false,
      quotes: [quoteEarth1],
      supplier_count: 2,
    });

    // Audit events
    const auditEvents: AuditEventDTO[] = [
      {
        id: "audit-1",
        organisation_id: contractorOrgId,
        actor_name: "Sipho Ndlovu",
        entity_type: "boq",
        entity_id: demoBoqId,
        action: "created",
        after_json: { title: demoBoq.title, tender_reference: demoBoq.tender_reference },
        created_at: createdAt,
      },
      {
        id: "audit-2",
        organisation_id: contractorOrgId,
        actor_name: "Sipho Ndlovu",
        entity_type: "quote",
        entity_id: "quote-102-1",
        action: "selected",
        before_json: { status: "unselected" },
        after_json: { status: "selected", supplier: "AfriReady Concrete", rate_zar: 1950 },
        metadata_json: { reason: "Lowest compliant quote meeting 48h turnaround" },
        created_at: new Date(now.getTime() - 2 * 60 * 60 * 1000).toISOString(),
      },
    ];

    return {
      users: allUsers,
      organisations: allOrgs,
      boqs: [demoBoq],
      quoteRequests,
      quotes,
      auditEvents,
      supplierProfiles,
    };
  }

  private loadState(): MockStorageState {
    if (typeof window === "undefined") {
      return this.getInitialState();
    }
    try {
      const data = localStorage.getItem(STORAGE_KEY) || localStorage.getItem(LEGACY_STORAGE_KEY);
      if (data) {
        return JSON.parse(data);
      }
    } catch {}
    const initial = this.getInitialState();
    this.saveState(initial);
    return initial;
  }

  private saveState(state: MockStorageState) {
    this.state = state;
    if (typeof window !== "undefined") {
      try {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
      } catch {}
    }
  }

  public resetToDefaults(): void {
    const initial = this.getInitialState();
    this.saveState(initial);
  }

  // Auth methods
  async login(email: string): Promise<AuthSession> {
    const user = this.state.users.find((u) => u.email.toLowerCase() === email.toLowerCase());
    if (!user) {
      throw new Error(`Demo user with email "${email}" not found.`);
    }
    const org = this.state.organisations.find((o) => o.id === user.organisation_id) || user.organisation!;
    const session: AuthSession = {
      access_token: "mock-jwt-" + generateId(),
      token_type: "bearer",
      user,
      organisation: org,
    };
    if (typeof window !== "undefined") {
      localStorage.setItem("tp_token", session.access_token);
      localStorage.setItem("tp_session", JSON.stringify(session));
    }
    return session;
  }

  async getMe(): Promise<AuthSession> {
    if (typeof window !== "undefined") {
      const sessionStr = localStorage.getItem("tp_session");
      if (sessionStr) {
        try {
          return JSON.parse(sessionStr);
        } catch {}
      }
    }
    return this.login("estimator@amandlacivils.co.za");
  }

  async getDemoTenants(): Promise<UserDTO[]> {
    return this.state.users;
  }

  // BoQs
  async listBoQs(): Promise<BoQSummaryDTO[]> {
    return this.state.boqs.map((b) => {
      let pricedMinor = 0;
      for (const item of b.line_items) {
        if (item.final_price_minor) {
          pricedMinor += item.final_price_minor * item.quantity;
        }
      }
      return {
        id: b.id,
        contractor_organisation_id: b.contractor_organisation_id,
        title: b.title,
        tender_reference: b.tender_reference,
        tender_deadline: b.tender_deadline,
        region: b.region,
        status: b.status,
        line_item_count: b.line_items.length,
        total_priced_minor: pricedMinor,
        created_at: b.created_at,
      };
    });
  }

  async getBoQ(id: string): Promise<BoQDetailDTO> {
    const boq = this.state.boqs.find((b) => b.id === id);
    if (!boq) {
      if (id === "demo" || id === "sample") {
        return this.state.boqs[0];
      }
      throw new Error(`Tender BoQ with ID "${id}" not found.`);
    }
    return boq;
  }

  async createBoQ(data: { title: string; tender_reference?: string; region: string }): Promise<BoQDetailDTO> {
    const me = await this.getMe();
    const newBoq: BoQDetailDTO = {
      id: generateId(),
      contractor_organisation_id: me.organisation.id,
      title: data.title,
      tender_reference: data.tender_reference || "REF-" + Math.floor(1000 + Math.random() * 9000),
      region: data.region || "KwaZulu-Natal",
      status: "draft",
      tender_deadline: new Date(Date.now() + 21 * 24 * 60 * 60 * 1000).toISOString(),
      line_item_count: 0,
      total_priced_minor: 0,
      created_at: new Date().toISOString(),
      line_items: [],
    };
    this.state.boqs.unshift(newBoq);
    this.saveState(this.state);
    return newBoq;
  }

  async deleteBoQ(id: string): Promise<void> {
    this.state.boqs = this.state.boqs.filter((b) => b.id !== id);
    this.saveState(this.state);
  }

  async uploadBoQDocument(boqId: string, file: File): Promise<any> {
    return {
      document_id: "doc-" + generateId(),
      filename: file.name,
      file_size_bytes: file.size,
      status: "uploaded",
    };
  }

  async parseBoQ(boqId: string, pastedText?: string): Promise<BoQDetailDTO> {
    const boq = await this.getBoQ(boqId);
    let items: LineItemDTO[] = [];

    if (pastedText && pastedText.trim().length > 0) {
      // Parse pasted lines
      const lines = pastedText
        .split("\n")
        .map((l) => l.trim())
        .filter((l) => l.length > 0);

      let rowIdx = 1;
      for (const line of lines) {
        // Skip obvious header or subtotal lines
        if (/^(total|subtotal|section|bill no|schedule)/i.test(line)) continue;

        // Try extracting quantity, unit, and description
        // e.g. "1.01 Excavate foundation trenches m3 250" or "Earthworks m3 100"
        let unit = "m3";
        let qty = 100;
        let desc = line;

        const qtyMatch = line.match(/\b(\d+(?:[.,]\d+)?)\s*(m3|m2|m|kg|t|no|nr|item|sum|l|litres|bags|hrs?)\b/i);
        if (qtyMatch) {
          qty = parseFloat(qtyMatch[1].replace(",", "."));
          unit = qtyMatch[2].toLowerCase();
        } else {
          // Look for number at end
          const endNumMatch = line.match(/\b(\d+(?:[.,]\d+)?)\s*$/);
          if (endNumMatch) {
            qty = parseFloat(endNumMatch[1].replace(",", "."));
            desc = line.replace(endNumMatch[0], "").trim();
          }
        }

        // Detect category
        let cat = "general-building";
        const lower = line.toLowerCase();
        if (lower.includes("excavat") || lower.includes("earth") || lower.includes("trench") || lower.includes("fill")) {
          cat = "earthworks";
        } else if (lower.includes("concrete") || lower.includes("slab") || lower.includes("cement") || lower.includes("ready-mix")) {
          cat = "concrete";
        } else if (lower.includes("brick") || lower.includes("block") || lower.includes("masonry") || lower.includes("mortar")) {
          cat = "building-materials";
        } else if (lower.includes("roof") || lower.includes("truss") || lower.includes("sheeting") || lower.includes("timber")) {
          cat = "roofing";
        } else if (lower.includes("pipe") || lower.includes("drain") || lower.includes("plumb") || lower.includes("sanitary")) {
          cat = "plumbing";
        } else if (lower.includes("cable") || lower.includes("electr") || lower.includes("conduit") || lower.includes("light")) {
          cat = "electrical";
        } else if (lower.includes("ppe") || lower.includes("safety") || lower.includes("vest") || lower.includes("boot")) {
          cat = "ppe";
        }

        items.push({
          id: "item-" + generateId(),
          boq_id: boq.id,
          source_row_reference: `1.${rowIdx < 10 ? "0" + rowIdx : rowIdx}`,
          description: desc,
          unit,
          quantity: qty,
          category: cat,
          benchmark_min_minor: 5000,
          benchmark_max_minor: 15000,
          benchmark_source: "SA Market Baseline 2026",
          pricing_status: "unsourced",
          parsing_confidence: 0.94,
          review_status: "accepted",
        });
        rowIdx++;
      }
    }

    if (items.length === 0) {
      // Provide default structured items if empty text or file upload
      items = [
        {
          id: "item-" + generateId(),
          boq_id: boq.id,
          source_row_reference: "1.01",
          description: "Bulk site clearance, topsoil stripping and stockpiling on site",
          unit: "m2",
          quantity: 1200,
          category: "earthworks",
          benchmark_min_minor: 1800,
          benchmark_max_minor: 3200,
          pricing_status: "unsourced",
          parsing_confidence: 0.98,
          review_status: "accepted",
        },
        {
          id: "item-" + generateId(),
          boq_id: boq.id,
          source_row_reference: "1.02",
          description: "Reinforced 30MPa cast-in-situ concrete for storm water retaining culverts",
          unit: "m3",
          quantity: 85,
          category: "concrete",
          benchmark_min_minor: 210000,
          benchmark_max_minor: 265000,
          pricing_status: "unsourced",
          parsing_confidence: 0.95,
          review_status: "accepted",
        },
        {
          id: "item-" + generateId(),
          boq_id: boq.id,
          source_row_reference: "1.03",
          description: "110mm Class 34 heavy-duty uPVC sewer and stormwater piping laid in trenches",
          unit: "m",
          quantity: 450,
          category: "plumbing",
          benchmark_min_minor: 16500,
          benchmark_max_minor: 24000,
          pricing_status: "unsourced",
          parsing_confidence: 0.92,
          review_status: "accepted",
        },
      ];
    }

    boq.line_items = items;
    boq.line_item_count = items.length;
    boq.status = "parsed";
    this.saveState(this.state);
    return boq;
  }

  async addLineItem(boqId: string, item: any): Promise<LineItemDTO> {
    const boq = await this.getBoQ(boqId);
    const newItem: LineItemDTO = {
      id: "item-" + generateId(),
      boq_id: boqId,
      source_row_reference: item.source_row_reference || `1.${boq.line_items.length + 1}`,
      description: item.description,
      unit: item.unit || "item",
      quantity: Number(item.quantity) || 1,
      category: item.category || "general-building",
      pricing_status: "unsourced",
      parsing_confidence: 1.0,
      review_status: "accepted",
    };
    boq.line_items.push(newItem);
    boq.line_item_count = boq.line_items.length;
    this.saveState(this.state);
    return newItem;
  }

  async updateLineItem(boqId: string, itemId: string, itemPatch: Partial<LineItemDTO>): Promise<LineItemDTO> {
    const boq = await this.getBoQ(boqId);
    const item = boq.line_items.find((i) => i.id === itemId);
    if (!item) throw new Error("Line item not found");
    Object.assign(item, itemPatch);
    this.saveState(this.state);
    return item;
  }

  async deleteLineItem(boqId: string, itemId: string): Promise<void> {
    const boq = await this.getBoQ(boqId);
    const item = boq.line_items.find((i) => i.id === itemId);
    if (item) {
      item.review_status = "excluded";
      item.exclusion_reason = "Manually excluded by contractor";
      this.saveState(this.state);
    }
  }

  async bulkDeleteLineItems(boqId: string, lineItemIds: string[]): Promise<{ deleted_count: number }> {
    const boq = await this.getBoQ(boqId);
    let count = 0;
    for (const id of lineItemIds) {
      const item = boq.line_items.find((i) => i.id === id);
      if (item) {
        item.review_status = "excluded";
        item.exclusion_reason = "Excluded in bulk review";
        count++;
      }
    }
    this.saveState(this.state);
    return { deleted_count: count };
  }

  async restoreLineItem(boqId: string, itemId: string): Promise<LineItemDTO> {
    const boq = await this.getBoQ(boqId);
    const item = boq.line_items.find((i) => i.id === itemId);
    if (!item) throw new Error("Line item not found");
    item.review_status = "accepted";
    item.exclusion_reason = undefined;
    this.saveState(this.state);
    return item;
  }

  async getParserFeedbackSummary(): Promise<any> {
    return { total_corrections: 14, accuracy_rate: 0.96 };
  }

  // Quote Sourcing & Broadcast
  async validateBroadcastSafety(boqId: string, lineItemIds: string[]) {
    const boq = await this.getBoQ(boqId);
    const selectedItems = boq.line_items.filter((i) => lineItemIds.includes(i.id));
    const corrupted = selectedItems.filter((i) => i.description.includes("\ufffd") || i.description.includes("\x00"));
    return {
      is_safe: corrupted.length === 0,
      safe: corrupted.length === 0,
      total_items: selectedItems.length,
      valid_items_count: selectedItems.length - corrupted.length,
      corrupted_items_count: corrupted.length,
      corrupted_items: corrupted.map((c) => ({
        id: c.id,
        description: c.description,
        reason: "Contains invalid character sequence",
        corruption_ratio: 0.5,
      })),
      message: corrupted.length === 0 ? "All items valid for broadcast" : `${corrupted.length} items contain corrupted text`,
    };
  }

  async createQuoteRequest(lineItemId: string, responseDeadline: string): Promise<QuoteRequestDTO> {
    // Find line item across boqs
    let targetItem: LineItemDTO | undefined;
    let targetBoq: BoQDetailDTO | undefined;
    for (const b of this.state.boqs) {
      const it = b.line_items.find((i) => i.id === lineItemId);
      if (it) {
        targetItem = it;
        targetBoq = b;
        break;
      }
    }
    if (!targetItem || !targetBoq) throw new Error("Line item not found");

    const req: QuoteRequestDTO = {
      id: "req-" + generateId(),
      line_item_id: targetItem.id,
      line_item_description: targetItem.description,
      line_item_quantity: targetItem.quantity,
      line_item_unit: targetItem.unit,
      line_item_category: targetItem.category,
      boq_id: targetBoq.id,
      boq_title: targetBoq.title,
      boq_region: targetBoq.region,
      response_deadline: responseDeadline,
      status: "open",
      is_expired: false,
      quotes: [],
      supplier_count: 2,
    };
    this.state.quoteRequests.push(req);
    this.saveState(this.state);
    return req;
  }

  async broadcastQuoteRequest(requestId: string): Promise<QuoteRequestDTO> {
    const req = this.state.quoteRequests.find((r) => r.id === requestId);
    if (!req) throw new Error("Quote request not found");
    req.status = "open";
    this.saveState(this.state);
    return req;
  }

  async getQuoteComparison(boqId: string): Promise<BoQComparisonDTO> {
    const boq = await this.getBoQ(boqId);
    let totalEstimated = 0;
    let totalPriced = 0;

    const lineComparisons: LineItemComparisonDTO[] = boq.line_items.map((item) => {
      const benchmarkMid = item.benchmark_min_minor && item.benchmark_max_minor
        ? Math.round((item.benchmark_min_minor + item.benchmark_max_minor) / 2)
        : 10000;
      totalEstimated += benchmarkMid * item.quantity;

      // Find matching quotes
      const matchingQuotes = this.state.quotes.filter((q) => {
        const req = this.state.quoteRequests.find((r) => r.id === q.quote_request_id);
        return req && req.line_item_id === item.id;
      });

      const lowestQuote = matchingQuotes.length > 0
        ? [...matchingQuotes].sort((a, b) => a.unit_price_minor - b.unit_price_minor)[0]
        : undefined;

      const fastestQuote = matchingQuotes.length > 0
        ? [...matchingQuotes].sort((a, b) => (a.lead_time_days || 99) - (b.lead_time_days || 99))[0]
        : undefined;

      const selectedQuote = matchingQuotes.find((q) => q.is_selected);

      if (item.final_price_minor) {
        totalPriced += item.final_price_minor * item.quantity;
      }

      return {
        line_item_id: item.id,
        description: item.description,
        unit: item.unit,
        quantity: item.quantity,
        category: item.category,
        benchmark_min_minor: item.benchmark_min_minor,
        benchmark_max_minor: item.benchmark_max_minor,
        final_price_minor: item.final_price_minor,
        pricing_status: item.pricing_status,
        quote_request_id: matchingQuotes[0]?.quote_request_id,
        response_deadline: new Date(Date.now() + 48 * 3600000).toISOString(),
        is_deadline_passed: false,
        quotes: matchingQuotes,
        lowest_quote: lowestQuote,
        fastest_quote: fastestQuote,
        selected_quote: selectedQuote,
      };
    });

    return {
      boq_id: boq.id,
      title: boq.title,
      region: boq.region,
      tender_deadline: boq.tender_deadline,
      line_items: lineComparisons,
      total_estimated_minor: totalEstimated,
      total_priced_minor: totalPriced,
    };
  }

  async selectQuote(requestId: string, quoteId: string): Promise<LineItemComparisonDTO> {
    const req = this.state.quoteRequests.find((r) => r.id === requestId);
    if (!req) throw new Error("Quote request not found");

    for (const q of this.state.quotes) {
      if (q.quote_request_id === requestId) {
        q.is_selected = q.id === quoteId;
      }
    }

    const selected = this.state.quotes.find((q) => q.id === quoteId);
    if (selected) {
      for (const b of this.state.boqs) {
        const item = b.line_items.find((i) => i.id === req.line_item_id);
        if (item) {
          item.final_price_minor = selected.unit_price_minor;
          item.pricing_status = "selected";
          break;
        }
      }
    }

    this.saveState(this.state);
    const comparison = await this.getQuoteComparison(req.boq_id || "demo");
    return comparison.line_items.find((i) => i.line_item_id === req.line_item_id)!;
  }

  async autoSelectBestQuotes(boqId: string) {
    const comp = await this.getQuoteComparison(boqId);
    let count = 0;
    for (const item of comp.line_items) {
      if (item.lowest_quote && !item.selected_quote) {
        await this.selectQuote(item.lowest_quote.quote_request_id, item.lowest_quote.id);
        count++;
      }
    }
    const updated = await this.getQuoteComparison(boqId);
    return {
      selected_count: count,
      total_priced_minor: updated.total_priced_minor,
      message: `Automatically selected ${count} best compliant quotes`,
    };
  }

  async overridePrice(boqId: string, itemId: string, priceMinor: number, reason: string) {
    const boq = await this.getBoQ(boqId);
    const item = boq.line_items.find((i) => i.id === itemId);
    if (!item) throw new Error("Line item not found");

    item.final_price_minor = priceMinor;
    item.pricing_status = "manual_override";

    this.state.auditEvents.unshift({
      id: "audit-" + generateId(),
      organisation_id: boq.contractor_organisation_id,
      actor_name: "Contractor Estimator",
      entity_type: "line_item",
      entity_id: itemId,
      action: "price_override",
      after_json: { price_minor: priceMinor },
      metadata_json: { reason },
      created_at: new Date().toISOString(),
    });

    this.saveState(this.state);
    const comp = await this.getQuoteComparison(boqId);
    return comp.line_items.find((i) => i.line_item_id === itemId)!;
  }

  // Supplier Portal
  async getSupplierQuoteRequests(): Promise<QuoteRequestDTO[]> {
    const me = await this.getMe();
    return this.state.quoteRequests.map((r) => {
      const myQuotes = this.state.quotes.filter(
        (q) => q.quote_request_id === r.id && q.supplier_organisation_id === me.organisation.id
      );
      return {
        ...r,
        quotes: myQuotes,
      };
    });
  }

  async getSupplierQuoteRequest(requestId: string): Promise<QuoteRequestDTO> {
    const req = this.state.quoteRequests.find((r) => r.id === requestId);
    if (!req) {
      return this.state.quoteRequests[0] || (await this.createQuoteRequest("item-101", new Date().toISOString()));
    }
    const me = await this.getMe();
    const myQuotes = this.state.quotes.filter(
      (q) => q.quote_request_id === req.id && q.supplier_organisation_id === me.organisation.id
    );
    return {
      ...req,
      quotes: myQuotes,
    };
  }

  async submitSupplierQuote(
    requestId: string,
    unitPriceMinor: number,
    leadTimeDays?: number,
    notes?: string
  ): Promise<QuoteDTO> {
    const me = await this.getMe();
    const req = this.state.quoteRequests.find((r) => r.id === requestId);
    if (!req) throw new Error("Quote request not found");

    const newQuote: QuoteDTO = {
      id: "quote-" + generateId(),
      quote_request_id: requestId,
      supplier_organisation_id: me.organisation.id,
      supplier_name: me.organisation.trading_name || me.organisation.legal_name,
      unit_price_minor: unitPriceMinor,
      total_price_minor: (req.line_item_quantity || 1) * unitPriceMinor,
      currency: "ZAR",
      lead_time_days: leadTimeDays || 3,
      notes: notes || "Submitted via BoQPro Supplier Portal",
      is_selected: false,
      submitted_at: new Date().toISOString(),
    };

    // Replace any existing quote by this supplier for this request
    this.state.quotes = this.state.quotes.filter(
      (q) => !(q.quote_request_id === requestId && q.supplier_organisation_id === me.organisation.id)
    );
    this.state.quotes.push(newQuote);

    // Update BoQ line item status to 'quoted'
    for (const b of this.state.boqs) {
      const it = b.line_items.find((i) => i.id === req.line_item_id);
      if (it && it.pricing_status === "unsourced") {
        it.pricing_status = "quoted";
      }
    }

    this.saveState(this.state);
    return newQuote;
  }

  // Audit
  async getAuditTrail(boqId: string): Promise<AuditEventDTO[]> {
    return this.state.auditEvents;
  }

  // Export
  async createExport(boqId: string, format: "xlsx" | "pdf") {
    const boq = await this.getBoQ(boqId);
    return {
      download_url: `data:text/plain;charset=utf-8,${encodeURIComponent(
        `BOQPRO VERIFIED EXPORT\nTender: ${boq.title}\nRef: ${boq.tender_reference}\nRegion: ${boq.region}\nExported: ${new Date().toISOString()}\n\nLine Items:\n` +
          boq.line_items.map((i) => `${i.source_row_reference} | ${i.description} | ${i.quantity} ${i.unit} | R${((i.final_price_minor || 0) / 100).toFixed(2)}`).join("\n")
      )}`,
      filename: `BoQPro_Priced_BoQ_${boq.tender_reference || "Tender"}_${new Date().toISOString().slice(0, 10)}.${format === "xlsx" ? "csv" : "txt"}`,
    };
  }

  // Quote Simulation (Contractor demo testing)
  async simulateBoqQuotes(boqId: string) {
    const boq = await this.getBoQ(boqId);
    let totalCreated = 0;

    const demoSuppliers = [
      { id: "org-afriready-concrete", name: "AfriReady Concrete", factor: 0.95, lead: 2 },
      { id: "org-durban-builders", name: "Durban Builders Hub", factor: 1.05, lead: 1 },
      { id: "org-natal-roofing", name: "Natal Roof Trusses", factor: 0.98, lead: 4 },
      { id: "org-protec-safety", name: "Protec Safety Direct", factor: 0.92, lead: 1 },
    ];

    for (const item of boq.line_items) {
      if (item.review_status === "excluded") continue;

      // Find or create request
      let req = this.state.quoteRequests.find((r) => r.line_item_id === item.id);
      if (!req) {
        req = {
          id: "req-" + generateId(),
          line_item_id: item.id,
          line_item_description: item.description,
          line_item_quantity: item.quantity,
          line_item_unit: item.unit,
          line_item_category: item.category,
          boq_id: boq.id,
          boq_title: boq.title,
          boq_region: boq.region,
          response_deadline: new Date(Date.now() + 48 * 3600000).toISOString(),
          status: "open",
          is_expired: false,
          quotes: [],
          supplier_count: 2,
        };
        this.state.quoteRequests.push(req);
      }

      // Generate 2 simulated quotes
      const baseRate = item.benchmark_min_minor && item.benchmark_max_minor
        ? Math.round((item.benchmark_min_minor + item.benchmark_max_minor) / 2)
        : 10000;

      for (let sIdx = 0; sIdx < 2; sIdx++) {
        const s = demoSuppliers[(sIdx + item.quantity) % demoSuppliers.length];
        const variance = 0.9 + Math.random() * 0.2;
        const quoteRate = Math.round(baseRate * variance);

        const newQ: QuoteDTO = {
          id: "quote-" + generateId(),
          quote_request_id: req.id,
          supplier_organisation_id: s.id,
          supplier_name: s.name,
          unit_price_minor: quoteRate,
          total_price_minor: quoteRate * item.quantity,
          currency: "ZAR",
          lead_time_days: s.lead + Math.floor(Math.random() * 2),
          notes: "Official simulated response with 30-day validity guarantee.",
          is_selected: false,
          submitted_at: new Date().toISOString(),
        };
        this.state.quotes.push(newQ);
        totalCreated++;
      }
      item.pricing_status = "quoted";
    }

    this.saveState(this.state);
    return { total_quotes: totalCreated, message: `Simulated ${totalCreated} competitive quotes across suppliers` };
  }

  async simulateRequestQuotes(requestId: string) {
    const req = this.state.quoteRequests.find((r) => r.id === requestId);
    if (!req) throw new Error("Quote request not found");
    const qty = req.line_item_quantity || 1;
    const q1: QuoteDTO = {
      id: "quote-" + generateId(),
      quote_request_id: req.id,
      supplier_organisation_id: "org-afriready-concrete",
      supplier_name: "AfriReady Concrete",
      unit_price_minor: 185000,
      total_price_minor: 185000 * qty,
      currency: "ZAR",
      lead_time_days: 2,
      notes: "Direct supplier price valid 30 days.",
      is_selected: false,
      submitted_at: new Date().toISOString(),
    };
    this.state.quotes.push(q1);
    this.saveState(this.state);
    return { quotes_count: 1, message: "Added 1 simulated quote response" };
  }
}

export const mockStore = new MockStore();
