import { TrendingUp, TrendingDown, Activity, Award } from 'lucide-react'
import type { GrowthState } from '../../types'

interface Props {
  state: GrowthState | null
  loading: boolean
}

function TrendIcon({ trend }: { trend: string }) {
  switch (trend) {
    case 'accelerating':
      return <TrendingUp className="text-green-500" size={24} />
    case 'decelerating':
      return <TrendingDown className="text-yellow-500" size={24} />
    case 'plateauing':
      return <Activity className="text-blue-500" size={24} />
    case 'declining':
      return <TrendingDown className="text-red-500" size={24} />
    default:
      return <Activity className="text-slate-400" size={24} />
  }
}

function TrendBadge({ trend }: { trend: string }) {
  const colors: Record<string, string> = {
    accelerating: 'bg-green-100 text-green-700',
    decelerating: 'bg-yellow-100 text-yellow-700',
    plateauing: 'bg-blue-100 text-blue-700',
    declining: 'bg-red-100 text-red-700',
  }
  return (
    <span className={`px-2 py-1 rounded-full text-xs font-medium capitalize ${colors[trend] ?? 'bg-slate-100 text-slate-600'}`}>
      {trend}
    </span>
  )
}

export default function GrowthOverview({ state, loading }: Props) {
  if (loading && !state) {
    return (
      <div className="bg-white rounded-xl border border-slate-200 p-6 animate-pulse">
        <div className="h-6 bg-slate-200 rounded w-1/3 mb-4" />
        <div className="grid grid-cols-2 gap-4">
          {[...Array(4)].map((_, i) => <div key={i} className="h-16 bg-slate-100 rounded" />)}
        </div>
      </div>
    )
  }

  if (!state) {
    return (
      <div className="bg-white rounded-xl border border-slate-200 p-8 text-center text-slate-500">
        <Award size={40} className="mx-auto mb-3 text-slate-300" />
        <p>Enter a Website ID and click <strong>Analyze</strong> to view growth data.</p>
      </div>
    )
  }

  return (
    <div className="bg-white rounded-xl border border-slate-200 p-6">
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-lg font-semibold text-slate-900">Growth Overview</h2>
        <TrendBadge trend={state.trend} />
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-slate-50 rounded-lg p-4">
          <div className="flex items-center gap-2 text-slate-500 text-sm mb-1">
            <TrendingUp size={16} />
            Growth Score
          </div>
          <p className="text-2xl font-bold text-slate-900">{state.growth_score.toFixed(1)}</p>
        </div>

        <div className="bg-slate-50 rounded-lg p-4">
          <div className="flex items-center gap-2 text-slate-500 text-sm mb-1">
            <Activity size={16} />
            Avg Reward
          </div>
          <p className="text-2xl font-bold text-slate-900">{state.avg_reward.toFixed(3)}</p>
        </div>

        <div className="bg-slate-50 rounded-lg p-4">
          <div className="flex items-center gap-2 text-slate-500 text-sm mb-1">
            <TrendingUp size={16} />
            Trajectories
          </div>
          <p className="text-2xl font-bold text-slate-900">{state.trajectory_count}</p>
        </div>

        <div className="bg-slate-50 rounded-lg p-4">
          <div className="flex items-center gap-2 text-slate-500 text-sm mb-1">
            <TrendIcon trend={state.trend} />
            Trend
          </div>
          <p className="text-2xl font-bold text-slate-900 capitalize">{state.trend}</p>
        </div>
      </div>
    </div>
  )
}
