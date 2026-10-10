"""Generate the simulated source data for the Lumen Labs sales forecast dashboard.

Every file stands in for a real system:
  crm_deals.csv                 CRM (e.g. HubSpot) deal export
  sheets_sales_quotas.csv       Google Sheets: monthly quota per rep
  sheets_stage_probabilities.csv Google Sheets: forecast assumptions per stage
  sheets_mrr_plan.csv           Google Sheets: finance MRR plan
  warehouse_mrr.csv             Data warehouse: monthly MRR movements

Run:  python scripts/generate_data.py   (writes into ./data)
The data is "as of" 2026-10-10: deals closed up to that date, open deals expected later.
"""
import csv
import datetime as dt
import os
import random

random.seed(7)
OUT = os.path.join(os.path.dirname(__file__), "..", "data")
os.makedirs(OUT, exist_ok=True)

AS_OF = dt.date(2026, 10, 10)
MONTHS = [f"2026-{m:02d}" for m in range(1, 13)]
REPS = {  # owner: (region, base monthly quota, how well they perform vs quota)
    "A. Becker": ("DACH", 70000, 1.08),
    "J. Sørensen": ("Nordics", 60000, 0.97),
    "M. Dubois": ("Benelux", 55000, 0.78),
    "L. Okafor": ("UK & Ireland", 65000, 0.92),
    "S. Vermeulen": ("Benelux", 50000, 1.15),
}
SEASON = {1: .85, 2: .9, 3: 1.05, 4: .95, 5: 1.0, 6: 1.1, 7: .85, 8: .8, 9: 1.1, 10: 1.05, 11: 1.15, 12: 1.3}
CHANNELS = ["Paid Search", "LinkedIn Ads", "Content/SEO", "Events", "Referral", "Outbound"]
SIZES = [6000, 9000, 12000, 18000, 24000, 36000, 48000, 60000]
STAGES = [  # stage, probability, forecast category
    ("Discovery", 0.10, "Pipeline"),
    ("Demo", 0.25, "Pipeline"),
    ("Proposal", 0.50, "Best Case"),
    ("Negotiation", 0.80, "Commit"),
]


def rand_day(year, month, lo=1, hi=28):
    return dt.date(year, month, random.randint(lo, hi))


def write(name, header, rows):
    with open(os.path.join(OUT, name), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)


# --- Google Sheets: quotas and stage assumptions ---
quotas = []
for m in range(1, 13):
    for rep, (_, base, _) in REPS.items():
        quotas.append([MONTHS[m - 1], rep, round(base * SEASON[m] / 1000) * 1000])
write("sheets_sales_quotas.csv", ["month", "owner", "quota_eur"], quotas)
write("sheets_stage_probabilities.csv", ["stage", "probability", "forecast_category"], STAGES)
quota_of = {(q[0], q[1]): q[2] for q in quotas}

# --- CRM deals ---
deals = []
n = 0


def add(owner, stage, amount, created, close):
    global n
    n += 1
    deals.append([f"D-{2000 + n}", owner, REPS[owner][0], random.choice(CHANNELS), stage, amount,
                  created.isoformat(), close.isoformat(), AS_OF.isoformat()])


for rep, (_, _, perf) in REPS.items():
    # Closed deals Jan–Sep: won value tracks quota x performance, with noise
    for m in range(1, 10):
        target = quota_of[(MONTHS[m - 1], rep)] * perf * random.uniform(.55, .95)
        won = 0
        while won < target:
            amt = random.choice(SIZES)
            close = rand_day(2026, m)
            add(rep, "Closed Won", amt, close - dt.timedelta(days=random.randint(30, 110)), close)
            won += amt
        for _ in range(random.randint(2, 5)):
            close = rand_day(2026, m)
            add(rep, "Closed Lost", random.choice(SIZES), close - dt.timedelta(days=random.randint(25, 100)), close)
    # Early October wins (month to date)
    for _ in range(random.randint(0, 2)):
        close = rand_day(2026, 10, 1, AS_OF.day)
        add(rep, "Closed Won", random.choice(SIZES), close - dt.timedelta(days=random.randint(30, 90)), close)
    # Open pipeline, expected to close Oct 2026 – Feb 2027
    for _ in range(random.randint(17, 23)):
        stage = random.choices([s[0] for s in STAGES], [30, 28, 24, 18])[0]
        y, mm = random.choices([(2026, 10), (2026, 11), (2026, 12), (2027, 1), (2027, 2)], [24, 28, 26, 14, 8])[0]
        lo = AS_OF.day + 1 if (y, mm) == (2026, 10) else 1
        close = rand_day(y, mm, lo, 28)
        created = AS_OF - dt.timedelta(days=random.randint(5, 120))
        add(rep, stage, int(random.choice(SIZES) * (1.4 if perf < .9 else 1) // 1000 * 1000), created, close)

deals.sort(key=lambda d: d[0])
write("crm_deals.csv", ["deal_id", "owner", "region", "source_channel", "stage", "amount_eur",
                        "created_date", "close_date", "snapshot_date"], deals)

# --- Finance plan and warehouse MRR ---
write("sheets_mrr_plan.csv", ["month", "mrr_plan_eur"], [[m, 180000 + i * 9000] for i, m in enumerate(MONTHS)])
rows, mrr, cust = [], 176000, 412
for m in MONTHS[:9]:
    new, exp, churn = random.randint(9000, 15000), random.randint(3000, 7000), random.randint(4000, 8500)
    end = mrr + new + exp - churn
    cust += random.randint(8, 18)
    rows.append([m, mrr, new, exp, churn, end, cust])
    mrr = end
write("warehouse_mrr.csv", ["month", "starting_mrr_eur", "new_mrr_eur", "expansion_mrr_eur",
                            "churned_mrr_eur", "ending_mrr_eur", "paying_customers"], rows)
print(f"Wrote {len(deals)} deals and 4 other files to {os.path.abspath(OUT)}")
