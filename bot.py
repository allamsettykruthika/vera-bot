import os
import time
import uuid
from datetime import datetime
from flask import Flask, request, jsonify

app = Flask(__name__)
START_TIME = time.time()

# In-memory storage
contexts = {}
conversations = {}
suppression_log = set()

# ---------------- SIMPLE LOGIC ---------------- #

def compose_message(category, merchant, trigger, customer=None):
    merchant_name = merchant.get("identity", {}).get("name", "Merchant")
    trigger_kind = trigger.get("kind", "update")

    return {
        "body": f"Hi {merchant_name}, based on your recent {trigger_kind}, we found an opportunity to grow your business. Want to explore?",
        "cta": "open_ended",
        "send_as": "vera",
        "suppression_key": trigger.get("suppression_key", trigger_kind),
        "rationale": "Simple rule-based message"
    }


def compose_reply(conversation_id, merchant_id, customer_id, from_role, message, turn_number):
    msg = message.lower()

    if "yes" in msg or "ok" in msg or "haan" in msg:
        return {
            "action": "send",
            "body": "Great! I’ll set this up for you right away 👍",
            "cta": "none",
            "rationale": "User agreed"
        }

    if "no" in msg or "stop" in msg:
        return {
            "action": "end",
            "rationale": "User not interested"
        }

    return {
        "action": "send",
        "body": "Got it 👍 Let me handle this for you.",
        "cta": "none",
        "rationale": "Default reply"
    }


# ---------------- ENDPOINTS ---------------- #

@app.get("/v1/healthz")
def healthz():
    counts = {"category": 0, "merchant": 0, "customer": 0, "trigger": 0}
    for (scope, _) in contexts:
        counts[scope] = counts.get(scope, 0) + 1

    return jsonify({
        "status": "ok",
        "uptime_seconds": int(time.time() - START_TIME),
        "contexts_loaded": counts
    })


@app.get("/v1/metadata")
def metadata():
    return jsonify({
        "team_name": "Vera Pro",
        "team_members": ["Kruthika"],
        "model": "rule-based",
        "approach": "Lightweight rule-based messaging without external APIs",
        "version": "1.0"
    })


@app.post("/v1/context")
def push_context():
    body = request.get_json(force=True)

    scope = body.get("scope")
    context_id = body.get("context_id")
    version = body.get("version", 1)
    payload = body.get("payload", {})

    key = (scope, context_id)
    existing = contexts.get(key)

    if existing and existing["version"] >= version:
        return jsonify({"accepted": False}), 409

    contexts[key] = {"version": version, "payload": payload}

    return jsonify({
        "accepted": True,
        "ack_id": f"ack_{uuid.uuid4().hex[:6]}"
    })


@app.post("/v1/tick")
def tick():
    body = request.get_json(force=True)
    triggers = body.get("available_triggers", [])

    actions = []

    for trg_id in triggers:
        trg_entry = contexts.get(("trigger", trg_id))
        if not trg_entry:
            continue

        trg = trg_entry["payload"]

        merchant_id = trg.get("merchant_id")
        if not merchant_id:
            continue

        merchant = contexts.get(("merchant", merchant_id), {}).get("payload", {})
        category = contexts.get(("category", merchant.get("category_slug", "")), {}).get("payload", {})

        result = compose_message(category, merchant, trg)

        conv_id = f"conv_{merchant_id}_{trg_id}"

        actions.append({
            "conversation_id": conv_id,
            "merchant_id": merchant_id,
            "send_as": result["send_as"],
            "trigger_id": trg_id,
            "body": result["body"],
            "cta": result["cta"],
            "suppression_key": result["suppression_key"],
            "rationale": result["rationale"]
        })

        conversations.setdefault(conv_id, []).append({
            "from": "vera",
            "msg": result["body"]
        })

    return jsonify({"actions": actions})


@app.post("/v1/reply")
def reply():
    body = request.get_json(force=True)

    conv_id = body.get("conversation_id")
    merchant_id = body.get("merchant_id")
    customer_id = body.get("customer_id")
    message = body.get("message", "")
    turn_number = body.get("turn_number", 1)

    conversations.setdefault(conv_id, []).append({
        "from": "merchant",
        "msg": message
    })

    result = compose_reply(conv_id, merchant_id, customer_id, "merchant", message, turn_number)

    if result.get("action") == "send":
        conversations[conv_id].append({
            "from": "vera",
            "msg": result["body"]
        })

    return jsonify(result)


@app.post("/v1/teardown")
def teardown():
    contexts.clear()
    conversations.clear()
    suppression_log.clear()
    return jsonify({"status": "reset"})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)