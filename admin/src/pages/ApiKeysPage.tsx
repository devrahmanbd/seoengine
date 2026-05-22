import { useState, useEffect } from 'react'
import { Key, Plus, Trash2, Copy, Search } from 'lucide-react'
import { useAuth } from '../hooks/useAuth'
import axios from 'axios'
import { Button } from '../components/Button'
import { Card } from '../components/Card'
import { Input } from '../components/Input'

interface ApiKey {
  id: string
  label: string
  user: string
  keyPrefix: string
  rateLimit: number
  callsCount: number
  lastUsed: string
  created: string
  expires: string
  isActive: boolean
}

export default function ApiKeysPage() {
  const { token } = useAuth()
  const [keys, setKeys] = useState<ApiKey[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (token) {
      axios.get('/api/admin/v1/api-keys', {
        headers: { Authorization: `Bearer ${token}` }
      })
      .then(res => setKeys(res.data.data))
      .catch(err => console.error(err))
      .finally(() => setLoading(false))
    }
  }, [token])

  const stats = [
    { label: 'Total Keys', value: keys.length.toString() },
    { label: 'Active Keys', value: keys.filter(k => k.isActive).length.toString() },
    { label: 'Total Calls (24h)', value: keys.reduce((a, b) => a + b.callsCount, 0).toLocaleString() },
  ]

  if (loading) return <div className="p-8 text-center text-slate-500">Loading...</div>

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold text-slate-900">API Keys</h1>
      </div>

      <div className="grid grid-cols-3 gap-4">
        {stats.map(({ label, value }) => (
          <div key={label} className="bg-white rounded-xl p-4 border border-slate-200">
            <p className="text-2xl font-semibold text-slate-900">{value}</p>
            <p className="text-sm text-slate-500">{label}</p>
          </div>
        ))}
      </div>

      {keys.length === 0 ? (
        <div className="bg-white rounded-xl border border-slate-200 p-12 text-center">
          <Key className="w-12 h-12 text-slate-300 mx-auto mb-4" />
          <p className="text-slate-500">No API keys found</p>
        </div>
      ) : (
        <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
          <table className="w-full">
            <thead className="bg-slate-50 border-b border-slate-200">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">Label</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">User</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">API Key</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">Rate Limit</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">Usage</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {keys.map((key) => (
                <tr key={key.id} className="hover:bg-slate-50">
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      <Key size={16} className="text-slate-400" />
                      <span className="font-medium text-slate-900">{key.label}</span>
                    </div>
                  </td>
                  <td className="px-4 py-3 text-sm text-slate-600">{key.user}</td>
                  <td className="px-4 py-3">
                    <code className="text-sm bg-slate-100 px-2 py-1 rounded font-mono">{key.keyPrefix}****</code>
                  </td>
                  <td className="px-4 py-3 text-sm text-slate-600">{key.rateLimit.toLocaleString()}/day</td>
                  <td className="px-4 py-3 text-sm text-slate-600">{key.callsCount.toLocaleString()}</td>
                  <td className="px-4 py-3">
                    <span className={`px-2 py-1 rounded-md text-xs font-medium ${key.isActive ? 'bg-accent/10 text-accent' : 'bg-slate-100 text-slate-500'}`}>
                      {key.isActive ? 'Active' : 'Inactive'}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}