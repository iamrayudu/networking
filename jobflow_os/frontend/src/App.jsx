import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { useWebSocket } from './hooks/useWebSocket'
import CommandCenter from './pages/CommandCenter'
import Dashboard from './pages/Dashboard'

function AppRoutes() {
  useWebSocket() // single persistent connection for the whole app
  return (
    <Routes>
      <Route path='/command' element={<CommandCenter />} />
      <Route path='/dashboard' element={<Dashboard />} />
      <Route path='/' element={<Navigate to='/command' />} />
    </Routes>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <AppRoutes />
    </BrowserRouter>
  )
}
