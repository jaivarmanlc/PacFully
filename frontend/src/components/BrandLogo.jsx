import React from 'react';

export default function BrandLogo({ width = 150, className = '', style = {} }) {
  return (
    <img
      src="/pck%20logo%20.png"
      alt="Pacfully Packaging Engineered"
      className={className}
      style={{ width, height: 'auto', display: 'block', objectFit: 'contain', ...style }}
    />
  );
}