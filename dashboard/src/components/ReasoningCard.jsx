export default function ReasoningCard({ decision }) {
  if (!decision) return null

  const formatDate = (iso) => {
    if (!iso) return ''
    const d = new Date(iso)
    return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
  }

  const prices = decision.prices || {}
  const btcPrice = prices['BTC/USDT']?.price
  const version = decision.strategy_version || decision.version || 'V2'
  const model = decision.model || null

  // Build decision label
  const getDecisionLabel = () => {
    if (!decision.decision) return ''
    const dec = decision.decision.toUpperCase()
    if (dec === 'LONG') return 'Opening a long position'
    if (dec === 'SHORT') return 'Opening a short position'
    if (dec === 'CLOSE') return 'Closing position'
    return dec
  }

  return (
    <div className="border-2 border-gray-300 rounded-2xl p-4 mb-3 bg-white shadow-sm w-full">
      {/* Header with NovaTrader logo and timestamp */}
      <div className="flex justify-between mb-3">
        <div className="flex items-center gap-2">
          <div className="w-6 h-6 rounded-full bg-gradient-to-br from-gray-700 to-gray-900 flex items-center justify-center text-white text-xs font-bold">
            {version === 'V1' ? 'NT' : 'NR'}
          </div>
          <div className="font-semibold">{version === 'V1' ? 'Nova Trend' : 'Nova Range'}</div>
        </div>
        <div className="text-xs text-gray-400">
          {formatDate(decision.timestamp)}
        </div>
      </div>

      {/* Analysis header with decision on right */}
      <div className="flex justify-between items-center mb-2">
        <div className="text-sm font-medium">
          Analysis for BTC {btcPrice ? `@ $${btcPrice.toLocaleString('en-US', { minimumFractionDigits: 2 })}` : ''}
        </div>
        {decision.decision && (
          <span className={`inline-block text-xs font-semibold px-2 py-1 rounded ${
            decision.decision === 'LONG' ? 'bg-green-100 text-green-700' :
            decision.decision === 'SHORT' ? 'bg-red-100 text-red-700' :
            decision.decision === 'CLOSE' ? 'bg-blue-100 text-blue-700' :
            'bg-gray-100 text-gray-700'
          }`}>
            {getDecisionLabel() || 'HOLD'}
          </span>
        )}
      </div>

      {/* Analysis text - only show if exists */}
      {decision.analysis && (
        <div className="text-sm text-gray-600 mb-3 leading-relaxed">
          {decision.analysis}
        </div>
      )}

      {/* Reasoning section - scrollable */}
      <div className="text-xs font-semibold text-gray-500 mb-1">
        {model ? `Reasoning by ${model}:` : 'Reasoning:'}
      </div>
      <div className="max-h-[150px] overflow-y-auto border border-gray-100 rounded p-2">
        <p className="text-sm text-gray-600 leading-relaxed">
          {decision.reasoning || 'No reasoning provided'}
        </p>
      </div>
    </div>
  )
}
