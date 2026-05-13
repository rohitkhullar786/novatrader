import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.jsx'
import './index.css'

// Error Boundary - catches crashes instead of white screen
class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props)
    this.state = { error: null, info: null }
  }
  componentDidCatch(error, info) {
    this.setState({ error, info })
    console.error('App crashed:', error, info)
  }
  render() {
    if (this.state.error) {
      return (
        <div style={{ padding: 40, fontFamily: 'system-ui', maxWidth: 600, margin: '0 auto' }}>
          <h2 style={{ color: '#e00' }}>⚠️ Something crashed</h2>
          <pre style={{ 
            background: '#1a1a1a', color: '#f0f0f0', padding: 16, borderRadius: 8,
            fontSize: 13, overflow: 'auto', maxHeight: 300, whiteSpace: 'pre-wrap'
          }}>
            {this.state.error.toString()}
          </pre>
          <button 
            onClick={() => window.location.reload()}
            style={{ marginTop: 16, padding: '8px 20px', background: '#111', color: '#fff', border: 'none', borderRadius: 6, cursor: 'pointer' }}
          >
            Reload Page
          </button>
        </div>
      )
    }
    return this.props.children
  }
}

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <ErrorBoundary>
      <App />
    </ErrorBoundary>
  </React.StrictMode>,
)
