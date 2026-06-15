# calculate_distribution.py
from fastapi import FastAPI
from pydantic import BaseModel
from typing import List

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