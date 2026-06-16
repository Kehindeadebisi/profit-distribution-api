# calculate_distribution.py
from fastapi import FastAPI
from pydantic import BaseModel
from typing import List
import httpx
import os
from fastapi.responses import Response
from weasyprint import HTML
from jinja2 import Template


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
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {os.environ['GROQ_API_KEY']}",
                "Content-Type": "application/json"
            },
            json={
                "model": "llama-3.1-8b-instant",
                "messages": [
                    {"role": "user", "content": prompt}
                ],
                "max_tokens": 500,
                "temperature": 0.7
            }
        )

    if response.status_code != 200:
        return {
            "error": f"Groq API error: {response.status_code}",
            "detail": response.text
        }

    result = response.json()

    try:
        summary_text = result["choices"][0]["message"]["content"]
    except (KeyError, IndexError):
        return {
            "error": "Could not parse Groq response",
            "raw": result
        }

    return {"summary": summary_text}

REPORT_TEMPLATE = """
<!DOCTYPE html><html><head>
<style>
  body { font-family: Arial, sans-serif; padding: 48px; color: #1a1a1a; }
  h1 { color: #1a3a2a; border-bottom: 3px solid #b8963e; padding-bottom: 12px; }
  .ai-summary { background: #f9f6f0; padding: 20px 24px; 
                border-left: 4px solid #b8963e; margin: 24px 0; line-height: 1.7; }
  table { width: 100%; border-collapse: collapse; margin-top: 24px; }
  th { background: #1a3a2a; color: white; padding: 12px; text-align: left; }
  td { padding: 10px 12px; border-bottom: 1px solid #e0d8c8; }
  tr:nth-child(even) { background: #faf8f4; }
  .footer { margin-top: 48px; font-size: 11px; color: #999; border-top: 1px solid #e0d8c8; padding-top: 12px; }
</style></head><body>
  <h1>Profit Distribution Notice</h1>
  <p><strong>Period:</strong> {{ period }} &nbsp;|&nbsp; 
     <strong>Total Pool:</strong> ₦{{ "{:,.0f}".format(total_profit_pool) }}</p>
  <div class="ai-summary">{{ ai_summary }}</div>
  <table>
    <tr><th>Member</th><th>Contribution</th><th>Share</th><th>Profit Amount</th></tr>
    {% for d in distributions %}
    <tr>
      <td>{{ d.name }}</td>
      <td>₦{{ "{:,.0f}".format(d.contribution) }}</td>
      <td>{{ d.percentage }}%</td>
      <td><strong>₦{{ "{:,.2f}".format(d.profit_share) }}</strong></td>
    </tr>
    {% endfor %}
  </table>
  <div class="footer">Auto-generated | {{ period }} | Barakallahu feekum</div>
</body></html>
"""

@app.post("/generate-pdf")
def generate_pdf(data: dict):
    html = Template(REPORT_TEMPLATE).render(**data)
    pdf_bytes = HTML(string=html).write_pdf()
    return Response(content=pdf_bytes, media_type="application/pdf",
                    headers={"Content-Disposition": f"attachment; filename=distribution_{data['period']}.pdf"})