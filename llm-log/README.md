# Prompt log

Unedited prompts and AI sessions used in this exercise, in order. Each entry notes the commit it led to.

| File | Tool | Led to |
|------|------|--------|
| [01-gemini-prompt.md](01-gemini-prompt.md) | Gemini (drafting) → Claude Code | The plan in the session below |
| [02-claude-code-session.md](02-claude-code-session.md) | Claude Code (Claude Opus), the main working session | Every commit; commit messages reference this log |

`export_session.py` converts the raw Claude Code transcript (`.jsonl`) into the Markdown above. Prompts and replies are kept verbatim; tool output is left out for readability. The log is re-exported as the session continues.
