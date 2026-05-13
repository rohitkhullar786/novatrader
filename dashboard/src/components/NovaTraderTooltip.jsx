export default function NovaTraderTooltip({ active, payload, label }) {
  if (!active || !payload || payload.length === 0) return null

  const btc = payload.find(p => p.dataKey === "btc")
  const nova = payload.find(p => p.dataKey === "nova")

  return (
    <div className="bg-[#1c1c1c] text-white px-4 py-3 rounded-xl shadow-xl border border-black/20">
      <div className="text-xs text-gray-400 mb-2">
        {label}
      </div>

      {btc && (
        <div className="flex items-center gap-2 text-sm mb-1">
          <div className="w-2.5 h-2.5 rounded-full bg-[#f59e0b]"></div>
          <span className="text-gray-300">BTC Holding Returns:</span>
          <span className="font-semibold">${btc.value?.toLocaleString()}</span>
        </div>
      )}

      {nova && (
        <div className="flex items-center gap-2 text-sm mb-1">
          <div className="w-2.5 h-2.5 rounded-full bg-black"></div>
          <span className="text-gray-300">Nova Returns:</span>
          <span className="font-semibold">${nova.value?.toLocaleString()}</span>
        </div>
      )}
    </div>
  )
}
