"""Synthetic, redistributable observations with a frozen expected result."""

VARIANTS = [
    (True, "The current request failed at DNS resolution before any HTTP response."),
    (True, "The current TCP connection was refused. No HTTP headers arrived."),
    (True, "The current TLS handshake failed before HTTP started."),
    (False, "An older request timed out. The CURRENT attempt received HTTP 200 and a valid body."),
    (False, "HTTP 200 headers arrived; the body was empty."),
    (False, "The upstream returned HTTP 503 after completing TLS."),
    (True, "当前请求在 TLS 建连时失败，尚未收到 HTTP 响应。"),
    (False, "过去发生过 DNS 故障，当前请求已收到 HTTP 200。"),
]
SPEC = {
    "requirements": [
        {
            "id": "establishment",
            "statement": "The CURRENT request fails during DNS, TCP or TLS establishment, not a historical attempt.",
            "expected": True,
        },
        {
            "id": "response",
            "statement": "The CURRENT request received HTTP response headers.",
            "expected": False,
        },
    ]
}
TASK = "Select current connection-establishment failures before any HTTP response. Exclude recovered history and post-response errors."


def fixture(count=96):
    records = [
        {
            "id": f"r{i:03}",
            "source_id": f"r{i:03}",
            "text": f"Service {i}. " + VARIANTS[i % 8][1],
            "source": {},
        }
        for i in range(count)
    ]
    gold = [r["id"] for i, r in enumerate(records) if VARIANTS[i % 8][0]]
    return records, gold
