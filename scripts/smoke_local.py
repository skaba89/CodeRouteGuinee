import json
import os
import sys
import urllib.error
import urllib.request

BASE_URL = os.getenv("CODEROUTE_API_URL", "http://127.0.0.1:8000")
FRONTEND_URL = os.getenv("CODEROUTE_FRONTEND_URL")
BOOKING_REFERENCE = os.getenv("CODEROUTE_BOOKING_REFERENCE", "CRG-BOOK-DEMO-001")
VERIFICATION_CODE = os.getenv("CODEROUTE_VERIFICATION_CODE", "CRG-VERIFY-DEMO-001")
CENTER_CODE = os.getenv("CODEROUTE_CENTER_CODE", "CRG-CONAKRY-001")


def call_http(method, url, payload=None):
    headers = {}
    data = None
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=10) as response:
        return response.status, response.headers, response.read()


def call_api(method, path, payload=None):
    _, headers, raw = call_http(method, f"{BASE_URL}{path}", payload)
    if not raw:
        return None
    if headers.get("Content-Type", "").startswith("application/json"):
        return json.loads(raw.decode("utf-8"))
    return raw.decode("utf-8")


def check(condition, message):
    if not condition:
        raise AssertionError(message)
    print(f"OK - {message}")


def main():
    print("CodeRoute Guinee - smoke test local")
    health = call_api("GET", "/health")
    check(health.get("status") == "ok", "API health")

    readiness = call_api("GET", "/health/readiness")
    check(readiness.get("status") in {"ready", "degraded"}, "readiness disponible")
    check(readiness.get("checks", {}).get("database", {}).get("status") == "ok", "readiness base de donnees")
    check(readiness.get("checks", {}).get("schema", {}).get("status") == "ok", "readiness schema critique")

    dashboard = call_api("GET", "/api/v1/dashboard")
    check(dashboard.get("candidates", 0) >= 1, "dashboard candidats")
    check(dashboard.get("accredited_centers", 0) >= 1, "dashboard centres")

    convocation = call_api("GET", f"/api/v1/bookings/{BOOKING_REFERENCE}/convocation")
    check(convocation.get("booking", {}).get("reference") == BOOKING_REFERENCE, "convocation disponible")

    pdf_status, pdf_headers, pdf_content = call_http("GET", f"{BASE_URL}/api/v1/documents/convocations/{BOOKING_REFERENCE}.pdf")
    check(pdf_status == 200, "convocation PDF status")
    check(pdf_headers.get("Content-Type", "").startswith("application/pdf"), "convocation PDF type")
    check(pdf_content.startswith(b"%PDF"), "convocation PDF contenu")

    payment = call_api("POST", "/api/v1/payments", {
        "booking_reference": BOOKING_REFERENCE,
        "amount_gnf": 250000,
        "provider": "orange_money",
        "phone": "+224620000001",
    })
    check(payment.get("status") in {"paid", "pending"}, "paiement sandbox")

    entry = call_api("POST", "/api/v1/entries/validate", {
        "reference": BOOKING_REFERENCE,
        "verification_code": VERIFICATION_CODE,
        "center_code": CENTER_CODE,
    })
    check("allowed" in entry, "validation entree centre")

    exam_summary = call_api("GET", "/api/v1/exams/summary")
    check(exam_summary.get("total_attempts", 0) >= 1, "resume examen")

    if FRONTEND_URL:
        frontend_status, _, frontend_content = call_http("GET", FRONTEND_URL)
        check(frontend_status == 200, "frontend disponible")
        check(b"CodeRoute" in frontend_content or b"root" in frontend_content, "frontend contenu")

    print("Smoke test local termine avec succes")


if __name__ == "__main__":
    try:
        main()
    except (AssertionError, urllib.error.HTTPError, urllib.error.URLError) as exc:
        print(f"Smoke test local echoue: {exc}", file=sys.stderr)
        raise SystemExit(1)
