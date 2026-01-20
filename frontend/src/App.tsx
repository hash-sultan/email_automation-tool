import { Routes, Route } from 'react-router-dom'
import { Toaster } from 'react-hot-toast'
import Layout from './components/Layout'
import Dashboard from './pages/Dashboard'
import Campaigns from './pages/Campaigns'
import Leads from './pages/Leads'
import Templates from './pages/Templates'
import Senders from './pages/Senders'
import Analytics from './pages/Analytics'
import Settings from './pages/Settings'

function App() {
  return (
    <>
      <Toaster
        position="top-right"
        toastOptions={{
          duration: 4000,
          style: {
            background: '#1f2937',
            color: '#f3f4f6',
            border: '1px solid #374151',
          },
          success: {
            iconTheme: {
              primary: '#10b981',
              secondary: '#1f2937',
            },
          },
          error: {
            iconTheme: {
              primary: '#ef4444',
              secondary: '#1f2937',
            },
          },
        }}
      />
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<Dashboard />} />
          <Route path="campaigns" element={<Campaigns />} />
          <Route path="leads" element={<Leads />} />
          <Route path="templates" element={<Templates />} />
          <Route path="senders" element={<Senders />} />
          <Route path="analytics" element={<Analytics />} />
          <Route path="settings" element={<Settings />} />
        </Route>
      </Routes>
    </>
  )
}

export default App

