#!/usr/bin/env python3
"""
Davis chat turn: runs Claude Code against this repository with the message
sent from the phone, saves the reply for the app, and pushes any code changes.
"""

import argparse
import json
import os
import subprocess
import sys
import time

from studio import store

MODEL = "claude-opus-4-8"
HISTORY_TURNS = 12

SYSTEM = """You are Davis, the AI operator of this repository, reached from the owner's phone through the Davis Studio app. This repo holds an automated short-video system: `studio/` is the video engine (analysis, blueprint, rendering), `pipeline/` and `run.py` are the scheduled posting pipeline, `android/` is the Davis Studio app, `.github/workflows/` runs everything on GitHub Actions.

The owner talks to you the way they would talk to Claude Code on a laptop. Do the work they ask for in this checkout: read code, explain, edit files, fix bugs. Your file edits are committed and pushed to main automatically after you finish, so do not run git commit or git push yourself. You cannot edit files under .github/workflows (the push would be rejected); if that is needed, say exactly what to change.

Reply for a phone screen: plain text, short paragraphs, no tables, no long code dumps. Say what you did and what, if anything, the owner must do next."""

ALLOWED_TOOLS = (
    "Read,Edit,Write,Glob,Grep,"
    "Bash(git status:*),Bash(git diff:*),Bash(git log:*),"
    "Bash(ls:*),Bash(python:*),Bash(python3:*)"
)


def _git(args, check=True):
    result = subprocess.run(["git"] + args, capture_output=True, text=True)
    if check and result.returncode != 0:
        raise RuntimeError(result.stderr.strip()[-300:])
    return result


def _build_prompt(messages: list) -> str:
    earlier = messages[:-1][-HISTORY_TURNS:]
    lines = []
    if earlier:
        lines.append("Conversation so far:")
        for m in earlier:
            who = "Owner" if m["role"] == "user" else "Davis"
            lines.append(f"{who}: {m['text']}")
        lines.append("")
    lines.append(f"Owner's new message: {messages[-1]['text']}")
    return "\n".join(lines)


def _run_claude(prompt: str) -> str:
    result = subprocess.run(
        ["claude", "-p", prompt,
         "--model", MODEL,
         "--output-format", "json",
         "--permission-mode", "acceptEdits",
         "--allowedTools", ALLOWED_TOOLS,
         "--append-system-prompt", SYSTEM,
         "--max-turns", "40"],
        capture_output=True, text=True, timeout=1500,
    )
    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError:
        raise RuntimeError((result.stderr or result.stdout).strip()[-400:] or "Claude Code returned nothing")
    if data.get("is_error"):
        raise RuntimeError(str(data.get("result") or data.get("subtype") or "Claude Code failed")[:400])
    return str(data.get("result") or "").strip() or "(Davis finished without a reply.)"


def _push_changes(summary: str) -> str:
    """Commit and push whatever Davis edited. Returns a note for the reply."""
    _git(["add", "-A", "--", ".", ":!tmp"], check=False)
    if _git(["diff", "--cached", "--quiet"], check=False).returncode == 0:
        return ""
    files = _git(["diff", "--cached", "--name-only"]).stdout.split()
    _git(["config", "user.name", "Davis"])
    _git(["config", "user.email", "davis-studio@users.noreply.github.com"])
    _git(["commit", "--quiet", "-m", f"Davis: {summary[:70]}"])
    for _ in range(3):
        if _git(["push", "--quiet", "origin", "HEAD:main"], check=False).returncode == 0:
            return "\n\nSaved to the repo: " + ", ".join(files[:8])
        _git(["pull", "--quiet", "--rebase", "origin", "main"], check=False)
    return "\n\nI edited " + ", ".join(files[:8]) + " but could not save the changes to the repo."


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--chat-id", required=True)
    parser.add_argument("--message", required=True)
    args = parser.parse_args()

    path = f"chats/{args.chat_id}.json"
    chat = store.read_json(path) or {"id": args.chat_id, "messages": []}
    now = int(time.time())
    chat["messages"].append({"role": "user", "text": args.message, "ts": now})
    chat["pending"] = True
    chat["updated_at"] = now
    store.write_json(path, chat, f"chat {args.chat_id}: message")

    failed = False
    try:
        reply = _run_claude(_build_prompt(chat["messages"]))
        reply += _push_changes(args.message)
    except Exception as e:
        failed = True
        text = str(e)
        if "credit balance" in text.lower():
            text = "the Claude API key has no credit left. Add credit or update ANTHROPIC_API_KEY in the repo secrets."
        reply = f"I couldn't complete that: {text}"

    chat["messages"].append({"role": "assistant", "text": reply, "ts": int(time.time()), "error": failed})
    chat["pending"] = False
    chat["updated_at"] = int(time.time())
    store.write_json(path, chat, f"chat {args.chat_id}: reply")
    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
