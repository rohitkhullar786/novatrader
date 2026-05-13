import { useState, useEffect } from "react"

export default function SignalDetailsCard() {
  const [signalData, setSignalData] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchSignalDetails()
    const interval = setInterval(fetchSignalDetails, 10000) // Refresh every 10s
    return () => clearInterval(interval)
  }, [])

  function fetchSignalDetails() {
    Promise.all([
      fetch('/api/positions').then(r => r.json()),
      fetch('/api/decisions?limit=2').then(r => r.json())
    ])
      .then(([positionsData, decisionsData]) => {
        // Get V1 and V2 positions
        const v1Positions = positionsData.strategies?.V1 || []
        const v2Positions = positionsData.strategies?.V2 || []
        
        // Get the latest decisions for each strategy (API returns flat array)
        const allDecisions = Array.isArray(decisionsData) ? decisionsData : []
        const v1Decisions = allDecisions.filter(d => d && d.strategy_version === 'V1').slice(0, 1)
        const v2Decisions = allDecisions.filter(d => d && d.strategy_version === 'V2').slice(0, 1)
        
        // Find the position that triggered the latest buy for each strategy
        const getSignalInfo = (positions, decisions, version) => {
          const openPos = positions.find(p => p.coin !== 'USDD' && p.coin !== 'Free' && p.entry_price)
          
          if (!openPos) return null
          
          const positionReasoning = openPos.reasoning || ''
          const isManual = positionReasoning.toLowerCase().includes('manual')
          
          const posTime = new Date(openPos.timestamp)
          const relevantDecision = decisions.find(d => {
            const decTime = new Date(d.timestamp)
            return decTime <= posTime && d.decision !== 'HOLD'
          })
          
          return {
            version: version,
            versionName: version === 'V1' ? 'Nova Trend' : 'Nova Range',
            isManual: isManual,
            signalType: isManual 
    ? (openPos.timestamp ? `Manual @ ${new Date(openPos.timestamp).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })}` : 'Manual')
    : (relevantDecision ? `AI @ ${new Date(relevantDecision.timestamp).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })}` : 'AI'),
            entryPrice: openPos.entry_price,
            currentPrice: openPos.current_price || 0,
            quantity: openPos.quantity,
            positionSize: openPos.position_size || (openPos.quantity * openPos.entry_price),
            unrealizedPnl: openPos.unrealized_pnl || 0,
            reasoning: positionReasoning || (relevantDecision ? relevantDecision.reasoning : 'No reasoning available'),
            confidence: openPos.confidence || (relevantDecision ? relevantDecision.confidence : 0),
            timestamp: openPos.timestamp,
            stopLoss: openPos.stop_loss_price,
            takeProfit: openPos.take_profit_price
          }
        }
        
        const v1Signal = getSignalInfo(v1Positions, v1Decisions, 'V1')
        const v2Signal = getSignalInfo(v2Positions, v2Decisions, 'V2')
        
        setSignalData({ V1: v1Signal, V2: v2Signal })
        setLoading(false)
      })
      .catch(err => {
        console.error('Failed to fetch signal details:', err)
        setLoading(false)
      })
  }

  const formatUSD = (q) => {
    if (q == null || q === undefined) return '—'
    const num = parseFloat(q)
    if (isNaN(num)) return '—'
    return num.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
  }

  const formatQty = (q) => {
    if (q == null || q === undefined) return '—'
    const num = parseFloat(q)
    if (isNaN(num)) return '—'
    if (num > 1) return num.toFixed(4)
    return num.toFixed(8)
  }

  const SignalInfo = ({ data }) => {
    if (!data) return null
    
    const badgeColor = data.isManual ? 'bg-orange-500' : 'bg-blue-500'
    
    return (
      <div className="border border-gray-200 rounded-xl p-4 mt-3 bg-gray-50">
        {/* Header Row */}
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <div className={`w-8 h-8 rounded-full flex items-center justify-center text-white text-xs font-bold ${
              data.version === 'V1' ? 'bg-black' : 'bg-gray-700'
            }`}>
              {data.version === 'V1' ? 'NT' : 'NR'}
            </div>
            <span className="font-semibold">{data.versionName}</span>
          </div>
          <span className={`px-3 py-1 rounded-full text-white text-xs font-semibold ${badgeColor}`}>
            {data.signalType}
          </span>
        </div>
        
        {/* Stats Row - Mobile friendly grid */}
        <div className="grid grid-cols-2 gap-2 mb-4">
          <div className="bg-white rounded-lg p-3 border border-gray-200 text-center">
            <div className="text-gray-500 text-xs mb-1">Confidence</div>
            <div className={`font-bold text-lg ${(data.confidence || 0) >= 0.7 ? 'text-green-600' : (data.confidence || 0) >= 0.5 ? 'text-orange-600' : 'text-red-600'}`}>{((data.confidence || 0) * 100).toFixed(0)}%</div>
          </div>
          {data.takeProfit ? (
            <div className="bg-white rounded-lg p-3 border border-gray-200 text-center">
              <div className="text-gray-500 text-xs mb-1">Take Profit</div>
              <div className="font-bold text-green-600 text-sm">${formatUSD(data.takeProfit)}</div>
            </div>
          ) : (
            <div className="bg-white rounded-lg p-3 border border-gray-200 text-center opacity-50">
              <div className="text-gray-500 text-xs mb-1">Take Profit</div>
              <div className="font-bold text-gray-400 text-sm">—</div>
            </div>
          )}
        </div>
        
        {/* AI Reasoning */}
        <div className="bg-white rounded-lg p-3 border border-gray-200">
          <div className="text-gray-500 text-xs mb-2 font-medium">AI Reasoning</div>
          <div className="text-sm text-gray-700 leading-relaxed">"{data.reasoning}"</div>
        </div>
      </div>
    )
  }

  if (loading) {
    return (
      <div className="bg-white border border-gray-200 rounded-2xl p-4 shadow-sm">
        <div className="font-semibold mb-2">Signal Details</div>
        <div className="text-center text-gray-400 py-4">Loading...</div>
      </div>
    )
  }

  const hasSignals = signalData?.V1 || signalData?.V2

  return (
    <div className="bg-white border border-gray-200 rounded-2xl p-4 shadow-sm">
      <div className="font-semibold mb-2">Signal Details</div>
      
      {!hasSignals ? (
        <div className="text-center text-gray-400 py-6">
          <div className="text-2xl mb-2">📊</div>
          <div className="text-sm">No active signals</div>
          <div className="text-xs text-gray-400 mt-1">AI decisions will appear here</div>
        </div>
      ) : (
        <div>
          {signalData.V1 && <SignalInfo data={signalData.V1} />}
          {signalData.V2 && <SignalInfo data={signalData.V2} />}
        </div>
      )}
    </div>
  )
}