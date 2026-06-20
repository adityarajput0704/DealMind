import React from 'react';
import { NavLink } from 'react-router-dom';
import { Handshake, FilePlus2, Activity, Clock, Bell, HelpCircle } from 'lucide-react';

function Navbar() {
  return (
    <nav className="navbar">
      <div className="navbar-logo">
        <Handshake size={24} color="#14b8a6" />
        <span>DealMind</span>
      </div>

      <div className="navbar-links">
        <NavLink
          to="/create-deal"
          className={({ isActive }) => `navbar-link ${isActive ? 'active' : ''}`}
        >
          <FilePlus2 size={16} />
          <span>Create Deal</span>
        </NavLink>
        <NavLink
          to="/negotiation"
          className={({ isActive }) => `navbar-link ${isActive ? 'active' : ''}`}
        >
          <Activity size={16} />
          <span>Negotiation</span>
        </NavLink>
        <NavLink
          to="/history"
          className={({ isActive }) => `navbar-link ${isActive ? 'active' : ''}`}
        >
          <Clock size={16} />
          <span>History</span>
        </NavLink>
      </div>

      <div className="navbar-actions">
        <button className="navbar-icon-btn" aria-label="Notifications">
          <Bell size={18} />
        </button>
        <button className="navbar-icon-btn" aria-label="Help">
          <HelpCircle size={18} />
        </button>
        <div className="navbar-avatar">SM</div>
      </div>
    </nav>
  );
}

export default Navbar;
