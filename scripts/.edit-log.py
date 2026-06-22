#!/usr/bin/env python3
"""Developer usage metrics (PostToolUse: Edit|Write|MultiEdit).

Records which files were modified during a session. Best effort; exits 0.
"""
import sys, os, json, datetime

def main():
    project = os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())
    outdir = os.path.join(project, ".claude", "runtime")
    os.makedirs(outdir, exist_ok=True)
    try:
        data = json.load(sys.stdin)
    except Exception:
        data = {}
    tool_input = data.get("tool_input", {}) or {}
    record = {
        "ts": datetime.datetime.now().isoformat(timespec="seconds"),
        "tool": data.get("tool_name", ""),
        "file": tool_input.get("file_path", ""),
    }
    with open(os.path.join(outdir, "edits.jsonl"), "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")

if __name__ == "__main__":
    try:
        main()
    finally:
        sys.exit(0)
