import { useState } from 'react'

export default function MobileNav({ activeTab = 'home', onTabChange, onClose, open = false }) {
  const tabs = [
    { id: 'home', label: 'Home', desc: 'Dashboard & chart' },
    { id: 'positions', label: 'Positions', desc: 'Active trades & P&L' },
    { id: 'trades', label: 'Trades', desc: 'Trade history' },
    { id: 'ai', label: 'AI Reasoning', desc: 'Latest analysis' },
  ]

  return (
    <>
      {/* Backdrop */}
      {open && (
        <div
          className="fixed inset-0 bg-black/40 z-40 transition-opacity duration-300"
          onClick={onClose}
        />
      )}

      {/* Slide-in Panel */}
      <div
        className={`fixed top-0 right-0 h-full w-[280px] bg-white z-50 shadow-2xl transform transition-transform duration-300 ease-out ${
          open ? 'translate-x-0' : 'translate-x-full'
        }`}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-5 pt-5 pb-4 border-b border-gray-100">
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 rounded-lg bg-black flex items-center justify-center text-white text-xs font-bold">NV</div>
            <span className="font-semibold text-base">Nova</span>
          </div>
          <button onClick={onClose} className="p-1.5 hover:bg-gray-100 rounded-lg transition-colors">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#111" strokeWidth="2" strokeLinecap="round">
              <line x1="18" y1="6" x2="6" y2="18"/>
              <line x1="6" y1="6" x2="18" y2="18"/>
            </svg>
          </button>
        </div>

        {/* Navigation Items */}
        <div className="px-3 pt-4 space-y-1">
          {tabs.map(tab => {
            const isActive = activeTab === tab.id
            return (
              <button
                key={tab.id}
                onClick={() => {
                  onTabChange(tab.id)
                  onClose()
                }}
                className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl text-left transition-colors ${
                  isActive 
                    ? 'bg-black text-white' 
                    : 'text-gray-700 hover:bg-gray-50'
                }`}
              >
                <TabIcon id={tab.id} active={isActive} />
                <div>
                  <div className={`text-sm font-medium ${isActive ? 'text-white' : 'text-gray-900'}`}>{tab.label}</div>
                  <div className={`text-xs ${isActive ? 'text-white/60' : 'text-gray-400'}`}>{tab.desc}</div>
                </div>
              </button>
            )
          })}
        </div>

        {/* Bottom info */}
        <div className="absolute bottom-0 left-0 right-0 p-5 border-t border-gray-100">
          <div className="text-xs text-gray-400">NovaTrader v1</div>
        </div>
      </div>
    </>
  )
}

function TabIcon({ id, active }) {
  const stroke = active ? '#fff' : '#6B7280'
  const props = { width: 20, height: 20, viewBox: '0 0 24 24', fill: 'none', stroke: stroke, strokeWidth: '2', strokeLinecap: 'round', strokeLinejoin: 'round' }
  
  switch(id) {
    case 'home':
      return <svg {...props}><path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/></svg>
    case 'positions':
      return <svg {...props}><path d="M21 12V7H5a2 2 0 0 1 0-4h14v4"/><path d="M3 5v14a2 2 0 0 0 2 2h16v-5"/><path d="M18 12a2 2 0 0 0 0 4h4v-4z"/></svg>
    case 'trades':
      return <svg {...props}><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>
    case 'ai':
      return <svg {...props}><path d="M12 2a4 4 0 0 1 4 4c0 2-2 4-4 4s-4-2-4-4a4 4 0 0 1 4-4z"/><path d="M16 14h-8a4 4 0 0 0-4 4v2h16v-2a4 4 0 0 0-4-4z"/><path d="M8 14l3-5 3 5"/></svg>
    default:
      return null
  }
}
