import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import Navbar from './components/Navbar';
import CreateDeal from './pages/CreateDeal';
import Negotiation from './pages/Negotiation';
import History from './pages/History';

function App() {
  return (
    <BrowserRouter>
      <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
        <Navbar />
        <main style={{ flex: 1 }}>
          <Routes>
            <Route path="/" element={<Navigate to="/create-deal" replace />} />
            <Route path="/create-deal" element={<CreateDeal />} />
            <Route path="/negotiation" element={<Negotiation />} />
            <Route path="/history" element={<History />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}

export default App;
