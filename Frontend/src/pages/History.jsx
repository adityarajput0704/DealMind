import { useState, useEffect } from 'react';
import Card from '../components/Card';
import Footer from '../components/Footer';
import HistoryTable from '../components/HistoryTable';
import HistoryDrawer from '../components/HistoryDrawer';

function History() {
  const [selectedDeal, setSelectedDeal] = useState(null);
  const [deals, setDeals] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let active = true;

    const baseUrl = import.meta.env.VITE_API_BASE_URL || '';

    async function fetchHistory() {
      try {
        const response = await fetch(`${baseUrl}/api/deals`);
        if (!response.ok) {
          const err = await response.json();
          throw new Error(err.detail || 'Failed to fetch deals');
        }
        const dealsData = await response.json();

        const fullDeals = await Promise.all(
          dealsData.map(async (deal) => {
            const sessionId = deal.id;

            let rounds = [];
            try {
             const roundsRes = await fetch(`${baseUrl}/api/sessions/${sessionId}/rounds`);
              if (roundsRes.ok) {
                rounds = await roundsRes.json();
              }
            } catch (e) {
              console.error(`Failed to fetch rounds for session ${sessionId}:`, e);
            }

            let agreement = null;
            try {
              const agreementRes = await fetch(`${baseUrl}/api/sessions/${sessionId}/agreement`);
              if (agreementRes.ok) {
                agreement = await agreementRes.json();
              }
            } catch (e) {
              console.error(`Failed to fetch agreement for session ${sessionId}:`, e);
            }

            const contractType = deal.contract_type;
            const clientBudget = deal.budget;
            const vendorAsk = deal.vendor_target;
            const isMonthly = deal.contract_type === 'Cloud Hosting Contract';

            let finalValue = 0;
            let date = new Date().toISOString();
            if (agreement) {
              finalValue = agreement.final_price;
              date = agreement.created_at;
            } else if (rounds.length > 0) {
              const lastR = rounds[rounds.length - 1];
              finalValue = (lastR.client_offer + lastR.vendor_ask) / 2;
              date = lastR.timestamp || new Date().toISOString();
            }

            let status = 'Negotiating';
            if (agreement) {
              status = 'Completed';
            } else if (deal.status === 'agreed') {
              status = 'Agreed';
            } else if (deal.status === 'failed') {
              status = 'Failed';
            }

            const timeline = rounds.map((r, index) => ({
              round: r.round_number,
              clientOffer: r.client_offer,
              vendorAsk: r.vendor_ask,
              agreed: (index === rounds.length - 1) && (deal.status === 'agreed'),
            }));

            const settlement = agreement ? {
              txHash: agreement.chain_tx_hash || 'N/A',
              settledDate: new Date(agreement.created_at).toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' }),
              verifiedOn: 'Monad Testnet',
            } : {
              txHash: 'Not Settled',
              settledDate: 'N/A',
              verifiedOn: 'N/A',
            };

            return {
              id: deal.id,
              contractType,
              clientBudget,
              vendorAsk,
              finalValue,
              status,
              date,
              isMonthly,
              requirements: deal.requirement,
              timeline,
              settlement,
            };
          })
        );

        if (active) {
          setDeals(fullDeals);
          setLoading(false);
        }
      } catch (err) {
        console.error(err);
        if (active) {
          setError(err.message || 'Failed to load history.');
          setLoading(false);
        }
      }
    }

    fetchHistory();

    return () => {
      active = false;
    };
  }, []);

  return (
    <div className="page-container">
      <div className="page-header">
        <h1 className="page-title">Negotiation History</h1>
        <p className="page-subtitle">
          Previously completed agreements and settlement records.
        </p>
      </div>

      <Card>
        {loading ? (
          <div style={{ textAlign: 'center', padding: '2rem' }}>
            <p>Loading history from database...</p>
          </div>
        ) : error ? (
          <div style={{ textAlign: 'center', padding: '2rem', color: 'var(--color-danger)' }}>
            <p>Error: {error}</p>
          </div>
        ) : deals.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '2rem' }}>
            <p>No deals found in history.</p>
          </div>
        ) : (
          <HistoryTable deals={deals} onSelectDeal={setSelectedDeal} />
        )}
      </Card>

      <HistoryDrawer
        deal={selectedDeal}
        onClose={() => setSelectedDeal(null)}
      />

      <Footer />
    </div>
  );
}

export default History;
