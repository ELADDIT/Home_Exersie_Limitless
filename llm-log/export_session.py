"""Convert a Claude Code session transcript (.jsonl) into a readable Markdown log.

User prompts and assistant replies are kept verbatim. Tool calls are listed as
one-line summaries (tool name + description), except prompts sent to sub-agents, which
are included in full. Tool output and injected system context are omitted to keep the log
readable. The only edit to prompt text: the public demo admin password is masked.

Usage: python llm-log/export_session.py <session.jsonl> <out.md>
"""
import json
import re
import sys

SYSTEM_TAG = re.compile(r"<system-reminder>.*?</system-reminder>", re.S)
EMAIL = re.compile(r"[\w.+-]+@gmail\.com")
# The brief forbids committing credentials, so the (public) demo admin password is masked.
SECRET = re.compile(r"(ADMIN_PASSWORD=)\S+|welcome01")


def clean(text: str) -> str:
    text = SYSTEM_TAG.sub("", text)
    text = EMAIL.sub("<redacted-email>", text)
    return SECRET.sub(lambda m: (m.group(1) or "") + "<redacted>", text).strip()


def main(src: str, dst: str) -> None:
    out = []
    for line in open(src, encoding="utf-8"):
        entry = json.loads(line)
        kind = entry.get("type")
        if kind not in ("user", "assistant") or entry.get("isSidechain"):
            continue
        content = entry["message"]["content"]
        if isinstance(content, str):
            content = [{"type": "text", "text": content}]
        ts = entry.get("timestamp", "")[:19].replace("T", " ")
        for block in content:
            btype = block.get("type")
            if btype == "text" and clean(block["text"]):
                who = "User" if kind == "user" else "Claude"
                out.append(f"### {who} ({ts} UTC)\n\n{clean(block['text'])}\n")
            elif btype == "tool_use" and block["name"] in ("Agent", "SendMessage"):
                inp = block.get("input", {})
                body = clean(inp.get("prompt") or inp.get("message") or "")
                out.append(f"> tool: `{block['name']}` - {inp.get('description') or inp.get('summary', '')}\n\n"
                           f"<details><summary>Full prompt sent to the sub-agent</summary>\n\n```text\n{body}\n```\n</details>\n")
            elif btype == "tool_use":
                inp = block.get("input", {})
                desc = inp.get("description") or inp.get("file_path") or inp.get("prompt", "")[:120]
                out.append(f"> tool: `{block['name']}` - {desc}\n")
    with open(dst, "w", encoding="utf-8") as f:
        f.write("# Claude Code session log\n\n" + "\n".join(out))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
