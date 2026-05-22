import { useState, useEffect } from 'react'
import { Users, Globe, Key, Plus, Pencil, Trash2, X, Cpu, RefreshCw, Power, PowerOff } from 'lucide-react'
import { useAuth } from '../hooks/useAuth'
import axios from 'axios'
import { Button } from '../components/Button';
import { Input } from '../components/Input';

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
      <div className="bg-surface rounded-modal border border-border shadow-xl w-full max-w-lg mx-4 max-h-[90vh] overflow-y-auto" onClick={e => e.stopPropagation()}>
        <div className="flex items-center justify-between px-6 py-4 border-b border-border">
          <h2 className="text-lg font-display font-semibold text-textPrimary">{title}</h2>
          <Button onClick={onClose} className="p-1 text-textSecondary hover:text-textPrimary rounded-lg">
            <X size={20} />
          </Button>
        </div>
        <div className="px-6 py-4">{children}</div>
      </div>
    </div>
  )
}

function ConfirmDialog({ message, onConfirm, onCancel }: { message: string; onConfirm: () => void; onCancel: () => void }) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40" onClick={onCancel}>
      <div className="bg-surface rounded-modal border border-border shadow-xl w-full max-w-sm mx-4 p-6" onClick={e => e.stopPropagation()}>
        <p className="text-textPrimary mb-6">{message}</p>
        <div className="flex justify-end gap-3">
          <Button onClick={onCancel} variant="ghost">Cancel</Button>
          <Button onClick={onConfirm} variant="danger">Delete</Button>
        </div>
      </div>
    </div>
  )
}


function Select({ label, value, onChange, options }: {
  label: string; value: string; onChange: (v: string) => void; options: { value: string; label: string }[]
}) {
  return (
    <div className="mb-4">
      <label className="block text-sm font-medium text-textPrimary mb-1">{label}</label>
      <select
        value={value}
        onChange={e => onChange(e.target.value)}
        className="w-full px-3 py-2 border border-border rounded-lg text-sm focus:outline-none focus:border-primary/50 bg-background"
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
    else setForm({ label: item.label || '', rateLimit: String(item.rateLimit || 1000), isActive: Boolean(item.isActive) ? 'true' : 'false' })
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
        <div className="mb-4"><Input label="Name" value={form.name || ''} onChange={e => setForm(f => ({ ...f, name: e.target.value } ))} /></div>
        <div className="mb-4"><Input label="Email" value={form.email || ''} onChange={e => setForm(f => ({ ...f, email: e.target.value } ))} /></div>
        {formMode === 'create' && <div className="mb-4"><Input label="Password" type="password" value={form.password || ''} onChange={e => setForm(f => ({ ...f, password: e.target.value } ))} /></div>}
        <div className="mb-4"><Input label="OpenRouter API Key" type="password" value={form.openrouter_key || ''} onChange={e => setForm(f => ({ ...f, openrouter_key: e.target.value } ))} placeholder="sk-or-v1-..." /></div>
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
        <div className="mb-4"><Input label="Name" value={form.name || ''} onChange={e => setForm(f => ({ ...f, name: e.target.value } ))} /></div>
        <div className="mb-4"><Input label="URL" value={form.url || ''} onChange={e => setForm(f => ({ ...f, url: e.target.value } ))} placeholder="https://example.com" /></div>
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
        <div className="mb-4"><Input label="Label" value={form.label || ''} onChange={e => setForm(f => ({ ...f, label: e.target.value } ))} placeholder="e.g. Production API Key" /></div>
        <Select label="User" value={form.userId || ''} onChange={v => setForm(f => ({ ...f, userId: v }))} options={[
          { value: '', label: 'Select user...' },
          ...users.map(u => ({ value: u.id, label: `${u.name} (${u.email})` }))
        ]} />
        <div className="mb-4"><Input label="Rate Limit (requests/day)" type="number" value={form.rateLimit || '1000'} onChange={e => setForm(f => ({ ...f, rateLimit: e.target.value } ))} /></div>
        {formMode === 'edit' && (
          <Select label="Active" value={form.isActive || 'true'} onChange={v => setForm(f => ({ ...f, isActive: v }))} options={[
            { value: 'true', label: 'Active' }, { value: 'false', label: 'Inactive' }
          ]} />
        )}
      </>
    )
  }

  if (loading) return <div className="p-8 text-center text-textSecondary">Loading...</div>

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-display font-semibold text-textPrimary">Management</h1>
        {activeTab !== 'ml' && (
          <Button onClick={() => openCreate(activeTab)} className="flex items-center gap-2">
            <Plus size={18} /> Add {activeTab === 'users' ? 'User' : activeTab === 'websites' ? 'Website' : 'API Key'}
          </Button>
        )}
      </div>

      {/* Tabs */}
      <div className="flex gap-1 bg-white rounded-xl border border-border p-1">
        {TABS.map(({ key, label, icon: Icon }) => (
          <Button
            key={key}
            onClick={() => { setActiveTab(key); resetForm() }}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              activeTab === key ? 'bg-background text-primary shadow-sm' : 'text-textSecondary hover:bg-background hover:text-textPrimary'
            }`}
          >
            <Icon size={18} /> {label}
          </Button>
        ))}
      </div>

      {/* Users Tab */}
      {activeTab === 'users' && (
        <>
          <div className="grid grid-cols-3 gap-4">
            {userStats.map(({ label, value, color }) => (
              <div key={label} className="bg-white rounded-xl p-4 border border-border">
                <p className={`text-2xl font-semibold ${color}`}>{value}</p>
                <p className="text-sm text-textSecondary">{label}</p>
              </div>
            ))}
          </div>
          <div className="bg-white rounded-xl border border-border overflow-hidden">
            <table className="w-full">
              <thead className="bg-background border-b border-border">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium text-textSecondary uppercase">User</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-textSecondary uppercase">Plan</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-textSecondary uppercase">Status</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-textSecondary uppercase">Websites</th>
                  <th className="px-4 py-3"></th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {users.map(u => (
                  <tr key={u.id} className="hover:bg-background">
                    <td className="px-4 py-3">
                      <p className="font-medium text-textPrimary">{u.name}</p>
                      <p className="text-sm text-textSecondary">{u.email}</p>
                    </td>
                    <td className="px-4 py-3"><span className="px-2 py-1 bg-background rounded-md text-xs font-medium text-textSecondary capitalize">{u.plan}</span></td>
                    <td className="px-4 py-3"><span className={`px-2 py-1 rounded-md text-xs font-medium ${u.subscriptionStatus === 'active' ? 'bg-accent/10 text-accent' : 'bg-background text-textSecondary'}`}>{u.subscriptionStatus}</span></td>
                    <td className="px-4 py-3 text-sm text-textSecondary">{u.websitesCount || 0}</td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <Button onClick={() => openEdit('users', u)} className="p-1.5 text-textSecondary hover:text-primary rounded-lg hover:bg-background"><Pencil size={16} /></Button>
                        <Button onClick={() => setDeleteTarget({ type: 'users', id: u.id, label: u.name })} className="p-1.5 text-textSecondary hover:text-error rounded-lg hover:bg-background"><Trash2 size={16} /></Button>
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
              <div key={label} className="bg-white rounded-xl p-4 border border-border">
                <p className={`text-2xl font-semibold ${color}`}>{value}</p>
                <p className="text-sm text-textSecondary">{label}</p>
              </div>
            ))}
          </div>
          <div className="bg-white rounded-xl border border-border overflow-hidden">
            <table className="w-full">
              <thead className="bg-background border-b border-border">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium text-textSecondary uppercase">Website</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-textSecondary uppercase">Platform</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-textSecondary uppercase">Status</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-textSecondary uppercase">SEO Score</th>
                  <th className="px-4 py-3"></th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {websites.map(w => (
                  <tr key={w.id} className="hover:bg-background">
                    <td className="px-4 py-3">
                      <p className="font-medium text-textPrimary">{w.name}</p>
                      <p className="text-sm text-textSecondary">{w.url}</p>
                    </td>
                    <td className="px-4 py-3"><span className="px-2 py-1 bg-background rounded-md text-xs font-medium text-textSecondary capitalize">{w.platform}</span></td>
                    <td className="px-4 py-3"><span className={`px-2 py-1 rounded-md text-xs font-medium capitalize ${w.status === 'connected' ? 'bg-accent/10 text-accent' : w.status === 'error' ? 'bg-error/10 text-error' : 'bg-background text-textSecondary'}`}>{w.status}</span></td>
                    <td className="px-4 py-3"><span className="text-lg font-display font-semibold text-textPrimary">{w.seoScore}</span></td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <Button onClick={() => openEdit('websites', w)} className="p-1.5 text-textSecondary hover:text-primary rounded-lg hover:bg-background"><Pencil size={16} /></Button>
                        <Button onClick={() => setDeleteTarget({ type: 'websites', id: w.id, label: w.name })} className="p-1.5 text-textSecondary hover:text-error rounded-lg hover:bg-background"><Trash2 size={16} /></Button>
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
              <div key={label} className="bg-white rounded-xl p-4 border border-border">
                <p className={`text-2xl font-semibold ${color}`}>{value}</p>
                <p className="text-sm text-textSecondary">{label}</p>
              </div>
            ))}
          </div>
          <div className="bg-white rounded-xl border border-border overflow-hidden">
            <table className="w-full">
              <thead className="bg-background border-b border-border">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium text-textSecondary uppercase">Label</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-textSecondary uppercase">API Key</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-textSecondary uppercase">Rate Limit</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-textSecondary uppercase">Usage</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-textSecondary uppercase">Status</th>
                  <th className="px-4 py-3"></th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {apiKeys.map(k => (
                  <tr key={k.id} className="hover:bg-background">
                    <td className="px-4 py-3"><span className="font-medium text-textPrimary">{k.label}</span></td>
                    <td className="px-4 py-3"><code className="text-sm bg-background px-2 py-1 rounded font-mono">{k.keyPrefix}****</code></td>
                    <td className="px-4 py-3 text-sm text-textSecondary">{k.rateLimit.toLocaleString()}/day</td>
                    <td className="px-4 py-3 text-sm text-textSecondary">{k.callsCount.toLocaleString()}</td>
                    <td className="px-4 py-3"><span className={`px-2 py-1 rounded-md text-xs font-medium ${k.isActive ? 'bg-accent/10 text-accent' : 'bg-background text-textSecondary'}`}>{k.isActive ? 'Active' : 'Inactive'}</span></td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <Button onClick={() => openEdit('api-keys', k)} className="p-1.5 text-textSecondary hover:text-primary rounded-lg hover:bg-background"><Pencil size={16} /></Button>
                        <Button onClick={() => setDeleteTarget({ type: 'api-keys', id: k.id, label: k.label })} className="p-1.5 text-textSecondary hover:text-error rounded-lg hover:bg-background"><Trash2 size={16} /></Button>
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
            <div className="bg-white rounded-xl p-4 border border-border">
              <p className={`text-2xl font-semibold ${mlStatus?.available ? 'text-accent' : 'text-textSecondary'}`}>
                {mlStatus?.available ? 'Online' : 'Offline'}
              </p>
              <p className="text-sm text-textSecondary">API Reachable</p>
            </div>
            <div className="bg-white rounded-xl p-4 border border-border">
              <p className={`text-2xl font-semibold ${dockerInfo?.container?.state === 'running' ? 'text-accent' : 'text-textSecondary'}`}>
                {dockerInfo?.container ? dockerInfo.container.state : 'N/A'}
              </p>
              <p className="text-sm text-textSecondary">Container</p>
            </div>
            <div className="bg-white rounded-xl p-4 border border-border">
              <p className="text-2xl font-display font-semibold text-textPrimary">{dockerInfo?.container?.image ? dockerInfo.container.image.split('/').pop()?.split(':')[0] || 'ml-service' : '-'}</p>
              <p className="text-sm text-textSecondary">Image</p>
            </div>
            <div className="bg-white rounded-xl p-4 border border-border">
              <p className="text-2xl font-display font-semibold text-textPrimary">{mlStatus?.train_step ?? '-'}</p>
              <p className="text-sm text-textSecondary">Train Step</p>
            </div>
          </div>

          {/* Container Control */}
          <div className="bg-white rounded-xl border border-border p-6">
            <h3 className="text-lg font-display font-semibold text-textPrimary mb-4 flex items-center gap-2">
              <Cpu size={20} className="text-primary" /> Container Lifecycle
            </h3>
            <div className="space-y-4">
              <div className="flex flex-wrap gap-3">
                <Button onClick={async () => {
                    if (!token) return; setContainerAction('start')
                    try {
                      const res = await axios.post('/api/admin/v1/ml/container/start', {}, authHeaders(token))
                      const d = await axios.get('/api/admin/v1/ml/container/status', authHeaders(token))
                      setDockerInfo(d.data)
                    } catch { alert('Failed to start container') }
                    setContainerAction(null)
                  }} disabled={!!containerAction} variant="secondary" className="!bg-success/10 !text-success !border-success/20 hover:!bg-success/20 gap-2">
                  {containerAction === 'start' ? <RefreshCw size={16} className="animate-spin" /> : <Power size={16} />}
                  Start
                </Button>
                <Button onClick={async () => {
                    if (!token) return; setContainerAction('stop')
                    try {
                      const res = await axios.post('/api/admin/v1/ml/container/stop', {}, authHeaders(token))
                      const d = await axios.get('/api/admin/v1/ml/container/status', authHeaders(token))
                      setDockerInfo(d.data)
                    } catch { alert('Failed to stop container') }
                    setContainerAction(null)
                  }} disabled={!!containerAction} variant="danger" className="gap-2">
                  {containerAction === 'stop' ? <RefreshCw size={16} className="animate-spin" /> : <PowerOff size={16} />}
                  Stop
                </Button>
                <Button onClick={async () => {
                    if (!token) return; setContainerAction('restart')
                    try {
                      const res = await axios.post('/api/admin/v1/ml/container/restart', {}, authHeaders(token))
                      await new Promise(r => setTimeout(r, 2000))
                      const d = await axios.get('/api/admin/v1/ml/container/status', authHeaders(token))
                      setDockerInfo(d.data)
                    } catch { alert('Failed to restart container') }
                    setContainerAction(null)
                  }} disabled={!!containerAction} variant="secondary" className="!bg-warning/10 !text-warning !border-warning/20 hover:!bg-warning/20 gap-2">
                  <RefreshCw size={16} className={containerAction === 'restart' ? 'animate-spin' : ''} />
                  Restart
                </Button>
                <Button onClick={async () => {
                    if (!token) return; setLogsLoading(true)
                    try {
                      const res = await axios.get('/api/admin/v1/ml/container/logs?tail=100', authHeaders(token))
                      setMlLogs(res.data.logs || [])
                    } catch { alert('Failed to fetch logs') }
                    setLogsLoading(false)
                  }}
                  className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-textPrimary bg-background rounded-lg hover:bg-slate-200"
                >
                  <RefreshCw size={16} className={logsLoading ? 'animate-spin' : ''} />
                  Fetch Logs
                </Button>
              </div>

              <div className="flex items-center justify-between p-4 bg-background rounded-lg">
                <div>
                  <p className="font-medium text-textPrimary">ML Service Toggle</p>
                  <p className="text-sm text-textSecondary">Enable/disable ML client in backend</p>
                </div>
                <Button
                  onClick={async () => {
                    if (!token) return; setMlToggling(true)
                    try {
                      const res = await axios.post('/api/admin/v1/ml/toggle', { enabled: !mlStatus?.available }, authHeaders(token))
                      setMlStatus((prev: any) => ({ ...prev, available: res.data.enabled }))
                    } catch { alert('Failed to toggle') }
                    setMlToggling(false)
                  }} disabled={mlToggling} variant={mlStatus?.available ? "danger" : "primary"} className="gap-2">
                  {mlToggling ? <RefreshCw size={16} className="animate-spin" /> : mlStatus?.available ? <PowerOff size={16} /> : <Power size={16} />}
                  {mlStatus?.available ? 'Disable Client' : 'Enable Client'}
                </Button>
              </div>
            </div>
          </div>

          {/* Components */}
          {mlStatus?.embeddings_loaded !== undefined && (
            <div className="bg-white rounded-xl border border-border p-6">
              <h3 className="text-sm font-semibold text-textSecondary uppercase tracking-wider mb-3">ML Components</h3>
              <div className="flex flex-wrap gap-2">
                {['trainer', 'lora', 'cross_site', 'embeddings'].map(c => (
                  <span key={c} className={`px-3 py-1.5 rounded-md text-sm font-medium ${
                    mlStatus?.[`${c}_loaded`] ? 'bg-accent/10 text-accent' : 'bg-background text-textSecondary'
                  }`}>
                    {c} {mlStatus?.[`${c}_loaded`] ? '✓' : '✗'}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Container Info */}
          {dockerInfo?.container && (
            <div className="bg-white rounded-xl border border-border p-6">
              <h3 className="text-sm font-semibold text-textSecondary uppercase tracking-wider mb-3">Container Details</h3>
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div><span className="text-textSecondary">Container ID:</span> <span className="font-mono text-textPrimary">{dockerInfo.container.id?.slice(0, 12)}</span></div>
                <div><span className="text-textSecondary">Status:</span> <span className="text-textPrimary">{dockerInfo.container.status}</span></div>
                <div><span className="text-textSecondary">Image:</span> <span className="text-textPrimary">{dockerInfo.container.image}</span></div>
                <div><span className="text-textSecondary">Ports:</span> <span className="text-textPrimary">{dockerInfo.container.ports || '-'}</span></div>
              </div>
            </div>
          )}

          {/* Container Logs */}
          <div className="bg-white rounded-xl border border-border overflow-hidden">
            <div className="px-6 py-4 border-b border-border flex items-center justify-between">
              <h3 className="text-sm font-semibold text-textSecondary uppercase tracking-wider">Container Logs</h3>
              <div className="flex gap-2">
                <Button onClick={() => setMlLogs([])} className="text-xs text-textSecondary hover:text-textPrimary">Clear</Button>
              </div>
            </div>
            <div className="bg-[#1E1E1E] p-4 max-h-64 overflow-y-auto font-mono text-xs leading-relaxed">
              {mlLogs.length === 0 ? (
                <p className="text-textSecondary italic">Click "Fetch Logs" to view container output</p>
              ) : (
                mlLogs.map((line, i) => (
                  <div key={i} className="text-[#A1A1AA] hover:text-surface transition-colors">
                    {line || <br />}
                  </div>
                ))
              )}
            </div>
          </div>

          <div className="flex items-center justify-end">
            <Button
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
            </Button>
          </div>
        </div>
      )}

      {/* Create / Edit Modal */}
      {formMode && (
        <Modal title={`${formMode === 'create' ? 'Create' : 'Edit'} ${activeTab === 'users' ? 'User' : activeTab === 'websites' ? 'Website' : 'API Key'}`} onClose={resetForm}>
          {newKeyValue ? (
            <div>
              <div className="mb-4 p-4 bg-amber-50 border border-amber-200 rounded-lg">
                <p className="text-sm font-medium text-warning mb-2">Copy this key now. You won't see it again.</p>
                <code className="block text-xs bg-white p-3 rounded border border-amber-200 font-mono break-all select-all">{newKeyValue}</code>
              </div>
              <Button onClick={resetForm} className="w-full px-4 py-2 bg-background text-primary shadow-sm rounded-lg text-sm font-medium hover:bg-primary/90">Done</Button>
            </div>
          ) : (
            <>
              {getFormFields()}
              <div className="flex justify-end gap-3 mt-4">
                <Button onClick={resetForm} className="px-4 py-2 text-sm text-textSecondary hover:bg-background hover:text-textPrimary rounded-lg">Cancel</Button>
                <Button onClick={handleSave} className="px-4 py-2 text-sm bg-background text-primary shadow-sm rounded-lg hover:bg-primary/90">Save</Button>
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
