import React, { useState } from 'react';
import { Download, TrendingUp, Users, BarChart3, Activity } from 'lucide-react';
import {
  BarChart, Bar, LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, Legend, CartesianGrid
} from 'recharts';
import { MetricCard } from '../components/CostCard';

const MONTHLY = [
  { month: 'Jan', value: 8, estimates: 9 }, { month: 'Feb', value: 12, estimates: 11 },
  { month: 'Mar', value: 7, estimates: 8 }, { month: 'Apr', value: 16, estimates: 14 },
  { month: 'May', value: 11, estimates: 12 }, { month: 'Jun', value: 19, estimates: 17 },
  { month: 'Jul', value: 14, estimates: 13 }, { month: 'Aug', value: 22, estimates: 20 },
  { month: 'Sep', value: 18, estimates: 20 },
];
const PIE_DATA = [
  { name: 'Kappa', value: 35.5, color: '#FF5A3A' },
  { name: 'Printing', value: 18.2, color: '#FF7A5C' },
  { name: 'Lamination', value: 13.1, color: '#FFB09C' },
  { name: 'Glue', value: 8.4, color: '#FFC352' },
  { name: 'Punching', value: 9.0, color: '#86B9EE' },
  { name: 'Others', value: 15.8, color: '#DCE1E5' },
];
const TOP_CUSTOMERS = [
  { name: 'Luxe Beauty', value: 28, color: '#FF5A3A' },
  { name: 'Aura Skincare', value: 18, color: '#FF7A5C' },
  { name: 'Veda Naturals', value: 12, color: '#FFB09C' },
  { name: 'Elite Brands', value: 10, color: '#FFC352' },
  { name: 'Others', value: 32, color: '#DCE1E5' },
];
const ORDER_TREND = [
  { month: 'Jan', value: 14 }, { month: 'Feb', value: 18 }, { month: 'Mar', value: 12 },
  { month: 'Apr', value: 24 }, { month: 'May', value: 16 }, { month: 'Jun', value: 28 },
  { month: 'Jul', value: 20 }, { month: 'Aug', value: 32 }, { month: 'Sep', value: 26 },
];

const TABS = ['Summary', 'Cost Analysis', 'Customer Analysis', 'Module Analysis', 'Trend Analysis'];

const CustomTooltip = ({ active, payload, label }) => {
  if (active && payload?.length) {
    return (
      <div style={{ background: '#fff', border: '1px solid #E5E9EE', borderRadius: 8, padding: '8px 14px', fontSize: 12, boxShadow: '0 4px 12px rgba(0,0,0,0.1)' }}>
        <div style={{ fontWeight: 600, marginBottom: 4 }}>{label}</div>
        {payload.map((p, i) => (
          <div key={i} style={{ color: p.color }}>
            {p.name === 'value' ? `₹ ${p.value}L` : `${p.value} estimates`}
          </div>
        ))}
      </div>
    );
  }
  return null;
};

export default function Reports() {
  const [activeTab, setActiveTab] = useState('Summary');
  const [dateRange, setDateRange] = useState('01 Sep 2026 – 30 Sep 2026');

  return (
    <div className="page-content">
      {/* Header */}
      <div className="page-header">
        <div className="page-header-left">
          <span className="eyebrow">Reports & Analytics</span>
          <h1 style={{ marginTop: 4 }}>Reports & Analytics</h1>
          <p>Business insights and detailed reports</p>
        </div>
        <div className="page-header-right">
          <div style={{ border: '1px solid var(--line)', borderRadius: 8, padding: '8px 14px', fontSize: 12, color: 'var(--muted)', background: 'var(--panel)' }}>
            📅 {dateRange}
          </div>
          <button className="btn btn-secondary">
            <Download size={14} /> Export
          </button>
        </div>
      </div>

      {/* Tabs */}
      <div className="tabs-bar">
        {TABS.map(t => (
          <button key={t} className={`tab-btn ${activeTab === t ? 'active' : ''}`} onClick={() => setActiveTab(t)}>{t}</button>
        ))}
      </div>

      {/* Metrics */}
      <div className="metric-grid" style={{ marginBottom: 20 }}>
        <MetricCard label="Total Estimates" value="124" detail="+13% vs last month" detailType="up" icon={BarChart3} iconColor="orange" />
        <MetricCard label="Total Order Value" value="₹ 28,45,000" detail="+15% vs last month" detailType="up" icon={TrendingUp} iconColor="green" />
        <MetricCard label="Avg. Cost / Box" value="₹ 18.42" detail="+6% vs last month" detailType="up" icon={Activity} iconColor="blue" />
        <MetricCard label="Conversion Rate" value="68%" detail="+4% vs last month" detailType="up" icon={Users} iconColor="purple" />
      </div>

      {/* Charts row 1 */}
      <div className="grid-col-6-4" style={{ marginBottom: 20 }}>
        {/* Bar: Estimate Trend */}
        <div className="panel">
          <div className="panel-header">
            <div>
              <div className="panel-title">Estimate Trend</div>
              <div className="panel-sub">Monthly estimate count & order value (₹ Lakhs)</div>
            </div>
          </div>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={MONTHLY} barSize={18} barGap={4}>
              <XAxis dataKey="month" axisLine={false} tickLine={false} tick={{ fontSize: 11, fill: '#9CA3AF' }} />
              <YAxis axisLine={false} tickLine={false} tick={{ fontSize: 11, fill: '#9CA3AF' }} />
              <Tooltip content={<CustomTooltip />} cursor={{ fill: 'rgba(255,90,58,0.06)' }} />
              <Bar dataKey="value" name="value" fill="#FF5A3A" radius={[4, 4, 0, 0]} />
              <Bar dataKey="estimates" name="estimates" fill="#FFB09C" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Pie: Top Customers */}
        <div className="panel">
          <div className="panel-header">
            <div>
              <div className="panel-title">Top Customers</div>
              <div className="panel-sub">By order value share</div>
            </div>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
            <ResponsiveContainer width={130} height={130}>
              <PieChart>
                <Pie data={TOP_CUSTOMERS} cx={60} cy={60} innerRadius={38} outerRadius={60} dataKey="value" paddingAngle={2}>
                  {TOP_CUSTOMERS.map((e, i) => <Cell key={i} fill={e.color} />)}
                </Pie>
              </PieChart>
            </ResponsiveContainer>
            <div style={{ flex: 1 }}>
              {TOP_CUSTOMERS.map(c => (
                <div key={c.name} style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
                  <div style={{ width: 8, height: 8, borderRadius: 2, background: c.color, flexShrink: 0 }} />
                  <span style={{ flex: 1, fontSize: 12, color: 'var(--muted)' }}>{c.name}</span>
                  <strong style={{ fontFamily: 'Manrope', fontSize: 12 }}>{c.value}%</strong>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Charts row 2 */}
      <div className="grid-col-6-4" style={{ marginBottom: 20 }}>
        {/* Pie: Cost Distribution */}
        <div className="panel">
          <div className="panel-header">
            <div>
              <div className="panel-title">Cost Distribution by Module</div>
              <div className="panel-sub">Average across all estimates</div>
            </div>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 24 }}>
            <div style={{ position: 'relative', flexShrink: 0 }}>
              <ResponsiveContainer width={150} height={150}>
                <PieChart>
                  <Pie data={PIE_DATA} cx={70} cy={70} innerRadius={45} outerRadius={68} dataKey="value" paddingAngle={2}>
                    {PIE_DATA.map((e, i) => <Cell key={i} fill={e.color} />)}
                  </Pie>
                </PieChart>
              </ResponsiveContainer>
              <div style={{
                position: 'absolute', inset: 0, display: 'flex', flexDirection: 'column',
                alignItems: 'center', justifyContent: 'center', pointerEvents: 'none',
              }}>
                <span style={{ fontFamily: 'Manrope', fontSize: 18, fontWeight: 800 }}>₹18.42</span>
                <span style={{ fontSize: 10, color: 'var(--muted-2)' }}>Avg Cost</span>
              </div>
            </div>
            <div style={{ flex: 1 }}>
              {PIE_DATA.map(d => (
                <div key={d.name} style={{ marginBottom: 8 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 3, fontSize: 12 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                      <div style={{ width: 8, height: 8, borderRadius: 2, background: d.color }} />
                      <span style={{ color: 'var(--muted)' }}>{d.name}</span>
                    </div>
                    <strong style={{ fontFamily: 'Manrope' }}>{d.value}%</strong>
                  </div>
                  <div className="bar-track" style={{ height: 5 }}>
                    <div className="bar-fill" style={{ width: `${d.value}%`, background: d.color }} />
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Line: Order Value Trend */}
        <div className="panel">
          <div className="panel-header">
            <div>
              <div className="panel-title">Order Value Trend</div>
              <div className="panel-sub">Monthly (₹ Lakhs)</div>
            </div>
          </div>
          <ResponsiveContainer width="100%" height={180}>
            <LineChart data={ORDER_TREND}>
              <XAxis dataKey="month" axisLine={false} tickLine={false} tick={{ fontSize: 11, fill: '#9CA3AF' }} />
              <YAxis axisLine={false} tickLine={false} tick={{ fontSize: 11, fill: '#9CA3AF' }} unit="L" />
              <Tooltip
                formatter={(v) => [`₹ ${v}L`, 'Order Value']}
                contentStyle={{ borderRadius: 8, fontSize: 12 }}
              />
              <CartesianGrid strokeDasharray="3 3" stroke="#F0F2F5" vertical={false} />
              <Line type="monotone" dataKey="value" stroke="#FF5A3A" strokeWidth={2.5} dot={{ r: 4, fill: '#FF5A3A' }} activeDot={{ r: 6 }} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Not Yet Configured modules */}
      <div className="panel">
        <div className="panel-header">
          <div className="panel-title">Module Performance Analytics</div>
          <div className="panel-sub">Advanced analytics per costing module</div>
        </div>
        <div style={{ padding: '32px', textAlign: 'center', color: 'var(--muted-2)' }}>
          <BarChart3 size={32} style={{ margin: '0 auto 10px', opacity: 0.4 }} />
          <div style={{ fontSize: 14, fontWeight: 600, color: 'var(--muted)', marginBottom: 6 }}>Not yet configured</div>
          <div style={{ fontSize: 12 }}>Module-level deep analytics will be available once more estimates are finalized.</div>
        </div>
      </div>
    </div>
  );
}
