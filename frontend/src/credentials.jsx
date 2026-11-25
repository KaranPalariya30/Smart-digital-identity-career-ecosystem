import { useState, useEffect } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api } from './api'
import { sameHash } from './hash'
import { useAsync, Notice, Field, Seal, CopyBtn } from './ui'
import { FilePick, Hash, Flow } from './hashui'

const STATUS = {
  VERIFIED: { tone: 'ok', title: 'Credential verified', text: 'This credential matches the record on the blockchain.' },
  REVOKED: { tone: 'warn', title: 'Credential revoked', text: 'The issuer has withdrawn this credential.' },
  INVALID: { tone: 'bad', title: 'Document doesn’t match', text: 'The file you added differs from the one that was registered.' },
  NOT_FOUND: { tone: 'bad', title: 'Credential not found', text: 'No credential exists with this ID. Check the ID and try again.' },
  DEPLOYMENT_MISMATCH: { tone: 'bad', title: 'Recorded on another deployment', text: 'This credential was registered on a different contract deployment.' },
}

/* Public page. The QR code opens /verify/:id. */
export function VerifyPage() {
  const { id: pid } = useParams()
  const [id, setId] = useState(pid || '')
  const [file, setFile] = useState(null), [hash, setHash] = useState('')
  const [res, setRes] = useState(null), [meta, setMeta] = useState(null), [used, setUsed] = useState('')
  const [s, run] = useAsync()

  const check = async (cid, f, h) => {
    setRes(null); setMeta(null); setUsed('')
    const r = await run(() => api.verifyCredential(cid, f))
    if (!r) return
    setRes(r); setUsed(f ? h : '')
    api.credential(cid).then(setMeta).catch(() => {})
  }
  useEffect(() => { if (pid) check(pid, null, '') }, [pid])

  const submit = e => {
    e.preventDefault()
    const cid = id.trim()
    window.history.replaceState(null, '', `/verify/${encodeURIComponent(cid)}`)
    check(cid, file, hash)
  }
  const clear = () => { setRes(null); setMeta(null); setUsed(''); setFile(null); setHash('') }

  const st = res && STATUS[res.status]
  const compared = used && ['VERIFIED', 'REVOKED', 'INVALID'].includes(res?.status)
  const flow = [
    [file ? 'Fingerprint your file' : 'Enter the ID', file && !hash ? 'now' : 'done'],
    ['Ask the service', s.busy ? 'now' : res ? 'done' : 'todo'],
    ['Compare with the chain', res ? (res.status === 'VERIFIED' ? 'done' : 'bad') : 'todo'],
  ]
  return (
    <div className="wrap auth wide">
      <div className="box swap">
        <h1 className="auth-h">Verify a credential</h1>
        <p className="lead" style={{ margin: '8px 0 22px' }}>Enter the credential ID or scan its QR code. Add the original file for the strongest check.</p>
        <Flow steps={flow} />
        <form onSubmit={submit}>
          <Field label="Credential ID" placeholder="CRED-XXXXXXXXXXXX" required value={id} onChange={e => setId(e.target.value)} />
          <FilePick label="Original document (optional)" file={file} hash={hash} onChange={(f, h) => { setFile(f); setHash(h) }} />
          <Notice>{s.error}</Notice>
          <div className="actions">
            <button className="btn" disabled={s.busy || (file && !hash)}>{s.busy ? 'Checking…' : 'Verify credential'}</button>
            {(res || file) && <button type="button" className="btn ghost" onClick={clear}>Clear</button>}
          </div>
        </form>

        {st && (
          <div className={`result ${st.tone}`} key={res.status + res.credential_id + used}>
            <Seal tone={st.tone === 'ok' ? 'ok' : 'bad'} />
            <div style={{ minWidth: 0, flex: 1 }}>
              <h2>{st.title}</h2><p>{st.text}</p>
              <dl>
                {meta && <><dt>Credential</dt><dd>{meta.certificate_name}{meta.certificate_type ? ` (${meta.certificate_type})` : ''}</dd></>}
                {(res.issued_at || meta?.issued_at) && <><dt>Issued</dt><dd>{new Date(res.issued_at || meta.issued_at).toLocaleDateString()}</dd></>}
                {res.issuer && <><dt>Issuer</dt><dd className="mono">{res.issuer}</dd></>}
                {meta?.contract_address && <><dt>Contract</dt><dd className="mono">{meta.contract_address}</dd></>}
                {meta?.blockchain_tx_hash && <><dt>Transaction</dt><dd className="mono">{meta.blockchain_tx_hash}</dd></>}
                {meta?.skills?.length > 0 && <><dt>Verifies skills</dt><dd>{meta.skills.join(', ')}</dd></>}
              </dl>
              {compared && (
                <div className="cmp">
                  <div className="lbl">Your file’s fingerprint</div>
                  <Hash value={used} mark={res.status === 'INVALID' ? 'bad' : 'ok'} />
                  {meta?.document_hash && (<><div className="lbl" style={{ marginTop: 12 }}>Fingerprint recorded at issue time</div><Hash value={meta.document_hash} mark="ok" /></>)}
                  <p>{res.status === 'INVALID' ? 'This fingerprint is not the one sealed on the blockchain. The file was changed, or it is a different document.' : 'This fingerprint matches the one sealed on the blockchain.'}</p>
                </div>
              )}
              {!used && res.status === 'VERIFIED' && <p className="idsub" style={{ marginTop: 14 }}>Checked against the stored record. Add the original file to confirm the document itself.</p>}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

/* Issuer console (ADMIN). Uses the logged-in user's token; the blockchain
   service checks the role, so there is no separate service token to paste. */
export function Issuer({ token }) {
  const [f, setF] = useState({ userId: '', name: '', type: '', skills: '' })
  const [file, setFile] = useState(null), [hash, setHash] = useState('')
  const [res, setRes] = useState(null), [rid, setRid] = useState(''), [msg, setMsg] = useState(''), [sure, setSure] = useState(false)
  const [s, run] = useAsync(), [s2, run2] = useAsync()

  const issue = async e => {
    e.preventDefault()
    const r = await run(() => api.issue({ ...f, file }, token))
    if (r) setRes(r)
  }
  const revoke = async e => {
    e.preventDefault()
    if (!sure) { setSure(true); setTimeout(() => setSure(false), 4000); return }
    setSure(false); setMsg('')
    const r = await run2(() => api.revoke(rid.trim(), token))
    if (r) setMsg(`Revoked. Transaction ${r.blockchain_tx_hash}`)
  }
  const again = () => { setRes(null); setFile(null); setHash(''); setF({ ...f, name: '', type: '', skills: '' }) }
  const matches = res && sameHash(hash, res.document_hash)
  const flow = [
    ['Fingerprint in browser', file ? (hash ? 'done' : 'now') : 'todo'],
    ['Seal on blockchain', s.busy ? 'now' : res ? 'done' : 'todo'],
    ['Fingerprints match', res ? (matches ? 'done' : 'bad') : 'todo'],
  ]
  return (
    <div className="panel">
      <div className="box swap">
        <h3>Issue a credential</h3>
        <p className="idsub">The service hashes the document and writes only the hash to the blockchain.</p>
        <Flow steps={flow} />
        <form onSubmit={issue}>
          <Field label="Student user ID (shown on the student’s Overview tab)" required inputMode="numeric" placeholder="e.g. 3" value={f.userId} onChange={e => setF({ ...f, userId: e.target.value })} />
          <Field label="Certificate name" required value={f.name} onChange={e => setF({ ...f, name: e.target.value })} />
          <Field label="Type (optional)" value={f.type} onChange={e => setF({ ...f, type: e.target.value })} />
          <Field label="Skills this verifies (optional, comma-separated)" placeholder="python, react, sql" value={f.skills} onChange={e => setF({ ...f, skills: e.target.value })} />
          <FilePick label="Document" required file={file} hash={hash} onChange={(x, h) => { setFile(x); setHash(h) }} />
          <Notice>{s.error}</Notice>
          <div className="actions"><button className="btn" disabled={s.busy || !hash}>{s.busy ? 'Sealing…' : 'Seal to blockchain'}</button></div>
        </form>
      </div>

      <div className="stack-col">
        {res && (
          <div className="box swap">
            <h3>Credential sealed</h3>
            <div className="sealed">
              <img className="qr" alt="QR code linking to the verification page" src={`data:image/png;base64,${res.qr_code_base64}`} />
              <div className={`match ${matches ? 'ok' : 'bad'}`}><Seal tone={matches ? 'ok' : 'bad'} /><span>{matches ? 'Browser and server fingerprints match' : 'Fingerprints differ. Do not share this credential.'}</span></div>
            </div>
            <dl className="kv">
              <dt>ID</dt><dd className="mono">{res.credential_id}</dd>
              <dt>Link</dt><dd className="mono">{res.verification_url}</dd>
              {res.skills?.length > 0 && <><dt>Skills</dt><dd>{res.skills.join(', ')}</dd></>}
              <dt>Browser</dt><dd><Hash value={hash} mark={matches ? 'ok' : 'bad'} /></dd>
              <dt>Server</dt><dd><Hash value={res.document_hash} mark={matches ? 'ok' : 'bad'} /></dd>
              <dt>Transaction</dt><dd className="mono">{res.blockchain_tx_hash}</dd>
            </dl>
            <div className="actions">
              <Link className="btn" to={`/verify/${res.credential_id}`}>Open verification page</Link>
              <a className="btn ghost" download={`${res.credential_id}-qr.png`} href={`data:image/png;base64,${res.qr_code_base64}`}>Download QR</a>
              <CopyBtn text={res.verification_url} label="Copy link" />
              <button className="btn ghost" onClick={again}>Issue another</button>
            </div>
          </div>
        )}
        <div className="box">
          <h3>Revoke a credential</h3>
          <form onSubmit={revoke} style={{ marginTop: 14 }}>
            <Field label="Credential ID" required value={rid} onChange={e => setRid(e.target.value)} />
            <Notice>{s2.error}</Notice><Notice kind="ok">{msg}</Notice>
            <div className="actions"><button className={`btn ${sure ? 'danger' : 'ghost'}`} disabled={s2.busy}>{s2.busy ? 'Revoking…' : sure ? 'Click again to confirm' : 'Revoke'}</button></div>
          </form>
        </div>
      </div>
    </div>
  )
}

/* A student's own credentials. Active ones feed the resume analysis as verified skills. */
export function MyCredentials({ token, userId }) {
  const [list, setList] = useState(null), [s, run] = useAsync()
  useEffect(() => { run(() => api.myCredentials(token)).then(r => r && setList(r)) }, [token])
  return (
    <div className="box swap">
      <h3>My credentials</h3>
      <p className="idsub">Credentials sealed on the blockchain for your account (user ID {userId}). Active ones count as verified skills in your resume analysis.</p>
      <Notice>{s.error}</Notice>
      {list === null && !s.error && <p className="idsub" style={{ marginTop: 14 }}>Loading…</p>}
      {list && list.length === 0 && <p className="lead" style={{ marginTop: 14 }}>No credentials yet. Give your institution your user ID ({userId}) and they can issue one.</p>}
      {list && list.map(c => (
        <div className="cred" key={c.credential_id}>
          <div style={{ minWidth: 0 }}>
            <strong>{c.certificate_name}</strong>{c.certificate_type ? <span className="idsub"> · {c.certificate_type}</span> : null}
            <div className="mono idsub">{c.credential_id} · {new Date(c.issued_at).toLocaleDateString()}</div>
            <div className="res-chips">{c.skills.map(k => <span className="chip" key={k}>{k}</span>)}</div>
          </div>
          <div className="cred-side">
            <span className={`chip ${c.verification_status === 'active' ? 'ok' : 'miss'}`}>{c.verification_status}</span>
            <Link className="mini" to={`/verify/${c.credential_id}`}>Verify</Link>
          </div>
        </div>
      ))}
    </div>
  )
}
