import { Calendar, Clock, CheckCircle, XCircle, Loader2 } from 'lucide-react'
import type { ScheduledAction } from '../../types'

interface Props {
  actions: ScheduledAction[]
  loading: boolean
}

const statusIcons: Record<string, typeof Loader2> = {
  pending: Clock,
  scheduled: Calendar,
  in_progress: Loader2,
  completed: CheckCircle,
  failed: XCircle,
}

const statusColors: Record<string, string> = {
  pending: 'text-slate-400',
  scheduled: 'text-blue-500',
  in_progress: 'text-yellow-500',
  completed: 'text-green-500',
  failed: 'text-red-500',
}

export default function ActionTimeline({ actions, loading }: Props) {
  return (
    <div className="bg-white rounded-xl border border-slate-200 p-6">
      <div className="flex items-center gap-2 mb-4">
        <Calendar size={20} className="text-primary" />
        <h2 className="text-lg font-semibold text-slate-900">Action Schedule</h2>
      </div>

      {loading && actions.length === 0 && (
        <div className="space-y-3 animate-pulse">
          {[...Array(3)].map((_, i) => (
            <div key={i} className="h-16 bg-slate-100 rounded" />
          ))}
        </div>
      )}

      {!loading && actions.length === 0 && (
        <p className="text-slate-500 text-sm">No scheduled actions.</p>
      )}

      <div className="space-y-3">
        {actions.map((action, i) => {
          const Icon = statusIcons[action.status] ?? Clock
          const color = statusColors[action.status] ?? 'text-slate-400'
          return (
            <div key={i} className="relative pl-6 border-l-2 border-slate-200 pb-3 last:pb-0">
              <div className={`absolute -left-[9px] top-0 bg-white ${color}`}>
                <Icon size={16} className={action.status === 'in_progress' ? 'animate-spin' : ''} />
              </div>
              <div className="text-sm font-medium text-slate-900">{action.action_type}</div>
              <p className="text-xs text-slate-600 mt-0.5">{action.description}</p>
              <div className="flex items-center gap-3 mt-1 text-xs text-slate-400">
                <span>Priority: {action.priority_score.toFixed(2)}</span>
                <span className="capitalize">{action.status.replace('_', ' ')}</span>
                {action.scheduled_at && <span>{new Date(action.scheduled_at).toLocaleDateString()}</span>}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
