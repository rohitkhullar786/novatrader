import { useState, useEffect } from "react"
import TradeCard from "./TradeCard"
import ReasoningCard from "./ReasoningCard"
import PositionTable from "./PositionTable"
import HoldingsCard from "./HoldingsCard"

export default function RightPanel(){

const tabs = [
  "Trades",
  "AI Reasoning", 
  "Positions",
  "Holdings"
]

const [active, setActive] = useState("Trades")
const [trades, setTrades] = useState([])
const [positions, setPositions] = useState({ NOVA: [] })
const [decisions, setDecisions] = useState([])

useEffect(() => {
  fetchTrades()
  fetchPositions()
  fetchDecisions()
}, [])

useEffect(() => {
  // Poll positions every 30 seconds (for position status updates)
  const positionsInterval = setInterval(fetchPositions, 30000)
  
  // Poll other data every 30 seconds
  const interval = setInterval(() => {
    if (active === "Trades") fetchTrades()
    // Always poll decisions in background so AI Reasoning tab has latest data
    fetchDecisions()
  }, 30000)
  
  return () => {
    clearInterval(positionsInterval)
    clearInterval(interval)
  }
}, [active])

function fetchTrades() {
  fetch('/api/trades')
    .then(r => { if (!r.ok) throw new Error(`HTTP ${r.status}`); return r.json() })
    .then(d => {
      if (Array.isArray(d)) setTrades(d)
    })
    .catch(e => console.error('fetchTrades:', e))
}

function fetchPositions() {
  fetch('/api/positions')
    .then(r => { if (!r.ok) throw new Error(`HTTP ${r.status}`); return r.json() })
    .then(d => {
      if (d && d.strategies) {
        setPositions({
          NOVA: d.strategies.NOVA || []
        })
      } else if (Array.isArray(d)) {
        const grouped = {V1: [], V2: []}
        d.forEach(p => {
          if (p && p.strategy_version === "V1") grouped.V1.push(p)
          else if (p && p.strategy_version === "V2") grouped.V2.push(p)
        })
        setPositions(grouped)
      }
    })
    .catch(e => console.error('fetchPositions:', e))
}

function fetchDecisions() {
  fetch('/api/decisions')
    .then(r => { if (!r.ok) throw new Error(`HTTP ${r.status}`); return r.json() })
    .then(d => {
      if (Array.isArray(d)) setDecisions(d)
    })
    .catch(e => console.error('fetchDecisions:', e))
}

// Show all closed trades
const filteredTrades = (trades || []).filter(t => t && t.status === 'closed')

// Show last 30 decisions (newest first)
const filteredDecisions = (decisions || []).slice(0, 30)

return(

<div className="bg-white border border-gray-200 rounded-2xl shadow-sm">

<div className="flex border-b text-sm">

{tabs.map(t => (
  <div
    key={t}
    onClick={() => setActive(t)}
    className={`px-4 py-2 cursor-pointer border-b-2
      ${active === t ? "border-black font-medium bg-white" : "border-transparent text-gray-500"}
    `}
  >
    {t}
  </div>
))}

</div>

<div className="p-4 text-sm text-gray-600">

{active === "Trades" && (
  <div>
    {/* Unified strategy */}
    <div className="flex gap-6 text-sm mb-3">
      <div className="font-medium">Closed Trades</div>
      <div className="text-gray-400">{filteredTrades.length} total</div>
    </div>

    {filteredTrades.length > 0 ? (
      <div className="max-h-[600px] overflow-y-auto pr-1">
        {filteredTrades.map((trade, i) => <TradeCard key={i} trade={trade} />)}
      </div>
    ) : (
      <div className="text-center text-gray-400 py-8">
        No closed trades yet
      </div>
    )}
  </div>
)}

{active === "AI Reasoning" && (
  <div>
    {/* Unified Strategy */}
    <div className="flex gap-4 text-sm mb-3">
      <div className="cursor-pointer pb-1 border-b-2 border-gray-800 font-medium">
        Nova
      </div>
    </div>

    {/* Scrollable Reasoning Cards */}
    <div className="max-h-[600px] pr-1 invisible-scroll">
      {/* Check if position is active */}
      {positions.NOVA && positions.NOVA.some(p => p.coin !== 'USDD' && p.quantity > 0) && (
        <div className="bg-yellow-50 border border-yellow-200 rounded-xl p-3 mb-3 text-xs text-yellow-700">
          ⏸ AI reasoning paused — position active. Resumes when position closes.
        </div>
      )}
      {filteredDecisions.length > 0 ? (
        filteredDecisions.map((dec, i) => <ReasoningCard key={i} decision={dec} />)
      ) : (
        <div className="text-center text-gray-400 py-8">
          No AI reasoning yet. Run the strategy to get a decision.
        </div>
      )}
    </div>
  </div>
)}

{active === "Positions" && (
  <div className="space-y-4">
    {/* Show both V1 and V2 positions stacked */}
    <PositionTable positions={positions.NOVA || []} version="NOVA" />
  </div>
)}

{active === "Holdings" && (
  <div>
    <HoldingsCard />
  </div>
)}

</div>

</div>

)

}
