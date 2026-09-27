import React from 'react';
import { TrendingUp, TrendingDown, Minus } from 'lucide-react';

export function MetricCard({ label, value, detail, detailType = 'neutral', icon: Icon, iconColor = 'orange' }) {
  const TrendIcon = detailType === 'up' ? TrendingUp : detailType === 'down' ? TrendingDown : Minus;
  return (
    <div className="metric-card">
      <div className="metric-card-top">
        <span className="metric-card-label">{label}</span>
        {Icon && (
          <div className={`metric-card-icon ${iconColor}`}>
            <Icon size={16} />
          </div>
        )}
      </div>
      <span className="metric-card-value">{value}</span>
      <div className={`metric-card-detail ${detailType}`}>
        <TrendIcon size={12} />
        <span>{detail}</span>
      </div>
    </div>
  );
}

export function ModuleWeightRow({ module, value, percent, color = '#FF5A3A' }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '7px 0', fontSize: 12 }}>
      <span style={{ width: 100, color: 'var(--muted)', flexShrink: 0 }}>{module}</span>
      <div className="bar-track">
        <div className="bar-fill" style={{ width: `${Math.min(percent, 100)}%`, background: color }} />
      </div>
      <span style={{ width: 46, textAlign: 'right', fontWeight: 600, fontFamily: 'Manrope', fontSize: 11 }}>
        {percent?.toFixed(1)}%
      </span>
      <span style={{ width: 70, textAlign: 'right', color: 'var(--muted)', fontSize: 11 }}>{value}</span>
    </div>
  );
}

export function StatusPill({ status }) {
  const map = {
    Finalized: 'pill pill-finalized',
    Draft: 'pill pill-draft',
    Quoted: 'pill pill-quoted',
    finalized: 'pill pill-finalized',
    draft: 'pill pill-draft',
    quoted: 'pill pill-quoted',
  };
  return <span className={map[status] || 'pill pill-draft'}>{status}</span>;
}

export function RateConfigRow({ masterRate, overrideRate, effectiveRate, onOverrideChange, onReset, label = 'Rate (₹/kg)' }) {
  return (
    <div className="rate-config">
      <div>
        <span className="rate-config-label">Master Rate</span>
        <span className="rate-val prominent">₹ {masterRate?.toFixed(2)}</span>
      </div>
      <div>
        <span className="rate-config-label">Estimate Override ✏</span>
        <div className="rate-override-input">
          <input
            type="number"
            value={overrideRate ?? ''}
            onChange={(e) => onOverrideChange?.(Number(e.target.value))}
            placeholder="—"
          />
        </div>
      </div>
      <div>
        <span className="rate-config-label">Effective Rate</span>
        <span className="rate-val prominent orange">₹ {effectiveRate?.toFixed(2)}</span>
      </div>
      <button className="btn btn-secondary btn-sm" onClick={onReset}>Reset to Master</button>
    </div>
  );
}

export function CalcTracePanel({ rows = [], formula }) {
  return (
    <div className="calc-trace">
      <div className="calc-trace-title">How was this calculated?</div>
      {rows.map(({ label, value, formula: rowFormula }, i) => (
        <div className="calc-trace-row" key={i}>
          <span>{label}</span>
          <strong>{value}</strong>
          {rowFormula && <em style={{ fontSize: 11, color: 'var(--muted-2)', fontStyle: 'normal' }}>{rowFormula}</em>}
        </div>
      ))}
      {formula && <div className="calc-formula">Formula: {formula}</div>}
    </div>
  );
}

export function PageHeader({ eyebrow, title, description, actions }) {
  return (
    <div className="page-header">
      <div className="page-header-left">
        {eyebrow && <span className="eyebrow">{eyebrow}</span>}
        <h1>{title}</h1>
        {description && <p>{description}</p>}
      </div>
      {actions && <div className="page-header-right">{actions}</div>}
    </div>
  );
}

export function Panel({ children, style, className = '' }) {
  return <div className={`panel ${className}`} style={style}>{children}</div>;
}

export function Stepper({ steps, current }) {
  return (
    <div className="stepper">
      {steps.map((step, i) => {
        const done = i < current;
        const active = i === current;
        return (
          <React.Fragment key={i}>
            <div className={`step-item ${done ? 'done' : active ? 'active' : ''}`}>
              <div className="step-num">
                {done ? '✓' : i + 1}
              </div>
              <span>{step}</span>
            </div>
            {i < steps.length - 1 && <div className="step-connector" />}
          </React.Fragment>
        );
      })}
    </div>
  );
}

export const money = (n) =>
  `₹ ${Number(n || 0).toLocaleString('en-IN', { maximumFractionDigits: 2, minimumFractionDigits: 2 })}`;
