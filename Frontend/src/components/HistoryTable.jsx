import React from 'react';
import Badge from './Badge';

const formatCurrency = (val) => `$${Number(val).toLocaleString()}`;

function HistoryTable({ deals, onSelectDeal }) {
  return (
    <div className="table-wrapper">
      <table className="table">
        <thead>
          <tr>
            <th>Deal ID</th>
            <th>Contract Type</th>
            <th>Client Budget</th>
            <th>Vendor Ask</th>
            <th>Final Value</th>
            <th>Status</th>
            <th>Date</th>
          </tr>
        </thead>
        <tbody>
          {deals.map((deal) => (
            <tr key={deal.id} onClick={() => onSelectDeal(deal)}>
              <td style={{ fontWeight: 600 }}>#{deal.id}</td>
              <td>{deal.contractType}</td>
              <td>
                {formatCurrency(deal.clientBudget)}
                {deal.isMonthly ? '/mo' : ''}
              </td>
              <td>
                {formatCurrency(deal.vendorAsk)}
                {deal.isMonthly ? '/mo' : ''}
              </td>
              <td className="table-value" style={{ color: '#3C6E71' }}>
                {formatCurrency(deal.finalValue)}
                {deal.isMonthly ? '/mo' : ''}
              </td>
              <td>
                <Badge variant="success">Completed</Badge>
              </td>
              <td>{new Date(deal.date).toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' })}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default HistoryTable;
