import { useState, useEffect, useRef } from 'react'
import { sha256Hex, hashSupported } from './hash'
import { CopyBtn } from './ui'

const HEX = '0123456789abcdef'
const fmt = n => n < 1024 ? n + ' B' : n < 1048576 ? (n / 1024).toFixed(1) + ' KB' : (n / 1048576).toFixed(1) + ' MB'

// Hex characters "resolve" left to right so a new fingerprint visibly arrives.
function useScramble(target) {
  const [out, setOut] = useState(target)
  useEffect(() => {
    if (!target || matchMedia('(prefers-reduced-motion: reduce)').matches) { setOut(target); return }
    let f = 0; const N = 20
    const id = setInterval(() => {
      f++
      const keep = Math.floor(target.length * f / N)
      setOut(target.slice(0, keep) + [...target.slice(keep)].map(() => HEX[Math.random() * 16 | 0]).join(''))
      if (f >= N) clearInterval(id)
    }, 30)
    return () => clearInterval(id)
  }, [target])
  return out
}

export function Hash({ value, mark }) {
  const hex = useScramble(value.slice(2))
  return (
    <div className={`hashbox ${mark || ''}`}>
      <code className="hash" aria-label={value}><span className="p">0x</span>{(hex.match(/.{1,8}/g) || []).map((g, i) => <span key={i}>{g}</span>)}</code>
      <CopyBtn text={value} />
    </div>
  )
}

export function Flow({ steps }) {
  return <ol className="flow">{steps.map(([l, s], i) => <li key={l} className={s}><i>{s === 'done' ? '✓' : s === 'bad' ? '!' : i + 1}</i><span>{l}</span></li>)}</ol>
}

// File input + drop zone that fingerprints the chosen file in the browser.
export function FilePick({ label, file, hash, onChange, required }) {
  const [busy, setBusy] = useState(false), [err, setErr] = useState(''), [over, setOver] = useState(false)
  const run = useRef(0)
  const pick = async f => {
    const id = ++run.current
    setErr('')
    if (!f) { onChange(null, ''); return }
    onChange(f, ''); setBusy(true)
    try { const h = await sha256Hex(f); if (id === run.current) onChange(f, h) }
    catch (e) { if (id === run.current) setErr(e.message) }
    if (id === run.current) setBusy(false)
  }
  return (
    <div className="pick">
      <span className="lbl">{label}</span>
      <label className={`drop${over ? ' over' : ''}${file ? ' has' : ''}`}
        onDragOver={e => { e.preventDefault(); setOver(true) }} onDragLeave={() => setOver(false)}
        onDrop={e => { e.preventDefault(); setOver(false); pick(e.dataTransfer.files[0]) }}>
        <input type="file" required={required && !file} onChange={e => pick(e.target.files[0])} />
        <strong>{file ? file.name : 'Choose a file or drop it here'}</strong>
        <small>{file ? `${fmt(file.size)} · click to change` : 'The SHA-256 fingerprint is calculated in your browser.'}</small>
      </label>
      {err && <div className="notice bad">{err}</div>}
      {file && !err && (
        <div className="fp swap">
          <div className="fp-h"><span>SHA-256 fingerprint</span><span className="ok">{busy ? 'Hashing…' : 'Computed in your browser'}</span></div>
          {busy ? <div className="bar"><b className="indet" /></div> : hash && <Hash value={hash} />}
        </div>
      )}
    </div>
  )
}

// Landing demo: edit the text, watch the whole fingerprint change.
export function HashDemo() {
  const [text, setText] = useState('Aarav Sharma · B.Tech Computer Science · 2026')
  const [hash, setHash] = useState('')
  const [diff, setDiff] = useState([])
  const prev = useRef('')
  useEffect(() => {
    let live = true
    sha256Hex(text).then(h => {
      if (!live) return
      setDiff(prev.current ? [...h.slice(2)].map((c, i) => c !== prev.current[i + 2]) : [])
      prev.current = h; setHash(h)
    }).catch(() => setHash(''))
    return () => { live = false }
  }, [text])
  const changed = diff.filter(Boolean).length
  return (
    <div className="box demo">
      <div className="sh" style={{ marginBottom: 20 }}>
        <h2 style={{ fontSize: 'clamp(1.6rem,3vw,2.2rem)' }}>See the fingerprint</h2>
        <p className="lead" style={{ marginTop: 10 }}>Every credential is sealed with a SHA-256 fingerprint. Change a single letter below and watch every character change.</p>
      </div>
      <label>Credential text<input value={text} onChange={e => setText(e.target.value)} maxLength={120} /></label>
      {!hashSupported ? <div className="notice bad" style={{ marginTop: 14 }}>Open this page over https or localhost to compute hashes.</div> : (
        <>
          <div className="hashbox live">
            <code className="hash"><span className="p">0x</span>{hash && [...hash.slice(2)].map((c, i) => <b key={hash + i} className={diff[i] ? 'chg' : ''}>{c}</b>)}</code>
            <CopyBtn text={hash} />
          </div>
          <p className="idsub" style={{ marginTop: 10 }}>{diff.length ? `${changed} of 64 characters changed with your last edit.` : 'Same text, same fingerprint, every time.'}</p>
        </>
      )}
    </div>
  )
}
