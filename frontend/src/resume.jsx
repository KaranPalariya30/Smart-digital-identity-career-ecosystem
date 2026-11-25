import { useEffect, useMemo, useState } from 'react'
import { api } from './api'
import { useAsync, Notice } from './ui'

const Chips = ({ items, cls = '', verified = false }) => (
  <div className="res-chips">
    {items.length === 0 && <span className="idsub">None</span>}
    {items.map(s => (
      <span key={s.name || s} className={`chip ${cls}`}>
        {verified && s.verified ? '✓ ' : ''}{s.name || s}
      </span>
    ))}
  </div>
)

const List = ({ title, items }) => items?.length ? (
  <div className="res-block"><h4>{title}</h4><ul>{items.map((t, i) => <li key={i}>{t}</li>)}</ul></div>
) : null

function Result({ out, verified }) {
  const { score, skills, feedback, learning_path: path, meta } = out
  return (
    <div className="res-out swap">
      <div className="res-score">
        <div><b>{score.overall}</b><span>/100</span></div>
        <div>
          <strong>Grade {score.grade}</strong>
          <p className="idsub">{score.summary}</p>
          <p className="idsub">Scored against {meta.role_title || 'your pasted job description'}</p>
        </div>
      </div>

      {verified.length > 0 && (
        <p className="res-verified">
          <strong>{skills.verified_percentage}%</strong> of your matched skills are backed by credentials sealed on the blockchain
          ({verified.join(', ')}).
        </p>
      )}

      <div className="res-grid">
        <div className="res-block"><h4>Matched skills</h4><Chips items={skills.matched} cls="ok" verified /></div>
        <div className="res-block"><h4>Missing skills</h4><Chips items={skills.missing} cls="miss" /></div>
      </div>

      {path.length > 0 && (
        <div className="res-block">
          <h4>Suggested learning order</h4>
          <ol>{path.map(p => <li key={p.order}>{p.skill}{p.kind === 'prerequisite' ? <span className="idsub"> · prerequisite</span> : null}</li>)}</ol>
        </div>
      )}

      <div className="res-grid">
        <List title="Strengths" items={feedback.strengths} />
        <List title="Improve" items={feedback.improvements} />
      </div>
      <List title="Tips" items={feedback.tips} />
      {feedback.verdict && <p className="lead">{feedback.verdict}</p>}
    </div>
  )
}

export function Resume({ token }) {
  const [roles, setRoles] = useState([]), [role, setRole] = useState(''), [rolesErr, setRolesErr] = useState('')
  const [file, setFile] = useState(null), [text, setText] = useState(''), [jd, setJd] = useState('')
  const [creds, setCreds] = useState([]), [out, setOut] = useState(null)
  const [s, run] = useAsync()

  useEffect(() => {
    api.roles(token).then(r => { setRoles(r); setRole(x => x || r[0]?.id || '') }).catch(e => setRolesErr(e.message))
    api.myCredentials(token).then(setCreds).catch(() => setCreds([]))
  }, [token])

  // Skills proven by active, sealed credentials are passed to the analysis as verified.
  const verified = useMemo(
    () => [...new Set(creds.filter(c => c.verification_status === 'active').flatMap(c => c.skills))],
    [creds],
  )

  const submit = async e => {
    e.preventDefault()
    const r = await run(() => api.analyzeResume({ file, text, targetRole: role, jdText: jd, verifiedSkills: verified }, token))
    if (r) setOut(r)
  }
  const ready = (file || text.trim()) && (jd.trim() || role)

  return (
    <div className="box swap">
      <h3>Resume analysis</h3>
      <p className="idsub">Upload a text-based PDF or paste your resume, then pick a target role or paste a job description.</p>
      <form onSubmit={submit} style={{ marginTop: 16 }}>
        <label>PDF resume<input type="file" accept="application/pdf" onChange={e => setFile(e.target.files[0] || null)} /></label>
        <label>Or paste text<textarea rows={5} value={text} onChange={e => setText(e.target.value)} /></label>
        <label>Target role
          <select value={role} onChange={e => setRole(e.target.value)} disabled={!roles.length}>
            {roles.map(r => <option key={r.id} value={r.id}>{r.title}</option>)}
          </select>
        </label>
        <label>Or paste a job description (overrides the role)
          <textarea rows={4} value={jd} onChange={e => setJd(e.target.value)} />
        </label>
        <p className="idsub">
          {verified.length
            ? `Verified skills from your sealed credentials: ${verified.join(', ')}.`
            : 'No verified skills yet. Credentials issued to you with skills attached will count here.'}
        </p>
        <Notice>{rolesErr}</Notice>
        <Notice>{s.error}</Notice>
        <button className="btn" disabled={s.busy || !ready}>{s.busy ? 'Analyzing…' : 'Analyze resume'}</button>
      </form>
      {out && <Result out={out} verified={verified} />}
    </div>
  )
}
