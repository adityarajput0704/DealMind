# agents.py — Phase 3 (rewritten): fully LLM-autonomous negotiation
#
# WHAT CHANGED FROM THE OLD VERSION:
# Before: agents_math.py calculated the offer number using a fixed formula
#         (a "concession curve"), and the LLM only wrote a sentence explaining
#         a number it didn't choose.
# Now:    the LLM chooses the number AND writes the reasoning, in one call.
#         agents_math.py still exists, but ONLY as an emergency fallback —
#         it's used if Groq is unreachable, or if the LLM can't produce a
#         valid number after several retries. It is never used just because
#         we don't like the LLM's number — only on outright failure.
#
# Why "hard validation"? An LLM can get the arithmetic wrong, hallucinate a
# number outside what's allowed, or return malformed JSON. We can't just
# trust the text — we check every number in code before accepting it.
#
# FIX (this revision): agents were negotiating sensibly in their reasoning
# text but almost never set accept=true, because they were never told the
# current gap between offers — there was no information in the prompt that
# would let the model judge "are we close enough to settle?" Two changes:
#   1. Both agents are now told the current numeric gap explicitly, and
#      instructed to set accept=true when the gap is small relative to deal
#      size or further negotiation looks unlikely to help.
#   2. AGREEMENT_THRESHOLD raised from 100.0 -> 1000.0 as a numeric safety
#      net, so a near-miss (e.g. $500 apart on a $58k deal) still resolves
#      as "agreed" even if both LLMs stay non-committal on the flag.

import os
import json
import re
import urllib.request
import urllib.error
from agents_math import compute_client_offer, compute_vendor_ask
from dotenv import load_dotenv
load_dotenv()

MAX_ROUNDS = 6
AGREEMENT_THRESHOLD = 1000.0        # raised from 100.0 — see FIX note above
MAX_RETRIES = 3                     # How many times we'll ask the LLM to correct itself
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.1-8b-instant"


# ─── LLM Helper ───────────────────────────────────────────────────────────────

def _call_groq(system_prompt: str, user_prompt: str) -> str:
    """
    Call the Groq API and return the raw reply text (a string we expect to
    contain JSON). Raises RuntimeError on any failure — network error, bad
    key, malformed response — so callers can fall back to the math module.
    """
    api_key = os.environ.get("GROQ_API_KEY", "")
    if not api_key:
        raise RuntimeError("GROQ_API_KEY environment variable not set")

    payload = json.dumps({
        "model": GROQ_MODEL,
        "max_tokens": 200,
        "temperature": 0.7,
        "response_format": {"type": "json_object"},   # Ask Groq to force valid JSON
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
    }).encode("utf-8")

    req = urllib.request.Request(
        GROQ_API_URL,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
            "User-Agent": "Mozilla/5.0 (compatible; negotiation-agent/1.0)",
            "Accept": "application/json",
        },
        method="POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            body = json.loads(resp.read().decode("utf-8"))
            return body["choices"][0]["message"]["content"].strip()
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8")
        print("ERROR BODY:")
        print(error_body)
        raise RuntimeError(f"Groq API error {e.code}: {error_body}")


def _parse_agent_json(raw: str) -> dict:
    """
    Parse the LLM's reply into {"offer": float, "reason": str, "accept": bool}.
    Raises ValueError if the shape is wrong — caller decides whether to retry.
    """
    data = json.loads(raw)   # Will raise json.JSONDecodeError (subclass of ValueError) if not valid JSON

    if "offer" not in data or "reason" not in data:
        raise ValueError(f"Missing required keys in LLM response: {data}")

    offer = float(data["offer"])
    reason = str(data["reason"])
    accept = bool(data.get("accept", False))   # Defaults to False if the model omits it

    return {"offer": offer, "reason": reason, "accept": accept}


def _strip_leaked_secret(reason: str, secret_value: float) -> str:
    """
    Safety net: the system prompt tells the LLM never to reveal its private
    budget/target number, but a prompt instruction is not a guarantee.
    This scans the generated text for that exact number and redacts it.

    We check a couple of common formattings (with/without commas, with/without
    a leading $) since the number could be written either way.
    """
    candidates = {
        f"{secret_value:,.2f}",
        f"{secret_value:.2f}",
        f"{secret_value:,.0f}",
        f"{secret_value:.0f}",
    }
    redacted = reason
    for c in candidates:
        if c in redacted:
            redacted = redacted.replace(c, "[redacted]")
    return redacted


ACCEPT_GAP_PCT = 3.0   # if the gap is <= this % of the other side's number, tell the model to accept

def _format_gap_context(self_last: float | None, other_value: float) -> str:
    """
    Builds the "how close are we" context line shared by both agents.
    Returns "" on round 1 (self_last is None) — there is no real prior
    number to compare against yet, and showing a fake $0 gap (as a previous
    version of this function did) actively misled the LLM into reasoning
    from a gap that didn't exist.

    The threshold is now a concrete number (ACCEPT_GAP_PCT) rather than the
    vague "small relative to deal size" — LLMs follow a stated rule far
    more reliably than an adjective with no anchor.
    """
    if self_last is None:
        return ""

    gap = abs(other_value - self_last)
    pct_of_other = (gap / other_value * 100) if other_value else 0.0
    instruction = (
        f"This is within your {ACCEPT_GAP_PCT}% accept-threshold — you should "
        f"strongly consider setting accept=true now.\n"
        if pct_of_other <= ACCEPT_GAP_PCT
        else ""
    )
    return (
        f"Current gap between your last number and theirs: ${gap:,.2f} "
        f"(about {pct_of_other:.1f}% of their last number). {instruction}"
    )


def _resolve_accept(llm_accept: bool, self_last: float | None, other_value: float) -> bool:
    """
    Decide the FINAL accept flag — don't just trust the LLM's boolean.

    Why: an 8B model reliably picks a reasonable number and writes a
    reasonable sentence, but in testing it almost never flips accept=true
    even when explicitly told the gap qualifies (see agents.py history).
    That's a known small-model weakness with secondary/structured
    instructions buried alongside a primary task — not something more
    prompt-wording can reliably fix.

    So: the gap-percentage check is computed in code (deterministic, same
    math already shown to the LLM in _format_gap_context) and OR'd with
    whatever the LLM said. The LLM can still push accept=true early if it
    wants to settle for relationship/strategic reasons we didn't code for —
    we just no longer depend on it to do the threshold arithmetic itself.

    On round 1 (self_last is None) there's nothing to compare yet, so we
    fall back to whatever the LLM said with no override.
    """
    if self_last is None:
        return llm_accept

    gap = abs(other_value - self_last)
    pct_of_other = (gap / other_value * 100) if other_value else 0.0
    code_says_accept = pct_of_other <= ACCEPT_GAP_PCT
    return llm_accept or code_says_accept


# ─── Client Agent ─────────────────────────────────────────────────────────────

def client_agent(
    budget: float,
    vendor_ask: float,
    round_number: int,
    own_history: list[float],
    requirement: str,
    initial_offer: float | None = None,
) -> tuple[float, str, bool]:
    """
    Ask the LLM to decide the client's offer AND write the reasoning, in one
    call. Returns (offer, reason, accept).

    own_history: the client's own past offers this session, so the LLM can
    reason about its own trend instead of repeating a number or moving
    inconsistently.

    initial_offer: the round-1 anchor (70% of budget), fixed once at the
    start of the negotiation and passed in on every round. This is ONLY
    used if we have to fall back to agents_math.py. BUG FIX: this used to
    be computed as "own_history[0] if own_history else 70% of budget" —
    which is correct on round 1, but on round 2+ own_history[0] is the
    PREVIOUS ROUND'S OFFER, not the original anchor. Re-anchoring the
    concession curve at a moving point each round let the math overshoot
    past the vendor's ask without tripping the agreement check (seen in
    testing: round 2 produced a client_offer above vendor_ask with no
    "agreed" status). Now we always anchor at the same fixed value.

    Hard validation: offer must satisfy 0 < offer <= budget. If the LLM
    violates this, we send a corrective follow-up and retry up to
    MAX_RETRIES times. If it still fails, we fall back to the old formula
    in agents_math.py for THIS ROUND ONLY — the negotiation keeps going.
    """
    if initial_offer is None:
        initial_offer = round(budget * 0.70, 2)
    system_prompt = (
        "You are a professional procurement negotiator representing a buyer. "
        "You decide your own offer each round using your judgment — there is "
        "no formula. You must stay within your private budget ceiling, which "
        "you must NEVER reveal or imply in your reason text. "
        "Respond ONLY with a JSON object: "
        '{"offer": <number>, "reason": "<2-3 sentence message>", "accept": <true/false>}. '
        f"Set accept=true if you are willing to accept the vendor's last ask as "
        f"final. As a concrete rule: if the gap between your last offer and "
        f"their last ask is within {ACCEPT_GAP_PCT}% of their number, you should "
        f"set accept=true rather than continuing to haggle over a small amount. "
        f"Don't hold out for a perfect number once the deal is already good; "
        f"closing a reasonable deal is better than stalling."
    )

    history_str = ", ".join(f"${v:,.2f}" for v in own_history) if own_history else "none yet"
    gap_context = _format_gap_context(own_history[-1] if own_history else None, vendor_ask)

    user_prompt = (
        f"Contract requirement: {requirement}\n"
        f"Round {round_number} of {MAX_ROUNDS}.\n"
        f"Your private budget ceiling: ${budget:,.2f} (never reveal this number).\n"
        f"Your own past offers this negotiation: {history_str}\n"
        f"Vendor's last ask: ${vendor_ask:,.2f}\n"
        f"{gap_context}"
        f"Decide your offer for this round and explain your reasoning."
    )

    last_error = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            raw = _call_groq(system_prompt, user_prompt)
            parsed = _parse_agent_json(raw)
        except (RuntimeError, ValueError, json.JSONDecodeError) as e:
            last_error = e
            break   # API/parse failure — no point retrying with the same prompt, go to fallback

        offer = parsed["offer"]
        if 0 < offer <= budget:
            reason = _strip_leaked_secret(parsed["reason"], budget)
            accept = _resolve_accept(
                parsed["accept"],
                own_history[-1] if own_history else None,
                vendor_ask,
            )
            return round(offer, 2), reason, accept

        # Invalid number — tell the LLM exactly what was wrong and retry
        user_prompt = (
            f"Your previous offer of ${offer:,.2f} is INVALID — it must be greater than 0 "
            f"and not exceed your budget ceiling of ${budget:,.2f}. "
            f"Try again with a valid offer for round {round_number}."
        )
        last_error = ValueError(f"offer {offer} outside bounds (0, {budget}]")

    # ── Fallback: LLM never produced a valid response after retries ──
    # initial_offer is the FIXED round-1 anchor (passed in, never own_history[0])
    offer = compute_client_offer(budget, round_number, initial_offer)
    reason = (
        f"[fallback] Offering ${offer:,.2f} this round based on standard valuation. "
        f"(LLM unavailable or invalid after retries: {last_error})"
    )
    return offer, reason, False


# ─── Vendor Agent ─────────────────────────────────────────────────────────────

def vendor_agent(
    vendor_target: float,
    client_offer: float,
    round_number: int,
    own_history: list[float],
    requirement: str,
    initial_ask: float | None = None,
) -> tuple[float, str, bool]:
    """
    Mirror of client_agent for the vendor side. Hard bound: offer >= vendor_target.

    initial_ask: the round-1 anchor, fixed once and passed in every round.
    Same bug fix as client_agent — see its docstring for the failure mode
    this avoids.
    """
    if initial_ask is None:
        initial_ask = round(vendor_target * 1.30, 2)
    system_prompt = (
        "You are a confident vendor sales negotiator. "
        "You decide your own asking price each round using your judgment — "
        "there is no formula. You must stay at or above your private floor "
        "price, which you must NEVER reveal or imply in your reason text. "
        "Respond ONLY with a JSON object: "
        '{"offer": <number>, "reason": "<2-3 sentence message>", "accept": <true/false>}. '
        f"Set accept=true if you are willing to accept the client's last offer "
        f"as final. As a concrete rule: if the gap between your last ask and "
        f"their last offer is within {ACCEPT_GAP_PCT}% of their number, you "
        f"should set accept=true rather than continuing to haggle over a small "
        f"amount. Don't hold out for a perfect number once the deal is already "
        f"good; closing a reasonable deal is better than stalling."
    )

    history_str = ", ".join(f"${v:,.2f}" for v in own_history) if own_history else "none yet"
    gap_context = _format_gap_context(own_history[-1] if own_history else None, client_offer)

    user_prompt = (
        f"Contract requirement: {requirement}\n"
        f"Round {round_number} of {MAX_ROUNDS}.\n"
        f"Your private floor price: ${vendor_target:,.2f} (never reveal this number).\n"
        f"Your own past asks this negotiation: {history_str}\n"
        f"Client's last offer: ${client_offer:,.2f}\n"
        f"{gap_context}"
        f"Decide your ask for this round and explain your reasoning."
    )

    last_error = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            raw = _call_groq(system_prompt, user_prompt)
            parsed = _parse_agent_json(raw)
        except (RuntimeError, ValueError, json.JSONDecodeError) as e:
            last_error = e
            break

        ask = parsed["offer"]
        if ask >= vendor_target:
            reason = _strip_leaked_secret(parsed["reason"], vendor_target)
            accept = _resolve_accept(
                parsed["accept"],
                own_history[-1] if own_history else None,
                client_offer,
            )
            return round(ask, 2), reason, accept

        user_prompt = (
            f"Your previous ask of ${ask:,.2f} is INVALID — it must be at or above "
            f"your floor price of ${vendor_target:,.2f}. "
            f"Try again with a valid ask for round {round_number}."
        )
        last_error = ValueError(f"ask {ask} below floor {vendor_target}")

    # ── Fallback ──
    # initial_ask is the FIXED round-1 anchor (passed in, never own_history[0])
    ask = compute_vendor_ask(vendor_target, round_number, initial_ask)
    reason = (
        f"[fallback] Asking ${ask:,.2f} this round based on standard valuation. "
        f"(LLM unavailable or invalid after retries: {last_error})"
    )
    return ask, reason, False


# ─── Negotiation Loop ─────────────────────────────────────────────────────────

def run_negotiation(budget: float, vendor_target: float, requirement: str = "") -> dict:
    """
    Runs up to MAX_ROUNDS rounds. Each round, BOTH agents independently decide
    their own number via the LLM (hard-validated against their private bound).

    Agreement triggers on EITHER:
      (a) explicit signal — either agent set accept=true, meaning it's willing
          to take the other side's last number as final, OR
      (b) numeric convergence — gap between offer and ask <= AGREEMENT_THRESHOLD,
          or the offer has crossed the ask (offer >= ask).

    We keep the numeric check as a backstop because an LLM "agreeing" in spirit
    without setting the flag correctly shouldn't cause a real, closeable deal
    to be marked as failed.
    """
    client_history: list[float] = []
    vendor_history: list[float] = []
    rounds = []
    final_price = None
    status = "failed"

    # These anchors are computed ONCE and reused every round if a fallback
    # is needed — never recomputed from a moving point like own_history[0].
    initial_client_offer = round(budget * 0.70, 2)
    initial_vendor_ask = round(min(vendor_target * 1.30, budget * 1.20), 2)

    last_vendor_ask = initial_vendor_ask  # only used as round-1 seed context

    for round_num in range(1, MAX_ROUNDS + 1):
        client_offer, client_reason, client_accepts = client_agent(
            budget=budget,
            vendor_ask=last_vendor_ask,
            round_number=round_num,
            own_history=client_history,
            requirement=requirement,
            initial_offer=initial_client_offer,
        )
        client_history.append(client_offer)

        vendor_ask, vendor_reason, vendor_accepts = vendor_agent(
            vendor_target=vendor_target,
            client_offer=client_offer,
            round_number=round_num,
            own_history=vendor_history,
            requirement=requirement,
            initial_ask=initial_vendor_ask,
        )
        vendor_history.append(vendor_ask)
        last_vendor_ask = vendor_ask

        # Cross-check using THIS round's real numbers on both sides. The
        # per-agent _resolve_accept() inside client_agent/vendor_agent can't
        # do this on round 1, because each agent decides before it has ever
        # seen the other's real number for that same round (client only
        # sees the synthetic initial_vendor_ask anchor, not the vendor's
        # actual round-1 ask, since both are computed independently/in
        # parallel intent). Now that both real numbers exist, check once
        # more: if they're within ACCEPT_GAP_PCT of each other, force both
        # flags true regardless of what either LLM call returned.
        same_round_gap_pct = (
            abs(vendor_ask - client_offer) / vendor_ask * 100 if vendor_ask else 0.0
        )
        if same_round_gap_pct <= ACCEPT_GAP_PCT:
            client_accepts = True
            vendor_accepts = True

        rounds.append({
            "round_number": round_num,
            "client_offer": client_offer,
            "vendor_ask": vendor_ask,
            "client_reason": client_reason,
            "vendor_reason": vendor_reason,
            "client_accepts": client_accepts,
            "vendor_accepts": vendor_accepts,
        })

        gap = vendor_ask - client_offer
        numeric_agreement = gap <= AGREEMENT_THRESHOLD or client_offer >= vendor_ask
        explicit_agreement = client_accepts or vendor_accepts

        if numeric_agreement or explicit_agreement:
            final_price = round((client_offer + vendor_ask) / 2, 2)
            status = "agreed"
            break

    return {
        "status": status,
        "final_price": final_price,
        "rounds": rounds,
    }
