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
              </dl>
              {compared && (
                <div className="cmp">
                  <div className="lbl">Your file’s fingerprint</div>
                  <Hash value={used} mark={res.status === 'INVALID' ? 'bad' : 'ok'} />
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

/* Issuer console (ADMIN). register/revoke need the blockchain service token. */
export function Issuer() {
  const [svc, setSvc] = useState(() => sessionStorage.getItem('svc') || '')
  const [f, setF] = useState({ userId: '', name: '', type: '' })
  const [file, setFile] = useState(null), [hash, setHash] = useState('')
  const [res, setRes] = useState(null), [rid, setRid] = useState(''), [msg, setMsg] = useState(''), [sure, setSure] = useState(false)
  const [s, run] = useAsync(), [s2, run2] = useAsync()

  const issue = async e => {
    e.preventDefault(); sessionStorage.setItem('svc', svc)
    const r = await run(() => api.issue({ ...f, file }, svc))
    if (r) setRes(r)
  }
  const revoke = async e => {
    e.preventDefault()
    if (!sure) { setSure(true); setTimeout(() => setSure(false), 4000); return }
    setSure(false); setMsg('')
    const r = await run2(() => api.revoke(rid.trim(), svc))
    if (r) setMsg(`Revoked. Transaction ${r.blockchain_tx_hash}`)
  }
  const again = () => { setRes(null); setFile(null); setHash(''); setF({ ...f, name: '', type: '' }) }
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
          <Field label="Service token" type="password" required value={svc} onChange={e => setSvc(e.target.value)} />
          <label>Student user ID (UUID)
            <div className="inline"><input required value={f.userId} onChange={e => setF({ ...f, userId: e.target.value })} /><button type="button" className="mini" onClick={() => setF({ ...f, userId: crypto.randomUUID() })}>New</button></div>
          </label>
          <Field label="Certificate name" required value={f.name} onChange={e => setF({ ...f, name: e.target.value })} />
          <Field label="Type (optional)" value={f.type} onChange={e => setF({ ...f, type: e.target.value })} />
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
