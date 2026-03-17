import os
import re
from dotenv import load_dotenv

from slack_bolt import App
from slack_bolt.adapter.flask import SlackRequestHandler
from flask import Flask, request, jsonify

from automation import run_browser

load_dotenv()

bolt_app = App(
    token=os.getenv("SLACK_BOT_TOKEN"),
    signing_secret=os.getenv("SLACK_SIGNING_SECRET")
)

app = Flask(__name__)
handler = SlackRequestHandler(bolt_app)


@app.route("/", methods=["GET"])
def home():
    return "✅ Server is running", 200


@app.route("/slack/events", methods=["POST"])
def slack_events():
    data = request.json

    # ✅ Handle Slack URL verification
    if data and data.get("type") == "url_verification":
        return jsonify({"challenge": data["challenge"]})

    return handler.handle(request)


# ✅ FINAL ROBUST PARSER
def parse_message(text):
    text = text.replace("•", "")
    text = text.strip()

    print("📩 RAW TEXT:\n", text)

    data = {}

    name = re.search(r"Name:\s*(.+)", text)
    phone = re.search(r"Phone:\s*(.+)", text)
    address = re.search(r"Address:\s*(.+)", text)
    customer_id = re.search(r"Customer ID:\s*(.+)", text)

    if name:
        data["name"] = name.group(1).strip()

    if phone:
        data["phone"] = phone.group(1).strip()

    if address:
        data["address"] = address.group(1).strip()

    if customer_id:
        data["customer_id"] = customer_id.group(1).strip()

    print("📦 PARSED DATA:", data)

    return data


@bolt_app.event("message")
def handle_message_events(body, logger):
    print("\n🔥 EVENT RECEIVED 🔥")
    print(body)
    print("====================================\n")

    event = body.get("event", {})

    if "bot_id" in event:
        return

    text = event.get("text", "")

    # fallback for Slack block messages
    if not text and "blocks" in event:
        text = str(event["blocks"])

    parsed = parse_message(text)

    print("🚀 Calling browser automation...")

    run_browser(parsed)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 3000))
    app.run(host="0.0.0.0", port=port)