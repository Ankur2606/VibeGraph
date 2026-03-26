import requests
import json
import time

URL = "http://localhost:8000/api/chat"

# Production-level O2C Queries
QUERIES = [
    "What is the total number of sales orders grouped by their transaction currency?",
    "Which customer has the highest total net amount across all their sales orders?",
    "Calculate the average amount made in INR payments that were cleared after April 2025.",
    "Are there any billing documents that have been cancelled? If so, count them.",
    "List the top 3 shipping points with the highest number of outbound deliveries.",
    "What is the total volume and gross weight of all outbound delivery items?"
]

print("=== O2C Graph Intelligence Chat Agent Benchmark ===")
print("Sending queries to evaluate domain efficiency & SQL generation...\n")

with open("./benchmark_results.log", "w", encoding="utf-8") as f:
    f.write("=== O2C Graph Intelligence Chat Agent Benchmark ===\n\n")
    for i, q in enumerate(QUERIES, 1):
        f.write(f"[{i}/{len(QUERIES)}] Query: {q}\n")
        start_time = time.time()
        
        try:
            resp = requests.post(URL, json={"message": q})
            resp.raise_for_status()
            data = resp.json()
            
            elapsed = time.time() - start_time
            answer = data.get("answer", "")
            code = data.get("code", "")
            code_type = data.get("code_type", "")
            
            f.write(f"  Answer: {answer}\n")
            if code:
                f.write(f"  Code ({code_type}):\n    {code.replace(chr(10), chr(10)+'    ')}\n")
            f.write(f"  Speed:  {elapsed:.2f}s\n")
            f.write("-" * 50 + "\n")
            
        except Exception as e:
            f.write(f"  Error: {e}\n")
            f.write("-" * 50 + "\n")

print("Done. Results saved to benchmark_results.log")
