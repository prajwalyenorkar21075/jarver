import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'
import SpherePrototype from './SpherePrototype.tsx'

const sphereOnly = new URLSearchParams(window.location.search).get('sphere') === '1'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    {sphereOnly ? <SpherePrototype /> : <App />}
  </StrictMode>,
)
