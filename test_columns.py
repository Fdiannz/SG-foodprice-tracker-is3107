# run this from SG-foodprice-tracker root
import sys
sys.path.append("pipeline/etl")
from load import get_client

client = get_client()
res = client.table("commodity_price_comparisons").select("*").limit(3).execute()
for row in res.data:
    print(row)