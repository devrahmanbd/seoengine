import { useState, useEffect } from 'react'
import { Globe, RefreshCw, Trash2, Search, ExternalLink } from 'lucide-react'
import { useAuth } from '../hooks/useAuth'
import axios from 'axios'
import { Button } from '../components/Button'
import { Card } from '../components/Card'
import { Input } from '../components/Input'

interface Website {
  id: string
  name: string
  url: string
  user: string
  platform: string
  status: string
  seoScore: number
  lastScan: string
}

interface WebsiteAPI {
  id: string
  name: string
  url: string
  user: string
  platform: string
  status: string
  seoScore: number
  lastScan: string
  userId?: string
}

export default function WebsitesPage() {
  const { token } = useAuth()
  const [websites, setWebsites] = useState<Website[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (token) {
      axios.get('/api/admin/v1/websites', {
        headers: { Authorization: `Bearer ${token}` }
      })
      .then(res => {
        const data = res.data.data.map((w: WebsiteAPI) => ({
          id: w.id,
          name: w.name || w.url,
          url: w.url,
          user: w.user || 'Unknown',
          platform: w.platform,
          status: w.status,
          seoScore: w.seoScore || 0,
          lastScan: w.lastScan || 'Never'
        }))
        setWebsites(data)
      })
      .catch(err => console.error(err))
      .finally(() => setLoading(false))
    }
  }, [token])

  const stats = [
    { label: 'Total Connected', value: websites.length.toString(), icon: Globe },
    { label: 'Active Scans', value: websites.filter(w => w.status === 'connected').length.toString(), icon: RefreshCw },
    { label: 'Avg SEO Score', value: websites.length ? Math.round(websites.reduce((a, b) => a + b.seoScore, 0) / websites.length) + '%' : '0%', icon: Globe },
    { label: 'Issues Found', value: websites.filter(w => w.status === 'error').length.toString(), icon: Globe },
  ]

  const getStatusColor = (status: string) => {
    const colors: Record<string, string> = {
      connected: 'bg-accent/10 text-accent',
      disconnected: 'bg-slate-100 text-slate-500',
      error: 'bg-error/10 text-error',
    }
    return colors[status] || colors.disconnected
  }

  const getScoreColor = (score: number) => {
    if (score >= 71) return 'text-accent'
    if (score >= 41) return 'text-warning'
    return 'text-error'
  }

  if (loading) return <div className="p-8 text-center text-slate-500">Loading...</div>

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold text-slate-900">Websites</h1>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-4 gap-4">
        {stats.map(({ label, value, icon: Icon }) => (
          <div key={label} className="bg-white rounded-xl p-4 border border-slate-200">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-slate-100 text-primary">
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
            placeholder="Search websites..." 
            className="w-full pl-10 pr-4 py-2 bg-slate-50 border border-slate-200 rounded-lg text-sm focus:outline-none"
          />
        </div>
      </div>

      {/* Table */}
      {websites.length === 0 ? (
        <div className="bg-white rounded-xl border border-slate-200 p-12 text-center">
          <Globe className="w-12 h-12 text-slate-300 mx-auto mb-4" />
          <p className="text-slate-500">No websites connected yet</p>
        </div>
      ) : (
        <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
          <table className="w-full">
            <thead className="bg-slate-50 border-b border-slate-200">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">Website</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">Owner</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">Platform</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">Status</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">SEO Score</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">Last Scan</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {websites.map((site) => (
                <tr key={site.id} className="hover:bg-slate-50">
                  <td className="px-4 py-3">
                    <div>
                      <p className="font-medium text-slate-900">{site.name}</p>
                      <a href={site.url} target="_blank" className="text-sm text-primary flex items-center gap-1 hover:underline">
                        {site.url.slice(0, 40)}... <ExternalLink size={12} />
                      </a>
                    </div>
                  </td>
                  <td className="px-4 py-3 text-sm text-slate-600">{site.user}</td>
                  <td className="px-4 py-3">
                    <span className="px-2 py-1 bg-slate-100 rounded-md text-xs font-medium text-slate-600 capitalize">
                      {site.platform}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <span className={`px-2 py-1 rounded-md text-xs font-medium ${getStatusColor(site.status)} capitalize`}>
                      {site.status}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <span className={`text-lg font-semibold ${getScoreColor(site.seoScore)}`}>
                      {site.seoScore}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-sm text-slate-500">{site.lastScan}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}