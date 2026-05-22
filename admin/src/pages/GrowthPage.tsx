import { Button } from '../components/Button'
import { Card } from '../components/Card'
import { Input } from '../components/Input'
import { useState } from 'react'
import { TrendingUp, Search } from 'lucide-react'
import { growthApi } from '../lib/api'
import type { GrowthState, Opportunity, ScheduledAction } from '../types'
import GrowthOverview from '../components/growth/GrowthOverview'
import TrajectoryChart from '../components/growth/TrajectoryChart'
import OpportunityList from '../components/growth/OpportunityList'
import ActionTimeline from '../components/growth/ActionTimeline'

export default function GrowthPage() {
  const [websiteId, setWebsiteId] = useState('')
  const [state, setState] = useState<GrowthState | null>(null)
  const [opportunities, setOpportunities] = useState<Opportunity[]>([])
  const [schedule, setSchedule] = useState<ScheduledAction[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  function loadGrowth() {
    if (!websiteId.trim()) return
    setLoading(true)
    setError('')
    Promise.all([
      growthApi.getState(websiteId.trim()),
      growthApi.opportunities(websiteId.trim(), { count: 5 }),
      growthApi.schedule(websiteId.trim(), { max_actions: 5 }),
    ])
      .then(([stateRes, oppRes, schedRes]) => {
        setState(stateRes.data)
        setOpportunities(oppRes.data.opportunities ?? [])
        setSchedule(schedRes.data.actions ?? [])
      })
      .catch((err) => {
        setError(err.response?.data?.detail ?? err.message)
      })
      .finally(() => setLoading(false))
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-textPrimary">Growth Dashboard</h1>
        <div className="flex items-center gap-2">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-textSecondary" size={18} />
            <input
              type="text"
              placeholder="Website ID..."
              value={websiteId}
              onChange={(e) => setWebsiteId(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && loadGrowth()}
              className="pl-10 pr-4 py-2 bg-white border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary/50 w-72"
            />
          </div>
          <Button variant="ghost"
            onClick={loadGrowth}
            disabled={loading}
            className="flex items-center gap-2 px-4 py-2 bg-primary text-white rounded-lg text-sm font-medium hover:bg-primary/90 disabled:opacity-50"
          >
            <TrendingUp size={18} />
            {loading ? 'Loading...' : 'Analyze'}
          </Button>
        </div>
      </div>

      {error && (
        <div className="p-4 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">{error}</div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-6">
          <GrowthOverview state={state} loading={loading} />
          <TrajectoryChart state={state} loading={loading} />
        </div>
        <div className="space-y-6">
          <OpportunityList opportunities={opportunities} loading={loading} />
          <ActionTimeline actions={schedule} loading={loading} />
        </div>
      </div>
    </div>
  )
}
