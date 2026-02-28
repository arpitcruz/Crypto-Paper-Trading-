import { useQuery } from 'react-query'
import { getAllPositions } from '../api/client'

interface Position {
  id: string
  user_id: string
  symbol: string
  side: string
  status: string
  quantity: number
  entry_price: number
  current_price: number
  leverage: number
  unrealized_pnl: number
  liquidation_price: number
  opened_at: string
}

export default function PositionsPage() {
  const { data, isLoading, refetch } = useQuery(
    'all-positions',
    () => getAllPositions({ status: 'open' }).then((r) => r.data),
    { refetchInterval: 10000 }
  )

  const positions: Position[] = data ?? []

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-white">Open Positions</h1>
        <button onClick={() => refetch()} className="btn-ghost text-sm">
          🔄 Refresh
        </button>
      </div>

      <div className="card overflow-hidden p-0">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-800 bg-gray-900/50">
              {['Symbol', 'Side', 'Qty', 'Entry', 'Current', 'Leverage', 'PnL', 'Liq. Price', 'Opened'].map((h) => (
                <th key={h} className="text-left text-gray-400 font-medium px-4 py-4">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {isLoading && (
              <tr><td colSpan={9} className="text-center py-8 text-gray-500">Loading...</td></tr>
            )}
            {positions.length === 0 && !isLoading && (
              <tr><td colSpan={9} className="text-center py-8 text-gray-500">No open positions</td></tr>
            )}
            {positions.map((pos) => (
              <tr key={pos.id} className="border-b border-gray-800 hover:bg-gray-800/30">
                <td className="px-4 py-3 font-medium text-white">{pos.symbol}</td>
                <td className="px-4 py-3">
                  <span className={pos.side === 'long' ? 'badge-green' : 'badge-red'}>
                    {pos.side.toUpperCase()}
                  </span>
                </td>
                <td className="px-4 py-3 text-gray-300 font-mono">{pos.quantity}</td>
                <td className="px-4 py-3 text-gray-300 font-mono">${pos.entry_price?.toLocaleString()}</td>
                <td className="px-4 py-3 text-gray-300 font-mono">
                  ${pos.current_price?.toLocaleString() ?? '—'}
                </td>
                <td className="px-4 py-3">
                  <span className="badge-yellow">{pos.leverage}x</span>
                </td>
                <td className={`px-4 py-3 font-mono font-medium ${pos.unrealized_pnl >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                  {pos.unrealized_pnl >= 0 ? '+' : ''}${pos.unrealized_pnl?.toFixed(2)}
                </td>
                <td className="px-4 py-3 text-red-400 font-mono">
                  ${pos.liquidation_price?.toLocaleString() ?? '—'}
                </td>
                <td className="px-4 py-3 text-gray-400 text-xs">
                  {new Date(pos.opened_at).toLocaleString()}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
