import React from 'react';
import { User, Building2 } from 'lucide-react';
import Card from './Card';

const formatCurrency = (val) => `$${Number(val).toLocaleString()}`;

function NegotiationArena({ currentRound, totalRounds, convergencePercent }) {
  if (!currentRound) return null;

  const gap = Math.abs(currentRound.vendorAsk - currentRound.clientOffer);
  const agreed = currentRound.agreed;

  return (
    <div className="arena-grid">
      {/* Client Agent - Left Column */}
      <Card className="arena-agent">
        <div className="arena-agent-header">
          <div className="arena-agent-title">
            <User size={18} />
            <span>Client Agent</span>
          </div>
          <span className={`badge ${agreed ? 'badge-success' : 'badge-teal'}`}>
            {agreed ? 'Agreed' : 'Negotiating'}
          </span>
        </div>
        <hr className="arena-divider" />
        <p className="arena-label">CURRENT OFFER</p>
        <p className="arena-offer" style={{ color: '#3C6E71' }}>
          {formatCurrency(currentRound.clientOffer)}
        </p>
        <p className="arena-reason">{currentRound.clientReason}</p>
      </Card>

      {/* Center Column */}
      <Card className="arena-center">
        <p className="arena-label">NEGOTIATION GAP</p>
        <p className="arena-value" style={{ color: 'var(--color-dark)' }}>
          {formatCurrency(gap)}
        </p>
        <div className="convergence-section">
          <div className="arena-label" style={{ display: 'flex', justifyContent: 'space-between', width: '100%' }}>
            <span>Convergence</span>
            <span>{Math.round(convergencePercent)}%</span>
          </div>
          <div className="convergence-track">
            <div
              className="convergence-fill"
              style={{ width: `${convergencePercent}%` }}
            />
          </div>
        </div>
        <p className="arena-round-indicator">
          Round {currentRound.round} of {totalRounds}
        </p>
      </Card>

      {/* Vendor Agent - Right Column */}
      <Card className="arena-agent">
        <div className="arena-agent-header">
          <div className="arena-agent-title">
            <Building2 size={18} />
            <span>Vendor Agent</span>
          </div>
          <span className={`badge ${agreed ? 'badge-success' : 'badge-blue'}`}>
            {agreed ? 'Agreed' : 'Negotiating'}
          </span>
        </div>
        <hr className="arena-divider" />
        <p className="arena-label">CURRENT ASK</p>
        <p className="arena-offer" style={{ color: '#284B63' }}>
          {formatCurrency(currentRound.vendorAsk)}
        </p>
        <p className="arena-reason">{currentRound.vendorReason}</p>
      </Card>
    </div>
  );
}

export default NegotiationArena;
