import React from 'react';

function Card({ children, className, style }) {
  return (
    <div className={`card${className ? ' ' + className : ''}`} style={style}>
      {children}
    </div>
  );
}

export default Card;
