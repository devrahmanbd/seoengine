import { useState, useEffect } from 'react'
import { Users, Globe, Key, Plus, Pencil, Trash2, X, Cpu, RefreshCw, Power, PowerOff } from 'lucide-react'
import { useAuth } from '../hooks/useAuth'
import axios from 'axios'

type Tab = 'users' | 'websites' | 'api-keys' | 'ml'

interface UserData {
  id: string; name: string; email: string; plan: string
  subscriptionStatus: string; apiCallsUsed: number; apiCallsLimit: number
  websitesCount: number; createdAt: string
}

interface WebsiteData {
  id: string; name: string; url: string; userId: string
  platform: string; status: string; seoScore: number; lastScan: string | null
}

interface ApiKeyData {
  id: string; label: string; userId: string; keyPrefix: string
  rateLimit: number; callsCount: number; lastUsed: string | null
  created: string; expires: string; isActive: boolean
}

type FormMode = 'create' | 'edit' | null

const TABS: { key: Tab; label: string; icon: typeof Users }[] = [
  { key: 'users', label: 'Users', icon: Users },
  { key: 'websites', label: 'Websites', icon: Globe },
  { key: 'api-keys', label: 'API Keys', icon: Key },
  { key: 'ml', label: 'ML Service', icon: Cpu },
]

function Modal({ title, children, onClose }: { title: string; children: React.ReactNode; onClose: () => void }) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40" onClick={onClose}>
      <div className="bg-white rounded-xl shadow-xl w-full max-w-lg mx-4 max-h-[90vh] overflow-y-auto" onClick={e => e.stopPropagation()}>
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-200">
          <h2 className="text-lg font-semibold text-slate-900">{title}</h2>
          <button onClick={onClose} className="p-1 text-slate-400 hover:text-slate-600 rounded-lg">
            <X size={20} />
          </button>
        </div>
        <div className="px-6 py-4">{children}</div>
      </div>
    </div>
  )
}

function ConfirmDialog({ message, onConfirm, onCancel }: { message: string; onConfirm: () => void; onCancel: () => void }) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40" onClick={onCancel}>
      <div className="bg-white rounded-xl shadow-xl w-full max-w-sm mx-4 p-6" onClick={e => e.stopPropagation()}>
        <p className="text-slate-900 mb-6">{message}</p>
        <div className="flex justify-end gap-3">
          <button onClick={onCancel} className="px-4 py-2 text-sm text-slate-600 hover:bg-slate-100 rounded-lg">Cancel</button>
          <button onClick={onConfirm} className="px-4 py-2 text-sm bg-error text-white rounded-lg hover:bg-error/90">Delete</button>
        </div>
      </div>
    </div>
  )
}

function Input({ label, value, onChange, type = 'text', placeholder }: {
  label: string; value: string; onChange: (v: string) => void; type?: string; placeholder?: string
}) {
  return (
    <div className="mb-4">
      <label className="block text-sm font-medium text-slate-700 mb-1">{label}</label>
      <input
        type={type}
        value={value}
        onChange={e => onChange(e.target.value)}
        placeholder={placeholder}
        className="w-full px-3 py-2 border border-slate-200 rounded-lg text-sm focus:outline-none focus:border-primary/50 bg-slate-50"
      />
    </div>
  )
}

function Select({ label, value, onChange, options }: {
  label: string; value: string; onChange: (v: string) => void; options: { value: string; label: string }[]
}) {
  return (
    <div className="mb-4">
      <label className="block text-sm font-medium text-slate-700 mb-1">{label}</label>
      <select
        value={value}
        onChange={e => onChange(e.target.value)}
        className="w-full px-3 py-2 border border-slate-200 rounded-lg text-sm focus:outline-none focus:border-primary/50 bg-slate-50"
      >
        {options.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
      </select>
    </div>
  )
}

function authHeaders(token: string | null) {
  if (!token) return {}
  return { headers: { Authorization: `Bearer ${token}` } }
}

export default function ManagementPage() {
  const { token } = useAuth()
  const [activeTab, setActiveTab] = useState<Tab>('users')

  const [users, setUsers] = useState<UserData[]>([])
  const [websites, setWebsites] = useState<WebsiteData[]>([])
  const [apiKeys, setApiKeys] = useState<ApiKeyData[]>([])
  const [loading, setLoading] = useState(true)
  const [newKeyValue, setNewKeyValue] = useState<string | null>(null)
  const [mlStatus, setMlStatus] = useState<any>(null)
  const [mlToggling, setMlToggling] = useState(false)
  const [dockerInfo, setDockerInfo] = useState<any>(null)
  const [containerAction, setContainerAction] = useState<string | null>(null)
  const [mlLogs, setMlLogs] = useState<string[]>([])
  const [logsLoading, setLogsLoading] = useState(false)

  const [formMode, setFormMode] = useState<FormMode>(null)
  const [editId, setEditId] = useState<string | null>(null)
  const [deleteTarget, setDeleteTarget] = useState<{ type: Tab; id: string; label: string } | null>(null)

  const [form, setForm] = useState<Record<string, string>>({})

  useEffect(() => {
    if (!token) return
    setLoading(true)
    const mlPromise = axios.get('/api/admin/v1/ml/status', authHeaders(token)).catch(() => null)
    const dockerPromise = axios.get('/api/admin/v1/ml/container/status', authHeaders(token)).catch(() => null)
    Promise.all([
      axios.get('/api/admin/v1/users', authHeaders(token)),
      axios.get('/api/admin/v1/websites', authHeaders(token)),
      axios.get('/api/admin/v1/api-keys', authHeaders(token)),
      mlPromise,
      dockerPromise,
    ]).then(([u, w, k, ml, docker]) => {
      setUsers(u.data.data)
      setWebsites(w.data.data)
      setApiKeys(k.data.data)
      if (ml?.data) setMlStatus(ml.data)
      if (docker?.data) setDockerInfo(docker.data)
    }).catch(console.error).finally(() => setLoading(false))
  }, [token])

  function resetForm() {
    setForm({})
    setFormMode(null)
    setEditId(null)
    setNewKeyValue(null)
  }

  function openCreate(tab: Tab) {
    setFormMode('create')
    setEditId(null)
    setNewKeyValue(null)
    if (tab === 'users') setForm({ name: '', email: '', password: 'password', plan: 'free', subscriptionStatus: 'active', openrouter_key: '' })
    else if (tab === 'websites') setForm({ name: '', url: '', userId: '', platform: 'wordpress', status: 'connected' })
    else setForm({ label: '', userId: '', rateLimit: '1000' })
  }

  function openEdit(tab: Tab, item: any) {
    setFormMode('edit')
    setEditId(item.id)
    setNewKeyValue(null)
    if (tab === 'users') setForm({ name: item.name || '', email: item.email || '', plan: item.plan || 'free', subscriptionStatus: item.subscriptionStatus || 'active', openrouter_key: item.openrouterKey || '' })
    else if (tab === 'websites') setForm({ name: item.name || '', url: item.url || '', userId: item.userId || '', platform: item.platform || 'wordpress', status: item.status || 'connected' })
    else setForm({ label: item.label || '', rateLimit: String(item.rateLimit || 1000), isActive: String(item.isActive ?? true) })
  }

  async function handleSave() {
    if (!token || !formMode) return
    try {
      if (activeTab === 'users') {
        if (formMode === 'create') {
          await axios.post('/api/admin/v1/users', form, authHeaders(token))
        } else {
          await axios.put(`/api/admin/v1/users/${editId}`, form, authHeaders(token))
        }
        const res = await axios.get('/api/admin/v1/users', authHeaders(token))
        setUsers(res.data.data)
      } else if (activeTab === 'websites') {
        if (formMode === 'create') {
          await axios.post('/api/admin/v1/websites', form, authHeaders(token))
        } else {
          await axios.put(`/api/admin/v1/websites/${editId}`, form, authHeaders(token))
        }
        const res = await axios.get('/api/admin/v1/websites', authHeaders(token))
        setWebsites(res.data.data)
      } else if (activeTab === 'api-keys') {
        if (formMode === 'create') {
          const res = await axios.post('/api/admin/v1/api-keys', form, authHeaders(token))
          setNewKeyValue(res.data.apiKey)
          const updated = await axios.get('/api/admin/v1/api-keys', authHeaders(token))
          setApiKeys(updated.data.data)
          return // keep modal open so user sees the new key
        } else {
          await axios.put(`/api/admin/v1/api-keys/${editId}`, form, authHeaders(token))
        }
        const res = await axios.get('/api/admin/v1/api-keys', authHeaders(token))
        setApiKeys(res.data.data)
      }
      resetForm()
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to save')
    }
  }

  async function handleDelete() {
    if (!token || !deleteTarget) return
    try {
      if (deleteTarget.type === 'users') {
        await axios.delete(`/api/admin/v1/users/${deleteTarget.id}`, authHeaders(token))
        const res = await axios.get('/api/admin/v1/users', authHeaders(token))
        setUsers(res.data.data)
      } else if (deleteTarget.type === 'websites') {
        await axios.delete(`/api/admin/v1/websites/${deleteTarget.id}`, authHeaders(token))
        const res = await axios.get('/api/admin/v1/websites', authHeaders(token))
        setWebsites(res.data.data)
      } else {
        await axios.delete(`/api/admin/v1/api-keys/${deleteTarget.id}`, authHeaders(token))
        const res = await axios.get('/api/admin/v1/api-keys', authHeaders(token))
        setApiKeys(res.data.data)
      }
      setDeleteTarget(null)
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to delete')
    }
  }

  const userStats = [
    { label: 'Total Users', value: users.length.toString(), color: 'text-primary' },
    { label: 'Active', value: users.filter(u => u.subscriptionStatus === 'active').length.toString(), color: 'text-accent' },
    { label: 'Websites', value: users.reduce((a, u) => a + (u.websitesCount || 0), 0).toString(), color: 'text-warning' },
  ]

  const websiteStats = [
    { label: 'Total Websites', value: websites.length.toString(), color: 'text-primary' },
    { label: 'Connected', value: websites.filter(w => w.status === 'connected').length.toString(), color: 'text-accent' },
    { label: 'Avg SEO Score', value: websites.length ? Math.round(websites.reduce((a, w) => a + w.seoScore, 0) / websites.length) + '%' : '0%', color: 'text-warning' },
  ]

  const keyStats = [
    { label: 'Total Keys', value: apiKeys.length.toString(), color: 'text-primary' },
    { label: 'Active', value: apiKeys.filter(k => k.isActive).length.toString(), color: 'text-accent' },
    { label: 'Total Calls', value: apiKeys.reduce((a, k) => a + k.callsCount, 0).toLocaleString(), color: 'text-warning' },
  ]

  function getFormFields() {
    if (activeTab === 'users') return (
      <>
        <Input label="Name" value={form.name || ''} onChange={v => setForm(f => ({ ...f, name: v }))} />
        <Input label="Email" value={form.email || ''} onChange={v => setForm(f => ({ ...f, email: v }))} />
        {formMode === 'create' && <Input label="Password" type="password" value={form.password || ''} onChange={v => setForm(f => ({ ...f, password: v }))} />}
        <Input label="OpenRouter API Key" type="password" value={form.openrouter_key || ''} onChange={v => setForm(f => ({ ...f, openrouter_key: v }))} placeholder="sk-or-v1-..." />
        <Select label="Plan" value={form.plan || 'free'} onChange={v => setForm(f => ({ ...f, plan: v }))} options={[
          { value: 'free', label: 'Free' }, { value: 'starter', label: 'Starter' }, { value: 'pro', label: 'Pro' }, { value: 'enterprise', label: 'Enterprise' }
        ]} />
        <Select label="Status" value={form.subscriptionStatus || 'active'} onChange={v => setForm(f => ({ ...f, subscriptionStatus: v }))} options={[
          { value: 'active', label: 'Active' }, { value: 'inactive', label: 'Inactive' }, { value: 'trial', label: 'Trial' }
        ]} />
      </>
    )
    if (activeTab === 'websites') return (
      <>
        <Input label="Name" value={form.name || ''} onChange={v => setForm(f => ({ ...f, name: v }))} />
        <Input label="URL" value={form.url || ''} onChange={v => setForm(f => ({ ...f, url: v }))} placeholder="https://example.com" />
        <Select label="User" value={form.userId || ''} onChange={v => setForm(f => ({ ...f, userId: v }))} options={[
          { value: '', label: 'Select user...' },
          ...users.map(u => ({ value: u.id, label: `${u.name} (${u.email})` }))
        ]} />
        <Select label="Platform" value={form.platform || 'wordpress'} onChange={v => setForm(f => ({ ...f, platform: v }))} options={[
          { value: 'wordpress', label: 'WordPress' }, { value: 'shopify', label: 'Shopify' },
          { value: 'wix', label: 'Wix' }, { value: 'custom', label: 'Custom' }, { value: 'other', label: 'Other' }
        ]} />
        <Select label="Status" value={form.status || 'connected'} onChange={v => setForm(f => ({ ...f, status: v }))} options={[
          { value: 'connected', label: 'Connected' }, { value: 'disconnected', label: 'Disconnected' }, { value: 'error', label: 'Error' }
        ]} />
      </>
    )
    return (
      <>
        <Input label="Label" value={form.label || ''} onChange={v => setForm(f => ({ ...f, label: v }))} placeholder="e.g. Production API Key" />
        <Select label="User" value={form.userId || ''} onChange={v => setForm(f => ({ ...f, userId: v }))} options={[
          { value: '', label: 'Select user...' },
          ...users.map(u => ({ value: u.id, label: `${u.name} (${u.email})` }))
        ]} />
        <Input label="Rate Limit (requests/day)" type="number" value={form.rateLimit || '1000'} onChange={v => setForm(f => ({ ...f, rateLimit: v }))} />
        {formMode === 'edit' && (
          <Select label="Active" value={form.isActive || 'true'} onChange={v => setForm(f => ({ ...f, isActive: v }))} options={[
            { value: 'true', label: 'Active' }, { value: 'false', label: 'Inactive' }
          ]} />
        )}
      </>
    )
  }

  if (loading) return <div className="p-8 text-center text-slate-500">Loading...</div>

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold text-slate-900">Management</h1>
        {activeTab !== 'ml' && (
          <button
            onClick={() => openCreate(activeTab)}
            className="flex items-center gap-2 px-4 py-2 bg-primary text-white rounded-lg text-sm font-medium hover:bg-primary/90"
          >
            <Plus size={18} /> Add {activeTab === 'users' ? 'User' : activeTab === 'websites' ? 'Website' : 'API Key'}
          </button>
        )}
      </div>

      {/* Tabs */}
      <div className="flex gap-1 bg-white rounded-xl border border-slate-200 p-1">
        {TABS.map(({ key, label, icon: Icon }) => (
          <button
            key={key}
            onClick={() => { setActiveTab(key); resetForm() }}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              activeTab === key ? 'bg-primary text-white' : 'text-slate-600 hover:bg-slate-100'
            }`}
          >
            <Icon size={18} /> {label}
          </button>
        ))}
      </div>

      {/* Users Tab */}
      {activeTab === 'users' && (
        <>
          <div className="grid grid-cols-3 gap-4">
            {userStats.map(({ label, value, color }) => (
              <div key={label} className="bg-white rounded-xl p-4 border border-slate-200">
                <p className={`text-2xl font-semibold ${color}`}>{value}</p>
                <p className="text-sm text-slate-500">{label}</p>
              </div>
            ))}
          </div>
          <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
            <table className="w-full">
              <thead className="bg-slate-50 border-b border-slate-200">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">User</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">Plan</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">Status</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">Websites</th>
                  <th className="px-4 py-3"></th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {users.map(u => (
                  <tr key={u.id} className="hover:bg-slate-50">
                    <td className="px-4 py-3">
                      <p className="font-medium text-slate-900">{u.name}</p>
                      <p className="text-sm text-slate-500">{u.email}</p>
                    </td>
                    <td className="px-4 py-3"><span className="px-2 py-1 bg-slate-100 rounded-md text-xs font-medium text-slate-600 capitalize">{u.plan}</span></td>
                    <td className="px-4 py-3"><span className={`px-2 py-1 rounded-md text-xs font-medium ${u.subscriptionStatus === 'active' ? 'bg-accent/10 text-accent' : 'bg-slate-100 text-slate-500'}`}>{u.subscriptionStatus}</span></td>
                    <td className="px-4 py-3 text-sm text-slate-600">{u.websitesCount || 0}</td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <button onClick={() => openEdit('users', u)} className="p-1.5 text-slate-400 hover:text-primary rounded-lg hover:bg-slate-100"><Pencil size={16} /></button>
                        <button onClick={() => setDeleteTarget({ type: 'users', id: u.id, label: u.name })} className="p-1.5 text-slate-400 hover:text-error rounded-lg hover:bg-slate-100"><Trash2 size={16} /></button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}

      {/* Websites Tab */}
      {activeTab === 'websites' && (
        <>
          <div className="grid grid-cols-3 gap-4">
            {websiteStats.map(({ label, value, color }) => (
              <div key={label} className="bg-white rounded-xl p-4 border border-slate-200">
                <p className={`text-2xl font-semibold ${color}`}>{value}</p>
                <p className="text-sm text-slate-500">{label}</p>
              </div>
            ))}
          </div>
          <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
            <table className="w-full">
              <thead className="bg-slate-50 border-b border-slate-200">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">Website</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">Platform</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">Status</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">SEO Score</th>
                  <th className="px-4 py-3"></th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {websites.map(w => (
                  <tr key={w.id} className="hover:bg-slate-50">
                    <td className="px-4 py-3">
                      <p className="font-medium text-slate-900">{w.name}</p>
                      <p className="text-sm text-slate-500">{w.url}</p>
                    </td>
                    <td className="px-4 py-3"><span className="px-2 py-1 bg-slate-100 rounded-md text-xs font-medium text-slate-600 capitalize">{w.platform}</span></td>
                    <td className="px-4 py-3"><span className={`px-2 py-1 rounded-md text-xs font-medium capitalize ${w.status === 'connected' ? 'bg-accent/10 text-accent' : w.status === 'error' ? 'bg-error/10 text-error' : 'bg-slate-100 text-slate-500'}`}>{w.status}</span></td>
                    <td className="px-4 py-3"><span className="text-lg font-semibold text-slate-900">{w.seoScore}</span></td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <button onClick={() => openEdit('websites', w)} className="p-1.5 text-slate-400 hover:text-primary rounded-lg hover:bg-slate-100"><Pencil size={16} /></button>
                        <button onClick={() => setDeleteTarget({ type: 'websites', id: w.id, label: w.name })} className="p-1.5 text-slate-400 hover:text-error rounded-lg hover:bg-slate-100"><Trash2 size={16} /></button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}

      {/* API Keys Tab */}
      {activeTab === 'api-keys' && (
        <>
          <div className="grid grid-cols-3 gap-4">
            {keyStats.map(({ label, value, color }) => (
              <div key={label} className="bg-white rounded-xl p-4 border border-slate-200">
                <p className={`text-2xl font-semibold ${color}`}>{value}</p>
                <p className="text-sm text-slate-500">{label}</p>
              </div>
            ))}
          </div>
          <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
            <table className="w-full">
              <thead className="bg-slate-50 border-b border-slate-200">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">Label</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">API Key</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">Rate Limit</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">Usage</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">Status</th>
                  <th className="px-4 py-3"></th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {apiKeys.map(k => (
                  <tr key={k.id} className="hover:bg-slate-50">
                    <td className="px-4 py-3"><span className="font-medium text-slate-900">{k.label}</span></td>
                    <td className="px-4 py-3"><code className="text-sm bg-slate-100 px-2 py-1 rounded font-mono">{k.keyPrefix}****</code></td>
                    <td className="px-4 py-3 text-sm text-slate-600">{k.rateLimit.toLocaleString()}/day</td>
                    <td className="px-4 py-3 text-sm text-slate-600">{k.callsCount.toLocaleString()}</td>
                    <td className="px-4 py-3"><span className={`px-2 py-1 rounded-md text-xs font-medium ${k.isActive ? 'bg-accent/10 text-accent' : 'bg-slate-100 text-slate-500'}`}>{k.isActive ? 'Active' : 'Inactive'}</span></td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <button onClick={() => openEdit('api-keys', k)} className="p-1.5 text-slate-400 hover:text-primary rounded-lg hover:bg-slate-100"><Pencil size={16} /></button>
                        <button onClick={() => setDeleteTarget({ type: 'api-keys', id: k.id, label: k.label })} className="p-1.5 text-slate-400 hover:text-error rounded-lg hover:bg-slate-100"><Trash2 size={16} /></button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}

      {/* ML Service Tab */}
      {activeTab === 'ml' && (
        <div className="space-y-6">
          {/* Status Cards */}
          <div className="grid grid-cols-4 gap-4">
            <div className="bg-white rounded-xl p-4 border border-slate-200">
              <p className={`text-2xl font-semibold ${mlStatus?.available ? 'text-accent' : 'text-slate-400'}`}>
                {mlStatus?.available ? 'Online' : 'Offline'}
              </p>
              <p className="text-sm text-slate-500">API Reachable</p>
            </div>
            <div className="bg-white rounded-xl p-4 border border-slate-200">
              <p className={`text-2xl font-semibold ${dockerInfo?.container?.state === 'running' ? 'text-accent' : 'text-slate-400'}`}>
                {dockerInfo?.container ? dockerInfo.container.state : 'N/A'}
              </p>
              <p className="text-sm text-slate-500">Container</p>
            </div>
            <div className="bg-white rounded-xl p-4 border border-slate-200">
              <p className="text-2xl font-semibold text-slate-900">{dockerInfo?.container?.image ? dockerInfo.container.image.split('/').pop()?.split(':')[0] || 'ml-service' : '-'}</p>
              <p className="text-sm text-slate-500">Image</p>
            </div>
            <div className="bg-white rounded-xl p-4 border border-slate-200">
              <p className="text-2xl font-semibold text-slate-900">{mlStatus?.train_step ?? '-'}</p>
              <p className="text-sm text-slate-500">Train Step</p>
            </div>
          </div>

          {/* Container Control */}
          <div className="bg-white rounded-xl border border-slate-200 p-6">
            <h3 className="text-lg font-semibold text-slate-900 mb-4 flex items-center gap-2">
              <Cpu size={20} className="text-primary" /> Container Lifecycle
            </h3>
            <div className="space-y-4">
              <div className="flex flex-wrap gap-3">
                <button
                  onClick={async () => {
                    if (!token) return; setContainerAction('start')
                    try {
                      const res = await axios.post('/api/admin/v1/ml/container/start', {}, authHeaders(token))
                      const d = await axios.get('/api/admin/v1/ml/container/status', authHeaders(token))
                      setDockerInfo(d.data)
                    } catch { alert('Failed to start container') }
                    setContainerAction(null)
                  }}
                  disabled={!!containerAction}
                  className="flex items-center gap-2 px-4 py-2 bg-accent text-white rounded-lg text-sm font-medium hover:bg-accent/90 disabled:opacity-50"
                >
                  {containerAction === 'start' ? <RefreshCw size={16} className="animate-spin" /> : <Power size={16} />}
                  Start
                </button>
                <button
                  onClick={async () => {
                    if (!token) return; setContainerAction('stop')
                    try {
                      const res = await axios.post('/api/admin/v1/ml/container/stop', {}, authHeaders(token))
                      const d = await axios.get('/api/admin/v1/ml/container/status', authHeaders(token))
                      setDockerInfo(d.data)
                    } catch { alert('Failed to stop container') }
                    setContainerAction(null)
                  }}
                  disabled={!!containerAction}
                  className="flex items-center gap-2 px-4 py-2 bg-error text-white rounded-lg text-sm font-medium hover:bg-error/90 disabled:opacity-50"
                >
                  {containerAction === 'stop' ? <RefreshCw size={16} className="animate-spin" /> : <PowerOff size={16} />}
                  Stop
                </button>
                <button
                  onClick={async () => {
                    if (!token) return; setContainerAction('restart')
                    try {
                      const res = await axios.post('/api/admin/v1/ml/container/restart', {}, authHeaders(token))
                      await new Promise(r => setTimeout(r, 2000))
                      const d = await axios.get('/api/admin/v1/ml/container/status', authHeaders(token))
                      setDockerInfo(d.data)
                    } catch { alert('Failed to restart container') }
                    setContainerAction(null)
                  }}
                  disabled={!!containerAction}
                  className="flex items-center gap-2 px-4 py-2 bg-warning text-white rounded-lg text-sm font-medium hover:bg-warning/90 disabled:opacity-50"
                >
                  <RefreshCw size={16} className={containerAction === 'restart' ? 'animate-spin' : ''} />
                  Restart
                </button>
                <button
                  onClick={async () => {
                    if (!token) return; setLogsLoading(true)
                    try {
                      const res = await axios.get('/api/admin/v1/ml/container/logs?tail=100', authHeaders(token))
                      setMlLogs(res.data.logs || [])
                    } catch { alert('Failed to fetch logs') }
                    setLogsLoading(false)
                  }}
                  className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-slate-700 bg-slate-100 rounded-lg hover:bg-slate-200"
                >
                  <RefreshCw size={16} className={logsLoading ? 'animate-spin' : ''} />
                  Fetch Logs
                </button>
              </div>

              <div className="flex items-center justify-between p-4 bg-slate-50 rounded-lg">
                <div>
                  <p className="font-medium text-slate-900">ML Service Toggle</p>
                  <p className="text-sm text-slate-500">Enable/disable ML client in backend</p>
                </div>
                <button
                  onClick={async () => {
                    if (!token) return; setMlToggling(true)
                    try {
                      const res = await axios.post('/api/admin/v1/ml/toggle', { enabled: !mlStatus?.available }, authHeaders(token))
                      setMlStatus((prev: any) => ({ ...prev, available: res.data.enabled }))
                    } catch { alert('Failed to toggle') }
                    setMlToggling(false)
                  }}
                  disabled={mlToggling}
                  className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium ${
                    mlStatus?.available ? 'bg-error/10 text-error hover:bg-error/20' : 'bg-accent/10 text-accent hover:bg-accent/20'
                  }`}
                >
                  {mlToggling ? <RefreshCw size={16} className="animate-spin" /> : mlStatus?.available ? <PowerOff size={16} /> : <Power size={16} />}
                  {mlStatus?.available ? 'Disable Client' : 'Enable Client'}
                </button>
              </div>
            </div>
          </div>

          {/* Components */}
          {mlStatus?.embeddings_loaded !== undefined && (
            <div className="bg-white rounded-xl border border-slate-200 p-6">
              <h3 className="text-sm font-semibold text-slate-500 uppercase tracking-wider mb-3">ML Components</h3>
              <div className="flex flex-wrap gap-2">
                {['trainer', 'lora', 'cross_site', 'embeddings'].map(c => (
                  <span key={c} className={`px-3 py-1.5 rounded-md text-sm font-medium ${
                    mlStatus?.[`${c}_loaded`] ? 'bg-accent/10 text-accent' : 'bg-slate-100 text-slate-400'
                  }`}>
                    {c} {mlStatus?.[`${c}_loaded`] ? '✓' : '✗'}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Container Info */}
          {dockerInfo?.container && (
            <div className="bg-white rounded-xl border border-slate-200 p-6">
              <h3 className="text-sm font-semibold text-slate-500 uppercase tracking-wider mb-3">Container Details</h3>
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div><span className="text-slate-500">Container ID:</span> <span className="font-mono text-slate-900">{dockerInfo.container.id?.slice(0, 12)}</span></div>
                <div><span className="text-slate-500">Status:</span> <span className="text-slate-900">{dockerInfo.container.status}</span></div>
                <div><span className="text-slate-500">Image:</span> <span className="text-slate-900">{dockerInfo.container.image}</span></div>
                <div><span className="text-slate-500">Ports:</span> <span className="text-slate-900">{dockerInfo.container.ports || '-'}</span></div>
              </div>
            </div>
          )}

          {/* Container Logs */}
          <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
            <div className="px-6 py-4 border-b border-slate-200 flex items-center justify-between">
              <h3 className="text-sm font-semibold text-slate-500 uppercase tracking-wider">Container Logs</h3>
              <div className="flex gap-2">
                <button onClick={() => setMlLogs([])} className="text-xs text-slate-400 hover:text-slate-600">Clear</button>
              </div>
            </div>
            <div className="bg-slate-950 p-4 max-h-64 overflow-y-auto font-mono text-xs leading-relaxed">
              {mlLogs.length === 0 ? (
                <p className="text-slate-500 italic">Click "Fetch Logs" to view container output</p>
              ) : (
                mlLogs.map((line, i) => (
                  <div key={i} className="text-slate-300 hover:text-white transition-colors">
                    {line || <br />}
                  </div>
                ))
              )}
            </div>
          </div>

          <div className="flex items-center justify-end">
            <button
              onClick={async () => {
                if (!token) return
                const [ml, docker] = await Promise.all([
                  axios.get('/api/admin/v1/ml/status', authHeaders(token)).catch(() => null),
                  axios.get('/api/admin/v1/ml/container/status', authHeaders(token)).catch(() => null),
                ])
                if (ml?.data) setMlStatus(ml.data)
                if (docker?.data) setDockerInfo(docker.data)
              }}
              className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-primary bg-primary/10 rounded-lg hover:bg-primary/20"
            >
              <RefreshCw size={16} /> Refresh All
            </button>
          </div>
        </div>
      )}

      {/* Create / Edit Modal */}
      {formMode && (
        <Modal title={`${formMode === 'create' ? 'Create' : 'Edit'} ${activeTab === 'users' ? 'User' : activeTab === 'websites' ? 'Website' : 'API Key'}`} onClose={resetForm}>
          {newKeyValue ? (
            <div>
              <div className="mb-4 p-4 bg-amber-50 border border-amber-200 rounded-lg">
                <p className="text-sm font-medium text-amber-800 mb-2">Copy this key now. You won't see it again.</p>
                <code className="block text-xs bg-white p-3 rounded border border-amber-200 font-mono break-all select-all">{newKeyValue}</code>
              </div>
              <button onClick={resetForm} className="w-full px-4 py-2 bg-primary text-white rounded-lg text-sm font-medium hover:bg-primary/90">Done</button>
            </div>
          ) : (
            <>
              {getFormFields()}
              <div className="flex justify-end gap-3 mt-4">
                <button onClick={resetForm} className="px-4 py-2 text-sm text-slate-600 hover:bg-slate-100 rounded-lg">Cancel</button>
                <button onClick={handleSave} className="px-4 py-2 text-sm bg-primary text-white rounded-lg hover:bg-primary/90">Save</button>
              </div>
            </>
          )}
        </Modal>
      )}

      {/* Delete Confirm */}
      {deleteTarget && (
        <ConfirmDialog
          message={`Delete "${deleteTarget.label}"? This action cannot be undone.`}
          onConfirm={handleDelete}
          onCancel={() => setDeleteTarget(null)}
        />
      )}
    </div>
  )
}
