# Prompt log

Unedited prompts and AI sessions used in this exercise, in order. Each entry notes the commit it led to.

| File | Tool | Led to |
|------|------|--------|
| [01-gemini-prompt.md](01-gemini-prompt.md) | Gemini (drafting) → Claude Code | The plan in the session below |
| [02-claude-code-session.md](02-claude-code-session.md) | Claude Code (Claude Opus 5.5), the main working session, including the full prompts it gave to 2 Sonnet sub-agents (API suite, UI suite) | Every commit; each commit message references this log |

`export_session.py` converts the raw Claude Code transcript (`.jsonl`) into the Markdown above. Prompts and replies are kept verbatim; tool output is left out for readability. The log is re-exported as the session continues. The only edit: the public demo admin password is masked, because the brief forbids committing credentials. A copy is in [docs/ai-conversation.md](../docs/ai-conversation.md).
