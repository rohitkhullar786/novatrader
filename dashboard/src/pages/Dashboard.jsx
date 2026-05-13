import { useState, useEffect } from "react"
import TickerRow from "../components/TickerRow"
import MainChartCard from "../components/MainChartCard"
import RightPanel from "../components/RightPanel"
import DecisionCard from "../components/DecisionCard"
import MobileNav from "../components/MobileNav"
import { getBalance, getHtxBalance, getPositions, startAutoRun } from "../services/api"

export default function Dashboard(){

const [decision, setDecision] = useState(null)
const [balance, setBalance] = useState({V1: 10000, V2: 10000})
const [htxBalance, setHtxBalance] = useState({USDD: 0, BTC: 0, total: 0})
const [totalValue, setTotalValue] = useState(10000)

const [activeMobileTab, setActiveMobileTab] = useState("home")
const [menuOpen, setMenuOpen] = useState(false)

async function fetchData() {
  try {
    const htxRes = await getHtxBalance()
    if (htxRes && !htxRes.error) {
      setHtxBalance({
        USDD: htxRes.assets?.USDD?.total || 0,
        BTC: htxRes.assets?.BTC?.total || 0,
        total: (htxRes.assets?.USDD?.value_usdd || 0) + (htxRes.assets?.BTC?.value_usdd || 0),
        btc_price: htxRes.btc_price || 0
      })
    }
    const balRes = await getBalance()
    const v1Bal = balRes?.V1?.equity ?? 10000
    const v2Bal = balRes?.V2?.equity ?? 10000
    setBalance({V1: v1Bal, V2: v2Bal})
    setTotalValue(v1Bal + v2Bal)
  } catch (e) {
    console.error("Error fetching data:", e)
  }
}

function handleMobileTabChange(tab) {
  setActiveMobileTab(tab)
}

useEffect(() => {
  startAutoRun()
  fetchData()
  const interval = setInterval(fetchData, 30000)
  return () => clearInterval(interval)
}, [])

return (
  <div className="bg-[#f5f6f7] min-h-screen text-[#111]">
    <div className="max-w-[1400px] mx-auto">

      {/* ===== MOBILE VIEW ===== */}
      <div className="md:hidden flex flex-col min-h-screen">
        
        {/* Compact Header */}
        <div className="bg-white px-4 pt-4 pb-3 border-b border-gray-100">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2">
              <div className="w-7 h-7 rounded-lg bg-black flex items-center justify-center text-white text-xs font-bold">NV</div>
              <span className="font-semibold text-base">Nova</span>
            </div>
            <button 
              onClick={() => setMenuOpen(true)}
              className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
            >
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#111" strokeWidth="2" strokeLinecap="round">
                <line x1="3" y1="6" x2="21" y2="6"/>
                <line x1="3" y1="12" x2="21" y2="12"/>
                <line x1="3" y1="18" x2="21" y2="18"/>
              </svg>
            </button>
          </div>
          <div className="flex items-center gap-6">
            <div>
              <div className="text-[10px] text-gray-400 uppercase tracking-wider">Balance</div>
              <div className="text-lg font-bold">${(htxBalance.total ?? 0).toLocaleString(undefined, {minimumFractionDigits: 2})}</div>
            </div>
            <div>
              <div className="text-[10px] text-gray-400 uppercase tracking-wider">BTC</div>
              <div className="text-sm font-semibold">${(htxBalance.btc_price ?? 0).toLocaleString(undefined, {minimumFractionDigits: 2})}</div>
            </div>
            <div>
              <div className="text-[10px] text-gray-400 uppercase tracking-wider">USDD</div>
              <div className="text-sm font-semibold">${(htxBalance.USDD ?? 0).toFixed(2)}</div>
            </div>
          </div>
        </div>

        {/* Tab Content */}
        <div className="flex-1 overflow-y-auto px-3 py-3 space-y-3 tab-content">
          {activeMobileTab === "home" && (
            <div className="space-y-3">
              <MainChartCard totalValue={totalValue} v1Balance={balance.V1} v2Balance={balance.V2}/>
              <DecisionCard decision={decision}/>
            </div>
          )}
          {activeMobileTab === "positions" && (
            <RightPanel mobileTab="Positions" />
          )}
          {activeMobileTab === "trades" && (
            <RightPanel mobileTab="Trades" />
          )}
          {activeMobileTab === "ai" && (
            <RightPanel mobileTab="AI Reasoning" />
          )}
        </div>

        {/* Bottom Tab Bar */}
        <MobileNav activeTab={activeMobileTab} onTabChange={handleMobileTabChange} open={menuOpen} onClose={() => setMenuOpen(false)}/>
      </div>

      {/* ===== DESKTOP VIEW ===== */}
      <div className="hidden md:block p-4 md:p-6">
        <div className="flex items-center justify-between mb-4 md:mb-6">
          <div className="font-semibold text-base md:text-lg">Nova</div>
          <div className="flex items-center gap-3 md:gap-4">
            <div className="text-xs md:text-sm font-medium">
              Balance: <span className="font-semibold">${(htxBalance.total ?? 0).toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}</span>
            </div>

          </div>
        </div>
        <div className="grid grid-cols-[1fr_500px] gap-6">
          <div className="space-y-6">
            <TickerRow/>
            <MainChartCard totalValue={totalValue} v1Balance={balance.V1} v2Balance={balance.V2}/>
            <DecisionCard decision={decision}/>
          </div>
          <RightPanel/>
        </div>
      </div>



    </div>
  </div>
)
}