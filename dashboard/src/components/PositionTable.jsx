import { useState, useEffect } from 'react'

export default function PositionTable({ positions, version = "NOVA" }) {
  const [livePrices, setLivePrices] = useState({})
  const filteredPositions = positions ? positions.filter(p => p.coin !== 'USDD' && p.coin !== 'Free') : [];
  const hasOpenPositions = filteredPositions.length > 0;

  // Live price from SSE stream
  useEffect(() => {
    const es = new EventSource('/api/prices/stream')
    es.onmessage = (e) => { try { setLivePrices(JSON.parse(e.data)) } catch {} }
    es.onerror = () => { es.close(); setTimeout(() => { const es2 = new EventSource('/api/prices/stream'); es2.onmessage = es.onmessage }, 3000) }
    return () => es.close()
  }, [])

  const formatUSD = (q) => {
    if (q == null) return '—';
    const num = parseFloat(q);
    if (isNaN(num)) return '—';
    return num.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  };

  const formatQty = (q) => {
    if (q == null) return '—';
    const num = parseFloat(q);
    if (isNaN(num)) return '—';
    if (num > 1) return num.toFixed(4);
    return num.toFixed(8);
  };

  return (
    <div className="bg-white border border-gray-200 rounded-2xl p-4 shadow-sm">
      <div className="flex items-center gap-2 mb-4">
        <div className="w-6 h-6 rounded-full bg-black flex items-center justify-center text-white text-xs font-bold">NV</div>
        <div className="font-semibold">Active</div>
      </div>

      {!hasOpenPositions ? (
        <div className="border border-gray-100 rounded-xl p-6 text-center">
          <div className="text-gray-400 text-3xl mb-2">📄</div>
          <div className="text-gray-500 text-sm">No open positions</div>
        </div>
      ) : (
        filteredPositions.map((pos, i) => {
          const pnl = pos.unrealized_pnl || 0;
          const isProfit = pnl >= 0;
          const size = pos.position_size || (pos.quantity || 0) * (pos.entry_price || 0);
          const qty = pos.quantity || 0;
          const entry = pos.entry_price || 0;
          const liveUsdd = livePrices["BTC/USDD"]?.price; const current = liveUsdd || pos.current_price || 0;
          const pnlPercent = size > 0 ? (pnl / size) * 100 : 0;
          const conf = (pos.confidence || 0) * 100;
          const sl = pos.stop_loss_price;
          const ts = pos.trailing_stop_active && pos.trailing_stop_price;

          return (
            <div key={i} className="space-y-3">
              {/* Main row: coin + P&L */}
              <div className="flex items-center justify-between">
                <div>
                  <div className="text-sm font-medium">BTC/USDD</div>
                  <div className="text-xs text-gray-400">{qty.toFixed(6)} BTC</div>
                </div>
                <div className="text-right">
                  <div className={`text-sm font-semibold ${isProfit ? 'text-green-600' : 'text-red-600'}`}>
                    {isProfit ? '+' : ''}{pnlPercent.toFixed(2)}%
                  </div>
                  <div className={`text-xs ${isProfit ? 'text-green-500' : 'text-red-500'}`}>
                    {isProfit ? '+' : ''}${pnl.toFixed(2)}
                  </div>
                </div>
              </div>

              {/* Stats grid */}
              <div className="grid grid-cols-2 gap-2 text-xs">
                <div className="bg-gray-50 rounded-lg p-2.5">
                  <div className="text-gray-400">Entry</div>
                  <div className="font-medium">${formatUSD(entry)}</div>
                </div>
                <div className="bg-gray-50 rounded-lg p-2.5">
                  <div className="text-gray-400">Current</div>
                  <div className="font-medium">${formatUSD(current)}</div>
                </div>
                <div className="bg-gray-50 rounded-lg p-2.5">
                  <div className="text-gray-400">Size</div>
                  <div className="font-medium">${formatUSD(size)}</div>
                </div>
                <div className="bg-gray-50 rounded-lg p-2.5">
                  <div className="text-gray-400">Confidence</div>
                  <div className="font-medium">{conf.toFixed(0)}%</div>
                </div>
              </div>

              {/* Stop info */}
              <div className="flex gap-2 text-xs">
                {sl ? (
                  <div className="flex-1 bg-red-50 rounded-lg p-2.5">
                    <div className="text-red-400">Stop Loss</div>
                    <div className="font-medium text-red-600">${formatUSD(sl)}</div>
                  </div>
                ) : (
                  <div className="flex-1 bg-gray-50 rounded-lg p-2.5">
                    <div className="text-gray-400">Stop Loss</div>
                    <div className="font-medium">—</div>
                  </div>
                )}
                {ts ? (
                  <div className="flex-1 bg-blue-50 rounded-lg p-2.5">
                    <div className="text-blue-400">Trailing Stop</div>
                    <div className="font-medium text-blue-600">${formatUSD(ts)}</div>
                    <div className="text-[10px] text-blue-400 mt-0.5">Trailing 1.2% below high</div>
                  </div>
                ) : (
                  <div className="flex-1 bg-gray-50 rounded-lg p-2.5 border border-dashed border-gray-200">
                    <div className="text-gray-400">Trailing Stop</div>
                    <div className="font-medium text-gray-400">—</div>
                    <div className="text-[10px] text-gray-300">Activates at ${formatUSD(entry * 1.02)}</div>
                  </div>
                )}
              </div>

              {/* Reasoning - matching AI Reasoning card style */}
              {pos.reasoning && pos.reasoning.length > 20 && (
                <div className="border border-gray-200 rounded-xl p-3 bg-white">
                  <div className="text-xs font-semibold text-gray-500 mb-1">Entry Signal</div>
                  <div className="max-h-[150px] overflow-y-auto border border-gray-100 rounded p-2">
                    <p className="text-sm text-gray-600 leading-relaxed">{pos.reasoning.replace(/^We need to[^.]*\.\s*/i, '')}</p>
                  </div>
                </div>
              )}
            </div>
          );
        })
      )}
    </div>
  );
}
