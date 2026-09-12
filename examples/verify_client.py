"""Script demonstrating how Person 4 (Frontend) or Person 2 (Analyzer) calls the API."""

import json
import httpx

BACKEND_URL = "http://127.0.0.1:8000"

def main():
    client = httpx.Client(base_url=BACKEND_URL)

    print("--- 1. Health Check ---")
    r = client.get("/health")
    print("GET /health:", r.status_code, r.json())

    print("\n--- 2. Explain Impact (Person 2 -> Person 3 -> Person 4) ---")
    with open("examples/impact_request.json", "r") as f:
        impact_payload = json.load(f)
    r = client.post("/impact/explain", json=impact_payload)
    print("POST /impact/explain:", r.status_code)
    data = r.json()
    print("  Summary:", data["summary"])
    print("  Risk Level:", data["risk"]["level"], "-", data["risk"]["reason"])
    print("  Root Cause:", data["root_cause"]["file"], ":", data["root_cause"]["line"])
    print("  Direct Impacts:", len(data["direct_impacts"]))
    print("  Claims:", len(data["claims"]))
    print("  Confidence:", data["confidence"])

    print("\n--- 3. Ask Assistant (Person 4 Q&A) ---")
    ask_payload = {
        "question": "Why is payment.py affected by this change?",
        "impact_context": impact_payload,
    }
    r = client.post("/ask", json=ask_payload)
    print("POST /ask:", r.status_code)
    print("  Answer:", r.json()["answer"])

    print("\n--- 4. Safe Fix Proposal (No Assumptions) ---")
    with open("examples/fix_request.json", "r") as f:
        fix_payload = json.load(f)
    r = client.post("/fix/propose", json=fix_payload)
    print("POST /fix/propose:", r.status_code)
    fix_data = r.json()
    print("  Status:", fix_data["status"])
    print("  Diff:")
    print(fix_data["diff"])

if __name__ == "__main__":
    main()
