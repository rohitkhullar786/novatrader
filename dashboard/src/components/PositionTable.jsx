import { useState, useEffect } from "react"

export default function PositionTable({ positions, version = "V2" }) {
  const [loading, setLoading] = useState(true)

  // Filter out USDD and Free coins from the passed positions prop
  const filteredPositions = positions ? positions.filter(p => p.coin !== 'USDD' && p.coin !== 'Free') : [];
  const hasOpenPositions = filteredPositions.length > 0;

  useEffect(() => {
    // Set loading to false once we have positions prop (it's already loaded by parent)
    if (positions) {
      setLoading(false);
    }
  }, [positions]);

  const formatQty = (q) => {
    if (q == null || q === undefined) return '—'
    const num = parseFloat(q)
    if (isNaN(num)) return '—'
    if (num > 1) return num.toFixed(4)
    return num.toFixed(8)
  }

  const formatUSD = (q) => {
    if (q == null || q === undefined) return '—'
    const num = parseFloat(q)
    if (isNaN(num)) return '—'
    return num.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
  }

  // Calculate P&L for positions
  const totalPnl = filteredPositions.reduce((sum, p) => sum + (p.unrealized_pnl || 0), 0)

  return (
    <div className="bg-white border border-gray-200 rounded-2xl p-4 shadow-sm">
      {/* Header - hidden on mobile, visible on desktop */}
      <div className="flex justify-between mb-4 text-sm">
        <div className="flex items-center gap-2">
          {/* NovaTrader logo circle */}
          <div className="w-6 h-6 rounded-full bg-gradient-to-br from-gray-700 to-gray-900 flex items-center justify-center text-white text-xs font-bold">
            {version === 'V1' ? 'NT' : version === 'NOVA' ? 'NV' : 'NR'}
          </div>
          <div className="font-semibold">{version === 'V1' ? 'Nova Trend' : version === 'NOVA' ? 'Nova' : 'Nova Range'}</div>
        </div>
        <div className={totalPnl >= 0 ? 'text-green-600' : 'text-red-600'}>
          Total unrealized P&L: {totalPnl >= 0 ? '+' : ''}${totalPnl.toFixed(2)}
        </div>
      </div>

      {loading ? (
        <div className="text-center text-gray-400 py-4">Loading...</div>
      ) : !hasOpenPositions ? (
        <div className="border border-gray-100 rounded-xl p-6 text-center">
          <div className="text-gray-400 text-3xl mb-2">📄</div>
          <div className="text-gray-500 text-sm">No open positions</div>
        </div>
      ) : (
        <>
          {/* Desktop Table Layout - hidden on mobile */}
          <div className="hidden md:block border border-gray-100 rounded-xl p-3 text-sm">
            <div className="grid grid-cols-6 gap-4 text-gray-400 mb-3 text-xs" style={{gridTemplateColumns: '1fr 1.2fr 1fr 1fr 1fr 1fr'}}>
              <div>Coin</div>
              <div className="text-right">Entry</div>
              <div className="text-right">Size</div>
              <div className="text-right">Unreal P&L</div>
              <div className="text-right">Stop Loss</div>
              <div className="text-right">Trail Stop</div>
            </div>

            {filteredPositions.map((pos, i) => {
              const pnl = pos.unrealized_pnl || 0
              const isProfit = pnl >= 0
              const size = pos.position_size || (pos.quantity || 0) * (pos.entry_price || 0)
              const pnlPercent = size > 0 ? (pnl / size) * 100 : 0
              const slPrice = pos.stop_loss_price ? `$${formatUSD(pos.stop_loss_price)}` : '-'
              const tsPrice = pos.trailing_stop_active && pos.trailing_stop_price ? `$${formatUSD(pos.trailing_stop_price)}` : (pos.trailing_stop_active ? 'Active' : '-')
              return (
                <div key={i} className="grid gap-4 items-center py-2 border-t border-gray-50" style={{gridTemplateColumns: '1fr 1.2fr 1fr 1fr 1fr 1fr'}}>
                  <div className="font-medium truncate">{pos.coin || pos.symbol}</div>
                  <div className="text-gray-600 text-right">${formatUSD(pos.entry_price)}</div>
                  <div className="text-gray-600 text-right">${formatUSD(size)}</div>
                  <div className={`text-right font-medium ${isProfit ? 'text-green-600' : 'text-red-600'}`}>
                    {pnlPercent >= 0 ? '+' : ''}{pnlPercent.toFixed(2)}%
                  </div>
                  <div className="text-right text-red-500 text-xs">{slPrice}</div>
                  <div className="text-right text-blue-500 text-xs">{tsPrice}</div>
                </div>
              )
            })}
          </div>

          {/* Mobile Card Layout - hidden on desktop */}
          <div className="md:hidden space-y-3">
            {filteredPositions.map((pos, i) => {
              const pnl = pos.unrealized_pnl || 0
              const isProfit = pnl >= 0
              const size = pos.position_size || (pos.quantity || 0) * (pos.entry_price || 0)
              const pnlPercent = size > 0 ? (pnl / size) * 100 : 0
              const slPrice = pos.stop_loss_price ? `$${formatUSD(pos.stop_loss_price)}` : '-'
              const tsPrice = pos.trailing_stop_active && pos.trailing_stop_price ? `$${formatUSD(pos.trailing_stop_price)}` : (pos.trailing_stop_active ? 'Active' : '-')
              return (
                <div key={i} className="border border-gray-100 rounded-xl p-3">
                  {/* Coin and P&L row */}
                  <div className="flex justify-between items-center mb-3">
                    <div className="font-semibold text-base">{pos.coin || pos.symbol}</div>
                    <div className={`text-right font-semibold ${isProfit ? 'text-green-600' : 'text-red-600'}`}>
                      {pnlPercent >= 0 ? '+' : ''}{pnlPercent.toFixed(2)}%
                    </div>
                  </div>
                  {/* Details grid */}
                  <div className="grid grid-cols-2 gap-2 text-xs">
                    <div className="flex justify-between">
                      <span className="text-gray-400">Entry:</span>
                      <span className="text-gray-600">${formatUSD(pos.entry_price)}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-400">Size:</span>
                      <span className="text-gray-600">${formatUSD(size)}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-400">Stop Loss:</span>
                      <span className="text-red-500">{slPrice}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-400">Trail Stop:</span>
                      <span className="text-blue-500">{tsPrice}</span>
                    </div>
                  </div>
                </div>
              )
            })}
          </div>
        </>
      )}
    </div>
  )
}