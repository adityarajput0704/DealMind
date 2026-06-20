import React, { useState, useEffect } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { FileCheck, ArrowRight } from 'lucide-react';
import Card from '../components/Card';
import NegotiationArena from '../components/NegotiationArena';
import NegotiationTimeline from '../components/NegotiationTimeline';
import { generateNegotiationRounds } from '../data/mockDeals';

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
  const deal = location.state?.deal || defaultDeal;

  const { rounds, finalValue } = generateNegotiationRounds(deal.clientBudget, deal.vendorPrice);
  const [currentRoundIndex, setCurrentRoundIndex] = useState(0);

  const isComplete = currentRoundIndex >= rounds.length - 1;
  const lastRound = rounds[rounds.length - 1];
  const agreed = isComplete && lastRound.agreed;

  useEffect(() => {
    if (currentRoundIndex >= rounds.length - 1) return;

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

  const convergencePercent = ((currentRoundIndex + 1) / rounds.length) * 100;
  const currentRound = rounds[currentRoundIndex];
  const visibleRounds = rounds.slice(0, currentRoundIndex + 1);

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
            onClick={() => navigate('/history')}
          >
            Save Deal to History
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
