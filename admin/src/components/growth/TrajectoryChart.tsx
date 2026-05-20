import type { GrowthState } from '../../types'

interface Props {
  state: GrowthState | null
  loading: boolean
}

function MiniBar({ height, label }: { height: number; label: string }) {
  return (
    <div className="flex flex-col items-center gap-1 flex-1">
      <div className="w-full flex justify-center" style={{ height: 120 }}>
        <div
          className="w-6 bg-primary/70 rounded-t transition-all duration-300 self-end"
          style={{ height: `${Math.max(height * 100, 4)}%` }}
        />
      </div>
      <span className="text-[10px] text-slate-500 truncate w-full text-center">{label}</span>
    </div>
  )
}

export default function TrajectoryChart({ state, loading }: Props) {
  if (loading && !state) {
    return (
      <div className="bg-white rounded-xl border border-slate-200 p-6 animate-pulse">
        <div className="h-6 bg-slate-200 rounded w-1/4 mb-4" />
        <div className="h-32 bg-slate-100 rounded" />
      </div>
    )
  }

  if (!state) return null

  const history = state.score_history ?? []
  const maxVal = Math.max(...history, 1)

  return (
    <div className="bg-white rounded-xl border border-slate-200 p-6">
      <h2 className="text-lg font-semibold text-slate-900 mb-4">Score Trajectory</h2>
      {history.length === 0 ? (
        <p className="text-slate-500 text-sm">No trajectory data available yet.</p>
      ) : (
        <div className="flex items-end gap-1 h-36">
          {history.map((score, i) => (
            <MiniBar key={i} height={score / maxVal} label={`#${i + 1}`} />
          ))}
        </div>
      )}
    </div>
  )
}
