import axios from "axios"

export async function loadBTCData() {
  try {
    const res = await axios.get(
      "https://api.coingecko.com/api/v3/coins/bitcoin/market_chart",
      {
        params: {
          vs_currency: "usd",
          days: 120,
          interval: "daily"
        }
      }
    )

    return res.data.prices.map(p => ({
      date: new Date(p[0]).toLocaleDateString("en-US", { month: "short", day: "numeric" }),
      btc: p[1]
    }))
  } catch (e) {
    console.error("Error loading BTC data:", e)
    return []
  }
}
