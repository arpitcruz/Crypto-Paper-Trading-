import { useState } from 'react'
import { useQuery } from 'react-query'
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, ReferenceLine,
} from 'recharts'
import { getAllTickers, getKlines } from '../api/client'

const INTERVALS = [
  { label: '1H', value: '1h', limit: 60 },
  { label: '4H', value: '4h', limit: 90 },
  { label: '1D', value: '1d', limit: 60 },
  { label: '1W', value: '1w', limit: 52 },
]

const COINS = [
  'BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'BNBUSDT', 'XRPUSDT',
  'ADAUSDT', 'DOGEUSDT', 'AVAXUSDT', 'LINKUSDT', 'DOTUSDT',
  'MATICUSDT', 'LTCUSDT', 'UNIUSDT', 'ATOMUSDT',
]

function fmt(price: number) {
  if (price >= 1000) return price.toLocaleString('en-US', { maximumFractionDigits: 2 })
  if (price >= 1) return price.toFixed(4)
  return price.toFixed(6)
}

function fmtTime(ts: number, interval: string) {
  const d = new Date(ts)
  if (interval === '1d' || interval === '1w') return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
  return d.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', hour12: false })
}

// Custom tooltip
function ChartTooltip({ active, payload, interval }: any) {
  if (!active || !payload?.length) return null
  const d = payload[0]?.payload
  return (
    <div className="bg-gray-900 border border-gray-700 rounded-lg p-3 text-xs shadow-xl">
      <p className="text-gray-400 mb-1">{fmtTime(d?.time, interval)}</p>
      <p className="text-white font-mono">O: <span className="text-blue-300">${fmt(d?.open ?? 0)}</span></p>
      <p className="text-white font-mono">H: <span className="text-green-400">${fmt(d?.high ?? 0)}</span></p>
      <p className="text-white font-mono">L: <span className="text-red-400">${fmt(d?.low ?? 0)}</span></p>
      <p className="text-white font-mono">C: <span className="text-yellow-300">${fmt(d?.close ?? 0)}</span></p>
    </div>
  )
}

export default function MarketsPage() {
  const [selected, setSelected] = useState('BTCUSDT')
  const [interval, setInterval] = useState(INTERVALS[0])

  const { data: tickersData } = useQuery('market-tickers', () => getAllTickers().then(r => r.data), {
    refetchInterval: 15000,
  })

  const { data: klinesData, isLoading: chartLoading } = useQuery(
    ['klines', selected, interval.value],
    () => getKlines(selected, interval.value, interval.limit).then(r => r.data),
    { refetchInterval: 30000, keepPreviousData: true }
  )

  const tickers: Record<string, any> = {}
  tickersData?.tickers?.forEach((t: any) => { tickers[t.symbol] = t })

  const current = tickers[selected]
  const isUp = (current?.change_percent_24h ?? 0) >= 0
  const chartColor = isUp ? '#22c55e' : '#ef4444'
  const chartGradientId = isUp ? 'greenGrad' : 'redGrad'

  const chartData = klinesData?.data ?? []
  const openPrice = chartData[0]?.open ?? 0
  const minClose = chartData.length ? Math.min(...chartData.map((c: any) => c.low)) : 0
  const maxClose = chartData.length ? Math.max(...chartData.map((c: any) => c.high)) : 0

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-white">Markets</h1>

      <div className="grid grid-cols-1 xl:grid-cols-4 gap-6">
        {/* Coin list */}
        <div className="card xl:col-span-1 p-0 overflow-hidden">
          <div className="p-4 border-b border-gray-800">
            <p className="text-sm font-semibold text-gray-400 uppercase tracking-wide">All Assets</p>
          </div>
          <div className="overflow-y-auto max-h-[600px]">
            {COINS.map((sym) => {
              const t = tickers[sym]
              const pct = t?.change_percent_24h ?? 0
              const pos = pct >= 0
              return (
                <button
                  key={sym}
                  onClick={() => setSelected(sym)}
                  className={`w-full flex items-center justify-between px-4 py-3 text-left transition-colors border-b border-gray-800/50 last:border-0 ${
                    selected === sym ? 'bg-blue-600/15 border-l-2 border-l-blue-500' : 'hover:bg-gray-800/50'
                  }`}
                >
                  <div>
                    <p className="text-sm font-semibold text-white">{sym.replace('USDT', '')}</p>
                    <p className="text-xs text-gray-500">/{sym.includes('USDT') ? 'USDT' : ''}</p>
                  </div>
                  <div className="text-right">
                    <p className="text-sm font-mono text-white">${t ? fmt(t.price) : '—'}</p>
                    <p className={`text-xs font-medium ${pos ? 'text-green-400' : 'text-red-400'}`}>
                      {t ? `${pos ? '+' : ''}${pct.toFixed(2)}%` : '—'}
                    </p>
                  </div>
                </button>
              )
            })}
          </div>
        </div>

        {/* Chart panel */}
        <div className="xl:col-span-3 space-y-4">
          {/* Price header */}
          <div className="card">
            <div className="flex items-start justify-between flex-wrap gap-4">
              <div>
                <h2 className="text-xl font-bold text-white">
                  {selected.replace('USDT', '')}<span className="text-gray-500 font-normal text-base">/USDT</span>
                </h2>
                <div className="flex items-baseline gap-3 mt-1">
                  <span className="text-3xl font-bold font-mono text-white">
                    ${current ? fmt(current.price) : '—'}
                  </span>
                  {current && (
                    <span className={`text-lg font-semibold ${isUp ? 'text-green-400' : 'text-red-400'}`}>
                      {isUp ? '▲' : '▼'} {isUp ? '+' : ''}{current.change_percent_24h.toFixed(2)}%
                    </span>
                  )}
                </div>
              </div>

              {current && (
                <div className="flex gap-6 text-sm">
                  <div>
                    <p className="text-gray-500 text-xs">24h High</p>
                    <p className="font-mono text-green-400 font-semibold">${fmt(current.high_24h)}</p>
                  </div>
                  <div>
                    <p className="text-gray-500 text-xs">24h Low</p>
                    <p className="font-mono text-red-400 font-semibold">${fmt(current.low_24h)}</p>
                  </div>
                  <div>
                    <p className="text-gray-500 text-xs">24h Volume</p>
                    <p className="font-mono text-gray-300 font-semibold">
                      {current.volume_24h?.toLocaleString('en-US', { maximumFractionDigits: 0 })}
                    </p>
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Interval selector + chart */}
          <div className="card">
            <div className="flex items-center gap-2 mb-4">
              {INTERVALS.map((iv) => (
                <button
                  key={iv.value}
                  onClick={() => setInterval(iv)}
                  className={`px-3 py-1.5 rounded text-sm font-medium transition-colors ${
                    interval.value === iv.value
                      ? 'bg-blue-600 text-white'
                      : 'text-gray-400 hover:text-white hover:bg-gray-700'
                  }`}
                >
                  {iv.label}
                </button>
              ))}
              <span className="ml-auto text-xs text-gray-600">
                {chartLoading ? 'Loading...' : `${chartData.length} candles`}
              </span>
            </div>

            <ResponsiveContainer width="100%" height={340}>
              <AreaChart data={chartData} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
                <defs>
                  <linearGradient id="greenGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#22c55e" stopOpacity={0.25} />
                    <stop offset="95%" stopColor="#22c55e" stopOpacity={0.02} />
                  </linearGradient>
                  <linearGradient id="redGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#ef4444" stopOpacity={0.25} />
                    <stop offset="95%" stopColor="#ef4444" stopOpacity={0.02} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" vertical={false} />
                <XAxis
                  dataKey="time"
                  tickFormatter={(v) => fmtTime(v, interval.value)}
                  stroke="#374151"
                  tick={{ fill: '#6b7280', fontSize: 11 }}
                  tickLine={false}
                  interval="preserveStartEnd"
                />
                <YAxis
                  dataKey="close"
                  domain={[minClose * 0.998, maxClose * 1.002]}
                  tickFormatter={(v) => `$${fmt(v)}`}
                  stroke="#374151"
                  tick={{ fill: '#6b7280', fontSize: 11 }}
                  tickLine={false}
                  axisLine={false}
                  width={90}
                  orientation="right"
                />
                <Tooltip content={<ChartTooltip interval={interval.value} />} />
                {openPrice > 0 && (
                  <ReferenceLine
                    y={openPrice}
                    stroke="#6b7280"
                    strokeDasharray="4 4"
                    strokeWidth={1}
                  />
                )}
                <Area
                  type="monotone"
                  dataKey="close"
                  stroke={chartColor}
                  strokeWidth={2}
                  fill={`url(#${chartGradientId})`}
                  dot={false}
                  activeDot={{ r: 4, fill: chartColor, strokeWidth: 0 }}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>

          {/* Mini stats row */}
          {current && (
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              {[
                { label: 'Open (24h)', value: `$${fmt(current.price - current.change_24h)}`, color: 'text-white' },
                { label: 'Change (24h)', value: `$${fmt(Math.abs(current.change_24h))}`, color: isUp ? 'text-green-400' : 'text-red-400' },
                { label: 'High (24h)', value: `$${fmt(current.high_24h)}`, color: 'text-green-400' },
                { label: 'Low (24h)', value: `$${fmt(current.low_24h)}`, color: 'text-red-400' },
              ].map((s) => (
                <div key={s.label} className="card py-3">
                  <p className="text-xs text-gray-500">{s.label}</p>
                  <p className={`text-sm font-mono font-semibold mt-0.5 ${s.color}`}>{s.value}</p>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
