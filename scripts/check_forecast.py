"""Recompute the dashboard's headline forecast figures from the CSVs (reference check)."""
import csv, os, collections
D = os.path.join(os.path.dirname(__file__), "..", "data")
r = lambda f: list(csv.DictReader(open(os.path.join(D, f))))
deals, quotas, probs = r("crm_deals.csv"), r("sheets_sales_quotas.csv"), r("sheets_stage_probabilities.csv")
p = {x["stage"]: float(x["probability"]) for x in probs}
cat = {x["stage"]: x["forecast_category"] for x in probs}
won = [d for d in deals if d["stage"] == "Closed Won"]
openq = [d for d in deals if d["stage"] in p]
as_of = deals[0]["snapshot_date"]
last_full = f"{as_of[:4]}-{int(as_of[5:7]) - 1:02d}"
fy_quota = sum(int(q["quota_eur"]) for q in quotas)
ytd_quota = sum(int(q["quota_eur"]) for q in quotas if q["month"] <= last_full)
won_ytd_full = sum(int(d["amount_eur"]) for d in won if d["close_date"][:7] <= last_full)
won_fy = sum(int(d["amount_eur"]) for d in won if d["close_date"][:4] == "2026")
open_fy = [d for d in openq if d["close_date"][:4] == "2026"]
weighted = sum(int(d["amount_eur"]) * p[d["stage"]] for d in open_fy)
q4 = lambda d: d["close_date"] >= "2026-10-01" and d["close_date"] <= "2026-12-31"
q4_quota = sum(int(q["quota_eur"]) for q in quotas if q["month"] >= "2026-10")
q4_closed = sum(int(d["amount_eur"]) for d in won if q4(d))
commit = sum(int(d["amount_eur"]) for d in open_fy if cat[d["stage"]] == "Commit")
best = commit + sum(int(d["amount_eur"]) for d in open_fy if cat[d["stage"]] == "Best Case")
pipe = sum(int(d["amount_eur"]) for d in open_fy)
print("as_of", as_of, "last full month", last_full)
print("FY quota", fy_quota, "| closed FY", won_fy, "| weighted open", round(weighted), "| FY forecast", round(won_fy + weighted), f"{(won_fy + weighted) / fy_quota:.1%}")
print("YTD (to", last_full, ") won", won_ytd_full, "quota", ytd_quota, f"{won_ytd_full / ytd_quota:.1%}")
print("Q4 quota", q4_quota, "closed", q4_closed, "commit", commit, "best", best, "pipeline", pipe,
      "forecast", round(q4_closed + weighted), f"{(q4_closed + weighted) / q4_quota:.1%}",
      "coverage", round(pipe / (q4_quota - q4_closed), 2))
print("\nRep: YTD att | Q4 forecast att | coverage")
for rep in sorted({d["owner"] for d in deals}):
    yq = sum(int(q["quota_eur"]) for q in quotas if q["owner"] == rep and q["month"] <= last_full)
    yw = sum(int(d["amount_eur"]) for d in won if d["owner"] == rep and d["close_date"][:7] <= last_full)
    qq = sum(int(q["quota_eur"]) for q in quotas if q["owner"] == rep and q["month"] >= "2026-10")
    qc = sum(int(d["amount_eur"]) for d in won if d["owner"] == rep and q4(d))
    qw = sum(int(d["amount_eur"]) * p[d["stage"]] for d in open_fy if d["owner"] == rep)
    qp = sum(int(d["amount_eur"]) for d in open_fy if d["owner"] == rep)
    print(f"  {rep:13} {yw / yq:6.1%} | {(qc + qw) / qq:6.1%} | {qp / (qq - qc):.2f}x")
