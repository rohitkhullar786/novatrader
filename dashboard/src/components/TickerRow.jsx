import { useEffect, useState } from 'react'

export default function TickerRow() {
  const [data, setData] = useState({})
  const [error, setError] = useState(null)

  useEffect(() => {
    let eventSource = null

    const connect = () => {
      eventSource = new EventSource('/api/prices/stream')
      
      eventSource.onmessage = (event) => {
        try {
          const newData = JSON.parse(event.data)
          setData(newData)
        } catch (e) {
          console.error('Parse error:', e)
        }
      }

      eventSource.onerror = () => {
        console.error('SSE error, reconnecting...')
        eventSource.close()
        setTimeout(connect, 3000)
      }
    }

    connect()

    return () => {
      if (eventSource) {
        eventSource.close()
      }
    }
  }, [])

  if (error) return <div className="p-4 text-red-500">Error: {error}</div>

  const pairs = [
    { key: 'BTC/USDT', label: 'BTC' },
    { key: 'TRX/USDT', label: 'TRX' },
    { key: 'BTC/USDD', label: 'BTC/USDD' }
  ]

  const formatPrice = (p) => {
    if (p == null) return '—'
    const num = parseFloat(p)
    if (isNaN(num)) return '—'
    if (num > 100) return num.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
    if (num > 1) return num.toFixed(4)
    return num.toFixed(6)
  }

  return (
    <div className="bg-white border border-gray-200 rounded-2xl p-3 md:p-4 shadow-sm">
      {/* Desktop: horizontal row */}
      <div className="hidden md:flex gap-6 text-sm">
        {pairs.map(c => {
          const d = data[c.key] || {}
          const change = d.changePercent ? parseFloat(d.changePercent).toFixed(2) : null
          const isPos = change >= 0
          return (
            <div key={c.key} className="flex gap-2 items-center">
              <span className="font-semibold text-gray-600">{c.label}</span>
              <span className="font-medium">${formatPrice(d.price)}</span>
              {change !== null && (
                <span className={isPos ? 'text-green-500' : 'text-red-500'}>
                  {isPos ? '+' : ''}{change}%
                </span>
              )}
            </div>
          )
        })}
      </div>
      
      {/* Mobile: horizontal scroll */}
      <div className="md:hidden flex gap-4 text-xs overflow-x-auto pb-1 -mx-1 px-1">
        {pairs.map(c => {
          const d = data[c.key] || {}
          const change = d.changePercent ? parseFloat(d.changePercent).toFixed(2) : null
          const isPos = change >= 0
          return (
            <div key={c.key} className="flex-shrink-0 flex gap-2 items-center bg-gray-50 rounded-lg px-3 py-2">
              <span className="font-semibold text-gray-600">{c.label}</span>
              <span className="font-medium">${formatPrice(d.price)}</span>
              {change !== null && (
                <span className={isPos ? 'text-green-500' : 'text-red-500'}>
                  {isPos ? '+' : ''}{change}%
                </span>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}