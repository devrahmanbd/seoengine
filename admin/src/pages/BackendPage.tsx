import { useState, useEffect } from 'react'
import { Activity, Database, Server, RefreshCw, Search } from 'lucide-react'
import { useAuth } from '../hooks/useAuth'
import axios from 'axios'
import { Button } from '../components/Button'
import { Card } from '../components/Card'
import { Input } from '../components/Input'

export default function BackendPage() {
  const { token } = useAuth()
  const [status, setStatus] = useState<any>(null)
  const [logs, setLogs] = useState<any[]>([])
  const [tasks, setTasks] = useState<any[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (token) {
      axios.get('/api/admin/v1/backend/status', {
        headers: { Authorization: `Bearer ${token}` }
      })
      .then(res => setStatus(res.data))
      .catch(err => console.error(err))

      axios.get('/api/admin/v1/logs/errors', {
        headers: { Authorization: `Bearer ${token}` }
      })
      .then(res => setLogs(res.data.data || []))
      .catch(err => console.error(err))

      axios.get('/api/admin/v1/tasks', {
        headers: { Authorization: `Bearer ${token}` }
      })
      .then(res => setTasks(res.data.data || []))
      .catch(err => console.error(err))
      .finally(() => setLoading(false))
    }
  }, [token])

  if (loading) return <div className="p-8 text-center text-textSecondary">Loading...</div>

  const services = [
    { name: 'API Server', status: status?.api?.status || 'unknown', uptime: status?.api?.uptime },
    { name: 'Database', status: status?.database?.status || 'unknown', latency: status?.database?.latency },
    { name: 'Redis', status: status?.redis?.status || 'unknown' },
    { name: 'AI Agents', status: status?.agents?.active ? 'active' : 'idle', count: status?.agents?.active },
  ]

  const getStatusDot = (status: string) => (
    <span className={`w-2.5 h-2.5 rounded-full ${status === 'online' || status === 'connected' ? 'bg-accent' : status === 'active' ? 'bg-accent' : 'bg-slate-300'}`} />
  )

  const getLevelBadge = (level: string) => (
    <span className={`px-2 py-0.5 rounded text-xs font-medium ${
      level === 'critical' ? 'bg-error/10 text-error' : 'bg-warning/10 text-warning'
    }`}>
      {level}
    </span>
  )

  const getTaskStatusBadge = (status: string) => {
    const styles: Record<string, string> = {
      completed: 'bg-accent/10 text-accent',
      processing: 'bg-primary/10 text-primary',
      pending: 'bg-border text-textSecondary',
      failed: 'bg-error/10 text-error',
    }
    return styles[status] || styles.pending
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-display font-semibold text-textPrimary">Backend Status</h1>
      </div>

      <div className="grid grid-cols-4 gap-4">
        {services.map((service) => (
          <div key={service.name} className="bg-surface rounded-card p-4 border border-border">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                {service.name === 'API Server' && <Server size={20} className="text-primary" />}
                {service.name === 'Database' && <Database size={20} className="text-primary" />}
                {service.name === 'Redis' && <Activity size={20} className="text-primary" />}
                {service.name === 'AI Agents' && <Activity size={20} className="text-primary" />}
                <span className="font-medium text-textPrimary">{service.name}</span>
              </div>
              {getStatusDot(service.status)}
            </div>
            <div className="text-sm text-textSecondary">
              {service.uptime && <p>Uptime: {service.uptime}</p>}
              {service.latency && <p>Latency: {service.latency}ms</p>}
              {service.count && <p>Active: {service.count}</p>}
              {!service.uptime && !service.latency && !service.count && <p className="text-accent">Connected</p>}
            </div>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-2 gap-6">
        <div className="bg-surface rounded-card border border-border overflow-hidden">
          <div className="p-4 border-b border-border">
            <h2 className="font-semibold text-textPrimary">Error Logs</h2>
          </div>
          {logs.length === 0 ? (
            <div className="p-8 text-center text-textSecondary">No errors</div>
          ) : (
            <table className="w-full">
              <thead className="bg-background">
                <tr>
                  <th className="px-4 py-2 text-left text-xs font-medium text-textSecondary">Time</th>
                  <th className="px-4 py-2 text-left text-xs font-medium text-textSecondary">Level</th>
                  <th className="px-4 py-2 text-left text-xs font-medium text-textSecondary">Message</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {logs.map((log) => (
                  <tr key={log.id} className="hover:bg-background">
                    <td className="px-4 py-2 text-sm text-textSecondary font-mono">{log.timestamp}</td>
                    <td className="px-4 py-2">{getLevelBadge(log.level)}</td>
                    <td className="px-4 py-2 text-sm text-textSecondary max-w-xs truncate">{log.message}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        <div className="bg-surface rounded-card border border-border overflow-hidden">
          <div className="p-4 border-b border-border">
            <h2 className="font-semibold text-textPrimary">Recent Tasks</h2>
          </div>
          {tasks.length === 0 ? (
            <div className="p-8 text-center text-textSecondary">No tasks</div>
          ) : (
            <table className="w-full">
              <thead className="bg-background">
                <tr>
                  <th className="px-4 py-2 text-left text-xs font-medium text-textSecondary">Type</th>
                  <th className="px-4 py-2 text-left text-xs font-medium text-textSecondary">Website</th>
                  <th className="px-4 py-2 text-left text-xs font-medium text-textSecondary">Status</th>
                  <th className="px-4 py-2 text-left text-xs font-medium text-textSecondary">Duration</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {tasks.map((task) => (
                  <tr key={task.id} className="hover:bg-background">
                    <td className="px-4 py-2 text-sm text-textPrimary">{task.type}</td>
                    <td className="px-4 py-2 text-sm text-textSecondary">{task.website}</td>
                    <td className="px-4 py-2">
                      <span className={`px-2 py-0.5 rounded text-xs font-medium capitalize ${getTaskStatusBadge(task.status)}`}>
                        {task.status}
                      </span>
                    </td>
                    <td className="px-4 py-2 text-sm text-textSecondary">{task.duration}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  )
}