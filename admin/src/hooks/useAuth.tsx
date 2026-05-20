import { createContext, useContext, useState, useEffect, ReactNode } from 'react'
import axios from 'axios'

interface AuthContextType {
  isAuthenticated: boolean
  token: string | null
  login: (email: string, password: string) => Promise<void>
  logout: () => void
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(localStorage.getItem('zenseo_token'))
  const [isAuthenticated, setIsAuthenticated] = useState<boolean>(!!token)

  useEffect(() => {
    if (token) {
      axios.defaults.headers.common['Authorization'] = `Bearer ${token}`
    }
  }, [token])

  const login = async (email: string, password: string) => {
    const formData = new URLSearchParams()
    formData.append('username', email)
    formData.append('password', password)
    
    const response = await axios.post('/api/admin/v1/auth/login', formData, {
      headers: { 
        'Content-Type': 'application/x-www-form-urlencoded',
        'Accept': 'application/json'
      },
      withCredentials: true
    })
    
    const accessToken = response.data.access_token
    localStorage.setItem('zenseo_token', accessToken)
    setToken(accessToken)
    setIsAuthenticated(true)
    axios.defaults.headers.common['Authorization'] = `Bearer ${accessToken}`
  }

  const logout = () => {
    localStorage.removeItem('zenseo_token')
    setToken(null)
    setIsAuthenticated(false)
    delete axios.defaults.headers.common['Authorization']
  }

  return (
    <AuthContext.Provider value={{ isAuthenticated, token, login, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}