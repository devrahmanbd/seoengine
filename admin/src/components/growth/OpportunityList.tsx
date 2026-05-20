import { Lightbulb, Zap, Clock, AlertTriangle } from 'lucide-react'
import type { Opportunity } from '../../types'

interface Props {
  opportunities: Opportunity[]
  loading: boolean
}

const confidenceColors: Record<string, string> = {
  high: 'text-green-600 bg-green-50 border-green-200',
  medium: 'text-yellow-600 bg-yellow-50 border-yellow-200',
  low: 'text-slate-600 bg-slate-50 border-slate-200',
}

const effortIcons: Record<string, typeof Clock> = {
  low: Zap,
  medium: Clock,
  high: AlertTriangle,
}

export default function OpportunityList({ opportunities, loading }: Props) {
  return (
    <div className="bg-white rounded-xl border border-slate-200 p-6">
      <div className="flex items-center gap-2 mb-4">
        <Lightbulb size={20} className="text-yellow-500" />
        <h2 className="text-lg font-semibold text-slate-900">Opportunities</h2>
      </div>

      {loading && opportunities.length === 0 && (
        <div className="space-y-3 animate-pulse">
          {[...Array(3)].map((_, i) => (
            <div key={i} className="h-20 bg-slate-100 rounded" />
          ))}
        </div>
      )}

      {!loading && opportunities.length === 0 && (
        <p className="text-slate-500 text-sm">No opportunities found. Analyze a website to discover growth opportunities.</p>
      )}

      <div className="space-y-3">
        {opportunities.map((opp, i) => {
          const EffortIcon = effortIcons[opp.effort] ?? Clock
          return (
            <div key={i} className="border border-slate-200 rounded-lg p-3 space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium text-slate-900">{opp.action_type}</span>
                <span className={`px-2 py-0.5 rounded text-xs font-medium border ${confidenceColors[opp.confidence] ?? confidenceColors.low}`}>
                  {opp.confidence}
                </span>
              </div>
              <p className="text-xs text-slate-600">{opp.description}</p>
              <div className="flex items-center gap-3 text-xs text-slate-500">
                <span className="flex items-center gap-1">
                  <EffortIcon size={14} />
                  {opp.effort} effort
                </span>
                <span>Reward: {opp.expected_reward.toFixed(2)}</span>
                <span className="capitalize">{opp.source.replace('_', ' ')}</span>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
