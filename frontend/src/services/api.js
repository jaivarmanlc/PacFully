/**
 * Pacfully API service layer.
 * Every request automatically attaches the stored JWT as a Bearer token.
 */

const BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

/** Read the JWT from localStorage (written by AuthContext after login). */
function getToken() {
  return localStorage.getItem('pac_token') || '';
}

async function request(method, path, body, responseType = 'json') {
  const headers = { 'Content-Type': 'application/json' };
  const tok = getToken();
  if (tok) headers['Authorization'] = `Bearer ${tok}`;

  const opts = { method, headers };
  if (body !== undefined) opts.body = JSON.stringify(body);

  const res = await fetch(`${BASE}${path}`, opts);

  if (res.status === 401) {
    if (localStorage.getItem('pac_testing_session') === 'true') {
      throw new Error('Backend authorization is unavailable in testing mode');
    }
    // Token expired or invalid — clear session and reload to /login
    localStorage.removeItem('pac_token');
    localStorage.removeItem('pac_user');
    window.location.href = '/login';
    throw new Error('Session expired');
  }

  if (!res.ok) {
    let msg = `API ${method} ${path} failed (${res.status})`;
    try { const j = await res.json(); msg = j.detail || msg; } catch {}
    throw new Error(msg);
  }

  if (res.status === 204) return null;
  if (responseType === 'blob') return res.blob();
  return res.json();
}

const get  = (path)       => request('GET',    path);
const post = (path, body) => request('POST',   path, body);
const put  = (path, body) => request('PUT',    path, body);
const del  = (path)       => request('DELETE', path);

// ── Health ─────────────────────────────────────────────────
export const checkHealth = () => get('/health');

export const extractLayout = async file => {
  const formData = new FormData();
  formData.append('file', file);
  const headers = {};
  const token = getToken();
  if (token) headers.Authorization = `Bearer ${token}`;
  const response = await fetch(`${BASE}/layout/extract`, { method: 'POST', headers, body: formData });
  if (!response.ok) {
    let message = `Unable to extract layout (${response.status})`;
    try { message = (await response.json()).detail || message; } catch {}
    throw new Error(message);
  }
  return response.json();
};

// ── Costing engine (stateless) ──────────────────────────────
export const calculateEstimate = (payload) => post('/estimates/calculate', payload);

// ── Estimates ───────────────────────────────────────────────
export const listEstimates    = ()    => get('/estimates');
export const getEstimate      = (id)  => get(`/estimates/${id}`);
export const saveEstimate     = (p)   => post('/estimates', p);
export const finalizeEstimate = (id)  => post(`/estimates/${id}/finalize`);
export const deleteEstimate   = (id)  => del(`/estimates/${id}`);

// ── Customers ───────────────────────────────────────────────
export const listCustomers  = ()    => get('/customers');
export const getCustomer    = (id)  => get(`/customers/${id}`);
export const createCustomer = (b)   => post('/customers', b);
export const deleteCustomer = (id)  => del(`/customers/${id}`);

// ── Master configuration ───────────────────────────────────
export const getMasterConfig = () => get('/master-config');
export const saveMasterConfig = (rates) => put('/master-config', { rates });
export const getFormulaConfig = () => get('/formulas');
export const saveFormulaConfig = (formulas) => put('/formulas', { formulas });
export const getSystemSettings = () => get('/settings');
export const saveSystemSettings = (settings) => put('/settings', settings);

// ── Quotations ──────────────────────────────────────────────
export const listQuotations  = ()    => get('/quotations');
export const getQuotation    = (id)  => get(`/quotations/${id}`);
export const getNextQuotationNumber = (docType) => get(`/quotations/next-number?doc_type=${encodeURIComponent(docType)}`);
export const createQuotation = (b)   => post('/quotations', b);
export const updateQuotation = (id, b) => put(`/quotations/${id}`, b);
export const previewQuotationPdf = (b) => request('POST', '/quotations/preview', b, 'blob');
export const getQuotationPdf = (id) => request('GET', `/quotations/${id}/pdf`, undefined, 'blob');
export const deleteQuotation = (id)  => del(`/quotations/${id}`);

/** PDF URL for inline preview or download. */
export const pdfUrl = (quotationId) => `${BASE}/quotations/${quotationId}/pdf`;

// ── Audit log ───────────────────────────────────────────────
export const getAuditLog = () => get('/audit-log');

// ── Auth ─────────────────────────────────────────────────────
export const getMe        = ()  => get('/auth/me');
export const listUsers    = ()  => get('/auth/users');
export const createUser   = (b) => post('/auth/users', b);
export const updateUserRole = (id, role) => put(`/auth/users/${id}`, { role });
export const deleteUser   = (id)=> del(`/auth/users/${id}`);
