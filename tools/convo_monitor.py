#!/usr/bin/env python3
"""
ExpoBeton RDC — Conversation Monitor CLI
========================================

A command-line tool to verify, analyze and intervene on chatbot conversations.

Connects to the existing analytics API at admincb.expobetonrdc.com.
No extra server deployment required beyond adding the monitor endpoints to
api_chatbot_analytics.php (already done).

Usage examples
--------------
    python tools/convo_monitor.py stats
    python tools/convo_monitor.py list --status active
    python tools/convo_monitor.py list --since 24h --status unresolved
    python tools/convo_monitor.py show session_1740000000_abc
    python tools/convo_monitor.py errors --since 7d
    python tools/convo_monitor.py errors --filter form_blocked,nlu_fallback
    python tools/convo_monitor.py watch                 # real-time tail
    python tools/convo_monitor.py report --since 7d --out report.md
    python tools/convo_monitor.py flag session_xxx --resolved
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sys
import textwrap
import time
from typing import Any, Dict, List, Optional
from urllib import error as urlerror
from urllib import parse as urlparse
from urllib import request as urlrequest

# ------------------------------------------------------------------
# Config — reads from env first, falls back to known production values
# ------------------------------------------------------------------
API_URL = os.environ.get(
    "EXPOBETON_MONITOR_API",
    "https://admincb.expobetonrdc.com/api_chatbot_analytics.php",
)
API_KEY = os.environ.get(
    "EXPOBETON_API_KEY",
    "ebx-rasa-2026-kAlEmIe-be96bac9f905b106ed2b941dfe536b07",
)
HTTP_TIMEOUT = int(os.environ.get("EXPOBETON_MONITOR_TIMEOUT", "20"))

ERROR_LABELS = {
    "nlu_fallback":         "NLU fallback (bot didn't understand)",
    "bot_fallback_text":    "Bot gave a generic 'I can't answer' reply",
    "dont_understand":      "User said 'je comprends pas' / asked for help",
    "form_blocked":         "Bot repeated same prompt 3+ times",
    "validation_loop":      "Validation loop (category/stand re-asked)",
    "repeated_user_message":"User sent same message more than once",
    "abandoned_registration": "Registration started but never confirmed",
    "no_bot_reply":         "User's last message got no bot reply",
    "very_short":           "Session too short (<= 2 messages)",
    "long_inactivity":      "Gap >= 3 min between two consecutive messages",
}

# ANSI colors (safe no-op on non-TTY)
def _supports_color() -> bool:
    if os.environ.get("NO_COLOR"):
        return False
    if not sys.stdout.isatty():
        return False
    return True

COLOR = _supports_color()
def c(text: str, code: str) -> str:
    if not COLOR:
        return text
    return f"\033[{code}m{text}\033[0m"
def bold(t: str)   -> str: return c(t, "1")
def red(t: str)    -> str: return c(t, "31")
def green(t: str)  -> str: return c(t, "32")
def yellow(t: str) -> str: return c(t, "33")
def blue(t: str)   -> str: return c(t, "34")
def magenta(t: str)-> str: return c(t, "35")
def cyan(t: str)   -> str: return c(t, "36")
def dim(t: str)    -> str: return c(t, "2")


# ------------------------------------------------------------------
# HTTP helpers
# ------------------------------------------------------------------
def _call(action: str, params: Optional[Dict[str, Any]] = None,
          method: str = "GET", body: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    qs = {"action": action, "api_key": API_KEY}
    if params:
        qs.update({k: str(v) for k, v in params.items() if v is not None})
    url = f"{API_URL}?{urlparse.urlencode(qs)}"
    data = None
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Accept": "application/json",
    }
    if method == "POST":
        data = json.dumps(body or {}).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urlrequest.Request(url, data=data, method=method, headers=headers)
    try:
        with urlrequest.urlopen(req, timeout=HTTP_TIMEOUT) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
    except urlerror.HTTPError as e:
        raw = e.read().decode("utf-8", errors="replace") if e.fp else ""
        try:
            parsed = json.loads(raw) if raw else {}
        except Exception:
            parsed = {"error": raw or str(e)}
        raise SystemExit(red(f"HTTP {e.code} on action={action}: {parsed.get('error', raw)}"))
    except urlerror.URLError as e:
        raise SystemExit(red(f"Network error calling {action}: {e.reason}"))
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        raise SystemExit(red(f"Non-JSON response from {action}:\n{raw[:500]}"))


# ------------------------------------------------------------------
# Formatting helpers
# ------------------------------------------------------------------
def _truncate(text: str, n: int = 60) -> str:
    text = (text or "").replace("\n", " ").replace("\r", " ").strip()
    return text if len(text) <= n else text[: n - 1] + "…"

def _fmt_duration(seconds: Optional[int]) -> str:
    if seconds is None or seconds == "":
        return "—"
    s = int(seconds)
    if s < 60:
        return f"{s}s"
    m, sec = divmod(s, 60)
    if m < 60:
        return f"{m}m{sec:02d}s"
    h, m = divmod(m, 60)
    return f"{h}h{m:02d}m"

def _fmt_time(ts: Optional[str]) -> str:
    if not ts:
        return "—"
    return str(ts)

def _row(cols: List[str], widths: List[int]) -> str:
    out = []
    for val, w in zip(cols, widths):
        s = str(val)
        # strip ANSI to compute visible length
        visible = re.sub(r"\033\[[0-9;]*m", "", s)
        pad = w - len(visible)
        if pad < 0:
            # need to truncate visible part; keep it simple: use non-color version
            s = visible[: max(0, w - 1)] + "…"
            pad = max(0, w - len(s))
        out.append(s + " " * pad)
    return "  ".join(out)


# ------------------------------------------------------------------
# Commands
# ------------------------------------------------------------------
def cmd_stats(args: argparse.Namespace) -> None:
    data = _call("monitor_stats", {"range": args.range})
    print(bold(f"\n📊 ExpoBeton chatbot — stats for last {data.get('range')}\n"))
    rows = [
        ("Total sessions",          data.get("total_sessions")),
        ("Total messages",          data.get("total_messages")),
        ("Active right now",        data.get("active_now")),
        ("Unresolved sessions",     data.get("unresolved")),
        ("Registrations completed", data.get("registrations")),
        ("Avg messages / session",  data.get("avg_messages_per_session")),
        ("Avg duration",            _fmt_duration(data.get("avg_duration_seconds"))),
    ]
    for label, value in rows:
        col = yellow(str(value)) if label == "Unresolved sessions" and int(value or 0) > 0 else str(value)
        print(f"  {label:<28} {col}")
    print()


def cmd_list(args: argparse.Namespace) -> None:
    data = _call("list_sessions", {
        "limit":  args.limit,
        "offset": args.offset,
        "since":  args.since,
        "status": args.status,
        "search": args.search,
    })
    sessions = data.get("sessions", [])
    total = data.get("total", 0)

    if args.json:
        print(json.dumps(sessions, indent=2, ensure_ascii=False))
        return

    print(bold(f"\n💬 {len(sessions)} sessions (of {total} matching)  —  status={args.status}, since={args.since or 'all'}\n"))
    widths = [24, 19, 8, 22, 18, 4]
    print(_row([bold("SESSION ID"), bold("STARTED"), bold("DUR"),
                bold("USER"), bold("COUNTRY"), bold("#")], widths))
    print(dim("-" * (sum(widths) + 2 * len(widths))))
    for s in sessions:
        sid = s["session_id"]
        sid_short = sid if len(sid) <= 24 else sid[:12] + "…" + sid[-8:]
        started = (s.get("started_at") or "")[:19]
        ended = s.get("ended_at")
        dur = _fmt_duration(s.get("duration_seconds"))
        if not ended:
            dur = green("LIVE")
        user = s.get("user_name") or dim("(anon)")
        if s.get("user_email"):
            user = f"{user} <{_truncate(s['user_email'], 18)}>"
        country = s.get("country") or "—"
        msgs = str(s.get("message_count") or 0)
        flags = ""
        if int(s.get("is_unresolved") or 0) == 1 and not s.get("resolved_at"):
            flags = "  " + red("⚠ unresolved")
        elif s.get("resolved_at"):
            flags = "  " + green("✓ resolved")
        print(_row([sid_short, started, dur, _truncate(user, 22), _truncate(country, 18), msgs], widths) + flags)
    print()


def cmd_show(args: argparse.Namespace) -> None:
    data = _call("get_session", {"session_id": args.session_id})
    s = data.get("session", {})
    msgs = data.get("messages", [])
    regs = data.get("registrations", [])
    replies = data.get("admin_replies", [])

    if args.json:
        print(json.dumps(data, indent=2, ensure_ascii=False))
        return

    print(bold(f"\n🗂  Session {s.get('session_id')}"))
    print(f"  Started:   {s.get('started_at')}")
    print(f"  Ended:     {s.get('ended_at') or green('(still active)')}")
    print(f"  Duration:  {_fmt_duration(s.get('duration_seconds'))}")
    print(f"  User:      {s.get('user_name') or dim('(anon)')}  <{s.get('user_email') or '—'}>")
    print(f"  Location:  {s.get('country') or '—'} / {s.get('city') or '—'}")
    print(f"  Device:    {s.get('device_type') or '—'}  ({s.get('browser') or '—'}, {s.get('os') or '—'})")
    unresolved = int(s.get("is_unresolved") or 0)
    if unresolved and not s.get("resolved_at"):
        print(f"  Status:    {red('⚠ unresolved')}")
    elif s.get("resolved_at"):
        print(f"  Status:    {green('✓ resolved')} at {s.get('resolved_at')} by {s.get('resolved_by')}")
    print(f"  Messages:  {len(msgs)}")

    # Detect errors locally for this session (client-side)
    flags = _detect_errors_client([{"sender": m["sender"], "message_text": m.get("message_text", ""),
                                     "timestamp": m["timestamp"]} for m in msgs],
                                   session=s, had_registration=bool(regs))
    if flags:
        print(f"\n  {yellow('⚑ Detected issues:')}")
        for f in flags:
            print(f"    • {red(f)}  — {ERROR_LABELS.get(f, '')}")

    print(bold("\n  Transcript\n  ----------"))
    for m in msgs:
        ts = (m.get("timestamp") or "")[11:19]
        sender = m.get("sender", "")
        text = (m.get("message_text") or "").replace("\n", "\n                ")
        if sender == "user":
            line = f"  [{ts}] {cyan('USER')}  {text}"
        else:
            line = f"  [{ts}] {magenta('BOT ')}  {text}"
        print(line)

    if regs:
        print(bold("\n  Registrations\n  -------------"))
        for r in regs:
            print(f"  • {r.get('reference_number') or '—'}  {r.get('category') or '—'}  —  {r.get('contact_name')} <{r.get('email')}>")

    if replies:
        print(bold("\n  Admin replies\n  -------------"))
        for r in replies:
            print(f"  • {r.get('sent_at')}  by {r.get('admin_username')}  →  {r.get('recipient_email')}  [{r.get('email_status')}]")

    print()


def _detect_errors_client(msgs: List[Dict[str, Any]], session: Dict[str, Any],
                          had_registration: bool = False) -> List[str]:
    """Mirror of server-side heuristics — used when we already have a transcript."""
    flags: List[str] = []
    if not msgs:
        return flags
    user_msgs = [m for m in msgs if m["sender"] == "user"]
    bot_msgs  = [m for m in msgs if m["sender"] == "bot"]
    user_texts = [(m.get("message_text") or "").lower().strip() for m in user_msgs]
    bot_texts  = [(m.get("message_text") or "").lower().strip() for m in bot_msgs]

    dont_patterns = ["je comprends pas", "je ne comprends pas", "j'ai pas compris",
                     "pas compris", "c est quoi", "c'est quoi", "help", "aidez",
                     " aide", "je sais pas"]
    for t in user_texts:
        if any(p in t for p in dont_patterns):
            flags.append("dont_understand"); break

    bot_fb = ["je ne peux pas vous fournir", "i cannot provide", "je n'ai pas d'information",
              "reformulez votre question", "could you rephrase"]
    for t in bot_texts:
        if any(p in t for p in bot_fb):
            flags.append("bot_fallback_text"); break

    for t in bot_texts:
        if "pourriez aussi demander" in t:
            flags.append("nlu_fallback"); break

    seen = set()
    for t in user_texts:
        if not t:
            continue
        if t in seen:
            flags.append("repeated_user_message"); break
        seen.add(t)

    counts: Dict[str, int] = {}
    for t in bot_texts:
        k = t[:80]
        if not k: continue
        counts[k] = counts.get(k, 0) + 1
    if any(v >= 3 for v in counts.values()):
        flags.append("form_blocked")

    loop = sum(1 for t in bot_texts if "tapez le numéro" in t or "pour quelle catégorie" in t)
    if loop >= 3:
        flags.append("validation_loop")

    asked_reg = any(("nom de votre entreprise" in t) or ("quelle est votre adresse email" in t)
                    or ("numéro de téléphone" in t) for t in bot_texts)
    if asked_reg and not had_registration and session.get("ended_at"):
        flags.append("abandoned_registration")

    if msgs[-1]["sender"] == "user" and session.get("ended_at"):
        flags.append("no_bot_reply")

    if len(msgs) <= 2 and session.get("ended_at"):
        flags.append("very_short")

    for i in range(1, len(msgs)):
        try:
            t1 = dt.datetime.fromisoformat(str(msgs[i-1]["timestamp"]).replace("Z", ""))
            t2 = dt.datetime.fromisoformat(str(msgs[i]["timestamp"]).replace("Z", ""))
            if (t2 - t1).total_seconds() >= 180:
                flags.append("long_inactivity"); break
        except Exception:
            pass

    # dedup keep order
    out: List[str] = []
    for f in flags:
        if f not in out:
            out.append(f)
    return out


def cmd_errors(args: argparse.Namespace) -> None:
    data = _call("list_errors", {"since": args.since})
    items = data.get("errors", [])
    wanted = [f.strip() for f in args.filter.split(",")] if args.filter else None
    if wanted:
        items = [x for x in items if any(f in x.get("error_flags", []) for f in wanted)]

    if args.json:
        print(json.dumps(items, indent=2, ensure_ascii=False))
        return

    print(bold(f"\n🚨 {len(items)} sessions with detected issues  —  since {args.since}\n"))
    # Summary by flag
    tally: Dict[str, int] = {}
    for it in items:
        for f in it.get("error_flags", []):
            tally[f] = tally.get(f, 0) + 1
    if tally:
        print(bold("  By category:"))
        for f, n in sorted(tally.items(), key=lambda kv: -kv[1]):
            print(f"    {red(f):<30}  {n:>3}  {dim(ERROR_LABELS.get(f, ''))}")
        print()

    widths = [24, 19, 18, 12, 40]
    print(_row([bold("SESSION ID"), bold("STARTED"), bold("USER"),
                bold("MSGS"), bold("FLAGS")], widths))
    print(dim("-" * (sum(widths) + 2 * len(widths))))
    for it in items:
        sid = it["session_id"]
        sid_short = sid if len(sid) <= 24 else sid[:12] + "…" + sid[-8:]
        started = (it.get("started_at") or "")[:19]
        user = it.get("user_name") or dim("(anon)")
        msgs = f"{it.get('message_count') or 0}"
        fl = ", ".join([red(f) for f in it.get("error_flags", [])])
        print(_row([sid_short, started, _truncate(user, 18), msgs, fl], widths))
    print()


def cmd_watch(args: argparse.Namespace) -> None:
    print(bold(f"\n👁  Watching new messages every {args.interval}s   (Ctrl+C to stop)\n"))
    since = dt.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    try:
        while True:
            data = _call("get_messages", {"since": since, "limit": 200})
            msgs = data.get("messages", [])
            for m in msgs:
                ts = (m.get("timestamp") or "")[11:19]
                sid = m.get("session_id", "")[-8:]
                user = m.get("user_name") or "anon"
                sender = m.get("sender", "")
                tag = cyan("USER") if sender == "user" else magenta("BOT ")
                text = _truncate(m.get("message_text") or "", 120)
                print(f"[{ts}] [{dim(sid)}] [{_truncate(user, 16):<16}] {tag} {text}")
            if msgs:
                since = data.get("server_time") or msgs[-1]["timestamp"]
            time.sleep(args.interval)
    except KeyboardInterrupt:
        print("\n" + dim("Stopped."))


def cmd_report(args: argparse.Namespace) -> None:
    stats = _call("monitor_stats", {"range": args.since})
    errs = _call("list_errors", {"since": args.since}).get("errors", [])
    tally: Dict[str, int] = {}
    for it in errs:
        for f in it.get("error_flags", []):
            tally[f] = tally.get(f, 0) + 1

    now = dt.datetime.now().strftime("%Y-%m-%d %H:%M")
    lines: List[str] = []
    lines.append(f"# ExpoBeton Chatbot — Conversation Report")
    lines.append("")
    lines.append(f"_Generated: {now}   •   Range: {args.since}_")
    lines.append("")
    lines.append("## Key metrics")
    lines.append("")
    lines.append(f"- **Total sessions**: {stats.get('total_sessions')}")
    lines.append(f"- **Total messages**: {stats.get('total_messages')}")
    lines.append(f"- **Active right now**: {stats.get('active_now')}")
    lines.append(f"- **Unresolved**: {stats.get('unresolved')}")
    lines.append(f"- **Registrations completed**: {stats.get('registrations')}")
    lines.append(f"- **Avg messages / session**: {stats.get('avg_messages_per_session')}")
    lines.append(f"- **Avg duration**: {_fmt_duration(stats.get('avg_duration_seconds'))}")
    lines.append("")
    lines.append("## Error categories (occurrence count)")
    lines.append("")
    if tally:
        lines.append("| Category | Count | Description |")
        lines.append("|---|---:|---|")
        for f, n in sorted(tally.items(), key=lambda kv: -kv[1]):
            lines.append(f"| `{f}` | {n} | {ERROR_LABELS.get(f, '')} |")
    else:
        lines.append("_No errors detected in range._")
    lines.append("")
    lines.append(f"## Problematic sessions ({len(errs)})")
    lines.append("")
    for it in errs[:200]:
        sid = it["session_id"]
        started = (it.get("started_at") or "")[:19]
        user = it.get("user_name") or "(anon)"
        email = it.get("user_email") or "—"
        country = it.get("country") or "—"
        flags = ", ".join([f"`{f}`" for f in it.get("error_flags", [])])
        lines.append(f"- **{started}** — `{sid}` — {user} <{email}> — {country} — flags: {flags}")
    content = "\n".join(lines) + "\n"

    if args.out:
        path = args.out
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(content)
        print(green(f"✓ Report written to {path}"))
    else:
        print(content)


def cmd_flag(args: argparse.Namespace) -> None:
    flag = "resolved" if args.resolved else ("unresolved" if args.unresolved else None)
    if not flag:
        raise SystemExit(red("Specify --resolved or --unresolved"))
    data = _call("flag_session", method="POST",
                 body={"session_id": args.session_id, "flag": flag, "by": args.by})
    if data.get("success"):
        print(green(f"✓ Session {args.session_id} marked as {flag}"))
    else:
        raise SystemExit(red(f"Flag failed: {data}"))


def cmd_health(_: argparse.Namespace) -> None:
    data = _call("health")
    print(json.dumps(data, indent=2))


# ------------------------------------------------------------------
# Arg parsing
# ------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="convo_monitor",
        description="ExpoBeton chatbot conversation monitor (view / detect / flag / report).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""\
            Examples:
              convo_monitor stats
              convo_monitor list --status active
              convo_monitor list --status unresolved --since 48h
              convo_monitor show session_1740000000_abc
              convo_monitor errors --since 7d
              convo_monitor errors --filter form_blocked,nlu_fallback
              convo_monitor watch
              convo_monitor report --since 7d --out docs/monitor_report.md
              convo_monitor flag session_xxx --resolved
        """),
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("health", help="Check API health")
    sp.set_defaults(func=cmd_health)

    sp = sub.add_parser("stats", help="Summary metrics over a time range")
    sp.add_argument("--range", default="7d", help="Time range (e.g. 24h, 7d, 30d). Default 7d.")
    sp.set_defaults(func=cmd_stats)

    sp = sub.add_parser("list", help="List sessions (paginated, filterable)")
    sp.add_argument("--limit", type=int, default=30)
    sp.add_argument("--offset", type=int, default=0)
    sp.add_argument("--since", default=None, help="e.g. 24h, 7d, or ISO timestamp")
    sp.add_argument("--status", default="all",
                    choices=["all", "active", "ended", "unresolved", "resolved"])
    sp.add_argument("--search", default="", help="Match in session_id/user/email")
    sp.add_argument("--json", action="store_true")
    sp.set_defaults(func=cmd_list)

    sp = sub.add_parser("show", help="Show a full session transcript with detected issues")
    sp.add_argument("session_id")
    sp.add_argument("--json", action="store_true")
    sp.set_defaults(func=cmd_show)

    sp = sub.add_parser("errors", help="List sessions with automatically-detected issues")
    sp.add_argument("--since", default="7d", help="Time range, e.g. 24h, 7d, 30d (default 7d).")
    sp.add_argument("--filter", default="",
                    help="Comma-separated tags to keep (e.g. form_blocked,nlu_fallback)")
    sp.add_argument("--json", action="store_true")
    sp.set_defaults(func=cmd_errors)

    sp = sub.add_parser("watch", help="Tail new messages in real time")
    sp.add_argument("--interval", type=int, default=5, help="Poll interval in seconds")
    sp.set_defaults(func=cmd_watch)

    sp = sub.add_parser("report", help="Generate a Markdown error report")
    sp.add_argument("--since", default="7d")
    sp.add_argument("--out", default=None, help="Output file. If omitted, prints to stdout.")
    sp.set_defaults(func=cmd_report)

    sp = sub.add_parser("flag", help="Mark a session resolved/unresolved")
    sp.add_argument("session_id")
    g = sp.add_mutually_exclusive_group(required=True)
    g.add_argument("--resolved", action="store_true")
    g.add_argument("--unresolved", action="store_true")
    sp.add_argument("--by", default="monitor-cli")
    sp.set_defaults(func=cmd_flag)

    return p


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    args.func(args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
