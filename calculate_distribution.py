# calculate_distribution.py
from fastapi import FastAPI
from pydantic import BaseModel
from typing import List
import httpx
import os

app = FastAPI()

class Member(BaseModel):
    id: str
    name: str
    email: str
    contribution: float

class SettlementInput(BaseModel):
    members: List[Member]
    profit_pool: float
    investor_ratio: float  # e.g. 0.70 means 70% goes to investors
    period: str

@app.post("/calculate")
def calculate_distribution(data: SettlementInput):
    total_contributions = sum(m.contribution for m in data.members)
    investor_profit = data.profit_pool * data.investor_ratio

    distributions = []
    for member in data.members:
        share = (member.contribution / total_contributions) * investor_profit
        distributions.append({
            "id": member.id,
            "name": member.name,
            "email": member.email,
            "contribution": member.contribution,
            "profit_share": round(share, 2),
            "percentage": round((member.contribution / total_contributions) * 100, 2)
        })

    return {
        "period": data.period,
        "total_profit_pool": data.profit_pool,
        "investor_profit": round(investor_profit, 2),
        "investor_ratio": data.investor_ratio,
        "total_contributions": total_contributions,
        "distributions": distributions
    }


@app.post("/summarise")
async def generate_summary(data: dict):
    # Safely convert all numeric fields — prevents crash if they arrive as strings
    period = str(data.get('period', ''))
    total_profit_pool = float(data.get('total_profit_pool', 0))
    investor_profit = float(data.get('investor_profit', 0))
    investor_ratio = float(data.get('investor_ratio', 0))
    distributions = data.get('distributions', [])

    prompt = f"""You are writing a formal profit distribution notice for an Islamic investment 
cooperative. Write a clear, professional 2-paragraph summary of the quarterly distribution 
below. Use respectful language appropriate for a Muslim financial institution. 
Note that distributions are calculated proportionally per member contribution (mudarabah). 
Do not use interest-related language.

Distribution data:
Period: {period}
Total Profit Pool: ₦{total_profit_pool:,.2f}
Investor Share ({investor_ratio * 100:.0f}%): ₦{investor_profit:,.2f}
Number of members: {len(distributions)}
"""

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={os.environ['GEMINI_API_KEY']}",
            headers={"Content-Type": "application/json"},
            json={
                "contents": [{
                    "parts": [{"text": prompt}]
                }]
            }
        )

    # Check Gemini responded correctly before parsing
    if response.status_code != 200:
        return {
            "error": f"Gemini API error: {response.status_code}",
            "detail": response.text
        }

    result = response.json()

    # Guard against unexpected Gemini response structure
    try:
        summary_text = result["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError) as e:
        return {
            "error": "Could not parse Gemini response",
            "raw": result
        }

    return {"summary": summary_text}