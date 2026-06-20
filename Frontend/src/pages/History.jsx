import React, { useState } from 'react';
import Card from '../components/Card';
import Footer from '../components/Footer';
import HistoryTable from '../components/HistoryTable';
import HistoryDrawer from '../components/HistoryDrawer';
import { mockHistory } from '../data/mockDeals';

function History() {
  const [selectedDeal, setSelectedDeal] = useState(null);

  return (
    <div className="page-container">
      <div className="page-header">
        <h1 className="page-title">Negotiation History</h1>
        <p className="page-subtitle">
          Previously completed agreements and settlement records.
        </p>
      </div>

      <Card>
        <HistoryTable deals={mockHistory} onSelectDeal={setSelectedDeal} />
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
