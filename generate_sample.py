"""Generate sample_data.csv for demo purposes."""

import random
from datetime import date, timedelta

import pandas as pd

random.seed(42)
n = 200
start = date(2024, 1, 1)

data = {
    "date": [(start + timedelta(days=i)).isoformat() for i in range(n)],
    "region": [random.choice(["North", "South", "East", "West"]) for _ in range(n)],
    "product": [random.choice(["Pro", "Starter", "Enterprise", "Add-on"]) for _ in range(n)],
    "revenue": [round(random.uniform(50, 2000), 2) for _ in range(n)],
    "orders": [random.randint(1, 50) for _ in range(n)],
    "users": [random.randint(10, 500) for _ in range(n)],
    "churn_rate": [round(random.uniform(0.01, 0.15), 4) for _ in range(n)],
}

df = pd.DataFrame(data)
df.to_csv("sample_data.csv", index=False)
print(f"sample_data.csv created with {n} rows.")
