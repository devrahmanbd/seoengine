import { useState, useEffect } from 'react'
import { Bot, Search, Eye } from 'lucide-react'
import { useAuth } from '../hooks/useAuth'
import axios from 'axios'
import { Button } from '../components/Button'
import { Card } from '../components/Card'
import { Input } from '../components/Input'

export default function AILogsPage() {
  const { token } = useAuth()
  const [stats, setStats] = useState<any>(null)
  const [agents, setAgents] = useState<any[]>([])
  const [logs, setLogs] = useState<any[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (token) {
      axios.get('/api/admin/v1/ai-logs/stats', {
        headers: { Authorization: `Bearer ${token}` }
      })
      .then(res => setStats(res.data))
      .catch(err => console.error(err))

      axios.get('/api/admin/v1/ai-logs/agents', {
        headers: { Authorization: `Bearer ${token}` }
      })
      .then(res => setAgents(res.data || []))
      .catch(err => console.error(err))

      axios.get('/api/admin/v1/ai-logs', {
        headers: { Authorization: `Bearer ${token}` }
      })
      .then(res => setLogs(res.data.data || []))
      .catch(err => console.error(err))
      .finally(() => setLoading(false))
    }
  }, [token])

  if (loading) return <div className="p-8 text-center text-slate-500">Loading...</div>

  const statCards = [
    { label: 'Total Runs (24h)', value: stats?.totalRuns24h || 0 },
    { label: 'Success Rate', value: stats?.successRate ? `${stats.successRate}%` : '0%' },
    { label: 'Avg Execution', value: stats?.avgExecutionTime ? `${stats.avgExecutionTime}s` : '0s' },
    { label: 'Active Agents', value: stats?.activeAgents || 0 },
  ]

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed': return <span className="text-accent">✓</span>
      case 'failed': return <span className="text-error">✗</span>
      case 'running': return <span className="text-primary animate-pulse">●</span>
      default: return <span className="text-slate-400">○</span>
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold text-slate-900">AI Logs</h1>
      </div>

      <div className="grid grid-cols-4 gap-4">
        {statCards.map(({ label, value }) => (
          <div key={label} className="bg-white rounded-xl p-4 border border-slate-200">
            <p className="text-2xl font-semibold text-slate-900">{value}</p>
            <p className="text-sm text-slate-500">{label}</p>
          </div>
        ))}
      </div>

      <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
        <div className="p-4 border-b border-slate-200">
          <h2 className="font-semibold text-slate-900">Agent Activity</h2>
        </div>
        {agents.length === 0 ? (
          <div className="p-8 text-center text-slate-500">No agent data</div>
        ) : (
          <div className="grid grid-cols-4 gap-px bg-slate-200">
            {agents.map((agent) => (
              <Button variant="ghost"
                key={agent.type}
                className="p-4 text-left hover:bg-slate-50 bg-white"
              >
                <div className="flex items-center gap-2 mb-2">
                  <Bot size={16} className="text-primary" />
                  <span className="font-medium text-sm text-slate-900">{agent.type}</span>
                </div>
                <div className="space-y-1 text-xs text-slate-500">
                  <p>{agent.runs24h} runs (24h)</p>
                  <p>Avg: {agent.avgTime}</p>
                </div>
              </Button>
            ))}
          </div>
        )}
      </div>

      {logs.length === 0 ? (
        <div className="bg-white rounded-xl border border-slate-200 p-12 text-center">
          <Bot className="w-12 h-12 text-slate-300 mx-auto mb-4" />
          <p className="text-slate-500">No agent logs</p>
        </div>
      ) : (
        <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
          <table className="w-full">
            <thead className="bg-slate-50 border-b border-slate-200">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">Agent</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">Task ID</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">Status</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">Input</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">Output</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">Duration</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">Time</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {logs.map((log) => (
                <tr key={log.id} className="hover:bg-slate-50">
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      <Bot size={16} className="text-primary" />
                      <span className="text-sm text-slate-900">{log.agentType}</span>
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <code className="text-xs bg-slate-100 px-2 py-1 rounded font-mono">{log.taskId}</code>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-1.5">
                      {getStatusIcon(log.status)}
                      <span className="text-sm capitalize">{log.status}</span>
                    </div>
                  </td>
                  <td className="px-4 py-3 text-sm text-slate-500 max-w-xs truncate">{log.input}</td>
                  <td className="px-4 py-3 text-sm text-slate-500 max-w-xs truncate">{log.output}</td>
                  <td className="px-4 py-3 text-sm text-slate-500 font-mono">{log.duration}</td>
                  <td className="px-4 py-3 text-sm text-slate-500 font-mono">{log.timestamp}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}