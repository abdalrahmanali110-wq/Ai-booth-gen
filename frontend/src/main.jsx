import { createRoot } from 'react-dom/client'
import './index.css'
import './styles/motion.css'
import App from './App.jsx'
import { applyTheme } from './hooks/useTheme.js'

const storedTheme = localStorage.getItem('booth-ai-theme')
if (storedTheme === 'light' || storedTheme === 'dark') {
  applyTheme(storedTheme)
} else if (window.matchMedia('(prefers-color-scheme: light)').matches) {
  applyTheme('light')
} else {
  applyTheme('dark')
}

createRoot(document.getElementById('root')).render(<App />)
