import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import Card from '../components/Card';
import Button from '../components/Button';
import Footer from '../components/Footer';
import { Handshake, ArrowRight } from 'lucide-react';

function CreateDeal() {
  const navigate = useNavigate();

  const [contractType, setContractType] = useState('');
  const [clientBudget, setClientBudget] = useState('');
  const [vendorPrice, setVendorPrice] = useState('');
  const [requirements, setRequirements] = useState('');

  const isFormValid =
    contractType !== '' &&
    clientBudget !== '' &&
    vendorPrice !== '' &&
    requirements.trim() !== '';

  const handleSubmit = () => {
    if (!isFormValid) return;

    navigate('/negotiation', {
      state: {
        deal: {
          contractType,
          clientBudget: Number(clientBudget),
          vendorPrice: Number(vendorPrice),
          requirements,
        },
      },
    });
  };

  return (
    <div>
      <div style={{ maxWidth: 640, margin: '0 auto', padding: '2.5rem 1.5rem 1rem' }}>
        {/* Page Header */}
        <div style={{ textAlign: 'center', marginBottom: '2rem' }}>
          <div
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              justifyContent: 'center',
              width: 72,
              height: 72,
              borderRadius: '50%',
              background: 'rgba(60, 110, 113, 0.1)',
              marginBottom: '1rem',
            }}
          >
            <Handshake size={40} color="var(--color-teal)" />
          </div>
          <h1 className="page-title" style={{ textAlign: 'center' }}>
            DealMind
          </h1>
          <p className="page-subtitle" style={{ textAlign: 'center' }}>
            Autonomous Agent Negotiation Platform
          </p>
        </div>

        {/* Form Card */}
        <Card>
          <div className="form-group">
            <label className="form-label">Contract Type</label>
            <select
              className="form-select"
              value={contractType}
              onChange={(e) => setContractType(e.target.value)}
            >
              <option value="">Select contract type...</option>
              <option value="Freelance Development Contract">
                Freelance Development Contract
              </option>
              <option value="Cloud Hosting Contract">Cloud Hosting Contract</option>
            </select>
          </div>

          <div className="form-group">
            <label className="form-label">Client Maximum Budget</label>
            <input
              className="form-input"
              type="number"
              placeholder="Enter maximum budget"
              value={clientBudget}
              onChange={(e) => setClientBudget(e.target.value)}
            />
          </div>

          <div className="form-group">
            <label className="form-label">Vendor Target Price</label>
            <input
              className="form-input"
              type="number"
              placeholder="Enter target price"
              value={vendorPrice}
              onChange={(e) => setVendorPrice(e.target.value)}
            />
          </div>

          <div className="form-group">
            <label className="form-label">Project Requirements</label>
            <textarea
              className="form-textarea"
              placeholder="Build a FastAPI backend with PostgreSQL, authentication, Docker deployment, monitoring, and CI/CD."
              value={requirements}
              onChange={(e) => setRequirements(e.target.value)}
            />
          </div>

          <Button
            variant="teal"
            size="lg"
            fullWidth={true}
            onClick={handleSubmit}
            disabled={!isFormValid}
          >
            Start Negotiation
            <ArrowRight size={18} />
          </Button>
        </Card>
      </div>

      <Footer />
    </div>
  );
}

export default CreateDeal;
