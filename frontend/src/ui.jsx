import { useState } from 'react'

/* ---------- small helpers ---------- */
export function useAsync() {
  const [state, set] = useState({ busy: false, error: '', ok: '' })
  const run = async fn => {
    set({ busy: true, error: '', ok: '' })
    try { const r = await fn(); set({ busy: false, error: '', ok: '' }); return r }
    catch (e) { set({ busy: false, error: e.message, ok: '' }) }
  }
  return [state, run]
}
export const Notice = ({ kind = 'bad', children }) => children ? <div className={`notice ${kind}`} role="status">{children}</div> : null
export const Field = ({ label, ...p }) => <label>{label}<input {...p} /></label>

export function Seal({ tone = 'ok' }) {
  return (
    <svg className={`seal big ${tone}`} viewBox="0 0 64 64" aria-hidden="true">
      <circle cx="32" cy="32" r="28" />
      <path d={tone === 'ok' ? 'M20 33l9 9 16-18' : 'M22 22l20 20M42 22L22 42'} />
    </svg>
  )
}


export function CopyBtn({ text, label = 'Copy' }) {
  const [done, setDone] = useState(false)
  const copy = async () => { try { await navigator.clipboard.writeText(text); setDone(true); setTimeout(() => setDone(false), 1400) } catch { /* clipboard blocked */ } }
  return <button type="button" className="mini" onClick={copy}>{done ? 'Copied' : label}</button>
}
