import re
from typing import List, Optional, Tuple
from app.core.config import settings

# Explicit negative patterns based on actual failure cases
LEGAL_AND_NARRATIVE_PATTERNS = [
    # Explicit clause references and numbers: "Clause 2.0 - Law", "Clause 14.1", "Cl. 4"
    (r'^(?:clause|cl\.?|section|article)\s+\d+(?:\.\d+)*\s*[-–:]?\s*(?:law|contract|obligations|definitions|general|scope|payment|insurance|disputes|termination)?', "Legal contract clause reference"),
    
    # Standalone sentence fragments and conjunctions: "however", "furthermore", "notwithstanding"
    (r'^(?:however|furthermore|notwithstanding|whereas|moreover|therefore|provided\s+always\s+that|in\s+addition|in\s+particular)[,\s.]*$', "Narrative transition / sentence fragment"),
    
    (r'^(?:without\s+limiting\s+the\s+generality\s+of|the\s+(?:contractor|tenderer)\s+(?:shall|must|is\s+required\s+to|is\s+referred\s+to|is\s+advised\s+to|agrees\s+to|will)|the\s+employer\s+(?:reserves|shall))', "Contractual narrative clause"),
    (r'^(?:all\s+(?:materials|plant|workmanship|goods)(?:[,\s]+(?:and|or)?\s*(?:materials|plant|workmanship|goods))*\s+(?:shall|must|to)\s+comply|all\s+rates\s+shall\s+include|no\s+claim\b.*?\bwill\s+be\s+entertained)', "Specification narrative note"),
    (r'^(?:allow\s+for\s+(?:water|lighting|temporary|security|compliance|site\s+management)|the\s+contractor\s+is\s+advised\s+to\s+visit\s+and\s+examine\s+the\s+site|prior\s+to\s+commencing\s+work)', "Site instruction note"),
    
    # Accounting / Collection / Carried Forward / Subtotal lines
    (r'^(?:carried\s+to\s+(?:collection|summary|final\s+summary)|carried\s+forward|brought\s+forward(?:\s+from\s+page\s+\d+)?|total\s+of\s+(?:bill|section|schedule)|grand\s+total|subtotal|collection\s+page)', "Accounting subtotal / collection summary"),
    
    (r'(?:page\s+\d+\s+of\s+\d+|(?:tenderer|contractor|employer|witness)(?:\'s)?(?:\s+[a-z]+)?\s+signature|date:\s*.*|dated\s+.*|witness(?:\'s)?\s+signature|initials?:\s*_+|signature:\s*_+)', "Administrative signature / page marker"),
    
    # Pure generic section / document headers without scope
    (r'^(?:schedule\s+of\s+quantities|bill\s+of\s+quantities|preliminaries\s+and\s+general|general\s+conditions\s+of\s+contract(?:\s+.*)?|special\s+conditions\s+of\s+contract(?:\s+.*)?|scope\s+of\s+work|pricing\s+instructions)$', "Document / Section Header"),
]

# Standard construction trade keywords indicating genuine physical work / materials
GENUINE_TRADE_KEYWORDS = [
    "excavat", "trench", "backfill", "earthwork", "fill", "clearing", "compaction", "soil",
    "concrete", "ready-mix", "rebar", "reinforce", "mesh", "formwork", "slab", "footing", "column", "beam",
    "brick", "block", "mortar", "plaster", "masonry", "cement", "sand", "aggregate", "stone",
    "truss", "sheeting", "ibr", "corrugated", "tiles", "gutter", "waterproofing", "flashing", "timber",
    "pipe", "pvc", "drain", "sewer", "tap", "valve", "geyser", "basin", "toilet", "sanitary",
    "cable", "wire", "conduit", "luminaire", "lighting", "distribution board", "db", "socket", "switch",
    "paint", "primer", "screed", "ceiling", "drywall", "door", "window", "glazing",
    "hardhat", "boots", "gloves", "ppe", "overalls",
    "tipper", "grader", "roller", "crane", "scaffolding", "generator", "tlb",
    "supply", "install", "construct", "lay", "testing", "survey", "investigat", "specialist", "provisional"
]

# Standard measurement units
MEASURABLE_UNITS = {
    "m2", "sqm", "m²", "rn2", "m3", "cum", "m³", "rn3", "m", "lm", "metres", "meter", "meters", "rn",
    "kg", "ton", "t", "tonne", "tonnes", "no", "nr", "ea", "each", "item", "units", "sum", "prov sum",
    "hr", "hrs", "hours", "day", "days", "week", "month", "ls", "lump sum",
    "ha", "km", "l", "litre", "litres", "pair", "pairs", "set", "sets", "roll", "rolls", "bag", "bags", "bay", "bays",
}


def clean_quantity_value(raw: object) -> float:
    """Parses raw quantity strings handling commas, spaces, currency symbols, and OCR artifacts."""
    if raw is None:
        return 1.0
    if isinstance(raw, (int, float)):
        return float(raw)

    val = str(raw).strip()
    if not val:
        return 1.0

    # OCR character normalization in numeric context: 'O'/'o' -> '0', 'l'/'I' -> '1'
    if any(c.isdigit() for c in val):
        val = re.sub(r'[oO]', '0', val)
        val = re.sub(r'\b[lI](?=\d)', '1', val)
        val = re.sub(r'(?<=\d)[lI]\b', '1', val)
        val = re.sub(r'(?<=[.,])[lI]', '1', val)
        val = re.sub(r'[lI](?=[.,])', '1', val)

    # Strip currency signs or common units from string (e.g. "R 1,500.00", "75m3")
    val = re.sub(r'^[R$€£\s]+', '', val)

    m = re.search(r'[-+]?\d+(?:[\s,.]\d+)*', val)
    if not m:
        return 1.0

    candidate = m.group(0).strip()
    candidate = re.sub(r'[.,\s]+$', '', candidate)

    # If both '.' and ',' exist
    if ',' in candidate and '.' in candidate:
        if candidate.rfind('.') > candidate.rfind(','):
            # Form: "1,250.50"
            candidate = candidate.replace(',', '').replace(' ', '')
        else:
            # Form: "1.250,50"
            candidate = candidate.replace('.', '').replace(' ', '').replace(',', '.')
    elif ',' in candidate:
        parts = candidate.split(',')
        if len(parts) > 2:
            candidate = candidate.replace(',', '').replace(' ', '')
        elif len(parts) == 2 and len(parts[1]) == 3:
            candidate = candidate.replace(',', '').replace(' ', '')
        else:
            candidate = candidate.replace(' ', '').replace(',', '.')
    elif ' ' in candidate:
        candidate = candidate.replace(' ', '')

    try:
        return float(candidate)
    except (ValueError, TypeError):
        return 1.0


def is_legal_or_narrative_noise(text: str) -> Tuple[bool, Optional[str]]:
    """Checks if a candidate text block matches known legal clauses, narrative boilerplate, or accounting noise."""
    cleaned = text.strip()
    if not cleaned or len(cleaned) < 4:
        return True, "Too short or empty candidate"
    
    cleaned_lower = cleaned.lower()
    for pattern, reason in LEGAL_AND_NARRATIVE_PATTERNS:
        if re.search(pattern, cleaned_lower, re.IGNORECASE):
            return True, f"Filtered: {reason}"
            
    return False, None


def is_text_corrupted(text: str, is_line_item: bool = False) -> Tuple[bool, float, str]:
    """Evaluates text quality and identifies garbled text, decoding artifacts, replacement characters,
    or non-printable byte-soup.
    
    Args:
        text: String content of document or line item.
        is_line_item: If True, evaluates a single line item description with strict per-item criteria.
                      If False, evaluates entire document text before segmentation/extraction.

    Returns:
        (is_corrupted: bool, corruption_ratio: float, reason: str)
    """
    if not text or not text.strip():
        if is_line_item:
            return True, 1.0, "Empty line item description"
        else:
            return True, 1.0, "Document contains no readable text (empty or scanned image without text layer)"

    clean_text = text.strip()
    total_len = len(clean_text)

    # 1. Check for Unicode replacement character (\ufffd / )
    replacement_count = clean_text.count("\ufffd")
    if is_line_item and replacement_count > 0:
        return True, round(replacement_count / max(1, total_len), 3), "Contains replacement characters (\ufffd) indicative of corrupted encoding"
    elif not is_line_item and replacement_count > 0:
        rep_ratio = replacement_count / max(1, total_len)
        if rep_ratio >= 0.02 or replacement_count >= 10:
            return True, round(rep_ratio, 3), f"Document contains {replacement_count} replacement characters (\ufffd) indicative of corrupted decoding"

    # 2. Check for null bytes (\x00)
    null_count = clean_text.count("\x00")
    if null_count > 0:
        return True, 1.0, "Contains null bytes (\x00) indicative of raw binary content"

    # 3. Check for non-printable control characters (excluding newline, cr, tab)
    control_chars = [c for c in clean_text if ord(c) < 32 and c not in ("\n", "\r", "\t")]
    if is_line_item and len(control_chars) > 0:
        return True, round(len(control_chars) / max(1, total_len), 3), "Contains unprintable control characters"
    elif not is_line_item and len(control_chars) > 0:
        ctrl_ratio = len(control_chars) / max(1, total_len)
        if ctrl_ratio >= 0.03 or len(control_chars) >= 15:
            return True, round(ctrl_ratio, 3), f"Document contains {len(control_chars)} unprintable control characters"

    # 4. Check for PDF font / CID mapping corruption artifacts: e.g. (cid:120) or CID#451
    cid_matches = re.findall(r'\(cid:\d+\)|CID#\d+', clean_text)
    if is_line_item and len(cid_matches) > 0:
        return True, 0.9, "Contains unmapped PDF font CID characters (cid:...)"
    elif not is_line_item and len(cid_matches) >= 3:
        return True, 0.9, "Document contains unmapped PDF font CID characters (cid:...) indicative of missing font encodings"

    # 5. Check for PK zip header or binary archive signatures decoded into string
    if clean_text.startswith("PK\x03\x04") or "[Content_Types].xml" in clean_text:
        return True, 1.0, "Raw ZIP / Office binary archive content decoded as plain text"

    # 6. Alphanumeric & Word Density Sanity Check
    words = re.findall(r'[a-zA-Z]{2,}', clean_text)
    alpha_chars = sum(1 for c in clean_text if c.isalnum() or c in " \t\n\r")
    alpha_ratio = alpha_chars / max(1, total_len)

    if is_line_item:
        if total_len >= 5 and len(words) == 0:
            return True, 1.0, "Description contains no recognizable text words"
        if total_len > 8 and alpha_ratio < 0.40:
            return True, round(1.0 - alpha_ratio, 3), "High concentration of random symbols or unreadable characters"
    else:
        # Document-level check
        if total_len < 20:
            return True, 1.0, "Document text is too short (< 20 characters) — likely a scanned image with no text layer"
        if total_len >= 40 and len(words) < 3:
            return True, 1.0, "Document contains fewer than 3 recognizable words — likely corrupted or image-only"
        if total_len >= 60 and alpha_ratio < 0.45:
            return True, round(1.0 - alpha_ratio, 3), "Document content has abnormal symbol density indicative of corrupted binary data"

    return False, 0.0, ""


def classify_candidate_line_item(
    description: Optional[str] = None,
    unit: Optional[str] = None,
    quantity: Optional[float] = None,
    raw_reference: Optional[str] = None,
    section_name: Optional[str] = None,
    raw_text: Optional[str] = None,
    category: Optional[str] = None,
) -> Tuple[bool, float, str, Optional[str]]:
    """Two-stage candidate classifier:
    1. Runs garbage-text and noise detection to eliminate unreadable content or clauses.
    2. Calculates a genuine, nuanced confidence score reflecting specific item attributes.
    3. Assigns review_status ('accepted' | 'needs_review' | 'excluded').
    4. Returns exclusion or review reason if applicable.
    """
    desc_val = raw_text if raw_text is not None else (description or "")
    desc_clean = desc_val.strip()

    # 1. Check for corrupted / garbage text
    is_corrupted, ratio, corrupt_reason = is_text_corrupted(desc_clean, is_line_item=True)
    if is_corrupted:
        return False, 0.05, "excluded", f"Corrupted text: {corrupt_reason}"
    
    # 2. Check explicit noise / narrative / legal patterns
    is_noise, noise_reason = is_legal_or_narrative_noise(desc_clean)
    if is_noise:
        return False, 0.15, "excluded", noise_reason
    
    # 3. Check if the description is merely a heading (e.g. "CONCRETE, FORMWORK & REBAR")
    if re.match(r'^(?:bill\s+no\.?\s*\d+|section\s+[a-z0-9]+|part\s+\d+)[\s:\-–]*$', desc_clean, re.I):
        return False, 0.10, "excluded", "Section/Bill header line"

    # 4. Deterministic scoring heuristics
    score = 0.50  # baseline
    
    unit_clean = (unit or "").strip().lower()
    has_valid_unit = unit_clean in MEASURABLE_UNITS
    has_distinct_qty = quantity is not None and quantity > 0 and quantity != 1.0
    is_default_qty = quantity == 1.0
    
    desc_lower = desc_clean.lower()
    has_trade_keyword = any(kw in desc_lower for kw in GENUINE_TRADE_KEYWORDS)
    if section_name:
        has_trade_keyword = has_trade_keyword or any(kw in section_name.lower() for kw in GENUINE_TRADE_KEYWORDS)
    
    # Unit contribution
    if has_valid_unit:
        score += 0.12
    else:
        score -= 0.12
        
    # Quantity contribution
    if has_distinct_qty:
        score += 0.10
    elif is_default_qty:
        if unit_clean in ("sum", "item", "ls", "lump sum", "prov sum"):
            score += 0.04
        elif unit_clean in ("m3", "m2", "ton", "kg", "m"):
            score -= 0.06  # Suspicious: bulk excavation or concrete with default qty 1.0
        
    # Trade keyword contribution
    if has_trade_keyword:
        score += 0.10
    else:
        score -= 0.12

    # Technical specification patterns (dimensions, ratings, SANS standards)
    has_tech_spec = bool(re.search(r'\b(?:\d+(?:\.\d+)?\s*(?:mm|m|mpa|class\s*\d+|kg|ton|dia|v|w|kva|cem\s*[a-z0-9]+)|sans\s*\d+|sabs)\b', desc_lower))
    if has_tech_spec:
        score += 0.08

    # Source reference contribution
    if raw_reference and re.match(r'^(?:[A-Za-z0-9]+\.)?\d+(?:\.\d+)*$', raw_reference.strip()):
        score += 0.05

    # Description length nuance
    desc_len = len(desc_clean)
    if 40 <= desc_len <= 180:
        score += 0.08
    elif 15 <= desc_len < 40:
        score += 0.03
    elif desc_len < 12:
        score -= 0.15
    elif desc_len > 220:
        score -= 0.10

    # Penalize narrative sentences ending with periods or legal modal verbs
    if any(w in desc_lower for w in ["shall", "must", "required to", "subject to", "in accordance with", "contractor is advised"]):
        score -= 0.25

    # Penalize single-word non-measurable items (e.g. "however", "notes")
    words = desc_clean.split()
    if len(words) <= 2 and not has_valid_unit and not has_trade_keyword:
        score -= 0.35

    # Clamp confidence
    final_confidence = round(max(0.10, min(0.98, score)), 2)
    
    high_thresh = getattr(settings, "parser_high_confidence_threshold", 0.80)
    low_thresh = getattr(settings, "parser_low_confidence_threshold", 0.50)
    
    if final_confidence >= high_thresh:
        return True, final_confidence, "accepted", None
    elif final_confidence >= low_thresh:
        return True, final_confidence, "needs_review", "Ambiguous item — verify description, unit or quantity"
    else:
        return False, final_confidence, "excluded", "Low confidence non-priceable candidate"


def segment_document_text(text: str) -> Tuple[List[str], List[dict]]:
    """Pre-processes raw document text into:
    1. Structured / Priceable candidates for extraction
    2. Excluded narrative blocks with reason
    """
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    structured_candidates = []
    excluded_candidates = []
    
    for line in lines:
        is_corrupted, _, corrupt_reason = is_text_corrupted(line, is_line_item=True)
        if is_corrupted:
            excluded_candidates.append({"text": line, "reason": f"Corrupted text: {corrupt_reason}"})
            continue

        is_noise, reason = is_legal_or_narrative_noise(line)
        if is_noise:
            excluded_candidates.append({"text": line, "reason": reason})
        else:
            structured_candidates.append(line)
            
    return structured_candidates, excluded_candidates
