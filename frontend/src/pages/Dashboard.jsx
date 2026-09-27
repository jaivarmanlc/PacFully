import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  ClipboardList, IndianRupee, Box, Clock, TrendingUp, Plus,
  ArrowRight, MoreHorizontal, ChevronRight, CalendarDays, ChevronDown
} from 'lucide-react';
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, Legend
} from 'recharts';
import { MetricCard, StatusPill, money } from '../components/CostCard';

const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep'];
const BAR_DATA = [
  { month: 'Jan', value: 8 }, { month: 'Feb', value: 12 }, { month: 'Mar', value: 7 },
  { month: 'Apr', value: 16 }, { month: 'May', value: 11 }, { month: 'Jun', value: 19 },
  { month: 'Jul', value: 14 }, { month: 'Aug', value: 22 }, { month: 'Sep', value: 18 },
];
const CHART_VIEWS = {
  Monthly: {
    subtitle: 'Jan – Sep 2026 (₹ Lakhs)',
    data: BAR_DATA,
  },
  Quarterly: {
    subtitle: 'Q1 – Q3 2026 (₹ Lakhs)',
    data: [
      { month: 'Q1', value: 27 }, { month: 'Q2', value: 46 }, { month: 'Q3', value: 54 },
    ],
  },
  Weekly: {
    subtitle: 'Last 8 weeks (₹ Lakhs)',
    data: [
      { month: 'W1', value: 4 }, { month: 'W2', value: 6 }, { month: 'W3', value: 5 },
      { month: 'W4', value: 8 }, { month: 'W5', value: 7 }, { month: 'W6', value: 9 },
      { month: 'W7', value: 8 }, { month: 'W8', value: 11 },
    ],
  },
};
const PIE_DATA = [
  { name: 'Kappa', value: 35.5, color: '#FF5A3A' },
  { name: 'Printing', value: 18.2, color: '#FF7A5C' },
  { name: 'Lamination', value: 13.1, color: '#FFB09C' },
  { name: 'Glue', value: 8.4, color: '#FFC352' },
  { name: 'Punching', value: 9.0, color: '#86B9EE' },
  { name: 'Embellishments', value: 6.4, color: '#A78BFA' },
  { name: 'Others', value: 9.4, color: '#DCE1E5' },
];
const RECENT = [
  { id: 'EST-00124', customer: 'Luxe Beauty Pvt Ltd', product: 'Premium Rigid Box', qty: 1000, costBox: 18.42, total: 22100, status: 'Finalized', date: '24 Sep 2026' },
  { id: 'EST-00123', customer: 'Aura Skincare', product: 'Gift Box', qty: 2000, costBox: 21.36, total: 42700, status: 'Draft', date: '23 Sep 2026' },
  { id: 'EST-00122', customer: 'Veda Naturals', product: 'Cosmetic Box', qty: 500, costBox: 16.80, total: 9800, status: 'Quoted', date: '22 Sep 2026' },
  { id: 'EST-00121', customer: 'Elite Brands', product: 'Luxury Box', qty: 1500, costBox: 19.25, total: 28875, status: 'Finalized', date: '21 Sep 2026' },
  { id: 'EST-00120', customer: 'Radiant Care', product: 'Skincare Box', qty: 800, costBox: 17.80, total: 17000, status: 'Draft', date: '20 Sep 2026' },
];

const CustomTooltip = ({ active, payload, label }) => {
  if (active && payload?.length) {
    return (
      <div style={{ background: '#fff', border: '1px solid #E5E9EE', borderRadius: 8, padding: '8px 14px', fontSize: 12, boxShadow: '0 4px 12px rgba(0,0,0,0.1)' }}>
        <div style={{ fontWeight: 600, marginBottom: 4 }}>{label}</div>
        <div style={{ color: '#FF5A3A' }}>₹ {payload[0].value}L</div>
      </div>
    );
  }
  return null;
};

export default function Dashboard() {
  const navigate = useNavigate();
  const [chartView, setChartView] = useState('Monthly');
  const [calendarOpen, setCalendarOpen] = useState(false);
  const [startDate, setStartDate] = useState('2026-09-01');
  const [endDate, setEndDate] = useState('2026-09-30');
  const activeChart = CHART_VIEWS[chartView];

  const formatDate = (value) => new Intl.DateTimeFormat('en-GB', {
    day: '2-digit', month: 'short', year: 'numeric',
  }).format(new Date(`${value}T00:00:00`));

  const dateRange = `${formatDate(startDate)} – ${formatDate(endDate)}`;

  return (
    <div className="page-content">
      {/* ── Header ─────────────────────────────────────── */}
      <div className="page-header">
        <div className="page-header-left">
          <span className="eyebrow">Dashboard / Cost Intelligence</span>
          <h1 style={{ marginTop: 4 }}>Cost Intelligence Overview</h1>
          <p>Monitor estimates, costs and key business insights</p>
        </div>
        <div className="page-header-right" style={{ alignItems: 'center', gap: 12 }}>
          <div style={{ position: 'relative' }}>
            <button
              type="button"
              aria-expanded={calendarOpen}
              onClick={() => setCalendarOpen(value => !value)}
              style={{
                border: '1px solid var(--line)', borderRadius: 8,
                padding: '8px 12px', fontSize: 12, color: 'var(--muted)',
                background: 'var(--panel)', display: 'flex', alignItems: 'center', gap: 7,
              }}
            >
              <CalendarDays size={13} color="#6B8DD6" /> {dateRange}
            </button>
            {calendarOpen && (
              <div style={{
                position: 'absolute', right: 0, top: 'calc(100% + 8px)', zIndex: 20,
                width: 260, padding: 14, background: '#fff', border: '1px solid var(--line)',
                borderRadius: 10, boxShadow: 'var(--shadow-lg)',
              }}>
                <div style={{ fontSize: 12, fontWeight: 700, marginBottom: 12 }}>Select date range</div>
                <div style={{ display: 'grid', gap: 10 }}>
                  <label style={{ display: 'grid', gap: 4, fontSize: 11, color: 'var(--muted)' }}>
                    From
                    <input
                      type="date" value={startDate} max={endDate}
                      onChange={event => setStartDate(event.target.value)}
                      style={{ width: '100%', height: 34, border: '1px solid var(--line)', borderRadius: 6, padding: '0 8px', fontSize: 12 }}
                    />
                  </label>
                  <label style={{ display: 'grid', gap: 4, fontSize: 11, color: 'var(--muted)' }}>
                    To
                    <input
                      type="date" value={endDate} min={startDate}
                      onChange={event => setEndDate(event.target.value)}
                      style={{ width: '100%', height: 34, border: '1px solid var(--line)', borderRadius: 6, padding: '0 8px', fontSize: 12 }}
                    />
                  </label>
                </div>
                <button
                  type="button" className="btn btn-primary btn-sm"
                  onClick={() => setCalendarOpen(false)}
                  style={{ width: '100%', justifyContent: 'center', marginTop: 12 }}
                >
                  Apply range
                </button>
              </div>
            )}
          </div>
          <button className="btn btn-primary" onClick={() => navigate('/estimator/new')}>
            <Plus size={15} /> New Estimate
          </button>
        </div>
      </div>

      {/* ── Metrics ─────────────────────────────────────── */}
      <div className="metric-grid">
        <MetricCard
          label="Total Estimates"
          value="124"
          detail="+13% vs last month"
          detailType="up"
          icon={ClipboardList}
          iconColor="orange"
        />
        <MetricCard
          label="Total Order Value"
          value="₹ 28,45,000"
          detail="+15% vs last month"
          detailType="up"
          icon={IndianRupee}
          iconColor="green"
        />
        <MetricCard
          label="Avg. Cost / Box"
          value="₹ 18.42"
          detail="+6% vs last month"
          detailType="up"
          icon={Box}
          iconColor="blue"
        />
        <MetricCard
          label="Quotations Sent"
          value="38"
          detail="+12% vs last month"
          detailType="up"
          icon={ClipboardList}
          iconColor="purple"
        />
      </div>

      {/* ── Charts row ──────────────────────────────────── */}
      <div className="grid-col-6-4" style={{ marginBottom: 20 }}>
        {/* Bar chart */}
        <div className="panel" style={{ padding: 20 }}>
          <div className="panel-header" style={{ marginBottom: 20 }}>
            <div>
              <div className="panel-title">Monthly Order Value</div>
              <div className="panel-sub">{activeChart.subtitle}</div>
            </div>
            <label style={{ position: 'relative' }}>
              <select
                value={chartView}
                aria-label="Chart grouping"
                onChange={event => setChartView(event.target.value)}
                className="btn btn-secondary btn-sm"
                style={{ appearance: 'auto', paddingRight: 8 }}
              >
                {Object.keys(CHART_VIEWS).map(view => <option key={view}>{view}</option>)}
              </select>
            </label>
          </div>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={activeChart.data} barSize={22}>
              <XAxis dataKey="month" axisLine={false} tickLine={false} tick={{ fontSize: 11, fill: '#9CA3AF' }} />
              <YAxis axisLine={false} tickLine={false} tick={{ fontSize: 11, fill: '#9CA3AF' }} unit="L" />
              <Tooltip content={<CustomTooltip />} cursor={{ fill: 'rgba(255,90,58,0.06)' }} />
              <Bar dataKey="value" fill="#FF5A3A" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Pie chart */}
        <div className="panel" style={{ padding: 20 }}>
          <div className="panel-header" style={{ marginBottom: 12 }}>
            <div>
              <div className="panel-title">Cost Distribution by Module</div>
              <div className="panel-sub">Latest calculation</div>
            </div>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
            <div style={{ position: 'relative', width: 140, height: 140, flexShrink: 0 }}>
              <ResponsiveContainer width={140} height={140}>
                <PieChart>
                  <Pie
                    data={PIE_DATA} cx={65} cy={65}
                    innerRadius={42} outerRadius={65}
                    dataKey="value" paddingAngle={2}
                  >
                    {PIE_DATA.map((entry, i) => (
                      <Cell key={i} fill={entry.color} />
                    ))}
                  </Pie>
                </PieChart>
              </ResponsiveContainer>
              <div style={{
                position: 'absolute', inset: 0,
                display: 'flex', flexDirection: 'column',
                alignItems: 'center', justifyContent: 'center',
                pointerEvents: 'none',
              }}>
                <span style={{ fontFamily: 'Manrope', fontSize: 16, fontWeight: 800 }}>₹18.42</span>
                <span style={{ fontSize: 9, color: '#9CA3AF' }}>Total Cost</span>
              </div>
            </div>
            <div style={{ flex: 1 }}>
              {PIE_DATA.map(d => (
                <div key={d.name} style={{ display: 'flex', alignItems: 'center', gap: 7, marginBottom: 5, fontSize: 11 }}>
                  <div style={{ width: 8, height: 8, borderRadius: 2, background: d.color, flexShrink: 0 }} />
                  <span style={{ flex: 1, color: 'var(--muted)' }}>{d.name}</span>
                  <strong style={{ fontFamily: 'Manrope' }}>{d.value}%</strong>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* ── Recent Estimates + Quick Actions ────────────── */}
      <div className="grid-col-6-4">
        {/* Table */}
        <div className="panel" style={{ padding: 0, overflow: 'hidden' }}>
          <div style={{ padding: '16px 20px', borderBottom: '1px solid var(--line)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <div>
              <div className="panel-title">Recent Estimates</div>
              <div className="panel-sub">Latest cost calculations</div>
            </div>
            <button
              className="btn btn-ghost btn-sm"
              onClick={() => navigate('/estimates')}
              style={{ display: 'flex', alignItems: 'center', gap: 4, color: 'var(--orange)' }}
            >
              View all <ChevronRight size={14} />
            </button>
          </div>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>#</th>
                  <th>Customer</th>
                  <th>Product</th>
                  <th style={{ textAlign: 'right' }}>Order Qty</th>
                  <th style={{ textAlign: 'right' }}>Cost/Box</th>
                  <th>Status</th>
                  <th>Date</th>
                </tr>
              </thead>
              <tbody>
                {RECENT.map(r => (
                  <tr
                    key={r.id}
                    style={{ cursor: 'pointer' }}
                    onClick={() => navigate(`/estimates/${r.id}`)}
                  >
                    <td style={{ fontFamily: 'Manrope', fontWeight: 700, color: 'var(--orange)', fontSize: 11 }}>{r.id}</td>
                    <td><strong style={{ fontSize: 12 }}>{r.customer}</strong></td>
                    <td style={{ fontSize: 12 }}>{r.product}</td>
                    <td style={{ textAlign: 'right', fontFamily: 'Manrope', fontWeight: 600 }}>{r.qty.toLocaleString()}</td>
                    <td style={{ textAlign: 'right', fontFamily: 'Manrope', fontWeight: 700, color: 'var(--ink-2)' }}>₹ {r.costBox}</td>
                    <td><StatusPill status={r.status} /></td>
                    <td style={{ fontSize: 11, color: 'var(--muted-2)' }}>{r.date}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Quick Actions */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          <div className="panel">
            <div className="panel-title" style={{ marginBottom: 14 }}>Quick Actions</div>
            {[
              { label: 'New Estimate', sub: 'Start a new packaging cost estimate', path: '/estimator/new', primary: true },
              { label: 'Manage Customers', sub: 'View and edit customer records', path: '/customers', primary: false },
              { label: 'View Reports', sub: 'Analytics and cost intelligence', path: '/reports', primary: false },
            ].map(a => (
              <button
                key={a.label}
                onClick={() => navigate(a.path)}
                style={{
                  width: '100%', display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                  padding: '11px 14px', borderRadius: 8, marginBottom: 8,
                  background: a.primary ? 'var(--orange-light)' : 'var(--line-2)',
                  border: `1px solid ${a.primary ? 'var(--orange-border)' : 'transparent'}`,
                  cursor: 'pointer', textAlign: 'left',
                }}
              >
                <div>
                  <div style={{ fontSize: 13, fontWeight: 600, color: a.primary ? 'var(--orange)' : 'var(--ink-2)' }}>{a.label}</div>
                  <div style={{ fontSize: 11, color: 'var(--muted-2)', marginTop: 2 }}>{a.sub}</div>
                </div>
                <ArrowRight size={14} style={{ color: a.primary ? 'var(--orange)' : 'var(--muted-2)', flexShrink: 0 }} />
              </button>
            ))}
          </div>

          {/* Top modules */}
          <div className="panel">
            <div className="panel-title" style={{ marginBottom: 14 }}>Top Cost Drivers</div>
            {PIE_DATA.slice(0, 5).map(d => (
              <div key={d.name} style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 10 }}>
                <span style={{ width: 88, fontSize: 12, color: 'var(--muted)', flexShrink: 0 }}>{d.name}</span>
                <div className="bar-track">
                  <div className="bar-fill" style={{ width: `${d.value}%`, background: d.color }} />
                </div>
                <span style={{ fontSize: 11, fontWeight: 600, fontFamily: 'Manrope', width: 38, textAlign: 'right' }}>{d.value}%</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
