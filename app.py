import os
import json
from datetime import date

from dotenv import load_dotenv
load_dotenv()

import anthropic
from flask import Flask, request

from memory import load_history, save_history

app = Flask(__name__)

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
DEFAULT_MODEL = os.environ.get("CLAUDE_MODEL", "claude-haiku-4-5-20251001")
DAILY_LIMIT = int(os.environ.get("DAILY_LIMIT", "200"))

# Rate limit storage dir
RATE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ratelimits")

# Load built-in system prompt from file
_prompt_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "system_prompt.txt")
with open(_prompt_path, "r") as _f:
    BUILTIN_SYSTEM_PROMPT = _f.read().strip()


def _get_usage(username):
    os.makedirs(RATE_DIR, exist_ok=True)
    path = os.path.join(RATE_DIR, f"{username}.json")
    if os.path.exists(path):
        with open(path, "r") as f:
            data = json.load(f)
        if data.get("date") == str(date.today()):
            return data.get("count", 0)
    return 0


def _increment_usage(username):
    os.makedirs(RATE_DIR, exist_ok=True)
    path = os.path.join(RATE_DIR, f"{username}.json")
    today = str(date.today())
    count = _get_usage(username) + 1
    with open(path, "w") as f:
        json.dump({"date": today, "count": count}, f)
    return count


@app.route("/")
def chat():
    content = request.args.get("content")
    if not content:
        return "Missing 'content' parameter", 400

    username = request.args.get("username", "default")
    system = request.args.get("system")
    use_builtin = request.args.get("builtin", "true").lower() not in ("false", "0", "no", "off")
    model = request.args.get("model", DEFAULT_MODEL)

    # Rate limit check
    usage = _get_usage(username)
    if usage >= DAILY_LIMIT:
        return f"Rate limit: {username} has used {usage}/{DAILY_LIMIT} requests today. Resets at midnight.", 429

    # Load existing chat history
    history = load_history(username)

    # Build system prompt
    sys_content = None
    if use_builtin:
        sys_content = BUILTIN_SYSTEM_PROMPT
        if system:
            sys_content += "\n\n" + system
    elif system:
        sys_content = system

    # Build messages (Claude API uses separate system param)
    messages = []
    messages.extend(history)
    messages.append({"role": "user", "content": content})

    # Call Claude
    try:
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        kwargs = {
            "model": model,
            "max_tokens": 4096,
            "messages": messages,
        }
        if sys_content:
            kwargs["system"] = sys_content
        resp = client.messages.create(**kwargs)
        reply = resp.content[0].text
    except anthropic.APIError as e:
        return f"Claude error: {e}", 502

    # Increment usage after successful response
    _increment_usage(username)

    # Save updated history
    history.append({"role": "user", "content": content})
    history.append({"role": "assistant", "content": reply})
    save_history(username, history)

    return reply, 200, {"Content-Type": "text/plain; charset=utf-8"}


@app.route("/usage")
def usage():
    username = request.args.get("username", "default")
    used = _get_usage(username)
    remaining = max(0, DAILY_LIMIT - used)
    return f"{username}: {used}/{DAILY_LIMIT} used, {remaining} remaining", 200, {"Content-Type": "text/plain; charset=utf-8"}


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
