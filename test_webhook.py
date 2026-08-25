import requests
import json
import time

# Your local FastAPI webhook endpoint
url = "http://127.0.0.1:8000/webhook/failure"
headers = {"Content-Type": "application/json"}

# A list of diverse test cases (Permanent & Recoverable errors)
test_cases = [
    {
        "event": "payment.failed",
        "payload": {
            "payment_id": "pay_test_perm_001",
            "amount": 5400,
            "error_code": "INSUFFICIENT_FUNDS",
            "error_description": "The customer's bank account does not have enough balance to cover the transaction."
        }
    },
    {
        "event": "payment.failed",
        "payload": {
            "payment_id": "pay_test_recov_002",
            "amount": 1200,
            "error_code": "GATEWAY_TIMEOUT",
            "error_description": "Bank network timeout occurred, please retry the transaction safely."
        }
    },
    {
        "event": "payment.failed",
        "payload": {
            "payment_id": "pay_test_perm_003",
            "amount": 15000,
            "error_code": "CARD_BLOCKED",
            "error_description": "Card has been reported lost or blocked by the issuer due to suspected fraud."
        }
    }
]

print("🚀 Sending batch test webhooks to RevShield AI...\n")

for i, test_case in enumerate(test_cases, 1):
    error_code = test_case["payload"]["error_code"]
    print(f"--- Sending Test Case {i}: {error_code} ---")
    
    response = requests.post(url, data=json.dumps(test_case), headers=headers)
    
    print(f"Status Code: {response.status_code}")
    print("Response JSON:")
    try:
        print(json.dumps(response.json(), indent=2))
    except Exception:
        print(response.text)
    
    print("\n" + "="*50 + "\n")
    time.sleep(0.5)  # Short half-second pause between requests

print("✅ All batch test webhooks sent successfully!")