// One place for every backend call. Shapes mirror the FastAPI code on the
// feature/authentication and feature/blockchain-verification branches.
async function req(url, { method = 'GET', json, form, token } = {}) {
  const headers = {}
  let body
  if (token) headers.Authorization = 'Bearer ' + token
  if (json) { headers['Content-Type'] = 'application/json'; body = JSON.stringify(json) }
  if (form) body = form
  let r
  try { r = await fetch(url, { method, headers, body }) }
  catch { throw new Error('Can’t reach the service. Check that the backend is running.') }
  const data = await r.json().catch(() => ({}))
  if (!r.ok) {
    const d = data.detail
    throw new Error(typeof d === 'string' ? d : Array.isArray(d) ? d.map(x => x.msg).join(', ') : `Request failed (${r.status})`)
  }
  return data
}

const A = '/api/auth', C = '/api/blockchain/credentials'

export const api = {
  health: async url => {
    const ctrl = new AbortController(); const t = setTimeout(() => ctrl.abort(), 3000)
    try { return (await fetch(url, { signal: ctrl.signal })).ok } catch { return false } finally { clearTimeout(t) }
  },
  register: (name, email, password) => req(`${A}/register`, { method: 'POST', json: { name, email, password } }),
  login: (email, password) => req(`${A}/login`, { method: 'POST', json: { email, password } }),
  me: token => req(`${A}/me`, { token }),
  verifyEmail: token => req(`${A}/verify-email`, { method: 'POST', json: { token } }),
  forgot: email => req(`${A}/forgot-password`, { method: 'POST', json: { email } }),
  reset: (token, new_password) => req(`${A}/reset-password`, { method: 'POST', json: { token, new_password } }),
  roleCheck: (role, token) => req(`${A}/${role}-only`, { token }),

  credential: id => req(`${C}/${encodeURIComponent(id)}`),
  verifyCredential: (id, file) => {
    const form = new FormData()
    if (file) form.append('file', file)
    return req(`${C}/${encodeURIComponent(id)}/verify`, { method: 'POST', form })
  },
  // register/revoke need the blockchain service's bearer token, not a user JWT.
  issue: ({ userId, name, type, file }, serviceToken) => {
    const form = new FormData(); form.append('file', file)
    const q = new URLSearchParams({ user_id: userId, certificate_name: name })
    if (type) q.set('certificate_type', type)
    return req(`${C}?${q}`, { method: 'POST', form, token: serviceToken })
  },
  revoke: (id, serviceToken) => req(`${C}/${encodeURIComponent(id)}/revoke`, { method: 'POST', token: serviceToken }),

  // Planned on feature/resume-analysis; no HTTP endpoint exists yet.
  analyzeResume: (file, text) => {
    const form = new FormData()
    if (file) form.append('file', file); else form.append('text', text)
    return req('/api/resume/analyze', { method: 'POST', form })
  },
}
