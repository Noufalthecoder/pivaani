"""
End-to-end workflow test for Pi Vaani (32 checks across all 6 phases).

Runs against a live backend and RESETS its sandbox data, so point it at a
scratch database, never your demo data:

    # terminal 1
    DATABASE_URL=sqlite:///./test.db python -m uvicorn main:app --app-dir ./backend --port 8001
    # terminal 2
    python backend/tests/test_workflow_e2e.py http://localhost:8001

Requires: pip install websockets
"""
import asyncio, json, sys, time, urllib.request, urllib.error, websockets
from concurrent.futures import ThreadPoolExecutor

B = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8001"
WS = B.replace("http", "ws") + "/ws"
FAIL = []
events = []

def call(method, path, body=None):
    req = urllib.request.Request(B + path, data=json.dumps(body).encode() if body is not None else None,
                                 headers={"Content-Type": "application/json"}, method=method)
    try:
        with urllib.request.urlopen(req) as r:
            return r.status, json.loads(r.read() or b"null")
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"{}")

def check(name, cond, info=""):
    print(("  PASS " if cond else "  FAIL ") + name + ("" if cond else f"  -> {info}"))
    if not cond:
        FAIL.append(name)

async def listen():
    async with websockets.connect(WS) as ws:
        while True:
            events.append(json.loads(await ws.recv()))

def take(t, **kw):
    return [e["payload"] for e in events if e.get("type") == t and all(e["payload"].get(k) == v for k, v in kw.items())]

async def wait_for(t, timeout=6, **kw):
    end = time.time() + timeout
    while time.time() < end:
        found = take(t, **kw)
        if found:
            return found[-1]
        await asyncio.sleep(0.1)
    return None

async def new_case(amount=40):
    events.clear()
    _, pay = call("POST", "/api/sandbox/pay", {"amount": amount})
    case = await wait_for("CASE_OPENED")
    return pay, case["case_id"]

async def main():
    asyncio.create_task(listen())
    await asyncio.sleep(0.5)
    _, b = call("GET", "/api/state")
    check("PIN not exposed by /api/state", "\"pin\"" not in json.dumps(b["merchant"]), b["merchant"])

    print("Phase 1-2: pay -> stuck -> case + voices")
    call("POST", "/api/reset")
    call("PATCH", "/api/merchant/dial", {"trust_dial": "balanced"})
    events.clear()
    s, pay = call("POST", "/api/sandbox/pay", {"amount": 40})
    check("pay creates payment (201)", s == 201, s)
    case = await wait_for("CASE_OPENED")
    check("case opened", case is not None)
    cid = case["case_id"]
    pre = await wait_for("GATES_EVALUATED", case_id=cid)
    check("pre-check is HOLD (bank may still settle)", pre and pre["decision"] == "HOLD", pre)
    await asyncio.sleep(3)
    speaks = take("SPEAK", case_id=cid)
    check("2 voices, both name the case", len(speaks) == 2 and all(cid.replace("-", " ") in x["text"] for x in speaks),
          [x["text"] for x in speaks])

    print("Phase 3: retap / duplicate pay")
    with ThreadPoolExecutor(3) as ex:
        rs = [f.result() for f in [ex.submit(call, "POST", "/api/sandbox/pay", {"amount": 40}) for _ in range(3)]]
    check("3 simultaneous re-pays return the ORIGINAL payment", all(r[0] == 200 and r[1]["id"] == pay["id"] for r in rs),
          [(r[0], r[1].get("id")) for r in rs])
    _, st = call("GET", "/api/state")
    check("still exactly 1 payment", len(st["payments"]) == 1, len(st["payments"]))
    g = await wait_for("GATES_EVALUATED", attack_kind="retap")
    check("retap blocked by Idempotency", g and g["blocked_by"] == "Idempotency", g)
    s, _ = call("POST", "/api/sandbox/retap", {"payment_id": pay["id"]})
    check("retap endpoint blocks too", s == 200, s)
    s, _ = call("POST", "/api/approval/challenge", {"case_id": cid})
    check("approval refused while bank pending (409)", s == 409, s)

    print("Phase 4: DEBITED_NOT_CREDITED, Balanced dial -> auto refund")
    events.clear()
    call("POST", f"/api/sandbox/payments/{pay['id']}/state", {"status": "DEBITED_NOT_CREDITED"})
    r = await wait_for("CASE_RESOLVED", case_id=cid)
    check("auto-refunded under Balanced (40 <= 200)", r and r["resolution"] == "REFUNDED", r)
    rc = await wait_for("RECEIPT", case_id=cid)
    check("receipt issued in hi + ta", rc and rc["customer"]["lang"] == "hi-IN" and rc["merchant"]["lang"] == "ta-IN", rc)
    call("POST", f"/api/sandbox/payments/{pay['id']}/state", {"status": "SUCCESS"})
    check("late credit after refund -> reconciliation alert", await wait_for("RECONCILIATION") is not None)

    print("Phase 4b: Careful dial -> approval + PIN, single-use nonce")
    call("PATCH", "/api/merchant/dial", {"trust_dial": "careful"})
    pay2, c2 = await new_case()
    call("POST", f"/api/sandbox/payments/{pay2['id']}/state", {"status": "DEBITED_NOT_CREDITED"})
    check("Careful: approval required", await wait_for("APPROVAL_REQUIRED", case_id=c2) is not None)
    s, ch = call("POST", "/api/approval/challenge", {"case_id": c2})
    check("challenge issues nonce", s == 200 and ch.get("nonce"), ch)
    _, b = call("POST", "/api/approval", {"case_id": c2, "nonce": ch["nonce"], "pin": "0000", "actor": "merchant_voice"})
    check("wrong PIN rejected by Authority", b.get("status") == "REJECTED" and b.get("blocked_by_gate") == "Authority", b)
    _, b = call("POST", "/api/approval", {"case_id": c2, "nonce": ch["nonce"], "pin": "4321", "actor": "merchant_voice"})
    check("reused nonce rejected by Idempotency", b.get("status") == "REJECTED" and b.get("blocked_by_gate") == "Idempotency", b)
    _, ch = call("POST", "/api/approval/challenge", {"case_id": c2})
    _, b = call("POST", "/api/approval", {"case_id": c2, "nonce": ch["nonce"], "pin": "4321", "actor": "customer_voice", "voice_command": "Yes"})
    check("customer voice rejected by Authority", b.get("status") == "REJECTED" and b.get("blocked_by_gate") == "Authority", b)
    _, ch = call("POST", "/api/approval/challenge", {"case_id": c2})
    _, b = call("POST", "/api/approval", {"case_id": c2, "nonce": ch["nonce"], "pin": "4321", "actor": "merchant_voice", "voice_command": "Refund kar do"})
    check("merchant voice + PIN + fresh nonce -> EXECUTED", b.get("status") == "EXECUTED", b)
    s, _ = call("POST", "/api/approval/challenge", {"case_id": c2})
    check("resolved case cannot be approved again (409)", s == 409, s)

    print("Phase 4c: 3 wrong PINs lock the case")
    pay3, c3 = await new_case()
    call("POST", f"/api/sandbox/payments/{pay3['id']}/state", {"status": "FAILED"})
    await wait_for("APPROVAL_REQUIRED", case_id=c3)
    for _ in range(3):
        _, ch = call("POST", "/api/approval/challenge", {"case_id": c3})
        call("POST", "/api/approval", {"case_id": c3, "nonce": ch.get("nonce"), "pin": "1111"})
    r = await wait_for("CASE_RESOLVED", case_id=c3)
    check("case BLOCKED after 3 wrong PINs", r and r["resolution"] == "BLOCKED", r)

    print("Phase 6: bank confirms -> resolved + receipt")
    call("PATCH", "/api/merchant/dial", {"trust_dial": "balanced"})
    pay4, c4 = await new_case()
    call("POST", f"/api/sandbox/payments/{pay4['id']}/state", {"status": "SUCCESS"})
    r = await wait_for("CASE_RESOLVED", case_id=c4)
    check("confirmed", r and r["resolution"] == "CONFIRMED", r)
    check("receipt on confirm", await wait_for("RECEIPT", case_id=c4) is not None)
    s, _ = call("POST", "/api/sandbox/pay", {"amount": 40})
    check("new purchase allowed after resolution (201)", s == 201, s)

    print("Phase 5: attacks")
    expect = {"refund_everything": ("BLOCK", "Authority"), "voice_spoof": ("BLOCK", "Authority"),
              "fraud_ring": ("NEEDS_APPROVAL", "Identity"), "amount_bypass": ("BLOCK", "Amount"),
              "low_confidence": ("BLOCK", "Confidence"), "replay_tap": ("BLOCK", "Idempotency")}
    for k, (d, gate) in expect.items():
        s, b = call("POST", f"/api/attack/{k}?lang=en-IN")
        check(f"attack {k} -> {d} at {gate}", (b.get("decision"), b.get("blocked_by_gate")) == (d, gate),
              (s, b.get("decision"), b.get("blocked_by_gate")))

    print("Fraud ring sim twice (no duplicate-key crash)")
    s1, _ = call("POST", "/api/sandbox/simulate-fraud-ring?customer_vpa=attacker@upi")
    s2, _ = call("POST", "/api/sandbox/simulate-fraud-ring?customer_vpa=attacker@upi")
    check("fraud ring sim runs repeatedly", (s1, s2) == (200, 200), (s1, s2))

    print("Audit")
    _, v = call("GET", "/api/audit/verify")
    check("chain valid + signed head", v.get("valid") and v.get("head_signature"), v)
    ids = [e.get("event_id") for e in events if e.get("event_id")]
    check("event ids unique", len(ids) == len(set(ids)))
    print("\nRESULT:", "ALL PASSED" if not FAIL else f"{len(FAIL)} FAILED: {FAIL}")

asyncio.run(main())
