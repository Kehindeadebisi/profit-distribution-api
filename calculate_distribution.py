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
        "total_contributions": total_contributions,
        "distributions": distributions
    }

@app.post("/summarise")
async def generate_summary(data: dict):
    prompt = f"""You are writing a formal profit distribution notice for an Islamic investment 
cooperative. Write a clear, professional 2-paragraph summary of the quarterly distribution 
below. Use respectful language appropriate for a Muslim financial institution. 
Note that distributions are calculated proportionally per member contribution (mudarabah). 
Do not use interest-related language.

Distribution data:
Period: {data['period']}
Total Profit Pool: {data['total_profit_pool']}
Investor Share ({data['investor_ratio']*100}%): {data['investor_profit']}
Number of members: {len(data['distributions'])}
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

    result = response.json()
    summary_text = result["candidates"][0]["content"]["parts"][0]["text"]
    return {"summary": summary_text}