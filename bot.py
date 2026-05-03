import os
import time
import uuid
from datetime import datetime
from flask import Flask, request, jsonify

app = Flask(__name__)
START_TIME = time.time()

contexts = {}
conversations = {}
suppression_log = set()

# ---------------- SMART MESSAGE ENGINE ---------------- #

def compose_message(category, merchant, trigger, customer=None):
    name = merchant.get("identity", {}).get("name", "Merchant")
    category_name = category.get("display_name", "business")
    trigger_kind = trigger.get("kind", "update")

    performance = merchant.get("performance", {})
    views = performance.get("views", 0)
    ctr = performance.get("ctr", 0)

    signals = merchant.get("signals", [])

    # 🔥 PRIORITY 1: PERFORMANCE ISSUE
    if ctr < 2 and views > 50:
        return {
            "body": f"Hi {name}, you’re getting {views} views but only {ctr}% CTR. A strong offer can boost conversions quickly. Want me to create one for you?",
            "cta": "binary_yes_stop",
            "send_as": "vera",
            "suppression_key": f"{trigger_kind}_low_ctr",
            "rationale": "Detected low CTR vs views → conversion optimization"
        }

    # 🔥 PRIORITY 2: INACTIVE CUSTOMERS
    if trigger_kind == "inactive_customer":
        return {
            "body": f"Hi {name}, some of your regular customers haven’t visited recently. A comeback offer like '20% off next visit' can bring them back fast. Shall I set it up?",
            "cta": "binary_yes_stop",
            "send_as": "vera",
            "suppression_key": "inactive_users",
            "rationale": "Customer reactivation strategy"
        }

    # 🔥 PRIORITY 3: PERFORMANCE DROP
    if trigger_kind == "performance_drop":
        return {
            "body": f"Hi {name}, your performance dropped recently. Nearby competitors are using limited-time deals to recover traffic. Want help launching one?",
            "cta": "binary_yes_stop",
            "send_as": "vera",
            "suppression_key": "performance_drop",
            "rationale": "Competitive recovery strategy"
        }

    # 🔥 PRIORITY 4: CATEGORY INTELLIGENCE
    if "salon" in category_name.lower():
        return {
            "body": f"Hi {name}, salons nearby offering 'Haircut @ ₹99' are seeing more bookings. Want to try a similar high-conversion offer?",
            "cta": "open_ended",
            "send_as": "vera",
            "suppression_key": "salon_strategy",
            "rationale": "Category-based optimization"
        }

    if "food" in category_name.lower():
        return {
            "body": f"Hi {name}, food outlets are increasing orders using combo deals and limited-time offers. Want me to create a combo strategy for you?",
            "cta": "open_ended",
            "send_as": "vera",
            "suppression_key": "food_strategy",
            "rationale": "Food category growth tactic"
        }

    # 🔥 PRIORITY 5: SIGNAL-BASED LOGIC
    if signals:
        return {
            "body": f"Hi {name}, based on recent activity signals, there’s a strong opportunity to improve your customer engagement. Want a quick strategy?",
            "cta": "open_ended",
            "send_as": "vera",
            "suppression_key": "signal_based",
            "rationale": "Using merchant signals"
        }

    # 🔥 DEFAULT SMART MESSAGE
    return {
        "body": f"Hi {name}, I found a simple way to improve your performance in {category_name}. It can increase visibility and conversions quickly. Want to try?",
        "cta": "open_ended",
        "send_as": "vera",
        "suppression_key": "default",
        "rationale": "General optimization"
    }


# ---------------- SMART REPLY ENGINE ---------------- #

def compose_reply(conversation_id, merchant_id, customer_id, from_role, message, turn_number):
    msg = message.lower()

    if any(x in msg for x in ["yes", "ok", "haan", "sure", "go ahead"]):
        return {
            "action": "send",
            "body": "Awesome! I’ll create and activate this for you right away 🚀 You should start seeing better results soon.",
            "cta": "none",
            "rationale": "User accepted → action mode"
        }

    if any(x in msg for x in ["no", "stop", "not interested"]):
        return {
            "action": "end",
            "rationale": "User declined"
        }

    if "how" in msg or "what" in msg:
        return {
            "action": "send",
            "body": "I analyze your performance and customer trends, then suggest actions that increase visibility and conversions 📈",
            "cta": "none",
            "rationale": "Explaining capability"
        }

    if "price" in msg or "cost" in msg:
        return {
            "action": "send",
            "body": "Most optimizations are low-cost and designed to maximize your ROI. I’ll make sure it benefits your business 👍",
            "cta": "none",
            "rationale": "Handling pricing concern"
        }

    return {
        "action": "send",
        "body": "Got it 👍 I’ll optimize this to improve your results.",
        "cta": "none",
        "rationale": "Default smart reply"
    }


# ---------------- ENDPOINTS ---------------- #

@app.route("/v1/healthz", methods=["GET"])
def healthz():
    counts = {"category": 0, "merchant": 0, "customer": 0, "trigger": 0}
    for (scope, _) in contexts:
        counts[scope] = counts.get(scope, 0) + 1

    return jsonify({
        "status": "ok",
        "uptime_seconds": int(time.time() - START_TIME),
        "contexts_loaded": counts
    })


@app.route("/v1/metadata", methods=["GET"])
def metadata():
    return jsonify({
        "team_name": "Kruthika",
        "model": "intelligent-rule-engine",
        "approach": "Context-aware decision engine using performance, triggers, and category intelligence",
        "version": "2.0"
    })


@app.route("/v1/context", methods=["POST"])
def push_context():
    body = request.get_json(force=True)

    key = (body.get("scope"), body.get("context_id"))
    contexts[key] = {"version": body.get("version", 1), "payload": body.get("payload", {})}

    return jsonify({"accepted": True})


@app.route("/v1/tick", methods=["POST"])
def tick():
    body = request.get_json(force=True)
    triggers = body.get("available_triggers", [])

    actions = []

    for trg_id in triggers:
        trg = contexts.get(("trigger", trg_id), {}).get("payload", {})
        merchant_id = trg.get("merchant_id")

        merchant = contexts.get(("merchant", merchant_id), {}).get("payload", {})
        category = contexts.get(("category", merchant.get("category_slug", "")), {}).get("payload", {})

        result = compose_message(category, merchant, trg)

        actions.append({
            "conversation_id": f"conv_{merchant_id}_{trg_id}",
            "merchant_id": merchant_id,
            "send_as": result["send_as"],
            "trigger_id": trg_id,
            "body": result["body"],
            "cta": result["cta"],
            "suppression_key": result["suppression_key"],
            "rationale": result["rationale"]
        })

    return jsonify({"actions": actions})


@app.route("/v1/reply", methods=["POST"])
def reply():
    body = request.get_json(force=True)

    result = compose_reply(
        body.get("conversation_id"),
        body.get("merchant_id"),
        body.get("customer_id"),
        body.get("from_role"),
        body.get("message", ""),
        body.get("turn_number", 1)
    )

    return jsonify(result)


@app.route("/v1/teardown", methods=["POST"])
def teardown():
    contexts.clear()
    conversations.clear()
    suppression_log.clear()
    return jsonify({"status": "reset"})


@app.route("/")
def home():
    return "Vera AI Bot is running 🚀"


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
