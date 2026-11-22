import { useState, useEffect, createContext, useContext, useRef } from 'react'
import { Routes, Route, Link, NavLink, Navigate, useParams, useNavigate, useLocation, useSearchParams } from 'react-router-dom'
import { api } from './api'
import { BRANCHES } from './branches'
import { useAsync, Notice, Field } from './ui'
import { VerifyPage, Issuer } from './credentials'
import { HashDemo } from './hashui'

/* ---------- auth state ---------- */
const AuthCtx = createContext(null)
const useAuth = () => useContext(AuthCtx)

function AuthProvider({ children }) {
  const [token, setToken] = useState(() => localStorage.getItem('token'))
  const [user, setUser] = useState(null)
  const [ready, setReady] = useState(!token)
  useEffect(() => {
    if (!token) { setUser(null); setReady(true); return }
    api.me(token).then(setUser).catch(() => { localStorage.removeItem('token'); setToken(null) }).finally(() => setReady(true))
  }, [token])
  const login = t => { localStorage.setItem('token', t); setToken(t) }
  const logout = () => { localStorage.removeItem('token'); setToken(null); setUser(null) }
  return <AuthCtx.Provider value={{ token, user, ready, login, logout }}>{children}</AuthCtx.Provider>
}

function Protected({ children }) {
  const { token, ready } = useAuth()
  if (!ready) return <div className="wrap" style={{ padding: 80 }}>Loading…</div>
  return token ? children : <Navigate to="/login" replace />
}

/* ---------- nav ---------- */
function Nav() {
  const { token, user, logout } = useAuth()
  const toggle = () => {
    const r = document.documentElement
    const dark = r.dataset.theme ? r.dataset.theme === 'dark' : matchMedia('(prefers-color-scheme:dark)').matches
    r.dataset.theme = dark ? 'light' : 'dark'
  }
  return (
    <nav>
      <div className="wrap">
        <Link className="logo" to="/"><i />Credia</Link>
        <div className="links">
          <NavLink to="/" end>Career paths</NavLink>
          <NavLink to="/verify">Verify a credential</NavLink>
          {token && <NavLink to="/dashboard">Dashboard</NavLink>}
        </div>
        <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
          <button className="icon-btn" onClick={toggle} aria-label="Toggle light or dark theme">◐</button>
          {token
            ? <button className="btn ghost" onClick={logout}>Log out{user ? `, ${user.name.split(' ')[0]}` : ''}</button>
            : <><Link className="btn ghost hide-sm" to="/login">Log in</Link><Link className="btn" to="/register">Get my identity</Link></>}
        </div>
      </div>
    </nav>
  )
}

/* ---------- career paths (all branches) ---------- */
function BranchExplorer() {
  const [i, setI] = useState(0)
  const [w, setW] = useState(false)
  const b = BRANCHES[i]
  useEffect(() => { setW(false); const t = setTimeout(() => setW(true), 40); return () => clearTimeout(t) }, [i])
  return (
    <>
      <div className="tabs" role="tablist">
        {BRANCHES.map((x, k) => <button key={x.n} role="tab" className="tab" aria-selected={k === i} onClick={() => setI(k)}>{x.n}</button>)}
      </div>
      <div className="panel" key={i}>
        <div className="box swap">
          <h3>Skills employers want</h3>
          <p className="idsub">Sample estimates until the resume model is connected.</p>
          {b.sk.map(s => (
            <div className="skill" key={s[0]}>
              <div className="row"><span>{s[0]}</span><span>{s[1]}%</span></div>
              <div className="bar"><b style={{ width: w ? s[1] + '%' : 0 }} /></div>
            </div>
          ))}
          <h3 style={{ marginTop: 28, fontSize: '1.1rem' }}>Roles you can grow into</h3>
          <div className="roles">{b.r.map(r => <span className="chip" key={r}>{r}</span>)}</div>
        </div>
        <div className="box swap">
          <h3>Your roadmap</h3>
          <ol className="road">
            {b.p.map((p, k) => <li key={p[0]} style={{ animationDelay: k * 0.09 + 's' }}><strong>{p[0]}: {p[1]}</strong><span>{p[2]}</span></li>)}
          </ol>
        </div>
      </div>
    </>
  )
}

/* ---------- landing ---------- */
function Landing() {
  const card = useRef(null)
  const move = e => {
    const el = card.current, b = el.getBoundingClientRect()
    const x = (e.clientX - b.left) / b.width, y = (e.clientY - b.top) / b.height
    el.style.transform = `rotateY(${(x - .5) * 14}deg) rotateX(${(.5 - y) * 14}deg)`
    el.style.setProperty('--mx', x * 100 + '%'); el.style.setProperty('--my', y * 100 + '%')
  }
  return (
    <>
      <header className="hero">
        <div className="orb a" /><div className="orb b" />
        <div className="wrap">
          <div>
            <h1 className="load l1">Prove what you’ve learned. Plan what’s next.</h1>
            <p className="lead load l2">One tamper-proof identity for your degrees, certificates and projects. Employers verify in seconds. AI maps a career path from what you can prove.</p>
            <div className="cta load l3"><Link className="btn" to="/register">Create my identity</Link><Link className="btn ghost" to="/verify">Verify a credential</Link></div>
            <div className="stack load l4"><span className="chip">Generative AI</span><span className="chip">Machine Learning</span><span className="chip">Blockchain</span><span className="chip">Cloud</span></div>
          </div>
          <div className="stage load l5" onPointerMove={move} onPointerLeave={() => (card.current.style.transform = '')}>
            <div className="idcard" ref={card}>
              <div className="idhead">
                <div style={{ display: 'flex', gap: 14, alignItems: 'center' }}>
                  <div className="avatar">AS</div>
                  <div><div className="idname">Aarav Sharma</div><div className="idsub">B.Tech, Computer Science</div></div>
                </div>
                <svg className="seal" viewBox="0 0 64 64" aria-hidden="true"><circle cx="32" cy="32" r="28" /><path d="M20 33l9 9 16-18" /></svg>
              </div>
              <ul className="creds">
                <li>B.Tech degree<span className="ok">Verified</span></li>
                <li>Cloud practitioner<span className="ok">Verified</span></li>
                <li>Internship, ML team<span className="ok">Verified</span></li>
              </ul>
            </div>
          </div>
        </div>
      </header>
      <section>
        <div className="wrap">
          <div className="sh"><h2>A path for every branch</h2><p className="lead">Pick your branch to see the skills employers ask for and a roadmap that starts where you are.</p></div>
          <BranchExplorer />
        </div>
      </section>
      <section style={{ paddingTop: 10 }}>
        <div className="wrap"><HashDemo /></div>
      </section>
    </>
  )
}

/* ---------- auth pages ---------- */
function Shell({ title, sub, children }) {
  return <div className="wrap auth"><div className="box swap"><h1 className="auth-h">{title}</h1><p className="lead" style={{ margin: '8px 0 22px' }}>{sub}</p>{children}</div></div>
}

function Login() {
  const { login } = useAuth(); const nav = useNavigate()
  const [f, setF] = useState({ email: '', password: '' }); const [s, run] = useAsync()
  const submit = async e => { e.preventDefault(); const r = await run(() => api.login(f.email, f.password)); if (r) { login(r.access_token); nav('/dashboard') } }
  return (
    <Shell title="Welcome back" sub="Log in to see your credentials and career path.">
      <form onSubmit={submit}>
        <Field label="Email" type="email" required value={f.email} onChange={e => setF({ ...f, email: e.target.value })} />
        <Field label="Password" type="password" required value={f.password} onChange={e => setF({ ...f, password: e.target.value })} />
        <Notice>{s.error}</Notice>
        {s.error.includes('verify your email') && <Link to="/verify-email">Verify your email</Link>}
        <button className="btn" disabled={s.busy}>{s.busy ? 'Logging in…' : 'Log in'}</button>
      </form>
      <p className="idsub" style={{ marginTop: 18 }}><Link to="/forgot">Forgot password?</Link> · <Link to="/register">Create an account</Link></p>
    </Shell>
  )
}

function Register() {
  const [f, setF] = useState({ name: '', email: '', password: '' }); const [s, run] = useAsync(); const [done, setDone] = useState(null)
  const submit = async e => { e.preventDefault(); if (f.password.length < 8) return alert('Use at least 8 characters.'); const r = await run(() => api.register(f.name, f.email, f.password)); if (r) setDone(r) }
  if (done) return (
    <Shell title="Check your email" sub={`We created your account for ${done.email}. Verify it to log in.`}>
      {done.verification_token
        ? <><Notice kind="ok">Dev mode: the backend returned your verification token.</Notice><Link className="btn" to={`/verify-email?token=${encodeURIComponent(done.verification_token)}`}>Verify now</Link></>
        : <Link className="btn" to="/verify-email">I have my token</Link>}
    </Shell>
  )
  return (
    <Shell title="Create your identity" sub="Free for students. Your credentials stay yours.">
      <form onSubmit={submit}>
        <Field label="Full name" required value={f.name} onChange={e => setF({ ...f, name: e.target.value })} />
        <Field label="Email" type="email" required value={f.email} onChange={e => setF({ ...f, email: e.target.value })} />
        <Field label="Password (8+ characters)" type="password" required minLength={8} value={f.password} onChange={e => setF({ ...f, password: e.target.value })} />
        <Notice>{s.error}</Notice>
        <button className="btn" disabled={s.busy}>{s.busy ? 'Creating…' : 'Create account'}</button>
      </form>
      <p className="idsub" style={{ marginTop: 18 }}>Already have one? <Link to="/login">Log in</Link></p>
    </Shell>
  )
}

function VerifyEmail() {
  const [q] = useSearchParams(); const [token, setToken] = useState(q.get('token') || ''); const [s, run] = useAsync(); const [msg, setMsg] = useState('')
  const submit = async e => { e.preventDefault(); const r = await run(() => api.verifyEmail(token)); if (r) setMsg(r.message) }
  return (
    <Shell title="Verify your email" sub="Paste the token from your verification email.">
      <form onSubmit={submit}>
        <Field label="Verification token" required value={token} onChange={e => setToken(e.target.value)} />
        <Notice>{s.error}</Notice><Notice kind="ok">{msg}</Notice>
        <button className="btn" disabled={s.busy}>Verify email</button>
      </form>
      {msg && <p style={{ marginTop: 16 }}><Link to="/login">Continue to log in</Link></p>}
    </Shell>
  )
}

function Forgot() {
  const [email, setEmail] = useState(''); const [token, setToken] = useState(''); const [pw, setPw] = useState('')
  const [step, setStep] = useState(1); const [s, run] = useAsync(); const [msg, setMsg] = useState('')
  const send = async e => { e.preventDefault(); const r = await run(() => api.forgot(email)); if (r) { setMsg(r.message); if (r.reset_token) setToken(r.reset_token); setStep(2) } }
  const reset = async e => { e.preventDefault(); const r = await run(() => api.reset(token, pw)); if (r) { setMsg(r.message); setStep(3) } }
  return (
    <Shell title="Reset your password" sub={step === 1 ? 'Enter your email and we’ll generate a reset token.' : step === 2 ? 'Enter the token and your new password.' : 'All set.'}>
      {step === 1 && <form onSubmit={send}><Field label="Email" type="email" required value={email} onChange={e => setEmail(e.target.value)} /><Notice>{s.error}</Notice><button className="btn" disabled={s.busy}>Send reset token</button></form>}
      {step === 2 && <form onSubmit={reset}><Notice kind="ok">{msg}</Notice><Field label="Reset token" required value={token} onChange={e => setToken(e.target.value)} /><Field label="New password" type="password" minLength={8} required value={pw} onChange={e => setPw(e.target.value)} /><Notice>{s.error}</Notice><button className="btn" disabled={s.busy}>Save new password</button></form>}
      {step === 3 && <><Notice kind="ok">{msg}</Notice><Link className="btn" to="/login">Log in</Link></>}
    </Shell>
  )
}

/* ---------- dashboard ---------- */
function ServiceStatus() {
  const [st, setSt] = useState({ auth: null, chain: null })
  const check = () => { setSt({ auth: null, chain: null }); api.health('/svc/auth/').then(v => setSt(p => ({ ...p, auth: v }))); api.health('/svc/chain/health').then(v => setSt(p => ({ ...p, chain: v }))) }
  useEffect(check, [])
  const dot = v => v === null ? 'wait' : v ? 'up' : 'down'
  return (
    <div className="status">
      <h3>Service status</h3>
      <div className="actions">
        <span className="chip"><i className={`dot ${dot(st.auth)}`} />Auth service</span>
        <span className="chip"><i className={`dot ${dot(st.chain)}`} />Blockchain service</span>
        <button className="mini" onClick={check}>Recheck</button>
      </div>
    </div>
  )
}

function Overview() {
  const { user, token } = useAuth(); const [msg, setMsg] = useState(''); const [s, run] = useAsync()
  const check = async () => { const r = await run(() => api.roleCheck(user.role.toLowerCase(), token)); if (r) setMsg(r.message) }
  return (
    <div className="box swap">
      <h3>Hello, {user.name}</h3>
      <p className="idsub">{user.email}</p>
      <div className="roles"><span className="chip">{user.role}</span></div>
      <p style={{ margin: '18px 0' }} className="lead">{user.role === 'STUDENT' ? 'Explore career paths for your branch, analyze your resume, or verify a credential.' : user.role === 'RECRUITER' ? 'Verify candidate credentials in seconds.' : 'Issue and revoke credentials from the issuer console.'}</p>
      <button className="btn ghost" onClick={check} disabled={s.busy}>Check my access</button>
      <Notice>{s.error}</Notice><Notice kind="ok">{msg}</Notice>
      <ServiceStatus />
    </div>
  )
}

function Resume() {
  const [file, setFile] = useState(null); const [text, setText] = useState(''); const [out, setOut] = useState(null); const [s, run] = useAsync()
  const submit = async e => { e.preventDefault(); const r = await run(() => api.analyzeResume(file, text)); if (r) setOut(r) }
  return (
    <div className="box swap">
      <h3>Resume analysis</h3>
      <p className="idsub">Upload a text-based PDF or paste your resume. Skills and entities are extracted by the ML service.</p>
      <form onSubmit={submit} style={{ marginTop: 16 }}>
        <label>PDF resume<input type="file" accept="application/pdf" onChange={e => setFile(e.target.files[0])} /></label>
        <label>Or paste text<textarea rows={5} value={text} onChange={e => setText(e.target.value)} /></label>
        <Notice>{s.error && `${s.error}. The resume analysis API isn’t exposed yet (feature/resume-analysis only has the Python modules).`}</Notice>
        <button className="btn" disabled={s.busy || (!file && !text.trim())}>{s.busy ? 'Analyzing…' : 'Analyze resume'}</button>
      </form>
      {out && <pre className="mono out">{JSON.stringify(out, null, 2)}</pre>}
    </div>
  )
}

function Dashboard() {
  const { user } = useAuth(); const [tab, setTab] = useState('overview')
  if (!user) return null
  const tabs = [['overview', 'Overview'], ...(user.role === 'STUDENT' ? [['paths', 'Career paths'], ['resume', 'Resume']] : []), ...(user.role === 'ADMIN' ? [['issuer', 'Issuer console']] : [])]
  return (
    <div className="wrap" style={{ padding: '44px 22px 80px' }}>
      <h1 className="auth-h" style={{ marginBottom: 22 }}>Your dashboard</h1>
      <div className="tabs">{tabs.map(([k, l]) => <button key={k} className="tab" aria-selected={tab === k} onClick={() => setTab(k)}>{l}</button>)}<Link className="tab" to="/verify">Verify a credential</Link></div>
      {tab === 'overview' && <Overview />}
      {tab === 'paths' && <BranchExplorer />}
      {tab === 'resume' && <Resume />}
      {tab === 'issuer' && <Issuer />}
    </div>
  )
}

/* ---------- app ---------- */
export default function App() {
  const loc = useLocation()
  useEffect(() => window.scrollTo(0, 0), [loc.pathname])
  return (
    <AuthProvider>
      <Nav />
      <main key={loc.pathname.split('/')[1] || 'home'} className="page">
        <Routes>
          <Route path="/" element={<Landing />} />
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
          <Route path="/verify-email" element={<VerifyEmail />} />
          <Route path="/forgot" element={<Forgot />} />
          <Route path="/verify" element={<VerifyPage />} />
          <Route path="/verify/:id" element={<VerifyPage />} />
          <Route path="/dashboard" element={<Protected><Dashboard /></Protected>} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
      <footer><div className="wrap"><span>© 2026 Credia — Smart Digital Identity &amp; Career Ecosystem</span><span>Verified by design</span></div></footer>
    </AuthProvider>
  )
}
