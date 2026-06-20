import { useState, useEffect } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { FileCheck, ArrowRight } from 'lucide-react';
import Card from '../components/Card';
import NegotiationArena from '../components/NegotiationArena';
import NegotiationTimeline from '../components/NegotiationTimeline';

const formatCurrency = (val) => `$${Number(val).toLocaleString()}`;

const defaultDeal = {
  contractType: 'Freelance Development Contract',
  clientBudget: 5000,
  vendorPrice: 7000,
  requirements: 'Build a FastAPI backend with PostgreSQL, authentication, Docker deployment, monitoring, and CI/CD.',
};

function Negotiation() {
  const location = useLocation();
  const navigate = useNavigate();

  const initialDeal = location.state?.deal || defaultDeal;
  const initialDealId = location.state?.dealId;
  const initialSessionId = location.state?.sessionId;

  const [deal] = useState(initialDeal);
  const [dealId, setDealId] = useState(initialDealId);
  const [sessionId, setSessionId] = useState(initialSessionId);

  const [rounds, setRounds] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [currentRoundIndex, setCurrentRoundIndex] = useState(0);
  const [finalValue, setFinalValue] = useState(null);
  const [settling, setSettling] = useState(false);

  useEffect(() => {
    let active = true;

    const baseUrl = import.meta.env.VITE_API_BASE_URL || '';

    async function runFlow() {
      try {
        let dId = dealId;
        let sId = sessionId;

        if (!dId || !sId) {
          const dealRes = await fetch(`${baseUrl}/api/deals`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              contract_type: deal.contractType,
              budget: Number(deal.clientBudget),
              vendor_target: Number(deal.vendorPrice),
              requirement: deal.requirements,
            }),
          });
          if (!dealRes.ok) {
            const err = await dealRes.json();
            throw new Error(err.detail || 'Failed to register deal');
          }
          const dealData = await dealRes.json();
          dId = dealData.id;
          if (active) setDealId(dId);

          const sessionRes = await fetch(`/api/deals/${dId}/negotiate`, { method: 'POST' });
          if (!sessionRes.ok) {
            const err = await sessionRes.json();
            throw new Error(err.detail || 'Failed to initialize session');
          }
          const sessionData = await sessionRes.json();
          sId = sessionData.id;
          if (active) setSessionId(sId);
        }

        const runRes = await fetch(`${baseUrl}/api/sessions/${sId}/run`, { method: 'POST' });
        if (!runRes.ok) {
          const err = await runRes.json();
          throw new Error(err.detail || 'Failed to execute negotiation');
        }
        const runData = await runRes.json();

        const mappedRounds = runData.rounds.map((r, index) => ({
          round: r.round_number,
          clientOffer: r.client_offer,
          vendorAsk: r.vendor_ask,
          clientReason: r.client_reason,
          vendorReason: r.vendor_reason,
          agreed: (index === runData.rounds.length - 1) && (runData.status === 'agreed'),
        }));

        if (active) {
          setRounds(mappedRounds);
          setFinalValue(runData.final_price);
          setLoading(false);
        }
      } catch (err) {
        console.error(err);
        if (active) {
          setError(err.message || 'An error occurred during negotiation setup.');
          setLoading(false);
        }
      }
    }

    runFlow();

    return () => {
      active = false;
    };
  }, []);

  const isComplete = rounds.length > 0 && currentRoundIndex >= rounds.length - 1;
  const lastRound = rounds.length > 0 ? rounds[rounds.length - 1] : null;
  const agreed = isComplete && lastRound && lastRound.agreed;

  useEffect(() => {
    if (rounds.length === 0 || currentRoundIndex >= rounds.length - 1) return;

    const interval = setInterval(() => {
      setCurrentRoundIndex((prev) => {
        if (prev >= rounds.length - 1) {
          clearInterval(interval);
          return prev;
        }
        return prev + 1;
      });
    }, 1500);

    return () => clearInterval(interval);
  }, [currentRoundIndex, rounds.length]);

  const convergencePercent = rounds.length > 0 ? ((currentRoundIndex + 1) / rounds.length) * 100 : 0;
  const currentRound = rounds.length > 0 ? rounds[currentRoundIndex] : null;
  const visibleRounds = rounds.length > 0 ? rounds.slice(0, currentRoundIndex + 1) : [];

  const handleSettle = async () => {
    if (!sessionId || settling) return;
    setSettling(true);
    try {
      const response = await fetch(`${baseUrl}/api/sessions/${sessionId}/settle`,{
        method: 'POST',
      });
      if (!response.ok) {
        const err = await response.json();
        throw new Error(err.detail || 'Failed to settle session on Monad blockchain.');
      }
      navigate('/history');
    } catch (err) {
      console.error(err);
      alert(err.message || 'An error occurred during on-chain settlement.');
    } finally {
      setSettling(false);
    }
  };

  if (loading) {
    return (
      <div className="page-container" style={{ textAlign: 'center', paddingTop: '6rem' }}>
        <h1 className="page-title">Initializing Agents...</h1>
        <p className="page-subtitle">Autonomous agents are analyzing strategy and starting LLM-based negotiation.</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="page-container" style={{ textAlign: 'center', paddingTop: '6rem' }}>
        <h1 className="page-title" style={{ color: 'var(--color-danger)' }}>Negotiation Error</h1>
        <p className="page-subtitle">{error}</p>
        <button
          className="btn btn-teal"
          style={{ marginTop: '1.5rem' }}
          onClick={() => window.location.reload()}
        >
          Retry
        </button>
      </div>
    );
  }

  return (
    <div className="page-container">
      {/* Page Header */}
      <div className="page-header">
        <h1 className="page-title">
          {isComplete ? 'Negotiation Complete' : 'Negotiation In Progress'}
        </h1>
        <p className="page-subtitle">
          {isComplete
            ? 'Agreement has been reached successfully.'
            : 'Autonomous agents are negotiating contract terms.'}
        </p>
      </div>

      {/* Negotiation Arena */}
      <NegotiationArena
        currentRound={currentRound}
        totalRounds={rounds.length}
        convergencePercent={convergencePercent}
      />

      {/* Negotiation Timeline */}
      <NegotiationTimeline
        rounds={visibleRounds}
        currentRoundIndex={currentRoundIndex}
      />

      {/* Agreement Summary */}
      {agreed && (
        <Card className="fade-up" style={{ marginTop: '1.5rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1.25rem' }}>
            <FileCheck size={20} style={{ color: 'var(--color-success)' }} />
            <h3 className="card-title" style={{ margin: 0 }}>Agreement Summary</h3>
          </div>

          <div className="summary-grid">
            <div className="summary-item">
              <span className="summary-label">Contract Type</span>
              <span className="summary-value">{deal.contractType}</span>
            </div>
            <div className="summary-item">
              <span className="summary-label">Client Initial Budget</span>
              <span className="summary-value">{formatCurrency(deal.clientBudget)}</span>
            </div>
            <div className="summary-item">
              <span className="summary-label">Vendor Initial Ask</span>
              <span className="summary-value">{formatCurrency(deal.vendorPrice)}</span>
            </div>
            <div className="summary-item">
              <span className="summary-label">Final Agreed Value</span>
              <span className="summary-value" style={{ color: '#3C6E71', fontWeight: 700 }}>
                {formatCurrency(finalValue)}
              </span>
            </div>
            <div className="summary-item">
              <span className="summary-label">Negotiation Rounds</span>
              <span className="summary-value">{rounds.length}</span>
            </div>
            <div className="summary-item">
              <span className="summary-label">Status</span>
              <span className="badge badge-success">Agreement Reached</span>
            </div>
          </div>

          <button
            className="btn btn-teal btn-lg btn-full"
            style={{ marginTop: '1.5rem' }}
            onClick={handleSettle}
            disabled={settling}
          >
            {settling ? 'Settling on Monad Testnet...' : 'Save Deal to History'}
            <ArrowRight size={18} />
          </button>
        </Card>
      )}

      {/* Footer */}
      <footer className="footer">
        <span>Powered by </span>
        <span className="footer-monad">Monad</span>
      </footer>
    </div>
  );
}

export default Negotiation;
