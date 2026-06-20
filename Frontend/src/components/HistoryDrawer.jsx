import React from 'react';
import { X } from 'lucide-react';
import Badge from './Badge';
import Card from './Card';

const formatCurrency = (val) => `$${Number(val).toLocaleString()}`;

function HistoryDrawer({ deal, onClose }) {
  if (!deal) return null;

  return (
    <div className="drawer-overlay" onClick={onClose}>
      <div className="drawer" onClick={(e) => e.stopPropagation()}>
        <div className="drawer-header">
          <h2 className="drawer-title">Deal #{deal.id}</h2>
          <button className="drawer-close" onClick={onClose}>
            <X size={18} />
          </button>
        </div>

        <div className="drawer-body">
          {/* Contract Details */}
          <div className="drawer-section">
            <h3 className="drawer-section-title">Contract Details</h3>
            <div className="drawer-row">
              <span className="drawer-row-label">Contract Type</span>
              <span className="drawer-row-value">{deal.contractType}</span>
            </div>
            <div className="drawer-row">
              <span className="drawer-row-label">Client Budget</span>
              <span className="drawer-row-value">
                {formatCurrency(deal.clientBudget)}
                {deal.isMonthly ? '/mo' : ''}
              </span>
            </div>
            <div className="drawer-row">
              <span className="drawer-row-label">Vendor Ask</span>
              <span className="drawer-row-value">
                {formatCurrency(deal.vendorAsk)}
                {deal.isMonthly ? '/mo' : ''}
              </span>
            </div>
            <div className="drawer-row">
              <span className="drawer-row-label">Final Value</span>
              <span className="drawer-row-value" style={{ fontWeight: 700, color: '#3C6E71' }}>
                {formatCurrency(deal.finalValue)}
                {deal.isMonthly ? '/mo' : ''}
              </span>
            </div>
            <div className="drawer-row">
              <span className="drawer-row-label">Rounds</span>
              <span className="drawer-row-value">{deal.timeline.length}</span>
            </div>
            <div className="drawer-row">
              <span className="drawer-row-label">Status</span>
              <Badge variant="success">Completed</Badge>
            </div>
          </div>

          {/* Negotiation Timeline */}
          <div className="drawer-section">
            <h3 className="drawer-section-title">Negotiation Timeline</h3>
            <div className="timeline">
              {deal.timeline.map((round) => (
                <div className="timeline-item" key={round.round}>
                  <div className={`timeline-dot${round.agreed ? ' agreed' : ' active'}`} />
                  <div className="timeline-round">Round {round.round}</div>
                  {round.agreed ? (
                    <div className="timeline-agreed">
                      Agreement Reached — {formatCurrency(round.clientOffer)}
                      {deal.isMonthly ? '/mo' : ''}
                    </div>
                  ) : (
                    <div className="timeline-values">
                      <div className="timeline-val">
                        <span className="timeline-val-label">Client:</span>
                        <span className="timeline-val-amount">
                          {formatCurrency(round.clientOffer)}
                          {deal.isMonthly ? '/mo' : ''}
                        </span>
                      </div>
                      <div className="timeline-val">
                        <span className="timeline-val-label">Vendor:</span>
                        <span className="timeline-val-amount">
                          {formatCurrency(round.vendorAsk)}
                          {deal.isMonthly ? '/mo' : ''}
                        </span>
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>

          {/* Settlement Record */}
          <div className="drawer-section">
            <h3 className="drawer-section-title">Settlement Record</h3>
            <div className="drawer-row">
              <span className="drawer-row-label">Transaction Hash</span>
              <span
                className="drawer-row-value"
                style={{ fontFamily: 'monospace', fontSize: '0.8125rem' }}
              >
                {deal.settlement.txHash}
              </span>
            </div>
            <div className="drawer-row">
              <span className="drawer-row-label">Settlement Date</span>
              <span className="drawer-row-value">{deal.settlement.settledDate}</span>
            </div>
            <div className="drawer-row">
              <span className="drawer-row-label">Verified On</span>
              <span className="drawer-row-value">{deal.settlement.verifiedOn}</span>
            </div>
            <div className="drawer-row">
              <span className="drawer-row-label">Status</span>
              <Badge variant="teal">Settled</Badge>
            </div>
            <div className="drawer-row">
              <span className="drawer-row-label">Verification</span>
              <Badge variant="success">Verified</Badge>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default HistoryDrawer;
