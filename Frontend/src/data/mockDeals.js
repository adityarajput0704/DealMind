// Mock data for completed deal history
export const mockHistory = [
  {
    id: 482,
    contractType: 'Freelance Development Contract',
    clientBudget: 5000,
    vendorAsk: 7000,
    finalValue: 5900,
    status: 'Completed',
    date: '2026-06-15',
    isMonthly: false,
    requirements: 'Build a FastAPI backend with PostgreSQL, authentication, Docker deployment, monitoring, and CI/CD.',
    timeline: [
      { round: 1, clientOffer: 5000, vendorAsk: 7000 },
      { round: 2, clientOffer: 5500, vendorAsk: 6500 },
      { round: 3, clientOffer: 5800, vendorAsk: 6000 },
      { round: 4, clientOffer: 5900, vendorAsk: 5900, agreed: true },
    ],
    settlement: {
      txHash: '0x8a3f...b7d2e4c1',
      settledDate: '2026-06-15',
      verifiedOn: 'Monad Testnet',
    },
  },
  {
    id: 483,
    contractType: 'Cloud Hosting Contract',
    clientBudget: 2000,
    vendorAsk: 3000,
    finalValue: 2500,
    status: 'Completed',
    date: '2026-06-14',
    isMonthly: true,
    requirements: 'Managed Kubernetes cluster with auto-scaling, CDN, 99.9% uptime SLA, and 24/7 support.',
    timeline: [
      { round: 1, clientOffer: 2000, vendorAsk: 3000 },
      { round: 2, clientOffer: 2200, vendorAsk: 2800 },
      { round: 3, clientOffer: 2400, vendorAsk: 2600 },
      { round: 4, clientOffer: 2500, vendorAsk: 2500, agreed: true },
    ],
    settlement: {
      txHash: '0x4e1c...a9f3d7b8',
      settledDate: '2026-06-14',
      verifiedOn: 'Monad Testnet',
    },
  },
  {
    id: 484,
    contractType: 'Freelance Development Contract',
    clientBudget: 8000,
    vendorAsk: 12000,
    finalValue: 9800,
    status: 'Completed',
    date: '2026-06-12',
    isMonthly: false,
    requirements: 'Full-stack React + Node.js e-commerce platform with payment integration, admin dashboard, and analytics.',
    timeline: [
      { round: 1, clientOffer: 8000, vendorAsk: 12000 },
      { round: 2, clientOffer: 8800, vendorAsk: 11000 },
      { round: 3, clientOffer: 9500, vendorAsk: 10200 },
      { round: 4, clientOffer: 9800, vendorAsk: 9800, agreed: true },
    ],
    settlement: {
      txHash: '0xd7b2...c3e5f1a9',
      settledDate: '2026-06-12',
      verifiedOn: 'Monad Testnet',
    },
  },
  {
    id: 485,
    contractType: 'Cloud Hosting Contract',
    clientBudget: 5000,
    vendorAsk: 7500,
    finalValue: 6200,
    status: 'Completed',
    date: '2026-06-10',
    isMonthly: true,
    requirements: 'Enterprise cloud migration with multi-region deployment, disaster recovery, compliance (SOC2), and dedicated support.',
    timeline: [
      { round: 1, clientOffer: 5000, vendorAsk: 7500 },
      { round: 2, clientOffer: 5500, vendorAsk: 7000 },
      { round: 3, clientOffer: 5900, vendorAsk: 6500 },
      { round: 4, clientOffer: 6200, vendorAsk: 6200, agreed: true },
    ],
    settlement: {
      txHash: '0xa1f8...e4c2b6d3',
      settledDate: '2026-06-10',
      verifiedOn: 'Monad Testnet',
    },
  },
];

// Generate negotiation rounds from deal parameters
export function generateNegotiationRounds(clientBudget, vendorAsk) {
  const gap = vendorAsk - clientBudget;
  const finalValue = Math.round(clientBudget + gap * 0.45);

  return {
    rounds: [
      {
        round: 1,
        clientOffer: clientBudget,
        vendorAsk: vendorAsk,
        clientReason: 'Initial budget based on market analysis and project scope.',
        vendorReason: 'Standard pricing for this scope with premium support included.',
      },
      {
        round: 2,
        clientOffer: Math.round(clientBudget + gap * 0.15),
        vendorAsk: Math.round(vendorAsk - gap * 0.15),
        clientReason: 'Adjusted offer considering vendor expertise and timeline.',
        vendorReason: 'Reduced price by removing optional premium add-ons.',
      },
      {
        round: 3,
        clientOffer: Math.round(clientBudget + gap * 0.35),
        vendorAsk: Math.round(vendorAsk - gap * 0.35),
        clientReason: 'Long-term maintenance commitment included.',
        vendorReason: 'Premium support and SLA included.',
      },
      {
        round: 4,
        clientOffer: finalValue,
        vendorAsk: finalValue,
        clientReason: 'Agreement reached at fair market value.',
        vendorReason: 'Agreement reached at fair market value.',
        agreed: true,
      },
    ],
    finalValue,
  };
}
