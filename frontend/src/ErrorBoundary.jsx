import { Component } from 'react'

/* If any page throws while rendering, show what happened instead of a blank screen. */
export default class ErrorBoundary extends Component {
  state = { error: null }
  static getDerivedStateFromError(error) { return { error } }
  componentDidCatch(error, info) { console.error('Page crashed:', error, info?.componentStack) }
  render() {
    if (!this.state.error) return this.props.children
    return (
      <div style={{ maxWidth: 560, margin: '12vh auto', padding: 24, fontFamily: 'system-ui, sans-serif' }}>
        <h1 style={{ marginTop: 0 }}>Something went wrong</h1>
        <p>This page hit an error. Reloading usually fixes it.</p>
        <pre style={{ whiteSpace: 'pre-wrap', background: '#eef2f7', padding: 12, borderRadius: 8, fontSize: 13 }}>{String(this.state.error?.message || this.state.error)}</pre>
        <button onClick={() => { window.location.href = '/' }} style={{ padding: '10px 18px', borderRadius: 10, border: 0, background: '#0e1b36', color: '#fff', cursor: 'pointer' }}>Back to home</button>
      </div>
    )
  }
}
