# agents_math.py
#
# IMPORTANT: this is no longer the primary way offers are computed.
# As of the LLM-autonomous rewrite, agents.py asks the LLM to choose every
# number using its own judgment. This file is kept ONLY as an emergency
# fallback for two situations:
#   1. The Groq API call fails outright (network error, bad key, etc.)
#   2. The LLM returns an invalid number 3 times in a row even after retries
#
# In both cases we need *something* to keep the negotiation moving instead
# of crashing the whole session — that's all this file is for now.

CONCESSION_RATE = 0.6


def compute_client_offer(budget: float, round_number: int, initial_offer: float) -> float:
    """
    Client moves UP from initial_offer toward budget.
    Returns a value in [initial_offer, budget], rounded to 2 decimal places.

    Example: budget=10000, initial=7000, round 1:
      fraction = 1 - 0.6^1 = 0.40
      gap = 10000 - 7000 = 3000
      offer = 7000 + 3000 * 0.40 = $8,200
    """
    fraction = 1 - (CONCESSION_RATE ** round_number)
    gap = budget - initial_offer
    offer = initial_offer + gap * fraction
    return round(min(offer, budget), 2)


def compute_vendor_ask(vendor_target: float, round_number: int, initial_ask: float) -> float:
    """
    Vendor moves DOWN from initial_ask toward vendor_target.
    Returns a value in [vendor_target, initial_ask], rounded to 2 decimal places.

    Example: target=7000, initial_ask=9100, round 1:
      fraction = 1 - 0.6^1 = 0.40
      gap = 9100 - 7000 = 2100
      ask = 9100 - 2100 * 0.40 = $8,260
    """
    fraction = 1 - (CONCESSION_RATE ** round_number)
    gap = initial_ask - vendor_target
    ask = initial_ask - gap * fraction
    return round(max(ask, vendor_target), 2)