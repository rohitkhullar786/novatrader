import { useState } from 'react'

export default function TradeCard({ trade }) {
  if (!trade) return null

  const [showReasoning, setShowReasoning] = useState(false)

  const formatDate = (dateStr) => {
    if (!dateStr) return ''
    return dateStr
  }

  const formatPrice = (p) => {
    if (p == null) return '—'
    return parseFloat(p).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
  }

  const formatQty = (q) => {
    if (q == null) return '—'
    return parseFloat(q).toFixed(4)
  }

  const pnl = trade.pnl || 0
  const netPnl = trade.net_pnl || trade.pnl || 0
  const isProfit = netPnl >= 0
  const hasPnl = netPnl !== 0
  const reasoning = trade.reasoning || trade.ai_reasoning || null

  // Calculate holding time if we have entry and exit timestamps
  const holdingTime = trade.holding_time || null
  const entryPrice = trade.entry_price || trade.price
  const exitPrice = trade.exit_price || trade.current_price
  const closeReason = trade.close_reason || trade.reason || null

  return (
    <div className="border border-gray-200 rounded-xl p-4 mb-3 bg-white shadow-sm">
      <div className="flex justify-between items-start">
        <div>
          <div className="flex items-center gap-2">
            <span className="font-medium">{(trade.strategy_version || trade.version) === 'V1' ? 'Nova Trend' : 'Nova Range'}</span>
            <span className={`text-xs font-semibold px-2 py-0.5 rounded ${
              trade.side === 'LONG' ? 'bg-green-100 text-green-700' :
              trade.side === 'SHORT' ? 'bg-red-100 text-red-700' :
              'bg-gray-100 text-gray-700'
            }`}>
              {trade.side || 'TRADE'}
            </span>
            <span className="text-gray-500 text-sm">{trade.symbol || 'BTC'}</span>
            {closeReason && (
              <span className={`text-xs font-medium px-2 py-0.5 rounded ${
                closeReason === 'TAKE_PROFIT' ? 'bg-blue-100 text-blue-700' :
                closeReason === 'TRAILING_STOP' ? 'bg-purple-100 text-purple-700' :
                closeReason === 'STOP_LOSS' ? 'bg-red-100 text-red-700' :
                'bg-gray-100 text-gray-600'
              }`}>
                {closeReason.replace('_', ' ')}
              </span>
            )}
          </div>
          <div className="text-gray-500 text-sm mt-1">
            Entry: ${formatPrice(entryPrice)} → Exit: ${exitPrice ? `$${formatPrice(exitPrice)}` : '—'}
          </div>
          <div className="text-gray-500 text-sm">
            Qty: {formatQty(trade.quantity)} | {trade.leverage || 1}× leverage
          </div>
          {holdingTime && (
            <div className="text-gray-400 text-xs mt-1">
              Held: {holdingTime}
            </div>
          )}
        </div>
        <div className="text-right">
          <div className="text-gray-400 text-sm">
            {formatDate(trade.datetime || trade.timestamp)}
          </div>
          {hasPnl && (
            <div className={`font-medium mt-2 ${isProfit ? 'text-green-600' : 'text-red-600'}`}>
              {isProfit ? '+' : ''}${netPnl.toFixed(2)}
            </div>
          )}
          {trade.confidence && (
            <div className="text-xs text-gray-400 mt-1">
              {Math.round(trade.confidence * 100)}% conf
            </div>
          )}
        </div>
      </div>

      {reasoning && (
        <div className="mt-3 pt-3 border-t border-gray-100">
          <button
            onClick={() => setShowReasoning(!showReasoning)}
            className="text-xs text-blue-600 hover:text-blue-700 font-medium flex items-center gap-1"
          >
            <span>{showReasoning ? '▼' : '▶'}</span>
            AI Reasoning
          </button>
          {showReasoning && (
            <div className="mt-2 text-xs text-gray-600 bg-gray-50 rounded-lg p-3 leading-relaxed">
              {reasoning}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
