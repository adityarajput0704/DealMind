import React from 'react';

const formatCurrency = (val) => `$${Number(val).toLocaleString()}`;

function NegotiationTimeline({ rounds, currentRoundIndex }) {
  if (!rounds || rounds.length === 0) return null;

  return (
    <div className="card" style={{ marginTop: '1.5rem' }}>
      <h3 className="card-title" style={{ marginBottom: '1.25rem' }}>Negotiation Journey</h3>
      <div className="timeline">
        {rounds.map((round, index) => {
          const isActive = index === currentRoundIndex;
          const isAgreed = round.agreed;

          let dotClass = 'timeline-dot';
          if (isAgreed) {
            dotClass += ' agreed';
          } else if (isActive) {
            dotClass += ' active';
          }

          return (
            <div className="timeline-item" key={round.round}>
              <div className={dotClass} />
              <p className="timeline-round">Round {round.round}</p>
              {isAgreed ? (
                <div>
                  <p className="timeline-agreed">Agreement Reached</p>
                  <p style={{ fontWeight: 700, fontSize: '0.9375rem', marginTop: '0.25rem' }}>
                    {formatCurrency(round.clientOffer)}
                  </p>
                </div>
              ) : (
                <div className="timeline-values">
                  <div className="timeline-val">
                    <span className="timeline-val-label">Client:</span>
                    <span className="timeline-val-amount">{formatCurrency(round.clientOffer)}</span>
                  </div>
                  <div className="timeline-val">
                    <span className="timeline-val-label">Vendor:</span>
                    <span className="timeline-val-amount">{formatCurrency(round.vendorAsk)}</span>
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

export default NegotiationTimeline;
