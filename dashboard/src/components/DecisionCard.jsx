export default function DecisionCard({decision}){

if(!decision){

return null

}

return(

<div className="bg-white border border-gray-200 rounded-2xl p-4">

<div className="text-sm text-gray-500">

AI Decision

</div>


<div className="text-lg font-medium mt-1">

{decision.decision}

</div>


<div className="text-sm text-gray-500 mt-2">

Confidence: {decision.confidence}

</div>


<p className="text-sm mt-2">

{decision.reasoning}

</p>


</div>

)

}