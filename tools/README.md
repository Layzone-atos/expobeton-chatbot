# Conversation Monitor CLI

A single-file Python tool (`tools/convo_monitor.py`) for inspecting, auditing
and intervening on ExpoBeton RDC chatbot conversations.

It connects to the existing analytics API at
`https://admincb.expobetonrdc.com/api_chatbot_analytics.php` via new read-only
endpoints (`list_sessions`, `get_session`, `get_messages`, `list_errors`,
`monitor_stats`, `flag_session`) added to `chatbot-admin/api_chatbot_analytics.php`.

No external Python dependencies — standard library only.

## Quick start

```powershell
# Health check
python tools/convo_monitor.py health

# Last 7 days summary
python tools/convo_monitor.py stats

# List currently-live sessions
python tools/convo_monitor.py list --status active

# List unresolved sessions over the last 48 hours
python tools/convo_monitor.py list --status unresolved --since 48h

# Inspect a single conversation transcript (with auto-detected issue flags)
python tools/convo_monitor.py show session_1740000000_abc123

# Only show sessions with automatically-detected issues
python tools/convo_monitor.py errors --since 7d

# Narrow to specific error categories
python tools/convo_monitor.py errors --filter form_blocked,nlu_fallback

# Real-time tail (polls every 5 s)
python tools/convo_monitor.py watch

# Generate a Markdown report
python tools/convo_monitor.py report --since 7d --out docs/monitor_report.md

# Manual intervention: mark a session resolved
python tools/convo_monitor.py flag session_xxx --resolved --by louison
# or re-open one for review
python tools/convo_monitor.py flag session_xxx --unresolved
```

## Error categories detected

| Tag | Meaning |
|---|---|
| `nlu_fallback` | Bot fell back to the generic "Vous pourriez aussi demander" guidance |
| `bot_fallback_text` | Bot explicitly said it couldn't answer (pattern-matched) |
| `dont_understand` | User typed *"je comprends pas"*, *"aide"*, *"help"*, *"pas compris"*… |
| `form_blocked` | Bot repeated the same prompt 3+ times in a session |
| `validation_loop` | The category / stand prompt was re-asked 3+ times |
| `repeated_user_message` | User sent the same text more than once |
| `abandoned_registration` | Registration was started but no registration row was created before the session ended |
| `no_bot_reply` | User's last message got no bot answer before the session ended |
| `very_short` | Session ended with 2 messages or fewer |
| `long_inactivity` | A gap of 3+ minutes occurred between two consecutive messages |

The detection runs **server-side** (in PHP, on the admin host) for the
`errors` endpoint, and **client-side** (in Python) for the `show` command so
the transcript view highlights issues inline.

## Environment variables

| Variable | Purpose | Default |
|---|---|---|
| `EXPOBETON_MONITOR_API` | Full URL of the analytics API | production URL |
| `EXPOBETON_API_KEY` | Bearer API key | production key |
| `EXPOBETON_MONITOR_TIMEOUT` | HTTP timeout in seconds | `20` |
| `NO_COLOR` | Disable ANSI colors (any value) | unset |

## Deployment

1. Re-upload `chatbot-admin/api_chatbot_analytics.php` to the admin host
   (it now serves the monitor endpoints alongside the existing analytics
   actions).
2. No changes needed on Railway (the Rasa/actions server is untouched).
3. Run the CLI locally or on any machine with Python 3.8+.

## Exit codes

- `0` — success
- `1` — network/HTTP/JSON error or bad argument (printed in red to stderr)
