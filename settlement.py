# settlement.py
#
# The Settlement Agent reads a completed negotiation session and produces
# a structured Final Agreement. No LLM calls — pure deterministic logic.
#
# Responsibilities:
#   1. Validate the session is actually agreed (not failed/open)
#   2. Validate final_price is within both parties' original bounds
#   3. Derive timeline and terms from contract_type + price
#   4. Return a structured dict ready to be saved as a FinalAgreement row


# ─── Timeline Rules ───────────────────────────────────────────────────────────
# Estimated delivery days based on contract type and price tier.
# These are simple lookup rules — easy to extend later.

TIMELINE_RULES = {
    "software_development": [(5000, 30), (15000, 60), (50000, 90), (float("inf"), 120)],
    "consulting":           [(3000, 10), (10000, 20), (30000, 45), (float("inf"), 60)],
    "saas_license":         [(2000,  7), (10000, 14), (50000, 30), (float("inf"), 45)],
    "design":               [(2000, 14), (8000,  30), (20000, 45), (float("inf"), 60)],
    "data_engineering":     [(5000, 21), (20000, 45), (60000, 90), (float("inf"), 120)],
}
DEFAULT_TIMELINE = [(5000, 21), (20000, 45), (float("inf"), 90)]


def _estimate_timeline(contract_type: str, price: float) -> int:
    """Return estimated delivery days based on contract type and price."""
    rules = TIMELINE_RULES.get(contract_type.lower(), DEFAULT_TIMELINE)
    for threshold, days in rules:
        if price <= threshold:
            return days
    return 90  # safe fallback


# ─── Terms Generator ──────────────────────────────────────────────────────────

def _generate_terms(contract_type: str, final_price: float, timeline_days: int) -> list[str]:
    """
    Produce a list of plain-English contract terms based on the deal parameters.
    These are deterministic — same inputs always produce the same terms.
    """
    # Payment schedule depends on deal size
    if final_price <= 5000:
        payment_terms = "50% upfront, 50% on delivery."
    elif final_price <= 20000:
        payment_terms = "30% upfront, 40% at midpoint, 30% on delivery."
    else:
        payment_terms = "25% upfront, 25% at design sign-off, 25% at UAT, 25% on delivery."

    # Revision rounds depend on contract type
    revision_map = {
        "software_development": "Two rounds of revisions included post-delivery.",
        "consulting": "One round of revisions to the final report included.",
        "saas_license": "License covers up to 3 configuration change requests per quarter.",
        "design": "Three rounds of design revisions included.",
        "data_engineering": "Two rounds of pipeline adjustments included post-delivery.",
    }
    revisions = revision_map.get(contract_type.lower(), "One round of revisions included.")

    terms = [
        f"Agreed price: ${final_price:,.2f} ({contract_type.replace('_', ' ').title()}).",
        f"Delivery timeline: {timeline_days} calendar days from contract signing.",
        payment_terms,
        revisions,
        "Any scope changes after signing require a written change order and may affect price and timeline.",
        "Confidentiality: both parties agree to keep the terms of this agreement private.",
        "Governing law: disputes resolved by binding arbitration under applicable commercial law.",
    ]

    return terms


# ─── Validation ───────────────────────────────────────────────────────────────

def _validate_price(final_price: float, budget: float, vendor_target: float) -> tuple[bool, str | None]:
    """
    Check that the final price sits within the legitimate negotiation zone.

    Valid range: [vendor_target, budget]
    - Below vendor_target → vendor agreed to something below their floor (suspicious)
    - Above budget       → client agreed to something above their ceiling (suspicious)

    Returns (is_valid, reason_if_invalid)
    """
    if final_price < vendor_target:
        return False, (
            f"Final price ${final_price:,.2f} is below vendor's stated target "
            f"${vendor_target:,.2f}. Agreement may be invalid."
        )
    if final_price > budget:
        return False, (
            f"Final price ${final_price:,.2f} exceeds client's stated budget "
            f"${budget:,.2f}. Agreement may be invalid."
        )
    return True, None


# ─── Main Settlement Function ─────────────────────────────────────────────────

def settle(
    session_id: int,
    session_status: str,
    contract_type: str,
    final_price: float,
    budget: float,
    vendor_target: float,
) -> dict:
    """
    Produce a structured Final Agreement from a completed negotiation.

    Args:
        session_id:      The NegotiationSession id
        session_status:  Must be "agreed" — we reject anything else
        contract_type:   From the Deal (e.g. "software_development")
        final_price:     The price both agents converged on
        budget:          Client's original max (from Deal)
        vendor_target:   Vendor's original floor (from Deal)

    Returns a dict ready to be saved as a FinalAgreement DB row.
    Raises ValueError for invalid inputs so the endpoint can return a clean 400.
    """
    # Guard: only settle agreed sessions
    if session_status != "agreed":
        raise ValueError(
            f"Session {session_id} has status '{session_status}'. "
            "Only agreed sessions can be settled."
        )

    # Guard: final_price must exist
    if final_price is None:
        raise ValueError(f"Session {session_id} has no final price recorded.")

    # Validate price is within bounds
    is_valid, invalidation_reason = _validate_price(final_price, budget, vendor_target)

    # Derive timeline and terms
    timeline_days = _estimate_timeline(contract_type, final_price)
    terms = _generate_terms(contract_type, final_price, timeline_days)

    return {
        "session_id":          session_id,
        "contract_type":       contract_type,
        "final_price":         final_price,
        "timeline_days":       timeline_days,
        "terms":               terms,           # list — main.py will JSON-encode before saving
        "status":              "agreed",
        "is_valid":            str(is_valid).lower(),
        "invalidation_reason": invalidation_reason,
    }