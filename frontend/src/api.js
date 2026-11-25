// One place for every backend call. Shapes mirror the FastAPI services in
// backend/auth-service, backend/blockchain-service and backend/resume-service.
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
    const d = data.detail ?? data.error   // resume service reports 400/501 as { error }
    throw new Error(typeof d === 'string' ? d : Array.isArray(d) ? d.map(x => x.msg).join(', ') : `Request failed (${r.status})`)
  }
  return data
}

const A = '/api/auth', C = '/api/blockchain/credentials', R = '/api/resume'

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
  myCredentials: token => req(`${C}/mine`, { token }),
  verifyCredential: (id, file) => {
    const path = `${C}/${encodeURIComponent(id)}/verify`
    // No file (opening a QR link): send no body at all. An empty multipart form is rejected by the server.
    if (!file) return req(path, { method: 'POST' })
    const form = new FormData(); form.append('file', file)
    return req(path, { method: 'POST', form })
  },
  // Issue and revoke use the logged-in user's token; the blockchain service
  // allows it when the user's role is an issuer role (ADMIN by default).
  issue: ({ userId, name, type, skills, file }, token) => {
    const form = new FormData(); form.append('file', file)
    const q = new URLSearchParams({ user_id: String(userId).trim(), certificate_name: name })
    if (type) q.set('certificate_type', type)
    if (skills && skills.trim()) q.set('skills', skills)
    return req(`${C}?${q}`, { method: 'POST', form, token })
  },
  revoke: (id, token) => req(`${C}/${encodeURIComponent(id)}/revoke`, { method: 'POST', token }),

  // Resume service (the dev proxy maps /api/resume/* to its /api/v1/*).
  roles: token => req(`${R}/roles`, { token }),
  analyzeResume: ({ file, text, targetRole, jdText, verifiedSkills }, token) => {
    const form = new FormData()
    if (file) form.append('resume_file', file); else form.append('resume_text', text)
    if (jdText && jdText.trim()) { form.append('jd_text', jdText); form.append('mode', 'jd') }
    else { form.append('target_role', targetRole); form.append('mode', 'role') }
    // Skills backed by sealed credentials: the glue between blockchain and resume.
    if (verifiedSkills && verifiedSkills.length) form.append('verified_skills', verifiedSkills.join(','))
    return req(`${R}/analyze`, { method: 'POST', form, token })
  },
}
