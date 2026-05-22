import { useState, useEffect } from 'react'
import { BarChart3, Download } from 'lucide-react'
import { useAuth } from '../hooks/useAuth'
import axios from 'axios'

export default function ResultsPage() {
  const { token } = useAuth()
  const [summary, setSummary] = useState<any>(null)
  const [issues, setIssues] = useState<any[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (token) {
      axios.get('/api/admin/v1/results/summary', {
        headers: { Authorization: `Bearer ${token}` }
      })
      .then(res => setSummary(res.data))
      .catch(err => console.error(err))

      axios.get('/api/admin/v1/results/issues', {
        headers: { Authorization: `Bearer ${token}` }
      })
      .then(res => setIssues(res.data.data || []))
      .catch(err => console.error(err))
      .finally(() => setLoading(false))
    }
  }, [token])

  if (loading) return <div className="p-8 text-center text-slate-500">Loading...</div>

  const stats = [
    { label: 'Total Websites', value: summary?.totalWebsites || 0 },
    { label: 'Avg SEO Score', value: summary?.avgSeoScore ? `${summary.avgSeoScore}%` : '0%' },
    { label: 'Total Issues', value: summary?.totalIssues || 0 },
    { label: 'Pages Scanned', value: '0' },
  ]

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold text-slate-900">Results</h1>
      </div>

      <div className="grid grid-cols-4 gap-4">
        {stats.map(({ label, value }) => (
          <div key={label} className="bg-white rounded-xl p-4 border border-slate-200">
            <p className="text-2xl font-semibold text-slate-900">{value}</p>
            <p className="text-sm text-slate-500">{label}</p>
          </div>
        ))}
      </div>

      {issues.length === 0 ? (
        <div className="bg-white rounded-xl border border-slate-200 p-12 text-center">
          <BarChart3 className="w-12 h-12 text-slate-300 mx-auto mb-4" />
          <p className="text-slate-500">No issues found</p>
        </div>
      ) : (
        <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
          <table className="w-full">
            <thead className="bg-slate-50 border-b border-slate-200">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">Website</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">Type</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">Category</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">Message</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">Severity</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {issues.map((issue) => (
                <tr key={issue.id} className="hover:bg-slate-50">
                  <td className="px-4 py-3 text-sm text-slate-900">{issue.website}</td>
                  <td className="px-4 py-3 text-sm text-slate-600">{issue.type}</td>
                  <td className="px-4 py-3 text-sm text-slate-600">{issue.category}</td>
                  <td className="px-4 py-3 text-sm text-slate-600 max-w-md truncate">{issue.message}</td>
                  <td className="px-4 py-3">
                    <span className={`px-2 py-1 rounded-md text-xs font-medium ${
                      issue.severity === 'error' ? 'bg-error/10 text-error' :
                      issue.severity === 'warning' ? 'bg-warning/10 text-warning' :
                      'bg-slate-100 text-slate-600'
                    }`}>
                      {issue.severity}
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