import React from 'react';

function Button({
  children,
  variant = 'primary',
  size = 'default',
  fullWidth = false,
  onClick,
  type = 'button',
  disabled = false,
  className,
}) {
  const classes = [
    'btn',
    `btn-${variant}`,
    size === 'lg' ? 'btn-lg' : '',
    fullWidth ? 'btn-full' : '',
    className || '',
  ]
    .filter(Boolean)
    .join(' ');

  return (
    <button
      className={classes}
      onClick={onClick}
      type={type}
      disabled={disabled}
    >
      {children}
    </button>
  );
}

export default Button;
