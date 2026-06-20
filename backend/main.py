# main.py

from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from datetime import timezone

import models
from database import engine, get_db
from agents import run_negotiation
from dotenv import load_dotenv
load_dotenv()
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Agent Economy — Negotiation Platform",
    description="AI agents negotiate contracts on behalf of clients and vendors.",
    version="0.3.0"
)


# ─── Request / Response Schemas ───────────────────────────────────────────────

class DealCreate(BaseModel):
    contract_type: str = Field(..., example="software_development")
    budget: float = Field(..., gt=0, description="Client's maximum budget")
    vendor_target: float = Field(..., gt=0, description="Vendor's target/floor price")
    requirement: str = Field(..., example="Build a REST API with authentication")


class DealResponse(BaseModel):
    id: int
    contract_type: str
    budget: float
    vendor_target: float
    requirement: str
    status: str
    model_config = {"from_attributes": True}


class SessionResponse(BaseModel):
    id: int
    deal_id: int
    status: str
    created_at: str
    model_config = {"from_attributes": True}


class RoundOut(BaseModel):
    round_number: int
    client_offer: float
    vendor_ask: float
    client_reason: str
    vendor_reason: str
    client_accepts: bool
    vendor_accepts: bool
    model_config = {"from_attributes": True}


class NegotiationResult(BaseModel):
    session_id: int
    deal_id: int
    status: str                    # "agreed" or "failed"
    final_price: float | None      # None if failed
    rounds: list[RoundOut]
    summary: str                   # Human-readable one-liner


# ─── Deal Endpoints ───────────────────────────────────────────────────────────

@app.get("/")
def root():
    return {"message": "Agent Economy API is running", "docs": "/docs"}


@app.post("/deals", response_model=DealResponse, status_code=201)
def create_deal(deal_data: DealCreate, db: Session = Depends(get_db)):
    if deal_data.budget < deal_data.vendor_target:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Budget (${deal_data.budget:,.2f}) is less than vendor target "
                f"(${deal_data.vendor_target:,.2f}). Negotiation zone is empty."
            )
        )
    new_deal = models.Deal(
        contract_type=deal_data.contract_type,
        budget=deal_data.budget,
        vendor_target=deal_data.vendor_target,
        requirement=deal_data.requirement,
        status="open"
    )
    db.add(new_deal)
    db.commit()
    db.refresh(new_deal)
    return new_deal


@app.get("/deals/{deal_id}", response_model=DealResponse)
def get_deal(deal_id: int, db: Session = Depends(get_db)):
    deal = db.query(models.Deal).filter(models.Deal.id == deal_id).first()
    if not deal:
        raise HTTPException(status_code=404, detail=f"Deal {deal_id} not found")
    return deal


@app.get("/deals", response_model=list[DealResponse])
def list_deals(db: Session = Depends(get_db)):
    return db.query(models.Deal).all()


@app.post("/deals/{deal_id}/negotiate", response_model=SessionResponse, status_code=201)
def start_negotiation(deal_id: int, db: Session = Depends(get_db)):
    deal = db.query(models.Deal).filter(models.Deal.id == deal_id).first()
    if not deal:
        raise HTTPException(status_code=404, detail=f"Deal {deal_id} not found")
    if deal.status != "open":
        raise HTTPException(
            status_code=400,
            detail=f"Deal {deal_id} has status '{deal.status}' — only 'open' deals can start negotiation."
        )
    session = models.NegotiationSession(deal_id=deal_id, status="open")
    db.add(session)
    deal.status = "negotiating"
    db.commit()
    db.refresh(session)
    return {
        "id": session.id,
        "deal_id": session.deal_id,
        "status": session.status,
        "created_at": session.created_at.isoformat()
    }


# ─── Run Negotiation Endpoint ─────────────────────────────────────────────────

@app.post("/sessions/{session_id}/run", response_model=NegotiationResult)
def run_session(session_id: int, db: Session = Depends(get_db)):
    """
    Run the full negotiation for an existing session.

    Flow:
    1. Load the session + its deal from DB
    2. Call run_negotiation() — each round, both agents independently use
       the LLM to decide their own number + reasoning (see agents.py)
    3. Save every round to the Round table
    4. Update session status (agreed/failed)
    5. Update deal status to match
    6. Return the full round-by-round history + final result
    """
    session = db.query(models.NegotiationSession).filter(
        models.NegotiationSession.id == session_id
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

    if session.status not in ("open",):
        raise HTTPException(
            status_code=400,
            detail=f"Session {session_id} already has status '{session.status}'. Can only run 'open' sessions."
        )

    deal = db.query(models.Deal).filter(models.Deal.id == session.deal_id).first()

    session.status = "in_progress"
    db.commit()

    # ── Run the negotiation (LLM-autonomous, see agents.py) ──
    result = run_negotiation(
        budget=deal.budget,
        vendor_target=deal.vendor_target,
        requirement=deal.requirement,
    )

    # ── Persist every round to the DB ──
    db_rounds = []
    for r in result["rounds"]:
        db_round = models.Round(
            session_id=session_id,
            round_number=r["round_number"],
            client_offer=r["client_offer"],
            vendor_ask=r["vendor_ask"],
            client_reason=r["client_reason"],
            vendor_reason=r["vendor_reason"],
            client_accepts=r["client_accepts"],
            vendor_accepts=r["vendor_accepts"],
        )
        db.add(db_round)
        db_rounds.append(db_round)

    session.status = result["status"]          # "agreed" or "failed"
    deal.status = result["status"]

    db.commit()

    # ── Build a human-readable summary ──
    if result["status"] == "agreed":
        num_rounds = len(result["rounds"])
        summary = (
            f"Deal reached after {num_rounds} round{'s' if num_rounds > 1 else ''}. "
            f"Final price: ${result['final_price']:,.2f} "
            f"(client budget: ${deal.budget:,.2f}, vendor target: ${deal.vendor_target:,.2f})."
        )
    else:
        last = result["rounds"][-1]
        summary = (
            f"No agreement after {len(result['rounds'])} rounds. "
            f"Final gap: ${last['vendor_ask'] - last['client_offer']:,.2f} "
            f"(client's last offer: ${last['client_offer']:,.2f}, "
            f"vendor's last ask: ${last['vendor_ask']:,.2f})."
        )

    return {
        "session_id": session_id,
        "deal_id": deal.id,
        "status": result["status"],
        "final_price": result["final_price"],
        "rounds": result["rounds"],
        "summary": summary,
    }


@app.get("/sessions/{session_id}/rounds", response_model=list[RoundOut])
def get_rounds(session_id: int, db: Session = Depends(get_db)):
    """Fetch all saved rounds for a session — useful after the fact."""
    session = db.query(models.NegotiationSession).filter(
        models.NegotiationSession.id == session_id
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
    return session.rounds


# ─── Settlement Endpoint ──────────────────────────────────────────────────────

import json as _json
import time as _time
from settlement import settle as _settle
from contracts.accord_chain import record_agreement_on_chain, AccordChainError


class TermsOut(BaseModel):
    session_id:          int
    contract_type:       str
    final_price:         float
    timeline_days:       int
    terms:               list[str]
    status:              str
    is_valid:            str
    invalidation_reason: str | None
    created_at:          str
    chain_tx_hash:        str
    chain_block_number:   int
    agreement_hash:        str


@app.post("/sessions/{session_id}/settle", response_model=TermsOut, status_code=201)
def settle_session(session_id: int, db: Session = Depends(get_db)):
    """
    Run the Settlement Agent on a completed (agreed) negotiation session,
    then write the result to the Accord on-chain registry on Monad testnet.

    ATOMICITY: settlement is only considered to have happened if BOTH the
    off-chain (DB) and on-chain (Monad) writes succeed. If the chain write
    fails for any reason — Monad RPC unreachable, insufficient gas funds,
    contract rejects the write — NOTHING is committed to the DB. The
    negotiation session itself remains "agreed" and can be retried by
    calling this endpoint again later (the function is safe to retry: it
    checks for an existing FinalAgreement before doing any work).

    This is a deliberate choice, not an accident: a half-settled state
    (saved in our DB but never proven on-chain, or vice versa) would be
    worse than a clean failure the caller can retry.

    Flow:
    1. Load session + deal from DB
    2. Check session is "agreed" and not already settled
    3. Call settle() — pure logic, returns structured agreement dict
    4. Write the agreement to Monad — BLOCKS until confirmed or raises
    5. ONLY IF the chain write succeeded: save FinalAgreement row to DB
    6. Return the clean final agreement, including the on-chain proof
    """
    session = db.query(models.NegotiationSession).filter(
        models.NegotiationSession.id == session_id
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

    existing = db.query(models.FinalAgreement).filter(
        models.FinalAgreement.session_id == session_id
    ).first()
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Session {session_id} already has a final agreement (id={existing.id})."
        )

    deal = db.query(models.Deal).filter(models.Deal.id == session.deal_id).first()

    last_round = (
        db.query(models.Round)
        .filter(models.Round.session_id == session_id)
        .order_by(models.Round.round_number.desc())
        .first()
    )
    if not last_round:
        raise HTTPException(
            status_code=400,
            detail=f"Session {session_id} has no rounds — cannot settle a negotiation that never ran."
        )

    final_price = round((last_round.client_offer + last_round.vendor_ask) / 2, 2)

    # settle() raises ValueError if session.status isn't "agreed" — the
    # one off-chain validity check we need, before we spend any gas.
    try:
        result = _settle(
            session_id=session_id,
            session_status=session.status,
            contract_type=deal.contract_type,
            final_price=final_price,
            budget=deal.budget,
            vendor_target=deal.vendor_target,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # ── Write to Monad FIRST. If this raises, we return an error and
    #    commit NOTHING — the DB has no record of this settlement attempt. ──
    settlement_timestamp = int(_time.time())
    try:
        chain_result = record_agreement_on_chain(
            deal_id=deal.id,
            contract_type=result["contract_type"],
            final_price=result["final_price"],
            timestamp=settlement_timestamp,
        )
    except AccordChainError as e:
        raise HTTPException(
            status_code=502,
            detail=(
                f"Settlement was computed but NOT saved, because writing to "
                f"the Monad blockchain failed: {e}. No data was committed. "
                f"You can safely retry POST /sessions/{session_id}/settle "
                f"once the chain is reachable again."
            ),
        )

    # ── Chain write confirmed. Now, and only now, save to DB. ──
    agreement = models.FinalAgreement(
        session_id=session_id,
        contract_type=result["contract_type"],
        final_price=result["final_price"],
        timeline_days=result["timeline_days"],
        terms=_json.dumps(result["terms"]),
        status=result["status"],
        is_valid=result["is_valid"],
        invalidation_reason=result["invalidation_reason"],
        chain_tx_hash=chain_result["tx_hash"],
        chain_block_number=chain_result["block_number"],
        agreement_hash=chain_result["agreement_hash"],
    )
    db.add(agreement)
    db.commit()
    db.refresh(agreement)

    return {
        **result,
        "terms":              _json.loads(agreement.terms),
        "created_at":         agreement.created_at.isoformat(),
        "chain_tx_hash":       agreement.chain_tx_hash,
        "chain_block_number":  agreement.chain_block_number,
        "agreement_hash":       agreement.agreement_hash,
    }


@app.get("/sessions/{session_id}/agreement", response_model=TermsOut)
def get_agreement(session_id: int, db: Session = Depends(get_db)):
    """Fetch the final agreement for a session."""
    agreement = db.query(models.FinalAgreement).filter(
        models.FinalAgreement.session_id == session_id
    ).first()
    if not agreement:
        raise HTTPException(status_code=404, detail=f"No agreement found for session {session_id}")
    return {
        "session_id":          agreement.session_id,
        "contract_type":       agreement.contract_type,
        "final_price":         agreement.final_price,
        "timeline_days":       agreement.timeline_days,
        "terms":               _json.loads(agreement.terms),
        "status":              agreement.status,
        "is_valid":            agreement.is_valid,
        "invalidation_reason": agreement.invalidation_reason,
        "created_at":          agreement.created_at.isoformat(),
        "chain_tx_hash":        agreement.chain_tx_hash,
        "chain_block_number":   agreement.chain_block_number,
        "agreement_hash":        agreement.agreement_hash,
    }