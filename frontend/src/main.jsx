import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import './index.css'
import { useThemeStore } from './store'

// Add visible loading indicator to DOM immediately
const styleEl = document.createElement('style')
styleEl.textContent = `
  #root { position: relative; }
  #root::before {
    content: 'Loading App...';
    position: fixed;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    color: #64c8ff;
    font-family: monospace;
    font-size: 18px;
    z-index: 9999;
    pointer-events: none;
    opacity: 0.8;
  }
  #root.app-loaded::before {
    display: none;
  }
`
document.head.appendChild(styleEl)

// Global error handlers
window.addEventListener('error', (event) => {
  console.error('❌ Global error:', event.error)
  const root = document.getElementById('root')
  if (root) {
    root.innerHTML = `<div style="color:#ff4444;padding:40px;font-family:monospace;background:#0a0b0f;height:100vh;overflow:auto"><h1>❌ Error Loading App</h1><pre>${event.error?.toString()}\n\n${event.error?.stack || ''}</pre></div>`
  }
})

window.addEventListener('unhandledrejection', (event) => {
  console.error('❌ Unhandled promise rejection:', event.reason)
  const root = document.getElementById('root')
  if (root && !root.querySelector('[style*="Error"]')) {
    root.innerHTML = `<div style="color:#ff4444;padding:40px;font-family:monospace;background:#0a0b0f;height:100vh;overflow:auto"><h1>❌ Unhandled Error</h1><pre>${event.reason?.toString()}\n\n${event.reason?.stack || ''}</pre></div>`
  }
})

// Init theme sebelum render
try { useThemeStore.getState().initTheme() } catch(e) { console.error('Theme init error:', e) }

console.log('🚀 App starting - rendering React root')
try {
  const root = document.getElementById('root')
  console.log('📍 Root element found:', root)
  
  if (!root) {
    console.error('❌ Root element NOT found!')
    throw new Error('Root element #root not found in HTML')
  }
  
  const onRender = () => {
    console.log('✅ React app rendered')
    root.classList.add('app-loaded')
  }
  
  ReactDOM.createRoot(root).render(
    <React.StrictMode>
      <App />
    </React.StrictMode>
  )
  
  // Check if app loaded after a delay
  setTimeout(onRender, 100)
  console.log('✅ React app mounted successfully')
} catch (err) {
  console.error('❌ Failed to mount React app:', err)
  const root = document.getElementById('root')
  if (root) {
    root.innerHTML = `<div style="color:#ff4444;padding:40px;font-family:monospace;background:#0a0b0f;height:100vh;overflow:auto;white-space:pre-wrap;"><h1>React Error</h1>${err.toString()}\n\n${err.stack || ''}</div>`
  }
}
