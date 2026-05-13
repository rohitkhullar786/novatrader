import { useState, useEffect, useRef } from "react"
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Brush,
  ReferenceDot
} from "recharts"
import { loadBTCData } from "../services/marketData"
import NovaTraderTooltip from "./NovaTraderTooltip"

const START_BALANCE = 10000 // Starting capital per strategy

// Helper functions
function formatCurrency(value) {
  return `$${value?.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
}

function formatPercent(percent) {
  const sign = percent >= 0 ? "+" : ""
  return `${sign}${percent.toFixed(2)}%`
}

// Strategy Badge Component
function StrategyBadge({ title, value, percent, lineColor, isBTC = false }) {
  const percentColor = percent >= 0 ? "text-green-600" : "text-red-500"
  
  if (isBTC) {
    return (
      <div 
        className="bg-white rounded-xl border-2 px-3 py-2 shadow-md"
        style={{ borderColor: "#f59e0b" }}
      >
        <div className="flex items-center gap-2 mb-1">
          <div 
            className="w-6 h-6 rounded-full flex items-center justify-center text-white text-xs font-bold"
            style={{ backgroundColor: "#f59e0b" }}
          >
            ₿
          </div>
          <div className="text-xs text-gray-500">{title}</div>
        </div>
        <div className="text-lg font-semibold">{formatCurrency(value)}</div>
        <div className={percentColor}>{formatPercent(percent)}</div>
      </div>
    )
  }
  
  return (
    <div 
      className="bg-white rounded-xl border px-3 py-2 shadow-md"
      style={{ borderColor: lineColor || "#d4d4d4" }}
    >
      <div className="text-xs text-gray-500 mb-1">{title}</div>
      <div className="text-lg font-semibold">{formatCurrency(value)}</div>
      <div className={percentColor}>{formatPercent(percent)}</div>
    </div>
  )
}

export default function MainChartCard({ v1Balance = 10000, v2Balance = 10000 }) {
  const [btcData, setBtcData] = useState([])
  const [equity, setEquity] = useState({ V1: [], V2: [] })
  const [metrics, setMetrics] = useState({ V1: {}, V2: {} })
  const [indicators, setIndicators] = useState(null)
  const [trades, setTrades] = useState({ V1: [], V2: [] })
  const containerRef = useRef(null)

  // Fetch trades for realized P&L calculation
  useEffect(() => {
    async function fetchTrades() {
      try {
        const res = await fetch('/api/trades')
        const data = await res.json()
        // Group by strategy
        const grouped = { V1: [], V2: [] }
        data.forEach(t => {
          if (t.strategy_version === 'V1') grouped.V1.push(t)
          else if (t.strategy_version === 'V2') grouped.V2.push(t)
        })
        setTrades(grouped)
      } catch (e) {
        console.error('Error fetching trades:', e)
      }
    }
    fetchTrades()
    const interval = setInterval(fetchTrades, 30000) // refresh every 30s
    return () => clearInterval(interval)
  }, [])

  // Get current equity values from metrics
  // /api/metrics returns equity directly
  // Both V1 and V2 use the same live HTX balance, so use V1 equity only (not V1 + V2)
  const currentV1Equity = metrics.V1?.equity ?? START_BALANCE
  const currentV2Equity = metrics.V2?.equity ?? START_BALANCE

  // Live trading project starting equity (Rohit confirmed $200)
  const INITIAL_PROJECT_Equity = 200

  // Calculate cumulative closed trade P&L (in BTC, then convert to USD)
  // User said to ignore closed trades - so no P&L from closed trades
  const allTrades = [...(trades.V1 || []), ...(trades.V2 || [])]
  const closedTrades = allTrades.filter(t => t.status === 'closed')
  
  // Use REAL equity from HTX balance
  const allEquity = [...(equity.REAL || [])]
    .sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp))
  const currentEquity = allEquity.length > 0 ? allEquity[0].equity : INITIAL_PROJECT_Equity
  const totalValue = currentEquity

  // Total return
  const totalReturn = INITIAL_PROJECT_Equity > 0 ? ((totalValue - INITIAL_PROJECT_Equity) / INITIAL_PROJECT_Equity) * 100 : 0
  const returnStr = totalReturn >= 0 ? `+${totalReturn.toFixed(2)}%` : `${totalReturn.toFixed(2)}%`

  // Calculate BTC return
  const firstBtcPrice = btcData.length > 0 ? btcData[0].btc : START_BALANCE
  const lastBtcPrice = btcData.length > 0 ? btcData[btcData.length - 1].btc : START_BALANCE
  const btcReturn = firstBtcPrice > 0 ? ((lastBtcPrice / firstBtcPrice) - 1) * 100 : 0
  const btcReturnStr = btcReturn >= 0 ? `+${btcReturn.toFixed(2)}%` : `${btcReturn.toFixed(2)}%`

  // vs BTC
  const vsBTC = totalReturn - btcReturn
  const vsBTCStr = vsBTC >= 0 ? `+${vsBTC.toFixed(2)}%` : `${vsBTC.toFixed(2)}%`

  useEffect(() => {
    loadBTCData().then(data => {
      if (data.length > 0) setBtcData(data)
    })
    
    fetchEquity()
    fetchMetrics()
    fetchIndicators()
    
    const interval = setInterval(() => {
      fetchEquity()
      fetchMetrics()
      fetchIndicators()
    }, 30000)
    return () => clearInterval(interval)
  }, [])

  async function fetchEquity() {
    try {
      const res = await fetch('/api/equity')
      const data = await res.json()
      setEquity(data)
    } catch (e) {
      console.error("Error fetching equity:", e)
    }
  }

  async function fetchMetrics() {
    try {
      const res = await fetch('/api/metrics')
      const data = await res.json()
      setMetrics(data)
    } catch (e) {
      console.error("Error fetching metrics:", e)
    }
  }

  async function fetchIndicators() {
    try {
      const res = await fetch('/api/indicators')
      const data = await res.json()
      setIndicators(data)
    } catch (e) {
      console.error("Error fetching indicators:", e)
    }
  }

  // Build chart data from CLOSED TRADES P&L + CoinGecko BTC prices
  // Iterate over BTC date range to show 3 months of data
  function prepareChartData() {
    const realData = equity.REAL || []
    const currentRealEquity = realData.length > 0 ? realData[0].equity : INITIAL_PROJECT_Equity
    
    // If no BTC data, return empty
    if (btcData.length === 0) {
      return []
    }
    
    const firstBtcPrice = btcData[0].btc
    
    // Show baseline ($200) for most of the chart, current value at the end
    return btcData.map((btcPoint, i) => {
      const { date: dateKey, btc: btcPrice } = btcPoint
      const isLast = i === btcData.length - 1
      
      const novaValue = Math.round(isLast ? currentRealEquity : INITIAL_PROJECT_Equity)
      const btcValue = Math.round(INITIAL_PROJECT_Equity * (btcPrice / firstBtcPrice))
      
      return {
        date: dateKey,
        btc: btcValue,
        nova: novaValue
      }
    })
  }

  const chartData = prepareChartData()
  const last = chartData[chartData.length - 1]
  // Combined return from $200 baseline (Rohit: combined only, not per-strategy)
  const combinedReturn = last ? ((last.nova - INITIAL_PROJECT_Equity) / INITIAL_PROJECT_Equity * 100) : 0
  // BTC return from $200 baseline
  const btcReturnVal = last ? ((last.btc - INITIAL_PROJECT_Equity) / INITIAL_PROJECT_Equity * 100) : 0

  return (
    <div className="bg-white rounded-2xl border border-gray-200 shadow-sm p-2 md:p-6 relative" ref={containerRef}>

      {/* Performance Summary - Desktop only on chart */}
      <div className="hidden md:flex gap-12 mb-6 text-sm">

        <div>
          <div className="text-gray-400">Current Value</div>
          <div className="font-semibold">${totalValue.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</div>
        </div>

        <div>
          <div className="text-gray-400">Total Return</div>
          <div className={`font-semibold ${totalReturn >= 0 ? "text-green-600" : "text-red-600"}`}>
            {returnStr}
          </div>
        </div>

        <div>
          <div className="text-gray-400">vs BTC</div>
          <div className={`font-semibold ${vsBTC >= 0 ? "text-green-600" : "text-red-600"}`}>
            {vsBTCStr}
          </div>
        </div>

      </div>

      {/* NovaTrader-style Chart */}
      <div className="w-full" style={{height: '400px'}}>
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart
            data={chartData}
            margin={{ top: 10, right: 40, left: 0, bottom: 0 }}
          >
            <defs>
              <linearGradient id="trendFill" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#000" stopOpacity={0.06} />
                <stop offset="100%" stopColor="#000" stopOpacity={0} />
              </linearGradient>
            </defs>

            <CartesianGrid
              stroke="#efefef"
              strokeDasharray="3 3"
            />

            <XAxis
              dataKey="date"
              tick={{ fill: "#9ca3af", fontSize: 12 }}
              axisLine={false}
              tickLine={false}
            />

            <YAxis
              domain={['auto', 'auto']}
              tick={{ fill: "#9ca3af", fontSize: 12 }}
              axisLine={false}
              tickLine={false}
            />

            <Tooltip
              isAnimationActive={false}
              content={<NovaTraderTooltip />}
              cursor={{
                stroke: "#d1d5db",
                strokeWidth: 1,
                strokeDasharray: "4 4"
              }}
            />

            {/* Shaded Nova Returns performance */}
            <Area
              type="monotoneX"
              dataKey="nova"
              name="Nova Returns"
              stroke="#111111"
              strokeWidth={2.4}
              fill="url(#trendFill)"
              dot={false}
              isAnimationActive={true}
              animationDuration={900}
            />

            {/* BTC baseline */}
            <Line
              type="monotoneX"
              dataKey="btc"
              name="BTC"
              stroke="#f59e0b"
              strokeWidth={2}
              dot={false}
              isAnimationActive={true}
              animationDuration={900}
            />

            {/* Floating badges at the end of each line */}
            {last && (
              <>
                {/* Nova Returns badge */}
                <ReferenceDot
                  x={last.date}
                  y={last.nova}
                  r={0}
                  label={<StrategyBadge title="Nova Returns" value={last.nova} percent={combinedReturn} lineColor="#111111" />}
                />
                {/* BTC badge */}
                <ReferenceDot
                  x={last.date}
                  y={last.btc}
                  r={0}
                  label={<StrategyBadge title="BTC Holding Returns" value={last.btc} percent={btcReturnVal} isBTC={true} />}
                />
              </>
            )}

            {/* Zoom slider */}
            <Brush
              dataKey="date"
              height={22}
              stroke="#e5e7eb"
              travellerWidth={8}
            />

          </AreaChart>
        </ResponsiveContainer>

      </div>

    </div>
  )
}
