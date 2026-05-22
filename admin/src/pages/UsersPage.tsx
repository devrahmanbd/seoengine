import { useState, useEffect } from 'react'
import { Users as UsersIcon, Plus, MoreVertical, Search } from 'lucide-react'
import { useAuth } from '../hooks/useAuth'
import axios from 'axios'
import { Button } from '../components/Button'
import { Card } from '../components/Card'
import { Input } from '../components/Input'

interface User {
  id: string
  name: string
  email: string
  plan: string
  subscriptionStatus: string
  apiCallsUsed: number
  apiCallsLimit: number
  websitesCount: number
  createdAt: string
}

export default function UsersPage() {
  const { token } = useAuth()
  const [users, setUsers] = useState<User[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (token) {
      axios.get('/api/admin/v1/users', {
        headers: { Authorization: `Bearer ${token}` }
      })
      .then(res => {
        setUsers(res.data.data)
      })
      .catch(err => console.error(err))
      .finally(() => setLoading(false))
    }
  }, [token])

  const stats = [
    { label: 'Total Users', value: users.length.toString(), icon: UsersIcon, color: 'text-primary' },
    { label: 'Active', value: users.filter(u => u.subscriptionStatus === 'active').length.toString(), icon: UsersIcon, color: 'text-accent' },
    { label: 'New This Month', value: '0', icon: UsersIcon, color: 'text-warning' },
  ]

  const getPlanColor = (plan: string) => {
    const colors: Record<string, string> = {
      free: 'bg-slate-100 text-slate-600',
      starter: 'bg-blue-100 text-blue-700',
      pro: 'bg-purple-100 text-purple-700',
      enterprise: 'bg-amber-100 text-amber-700',
    }
    return colors[plan] || colors.free
  }

  const getStatusColor = (subscriptionStatus: string) => {
    const colors: Record<string, string> = {
      active: 'bg-accent/10 text-accent',
      inactive: 'bg-slate-100 text-slate-500',
      trial: 'bg-warning/10 text-warning',
    }
    return colors[status] || colors.inactive
  }

  if (loading) return <div className="p-8 text-center text-slate-500">Loading...</div>

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold text-slate-900">Users</h1>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-3 gap-4">
        {stats.map(({ label, value, icon: Icon, color }) => (
          <div key={label} className="bg-white rounded-xl p-4 border border-slate-200">
            <div className="flex items-center gap-3">
              <div className={`p-2 rounded-lg bg-slate-100 ${color}`}>
                <Icon size={20} />
              </div>
              <div>
                <p className="text-2xl font-semibold text-slate-900">{value}</p>
                <p className="text-sm text-slate-500">{label}</p>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Filters */}
      <div className="flex items-center gap-4 bg-white p-4 rounded-xl border border-slate-200">
        <div className="relative flex-1 max-w-xs">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={18} />
          <input 
            type="text" 
            placeholder="Search users..." 
            className="w-full pl-10 pr-4 py-2 bg-slate-50 border border-slate-200 rounded-lg text-sm focus:outline-none focus:border-primary/50"
          />
        </div>
      </div>

      {/* Table */}
      {users.length === 0 ? (
        <div className="bg-white rounded-xl border border-slate-200 p-12 text-center">
          <UsersIcon className="w-12 h-12 text-slate-300 mx-auto mb-4" />
          <p className="text-slate-500">No users found</p>
        </div>
      ) : (
        <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
          <table className="w-full">
            <thead className="bg-slate-50 border-b border-slate-200">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">User</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">Plan</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">Status</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">API Usage</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">Websites</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">Joined</th>
                <th className="px-4 py-3"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {users.map((user) => (
                <tr key={user.id} className="hover:bg-slate-50">
                  <td className="px-4 py-3">
                    <div>
                      <p className="font-medium text-slate-900">{user.name}</p>
                      <p className="text-sm text-slate-500">{user.email}</p>
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <span className={`px-2 py-1 rounded-md text-xs font-medium ${getPlanColor(user.plan)}`}>
                      {user.plan}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <span className={`px-2 py-1 rounded-md text-xs font-medium ${getStatusColor(user.subscriptionStatus)}`}>
                      {user.subscriptionStatus}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <div className="w-24">
                      <div className="flex justify-between text-xs mb-1">
                        <span className="text-slate-600">{user.apiCallsUsed}</span>
                        <span className="text-slate-400">{user.apiCallsLimit}</span>
                      </div>
                      <div className="h-1.5 bg-slate-100 rounded-full overflow-hidden">
                        <div 
                          className="h-full bg-primary rounded-full"
                          style={{ width: `${(user.apiCallsUsed / user.apiCallsLimit) * 100}%` }}
                        />
                      </div>
                    </div>
                  </td>
                  <td className="px-4 py-3 text-sm text-slate-600">{user.websitesCount || 0}</td>
                  <td className="px-4 py-3 text-sm text-slate-500">{user.createdAt?.split('T')[0] || '-'}</td>
                  <td className="px-4 py-3">
                    <Button variant="ghost" className="p-1 text-slate-400 hover:text-slate-600">
                      <MoreVertical size={18} />
                    </Button>
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