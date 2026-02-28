import { useQuery } from 'react-query'
import { getAdminLogs } from '../api/client'

interface Log {
  id: string
  admin_id: string
  action: string
  target_user_id: string | null
  details: string | null
  created_at: string
}

export default function LogsPage() {
  const { data, isLoading, refetch } = useQuery(
    'admin-logs',
    () => getAdminLogs().then((r) => r.data)
  )

  const logs: Log[] = data ?? []

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-white">Admin Logs</h1>
        <button onClick={() => refetch()} className="btn-ghost text-sm">
          🔄 Refresh
        </button>
      </div>

      <div className="card overflow-hidden p-0">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-800 bg-gray-900/50">
              {['Time', 'Action', 'Target User', 'Details'].map((h) => (
                <th key={h} className="text-left text-gray-400 font-medium px-6 py-4">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {isLoading && (
              <tr><td colSpan={4} className="text-center py-8 text-gray-500">Loading...</td></tr>
            )}
            {logs.length === 0 && !isLoading && (
              <tr><td colSpan={4} className="text-center py-8 text-gray-500">No logs yet</td></tr>
            )}
            {logs.map((log) => (
              <tr key={log.id} className="border-b border-gray-800 hover:bg-gray-800/30">
                <td className="px-6 py-3 text-gray-400 text-xs whitespace-nowrap">
                  {new Date(log.created_at).toLocaleString()}
                </td>
                <td className="px-6 py-3">
                  <span className="badge-yellow">{log.action}</span>
                </td>
                <td className="px-6 py-3 text-gray-300 font-mono text-xs">
                  {log.target_user_id ? log.target_user_id.slice(0, 8) + '...' : '—'}
                </td>
                <td className="px-6 py-3 text-gray-400 text-xs">{log.details || '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
