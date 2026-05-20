import { Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider, useAuth } from './hooks/useAuth'
import Layout from './components/Layout'
import LoginPage from './pages/LoginPage'
import UsersPage from './pages/UsersPage'
import WebsitesPage from './pages/WebsitesPage'
import ApiKeysPage from './pages/ApiKeysPage'
import ResultsPage from './pages/ResultsPage'
import BackendPage from './pages/BackendPage'
import AILogsPage from './pages/AILogsPage'
import GrowthPage from './pages/GrowthPage'

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated } = useAuth()
  
  if (!isAuthenticated) {
    return <Navigate to="/login" replace />
  }
  
  return <>{children}</>
}

function AppRoutes() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route
        path="/"
        element={
          <ProtectedRoute>
            <Layout />
          </ProtectedRoute>
        }
      >
        <Route index element={<Navigate to="/users" replace />} />
        <Route path="users" element={<UsersPage />} />
        <Route path="websites" element={<WebsitesPage />} />
        <Route path="api-keys" element={<ApiKeysPage />} />
        <Route path="results" element={<ResultsPage />} />
        <Route path="backend" element={<BackendPage />} />
        <Route path="ai-logs" element={<AILogsPage />} />
        <Route path="growth" element={<GrowthPage />} />
      </Route>
    </Routes>
  )
}

function App() {
  return (
    <AuthProvider>
      <AppRoutes />
    </AuthProvider>
  )
}

export default App