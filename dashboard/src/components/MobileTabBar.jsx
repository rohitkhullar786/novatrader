export default function MobileTabBar({ activeTab = 'home', onTabChange }) {
  const tabs = [
    {
      id: 'home',
      label: 'Home',
      icon: (active) => (
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke={active ? '#000' : '#9CA3AF'} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>
          <polyline points="9 22 9 12 15 12 15 22"/>
        </svg>
      )
    },
    {
      id: 'positions',
      label: 'Positions',
      icon: (active) => (
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke={active ? '#000' : '#9CA3AF'} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M21 12V7H5a2 2 0 0 1 0-4h14v4"/>
          <path d="M3 5v14a2 2 0 0 0 2 2h16v-5"/>
          <path d="M18 12a2 2 0 0 0 0 4h4v-4z"/>
        </svg>
      )
    },
    {
      id: 'trades',
      label: 'Trades',
      icon: (active) => (
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke={active ? '#000' : '#9CA3AF'} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>
        </svg>
      )
    },
    {
      id: 'ai',
      label: 'AI',
      icon: (active) => (
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke={active ? '#000' : '#9CA3AF'} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M12 2a4 4 0 0 1 4 4c0 2-2 4-4 4s-4-2-4-4a4 4 0 0 1 4-4z"/>
          <path d="M16 14h-8a4 4 0 0 0-4 4v2h16v-2a4 4 0 0 0-4-4z"/>
          <path d="M8 14l3-5 3 5"/>
        </svg>
      )
    }
  ]

  return (
    <div className="flex items-center justify-around bg-white/90 backdrop-blur-lg border-t border-gray-100 pb-4 pt-2 px-2 safe-area-bottom" style={{paddingBottom: 'max(8px, env(safe-area-inset-bottom))'}}>
      {tabs.map(tab => {
        const isActive = activeTab === tab.id
        return (
          <button
            key={tab.id}
            onClick={() => onTabChange(tab.id)}
            className="flex flex-col items-center gap-0.5 relative py-1 px-3 min-w-[56px]"
          >
            {isActive && (
              <div className="absolute -top-2 w-8 h-0.5 bg-black rounded-full" />
            )}
            {tab.icon(isActive)}
            <span className={`text-[10px] font-medium ${isActive ? 'text-black' : 'text-gray-400'}`}>
              {tab.label}
            </span>
          </button>
        )
      })}
    </div>
  )
}
