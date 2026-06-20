import React from 'react';
import { Shield } from 'lucide-react';

function Footer() {
  return (
    <div className="footer">
      <Shield size={14} />
      Secured by <span className="footer-monad">Monad</span>
    </div>
  );
}

export default Footer;
