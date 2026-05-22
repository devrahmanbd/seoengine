import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'
import { Loader2 } from 'lucide-react'
import { Button } from '../components/Button'
import { Card } from '../components/Card'
import { Input } from '../components/Input'

export default function LoginPage() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const { login } = useAuth()
  const navigate = useNavigate()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    
    console.log('Attempting login with:', email)
    
    try {
      await login(email, password)
      console.log('Login successful!')
      navigate('/users')
    } catch (err: any) {
      console.error('Login error:', err)
      setError(err.response?.data?.detail || err.message || 'Login failed. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-background flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        <Card className="p-8 shadow-xl">
          <div className="text-center mb-8">
            <div className="w-16 h-16 bg-primary rounded-card flex items-center justify-center mx-auto mb-4">
              <span className="text-surface font-bold text-2xl">Z</span>
            </div>
            <h1 className="text-2xl font-display font-semibold text-textPrimary">ZenSEO Admin</h1>
            <p className="text-textSecondary mt-2">Sign in to your account</p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-6">
            {error && (
              <div className="bg-error/10 border border-error/20 text-error px-4 py-3 rounded-lg text-sm">
                {error}
              </div>
            )}

            <Input label="Email" type="email" value={email} onChange={e => setEmail(e.target.value)} placeholder="admin@zenseo.ai" required />

            <Input label="Password" type="password" value={password} onChange={e => setPassword(e.target.value)} placeholder="••••••••" required />

            <Button type="submit" disabled={loading} className="w-full h-[44px] mt-2">
              {loading ? (
                <>
                  <Loader2 className="animate-spin" size={20} />
                  Signing in...
                </>
              ) : (
                'Sign In'
              )}
            </Button>
          </form>
        </Card>
      </div>
    </div>
  )
}