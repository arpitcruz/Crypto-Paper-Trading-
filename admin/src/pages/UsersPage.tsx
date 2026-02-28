import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from 'react-query'
import { getUsers, updateUser } from '../api/client'

interface User {
  id: string
  email: string
  username: string
  full_name: string | null
  role: string
  is_active: boolean
  is_blocked: boolean
  created_at: string
  last_login: string | null
}

export default function UsersPage() {
  const qc = useQueryClient()
  const [search, setSearch] = useState('')
  const [selectedUser, setSelectedUser] = useState<User | null>(null)
  const [walletAdj, setWalletAdj] = useState('')
  const [walletType, setWalletType] = useState('spot')

  const { data, isLoading } = useQuery(
    ['users', search],
    () => getUsers({ search: search || undefined }).then((r) => r.data),
    { keepPreviousData: true }
  )

  const mutation = useMutation(
    ({ id, payload }: { id: string; payload: object }) => updateUser(id, payload),
    {
      onSuccess: () => {
        qc.invalidateQueries('users')
        setSelectedUser(null)
      },
    }
  )

  const handleToggleBlock = (user: User) => {
    mutation.mutate({ id: user.id, payload: { is_blocked: !user.is_blocked } })
  }

  const handleWalletAdjust = (user: User) => {
    if (!walletAdj) return
    mutation.mutate({
      id: user.id,
      payload: { wallet_adjustment: parseFloat(walletAdj), wallet_type: walletType },
    })
    setWalletAdj('')
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-white">Users</h1>
        <div className="flex items-center gap-3">
          <input
            type="search"
            placeholder="Search email or username..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="input w-64"
          />
        </div>
      </div>

      <div className="card overflow-hidden p-0">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-800 bg-gray-900/50">
              {['User', 'Role', 'Status', 'Last Login', 'Joined', 'Actions'].map((h) => (
                <th key={h} className="text-left text-gray-400 font-medium px-6 py-4">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {isLoading && (
              <tr><td colSpan={6} className="text-center py-8 text-gray-500">Loading...</td></tr>
            )}
            {data?.map((user: User) => (
              <tr key={user.id} className="border-b border-gray-800 hover:bg-gray-800/30">
                <td className="px-6 py-4">
                  <div className="font-medium text-white">{user.username}</div>
                  <div className="text-gray-400 text-xs">{user.email}</div>
                </td>
                <td className="px-6 py-4">
                  <span className={user.role === 'admin' ? 'badge-yellow' : 'badge-green'}>
                    {user.role}
                  </span>
                </td>
                <td className="px-6 py-4">
                  {user.is_blocked
                    ? <span className="badge-red">Blocked</span>
                    : user.is_active
                    ? <span className="badge-green">Active</span>
                    : <span className="badge-yellow">Inactive</span>}
                </td>
                <td className="px-6 py-4 text-gray-400 text-xs">
                  {user.last_login ? new Date(user.last_login).toLocaleString() : '—'}
                </td>
                <td className="px-6 py-4 text-gray-400 text-xs">
                  {new Date(user.created_at).toLocaleDateString()}
                </td>
                <td className="px-6 py-4">
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => handleToggleBlock(user)}
                      className={user.is_blocked ? 'btn-primary text-xs py-1 px-2' : 'btn-danger text-xs py-1 px-2'}
                    >
                      {user.is_blocked ? 'Unblock' : 'Block'}
                    </button>
                    <button
                      onClick={() => setSelectedUser(user)}
                      className="btn-ghost text-xs py-1 px-2"
                    >
                      Wallet
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Wallet Adjustment Modal */}
      {selectedUser && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50">
          <div className="card w-96">
            <h2 className="text-lg font-bold text-white mb-4">
              Adjust Wallet — {selectedUser.username}
            </h2>
            <div className="space-y-3">
              <div>
                <label className="block text-sm text-gray-400 mb-1">Wallet Type</label>
                <select
                  value={walletType}
                  onChange={(e) => setWalletType(e.target.value)}
                  className="input"
                >
                  <option value="spot">Spot</option>
                  <option value="futures">Futures</option>
                </select>
              </div>
              <div>
                <label className="block text-sm text-gray-400 mb-1">
                  Amount (+ to add, - to remove)
                </label>
                <input
                  type="number"
                  value={walletAdj}
                  onChange={(e) => setWalletAdj(e.target.value)}
                  className="input"
                  placeholder="e.g. 1000 or -500"
                />
              </div>
              <div className="flex gap-2 pt-2">
                <button
                  onClick={() => handleWalletAdjust(selectedUser)}
                  className="btn-primary flex-1"
                >
                  Apply
                </button>
                <button onClick={() => setSelectedUser(null)} className="btn-ghost flex-1">
                  Cancel
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
