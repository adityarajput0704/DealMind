import React from 'react';

function Badge({ children, variant = 'neutral' }) {
  return (
    <span className={`badge badge-${variant}`}>
      {children}
    </span>
  );
}

export default Badge;
