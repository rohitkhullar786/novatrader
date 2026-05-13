export default function ReadmeCard(){

return(

<div className="text-sm text-gray-600">

<h3 className="font-semibold mb-2">

NovaTrader Backtest Benchmark

</h3>


<p className="leading-relaxed">

This benchmark evaluates how the trading copilot performs vs buy and hold BTC.

</p>


<h4 className="mt-4 font-medium text-sm">

The contestants

</h4>


<ul className="mt-2 space-y-1">

<li className="flex items-center gap-2">

<span className="w-1.5 h-1.5 bg-gray-400 rounded-full"></span>

AI Trading Copilot

</li>

<li className="flex items-center gap-2">

<span className="w-1.5 h-1.5 bg-gray-400 rounded-full"></span>

Buy and Hold BTC

</li>

</ul>


</div>

)

}