import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import './index.css'
import { AuthProvider, useAuth } from './lib/auth'
import Layout from './components/Layout'
import { Spinner } from './components/ui'
import LoginPage from './pages/Login'
import CasesPage from './pages/Cases'
import CaseDetailPage from './pages/CaseDetail'
import MailPage from './pages/Mail'
import CustomersPage from './pages/Customers'
import CustomerDetailPage from './pages/CustomerDetail'
import KnowledgePage from './pages/Knowledge'
import SocialPage from './pages/Social'
import SocialEditorPage from './pages/SocialEditor'
import ReportsPage from './pages/Reports'
import AdminPage from './pages/Admin'

const qc = new QueryClient({ defaultOptions: { queries: { staleTime: 5000, retry: 1, refetchOnWindowFocus: false } } })

function Protected() {
  const { user, loading } = useAuth()
  if (loading) return <Spinner />
  if (!user) return <Navigate to="/prijava" replace />
  return <Layout />
}

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <QueryClientProvider client={qc}>
      <AuthProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/prijava" element={<LoginPage />} />
            <Route element={<Protected />}>
              <Route path="/" element={<Navigate to="/predmeti" replace />} />
              <Route path="/predmeti" element={<CasesPage />} />
              <Route path="/predmeti/:id" element={<CaseDetailPage />} />
              <Route path="/posta" element={<MailPage />} />
              <Route path="/korisnici" element={<CustomersPage />} />
              <Route path="/korisnici/:id" element={<CustomerDetailPage />} />
              <Route path="/znanje" element={<KnowledgePage />} />
              <Route path="/mreze" element={<SocialPage />} />
              <Route path="/mreze/:id" element={<SocialEditorPage />} />
              <Route path="/izvestaji" element={<ReportsPage />} />
              <Route path="/administracija" element={<AdminPage />} />
              <Route path="*" element={<Navigate to="/predmeti" replace />} />
            </Route>
          </Routes>
        </BrowserRouter>
      </AuthProvider>
    </QueryClientProvider>
  </StrictMode>,
)
