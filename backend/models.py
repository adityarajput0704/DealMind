# models.py
#
# Each class here = one table in the database.
# Each class attribute with "Column(...)" = one column in that table.
#
# Think of it like this:
#   class Deal  →  CREATE TABLE deals (...)
#   id = Column(Integer, primary_key=True)  →  id INTEGER PRIMARY KEY

from sqlalchemy import Column, Integer, Float, String, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime, timezone

from database import Base


class Deal(Base):
    """
    Represents a business deal that agents will negotiate over.

    Schema choices explained:
    - contract_type (String): e.g. "software_development", "consulting", "saas_license"
      We use String (not an enum) to keep it flexible at this stage.
    - budget (Float): The CLIENT's maximum — they don't want to pay more than this.
    - vendor_target (Float): The VENDOR's ideal price — they want to get paid at least this.
      These two numbers define the "negotiation zone". If budget < vendor_target, 
      a deal is impossible from the start (we handle this at deal-creation time).
    - requirement (Text): Free-form description of what's being bought/sold.
      Text vs String: String has a length limit, Text does not. Good for descriptions.
    - status: Tracks the deal lifecycle. Starts as "open", becomes "negotiating",
      then "agreed" or "failed".
    """
    __tablename__ = "deals"

    id = Column(Integer, primary_key=True, index=True)
    contract_type = Column(String, nullable=False)
    budget = Column(Float, nullable=False)           # Client's max
    vendor_target = Column(Float, nullable=False)    # Vendor's floor/ideal
    requirement = Column(Text, nullable=False)
    status = Column(String, default="open")          # open | negotiating | agreed | failed

    # "relationship" lets us do deal.sessions to get all sessions for this deal.
    # It's a Python-level convenience — not a real DB column.
    # back_populates="deal" means the Session model also knows about this link.
    sessions = relationship("NegotiationSession", back_populates="deal")


class NegotiationSession(Base):
    """
    One negotiation attempt for a deal. A deal could theoretically have
    multiple sessions (e.g. first attempt failed, retry later) — that's why
    it's a separate table instead of just columns on Deal.

    - deal_id: Foreign key linking back to the Deal table.
      ForeignKey("deals.id") means "this must match an existing id in the deals table".
    - status: open → in_progress → agreed | failed
    """
    __tablename__ = "negotiation_sessions"

    id = Column(Integer, primary_key=True, index=True)
    deal_id = Column(Integer, ForeignKey("deals.id"), nullable=False)
    status = Column(String, default="open")          # open | in_progress | agreed | failed
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    deal = relationship("Deal", back_populates="sessions")
    rounds = relationship("Round", back_populates="session")


class Round(Base):
    """
    One round of negotiation — client makes an offer, vendor responds with an ask.
    We store BOTH sides' moves in a single row per round for easy querying.

    - round_number: 1-indexed (Round 1, Round 2, ..., max Round 6)
    - client_offer: What the client is willing to pay THIS round
    - vendor_ask: What the vendor is asking for THIS round
    - client_reason / vendor_reason: Text explanation of why they offered that number.
      Now LLM-generated freely (not explaining a pre-computed formula result).
    - client_accepts / vendor_accepts (NEW): the LLM can now explicitly say
      "I'm willing to accept the other side's last number as final." This is
      a real signal we store, not just inferred from the numbers — useful for
      auditing WHY a deal closed (explicit agreement vs. numbers converging).
    - timestamp: When this round happened (useful for auditing/replay)

    Why store reasons? The whole point of the platform is to make negotiations
    transparent and auditable — you can replay exactly what each agent said and why.
    """
    __tablename__ = "rounds"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("negotiation_sessions.id"), nullable=False)
    round_number = Column(Integer, nullable=False)
    client_offer = Column(Float, nullable=False)
    vendor_ask = Column(Float, nullable=False)
    client_reason = Column(Text)
    vendor_reason = Column(Text)
    client_accepts = Column(Boolean, default=False, nullable=False)
    vendor_accepts = Column(Boolean, default=False, nullable=False)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    session = relationship("NegotiationSession", back_populates="rounds")


class FinalAgreement(Base):
    """
    The structured output produced by the Settlement Agent after a successful
    negotiation. Think of this as the "clean contract summary" — not the messy
    back-and-forth, just the final terms both sides agreed to.

    - session_id: 1-to-1 with NegotiationSession (one agreement per session)
    - final_price: The split-the-difference price from the last agreed round
    - timeline_days: Estimated delivery time, derived from contract_type + price
    - terms: JSON list of plain-English contract terms (stored as a JSON string)
    - is_valid: False if final_price falls outside budget/vendor_target bounds
    - invalidation_reason: Why it was flagged invalid, if applicable
    """
    __tablename__ = "final_agreements"

    id                   = Column(Integer, primary_key=True, index=True)
    session_id           = Column(Integer, ForeignKey("negotiation_sessions.id"), unique=True, nullable=False)
    contract_type        = Column(String, nullable=False)
    final_price          = Column(Float, nullable=False)
    timeline_days        = Column(Integer, nullable=False)
    terms                = Column(Text, nullable=False)   # JSON-encoded list of strings
    status               = Column(String, default="agreed")
    is_valid             = Column(String, default="true") # "true" | "false"
    invalidation_reason  = Column(Text, nullable=True)
    created_at           = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # On-chain proof — populated only after a successful write to Monad.
    # Since /settle now only succeeds if the chain write also succeeds,
    # these should always be filled in on any row that exists. They're
    # nullable anyway so existing rows from before this column existed
    # don't break, and so the DB schema doesn't silently assume chain
    # writes can never fail.
    chain_tx_hash        = Column(String, nullable=True)
    chain_block_number   = Column(Integer, nullable=True)
    agreement_hash        = Column(String, nullable=True)  # hex string of the on-chain hash

    session = relationship("NegotiationSession", backref="agreement")