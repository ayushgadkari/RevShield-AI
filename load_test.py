import concurrent.futures
import random
import time
import requests

URL = "http://127.0.0.1:8000/webhook/failure"

errors = [
    ("GATEWAY_TIMEOUT", "Bank server connection dropped"),
    ("INSUFFICIENT_FUNDS", "Account balance too low"),
    ("NETWORK_ERROR", "Socket timeout during TLS handshake"),
]


def send_fake_webhook(i):
  # Sleep briefly to avoid hitting Gemini free-tier rate limits all at once
  time.sleep(i * 1.5)

  code, desc = random.choice(errors)
  payload = {
      "event": "payment.failed",
      "payload": {
          "payment": {
              "entity": {
                  "id": f"pay_stress_test_{i}",
                  "amount": random.randint(1000, 500000),
                  "currency": "INR",
                  "error_code": code,
                  "error_description": desc,
              }
          }
      },
  }
  try:
    response = requests.post(URL, json=payload)
    return response.status_code
  except Exception as e:
    return str(e)


# Run a controlled batch test
print("Running controlled concurrent payment failure simulation...")
with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
  results = list(executor.map(send_fake_webhook, range(10)))

print(f"Simulation completed! Responses: {results}")