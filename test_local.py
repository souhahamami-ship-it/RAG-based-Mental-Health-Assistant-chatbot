"""
Local smoke test against a REAL running server.

Prerequisite: `uvicorn main:app --reload` is already running in another
terminal, on http://127.0.0.1:8000. This script does NOT mock anything --
it makes real HTTP requests, which will call your real Groq API key.

Usage:
    pip install requests   (if you don't already have it)
    python test_local.py
"""

import requests

BASE_URL = "http://127.0.0.1:8000"


def check(label: str, condition: bool, extra: str = "") -> None:
    status = "PASS" if condition else "FAIL"
    print(f"[{status}] {label}" + (f" -- {extra}" if extra else ""))


def main() -> None:
    print("=== /health ===")
    r = requests.get(f"{BASE_URL}/health")
    print(r.status_code, r.json())
    check("server is reachable", r.status_code == 200)
    check("knowledge base has chunks", r.json().get("knowledge_chunks", 0) > 0)

    print("\n=== normal chat, session A ===")
    r = requests.post(f"{BASE_URL}/chat", json={"session_id": "local-test-A", "message": "I've been feeling anxious lately"})
    print(r.status_code, r.json())
    check("normal chat returns 200", r.status_code == 200)
    check("not blocked", r.json().get("blocked") is False)

    print("\n=== crisis message, session A (this should NOT reach Groq) ===")
    r = requests.post(f"{BASE_URL}/chat", json={"session_id": "local-test-A", "message": "I want to kill myself"})
    print(r.status_code, r.json())
    check("crisis message returns 200", r.status_code == 200)
    check("session is now blocked", r.json().get("blocked") is True)

    print("\n=== follow-up on now-blocked session A ===")
    r = requests.post(f"{BASE_URL}/chat", json={"session_id": "local-test-A", "message": "hello?"})
    print(r.status_code, r.json())
    check("still blocked on same session", r.json().get("blocked") is True)

    print("\n=== brand new session B (must NOT be blocked) ===")
    r = requests.post(f"{BASE_URL}/chat", json={"session_id": "local-test-B", "message": "hi, different conversation"})
    print(r.status_code, r.json())
    check("new session is NOT blocked", r.json().get("blocked") is False,
          "if this fails, blocking is leaking across sessions -- serious bug")

    print("\n=== validation: empty message rejected ===")
    r = requests.post(f"{BASE_URL}/chat", json={"session_id": "local-test-C", "message": ""})
    print(r.status_code, r.json())
    check("empty message rejected with 422", r.status_code == 422)

    print("\n=== /health again -- active_sessions should be 2 (A and B) ===")
    r = requests.get(f"{BASE_URL}/health")
    print(r.status_code, r.json())
    # NOT 3: the rejected empty-message request for session "local-test-C"
    # never reached session_store.get_or_create() at all -- Pydantic's
    # validation (Field(min_length=1)) rejects it before the route body
    # runs, so no SessionRecord is ever created for it. That's correct
    # behavior, not a bug -- this check was wrong in the previous version.
    check("two sessions tracked (A and B; C was rejected before creation)",
          r.json().get("active_sessions") == 2)


if __name__ == "__main__":
    main()