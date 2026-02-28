import { useQuery } from 'react-query'
import { getSystemStats, getAllTickers } from '../api/client'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'

function StatCard({ label, value, icon, color = 'blue' }: {
  label: string; value: string | number; icon: string; color?: string
}) {
  const colorMap: Record<string, string> = {
    blue: 'text-blue-400',
    green: 'text-green-400',
    red: 'text-red-400',
    yellow: 'text-yellow-400',
  }
  return (
    <div className="card">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-gray-400 text-sm">{label}</p>
          <p className={`text-2xl font-bold mt-1 ${colorMap[color]}`}>{value}</p>
        </div>
        <span className="text-3xl">{icon}</span>
      </div>
    </div>
  )
}

export default function DashboardPage() {
  const { data: stats } = useQuery('system-stats', () => getSystemStats().then(r => r.data))
  const { data: tickers } = useQuery('tickers', () => getAllTickers().then(r => r.data), {
    refetchInterval: 10000,
  })

  const topPairs = tickers?.tickers?.slice(0, 8).map((t: any) => ({
    name: t.symbol.replace('USDT', ''),
    change: parseFloat(t.change_percent_24h?.toFixed(2) ?? 0),
    price: t.price,
  })) ?? []

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-white">Dashboard</h1>

      {/* Stats grid */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard label="Total Users" value={stats?.total_users ?? '—'} icon="👥" color="blue" />
        <StatCard label="Active Users" value={stats?.active_users ?? '—'} icon="✅" color="green" />
        <StatCard label="Blocked Users" value={stats?.blocked_users ?? '—'} icon="🚫" color="red" />
        <StatCard label="Open Positions" value={stats?.open_positions ?? '—'} icon="📈" color="yellow" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* 24h change chart */}
        <div className="card">
          <h2 className="text-lg font-semibold text-white mb-4">24h Price Change (%)</h2>
          <ResponsiveContainer width="100%" height={250}>
            <BarChart data={topPairs}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
              <XAxis dataKey="name" stroke="#6b7280" tick={{ fill: '#9ca3af', fontSize: 12 }} />
              <YAxis stroke="#6b7280" tick={{ fill: '#9ca3af', fontSize: 12 }} />
              <Tooltip
                contentStyle={{ backgroundColor: '#111827', border: '1px solid #374151' }}
                labelStyle={{ color: '#f9fafb' }}
              />
              <Bar
                dataKey="change"
                fill="#3b82f6"
                radius={[4, 4, 0, 0]}
                label={false}
              />
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Live prices */}
        <div className="card">
          <h2 className="text-lg font-semibold text-white mb-4">Live Prices</h2>
          <div className="space-y-2 max-h-60 overflow-auto">
            {topPairs.map((t: any) => (
              <div key={t.name} className="flex items-center justify-between py-2 border-b border-gray-800 last:border-0">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium text-white">{t.name}/USDT</span>
                </div>
                <div className="text-right">
                  <div className="text-sm font-mono text-white">${t.price?.toLocaleString()}</div>
                  <div className={`text-xs ${t.change >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                    {t.change >= 0 ? '+' : ''}{t.change}%
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
