// All calls are relative: nginx (Docker/K8s) or the Vite dev proxy routes /api to FastAPI.

export class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.status = status;
  }
}

function describeDetail(detail, fallback) {
  if (!detail) return fallback;
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((d) => {
        const field = Array.isArray(d.loc) ? d.loc.filter((p) => p !== 'body').join('.') : '';
        return field ? `${field}: ${d.msg}` : d.msg;
      })
      .join('; ');
  }
  return fallback;
}

async function request(path, { method = 'GET', body } = {}) {
  let res;
  try {
    res = await fetch(path, {
      method,
      headers: body ? { 'Content-Type': 'application/json' } : undefined,
      body: body ? JSON.stringify(body) : undefined,
    });
  } catch {
    throw new ApiError('Cannot reach the GearLoop API', 0);
  }
  if (res.status === 204) return null;
  let data = null;
  try {
    data = await res.json();
  } catch {
    /* non-JSON body (e.g. proxy error page) */
  }
  if (!res.ok) {
    throw new ApiError(describeDetail(data?.detail, `Request failed (${res.status})`), res.status);
  }
  return data;
}

function qs(params) {
  const search = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => {
    if (v !== undefined && v !== null && v !== '') search.set(k, v);
  });
  const s = search.toString();
  return s ? `?${s}` : '';
}

export const api = {
  stats: () => request('/api/stats'),
  items: ({ status, q } = {}) => request(`/api/items${qs({ status, q })}`),
  createItem: (item) => request('/api/items', { method: 'POST', body: item }),
  updateItem: (id, changes) => request(`/api/items/${id}`, { method: 'PUT', body: changes }),
  deleteItem: (id) => request(`/api/items/${id}`, { method: 'DELETE' }),
  loans: ({ active, limit } = {}) => request(`/api/loans${qs({ active, limit })}`),
  checkOut: (loan) => request('/api/loans', { method: 'POST', body: loan }),
  returnLoan: (id) => request(`/api/loans/${id}/return`, { method: 'POST' }),
};
