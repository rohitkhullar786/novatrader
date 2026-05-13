const API_BASE = "/api"

export async function getDecision(version = "V2") {
  const res = await fetch(`${API_BASE}/decision/${version}`, {
    method: "POST"
  })
  return res.json()
}

export async function runBothStrategies() {
  const res = await fetch(`${API_BASE}/run-both`, {
    method: "POST"
  })
  return res.json()
}

export async function startAutoRun() {
  const res = await fetch(`${API_BASE}/auto/start`, {
    method: "POST"
  })
  return res.json()
}

export async function stopAutoRun() {
  const res = await fetch(`${API_BASE}/auto/stop`, {
    method: "POST"
  })
  return res.json()
}

export async function getAutoStatus() {
  const res = await fetch(`${API_BASE}/auto/status`)
  return res.json()
}

export async function getPrices() {
  const res = await fetch(`${API_BASE}/prices`)
  return res.json()
}

export async function getTrades() {
  const res = await fetch(`${API_BASE}/trades`)
  return res.json()
}

export async function getPositions() {
  const res = await fetch(`${API_BASE}/positions`)
  return res.json()
}

export async function getDecisions() {
  const res = await fetch(`${API_BASE}/decisions`)
  return res.json()
}

export async function getBalance() {
  const res = await fetch(`${API_BASE}/balance`)
  return res.json()
}

export async function getHtxBalance() {
  const res = await fetch(`${API_BASE}/htx-balance`)
  return res.json()
}

export async function getEquity() {
  const res = await fetch(`${API_BASE}/equity`)
  return res.json()
}

export async function getMetrics() {
  const res = await fetch(`${API_BASE}/metrics`)
  return res.json()
}

export async function getIndicators() {
  const res = await fetch(`${API_BASE}/indicators`)
  return res.json()
}

export async function forceTrade(strategy = null, direction = "BUY") {
  const res = await fetch(`${API_BASE}/force-trade`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ direction })
  })
  return res.json()
}