from pathlib import Path
from datetime import datetime
import ast
import shutil
import subprocess
import sys

PROJECT_ROOT = Path(__file__).resolve().parent
BOT_PATH = PROJECT_ROOT / "bot.py"
LIVE_PATH = PROJECT_ROOT / "live_stability.py"
TURN_PATH = PROJECT_ROOT / "turn_runtime.py"
BACKUP_ROOT = PROJECT_ROOT / "live_fix_backups"

EXPECTED_BOT = 'BOT_VERSION = "4.0.0-agency-server-awareness"'
TARGET_BOT = 'BOT_VERSION = "4.0.1-turn-console-latency"'
EXPECTED_LIVE = 'LIVE_STABILITY_VERSION = "1.4-agency-server-awareness"'
TARGET_LIVE = 'LIVE_STABILITY_VERSION = "1.5-turn-console-latency"'
EXPECTED_CONSOLE = 'CONSOLE_OUTPUT_VERSION = "1.0"'
TARGET_CONSOLE = 'CONSOLE_OUTPUT_VERSION = "1.1-turn-summary"'

TURN_SOURCE = 'from __future__ import annotations\n\nimport re\nfrom typing import Any\n\nTURN_RUNTIME_VERSION = "1.0"\n\ndef _short(value: Any, limit: int = 170) -> str:\n    text = re.sub(r"\\s+", " ", str(value or "")).strip()\n    if len(text) <= limit:\n        return text\n    return text[: max(0, limit - 3)] + "..."\n\ndef _num(obj, name: str, default: float = 0.0) -> float:\n    try:\n        return float(getattr(obj, name, default) or 0.0)\n    except Exception:\n        return float(default)\n\ndef _dnum(data, name: str, default: float = 0.0) -> float:\n    try:\n        return float((data if isinstance(data, dict) else {}).get(name, default) or 0.0)\n    except Exception:\n        return float(default)\n\ndef _safe_social_state(user_id) -> dict:\n    user_id = str(user_id or "")\n    if not user_id:\n        return {}\n    try:\n        from social_emotional_state import get_social_state\n        return get_social_state(user_id, persist_decay=False) or {}\n    except Exception:\n        return {}\n\ndef _learning_label(result) -> str:\n    if not isinstance(result, dict):\n        return "none"\n    status = str(result.get("status", "") or "").strip()\n    confirmations = int(result.get("confirmations", 0) or 0)\n    reason = str(result.get("reason", "") or "").strip()\n    bits = []\n    if status:\n        bits.append(status)\n    if confirmations:\n        bits.append(f"evidence={confirmations}")\n    if reason and reason not in {"observed", "candidate_observed"}:\n        bits.append(_short(reason, 44))\n    return "/".join(bits) if bits else "none"\n\ndef _emote_label(result) -> str:\n    if result is None or not bool(getattr(result, "added", False)):\n        return "none"\n    return (\n        str(getattr(result, "emoji_name", "") or "").strip()\n        or str(getattr(result, "semantic", "") or "").strip()\n        or "added"\n    )\n\ndef format_turn_summary(\n    *,\n    username,\n    user_id,\n    mode,\n    delivery_seconds,\n    brain_seconds,\n    writer_seconds,\n    post_seconds,\n    dominant_feeling,\n    inner_state,\n    response_plan,\n    surface_writer_used,\n    surface_writer_result,\n    raw_surface_answer,\n    final_answer,\n    repair_count,\n    emote_result=None,\n    learning_result=None,\n    salience_result=None,\n) -> str:\n    social = _safe_social_state(user_id)\n\n    move = str(getattr(response_plan, "social_move", "") or "")\n    stance = str(getattr(response_plan, "stance", "") or "")\n    shape = str(getattr(response_plan, "reply_shape", "") or "")\n    banter = _num(response_plan, "banter_intensity", 0.0)\n    plan_warmth = _num(response_plan, "warmth_intensity", 0.0)\n\n    writer_source = "qwen-surface" if surface_writer_used else "openai/fallback"\n    qwen_seconds = _num(surface_writer_result, "duration", 0.0)\n    surface_reason = str(getattr(surface_writer_result, "reason", "") or "").strip()\n\n    raw_norm = re.sub(r"\\s+", " ", str(raw_surface_answer or "")).strip()\n    final_norm = re.sub(r"\\s+", " ", str(final_answer or "")).strip()\n    changed = raw_norm != final_norm\n\n    salience = str(getattr(salience_result, "event_level", "") or "").strip() or "n/a"\n\n    lines = [\n        (\n            "[TURN] "\n            f"{username} | mode={mode or \'unknown\'} | "\n            f"delivery={float(delivery_seconds or 0.0):.2f}s "\n            f"brain={float(brain_seconds or 0.0):.2f}s "\n            f"writer={float(writer_seconds or 0.0):.2f}s "\n            f"post={float(post_seconds or 0.0):.2f}s"\n        ),\n        (\n            "[TURN] "\n            f"feel={dominant_feeling or \'unknown\'} | "\n            f"val={_num(inner_state, \'valence\'):+.2f} "\n            f"energy={_num(inner_state, \'energy\'):.2f} "\n            f"irrit={_num(inner_state, \'irritation\'):.2f} "\n            f"social={_num(inner_state, \'social_energy\'):.2f} "\n            f"curious={_num(inner_state, \'curiosity\'):.2f} "\n            f"bored={_num(inner_state, \'boredom\'):.2f} "\n            f"amused={_num(inner_state, \'amusement\'):.2f} "\n            f"warm={_num(inner_state, \'warmth\'):.2f} "\n            f"chaos={_num(inner_state, \'chaos_drive\'):.2f}"\n        ),\n        (\n            "[TURN] "\n            f"toward-user: warm={_dnum(social, \'warmth\'):.2f} "\n            f"trust={_dnum(social, \'trust\'):.2f} "\n            f"close={_dnum(social, \'closeness\'):.2f} "\n            f"rivalry={_dnum(social, \'rivalry\'):.2f} "\n            f"irrit={_dnum(social, \'irritation\'):.2f} "\n            f"engage={_dnum(social, \'engagement\'):.2f} | "\n            f"plan={move}/{stance}/{shape} "\n            f"banter={banter:.2f} warmth={plan_warmth:.2f}"\n        ),\n        (\n            "[TURN] "\n            f"writer={writer_source} qwen={qwen_seconds:.2f}s "\n            f"repairs={int(repair_count or 0)} "\n            f"surface={_short(surface_reason, 50) or \'n/a\'} "\n            f"changed={\'yes\' if changed else \'no\'}"\n        ),\n        (\n            "[TURN] text="\n            + (\n                f"draft={_short(raw_surface_answer)!r} -> final={_short(final_answer)!r}"\n                if changed\n                else f"{_short(final_answer)!r}"\n            )\n        ),\n        (\n            "[TURN] "\n            f"emote={_emote_label(emote_result)} | "\n            f"learning={_learning_label(learning_result)} | "\n            f"salience={salience}"\n        ),\n    ]\n    return "\\n".join(lines)\n\ndef _self_test() -> int:\n    from types import SimpleNamespace\n\n    state = SimpleNamespace(\n        valence=0.2, energy=0.55, irritation=0.08, social_energy=0.65,\n        curiosity=0.55, boredom=0.20, amusement=0.30, warmth=0.45,\n        chaos_drive=0.35,\n    )\n    plan = SimpleNamespace(\n        social_move="tease", stance="smug", reply_shape="one_liner",\n        banter_intensity=0.5, warmth_intensity=0.25,\n    )\n    surface = SimpleNamespace(reason="surface_primary_ok", duration=2.5)\n\n    summary = format_turn_summary(\n        username="Tester", user_id="", mode="direct",\n        delivery_seconds=4.2, brain_seconds=1.1, writer_seconds=2.5,\n        post_seconds=0.6, dominant_feeling="neutral", inner_state=state,\n        response_plan=plan, surface_writer_used=True,\n        surface_writer_result=surface, raw_surface_answer="Nö.",\n        final_answer="Nö. Skill issue.", repair_count=1,\n        learning_result={"status": "candidate", "confirmations": 2},\n    )\n\n    tests = [\n        ("six-line turn block", len(summary.splitlines()) == 6 and all(line.startswith("[TURN]") for line in summary.splitlines())),\n        ("feelings visible", "feel=neutral" in summary and "irrit=0.08" in summary),\n        ("timings visible", "brain=1.10s" in summary and "writer=2.50s" in summary and "post=0.60s" in summary),\n        ("text change visible", "changed=yes" in summary and "draft=\'Nö.\'" in summary and "final=\'Nö. Skill issue.\'" in summary),\n        ("plan visible", "plan=tease/smug/one_liner" in summary),\n        ("learning visible", "learning=candidate/evidence=2" in summary),\n    ]\n\n    passed = sum(1 for _, ok in tests if ok)\n    print()\n    print("=" * 64)\n    print(f"TURN RUNTIME v{TURN_RUNTIME_VERSION} TEST")\n    print("=" * 64)\n    for name, ok in tests:\n        print(f"[{\'PASS\' if ok else \'FAIL\'}] {name}")\n    print(f"RESULT: {passed}/{len(tests)} PASS")\n    return 0 if passed == len(tests) else 1\n\nif __name__ == "__main__":\n    raise SystemExit(_self_test())\n'
AGENCY_IMPORT = 'from agency_initiative_v2 import (\n    AGENCY_INITIATIVE_V2_VERSION,\n    set_message_channel_context,\n    set_initiative_channel_context,\n    wrap_agency_guard_v2,\n    wrap_participation_brain_server_v2,\n    wrap_should_initiate_v2,\n    wrap_choose_initiative_type_v2,\n    wrap_initiative_prompt_v2,\n)\n\n'
TURN_IMPORT = 'from turn_runtime import (\n    TURN_RUNTIME_VERSION,\n    format_turn_summary,\n)\n\n'
OLD_COMPACT = '        if stripped.startswith(\n            (\n                "[LIVE IN]",\n                "[LIVE OUT]",\n                "[LIVE GUARD]",\n                "[LIVE WARN]",\n                "[AUTO FILE LOGGING]",\n                "[LOCAL VOICE WARM]",\n            )\n        ):\n            return True\n'
NEW_COMPACT = '        if stripped.startswith(\n            (\n                "[LIVE IN]",\n                "[TURN]",\n                "[SILENT FINAL]",\n                "[AGENCY APPLICATION REACTION]",\n                "[LIVE GUARD]",\n                "[LIVE WARN]",\n                "[AUTO FILE LOGGING]",\n                "[LOCAL VOICE WARM]",\n            )\n        ):\n            return True\n'
LIVE_STARTUP_OLD = '            "Response Agency v",\n            "Qwen Surface Writer v",\n'
LIVE_STARTUP_NEW = '            "Response Agency v",\n            "Turn Runtime v",\n            "Qwen Surface Writer v",\n'
USER_LOCK_OLD = '    async with user_lock:\n\n        total_start = (\n'
USER_LOCK_NEW = '    async with user_lock, message.channel.typing():\n\n        total_start = (\n'
WRITER_HEADER_OLD = '        # =================================================\n        # 10. WRITER\n        # =================================================\n\n        try:\n'
WRITER_HEADER_NEW = '        # =================================================\n        # 10. WRITER\n        # =================================================\n\n        writer_started_at = (\n            time.perf_counter()\n        )\n\n        try:\n'
VALIDATION_MARKER = '        # =================================================\n        # 11. VALIDATE + REPAIR\n        # =================================================\n'
VALIDATION_TIMING = '        writer_finished_at = (\n            time.perf_counter()\n        )\n\n        writer_duration = (\n            writer_finished_at\n            -\n            writer_started_at\n        )\n\n        raw_surface_answer = str(\n            getattr(\n                response,\n                "output_text",\n                "",\n            )\n            or ""\n        ).strip()\n\n'
LEARNING_DEBUG_MARKER = '        print(\n            format_character_learning_debug(\n                character_learning_result\n            )\n        )\n'
TURN_SUMMARY_BLOCK = '        turn_post_seconds = max(\n            0.0,\n            float(\n                response_total_duration\n            )\n            -\n            float(\n                brain_duration\n            )\n            -\n            float(\n                writer_duration\n            ),\n        )\n\n        print(\n            format_turn_summary(\n                username=username,\n                user_id=user_id,\n                mode=voice_conversation_mode,\n                delivery_seconds=(\n                    response_total_duration\n                ),\n                brain_seconds=(\n                    brain_duration\n                ),\n                writer_seconds=(\n                    writer_duration\n                ),\n                post_seconds=(\n                    turn_post_seconds\n                ),\n                dominant_feeling=(\n                    get_dominant_feeling(\n                        current_inner_state\n                    )\n                ),\n                inner_state=(\n                    current_inner_state\n                ),\n                response_plan=(\n                    response_plan\n                ),\n                surface_writer_used=(\n                    surface_writer_used\n                ),\n                surface_writer_result=(\n                    surface_writer_result\n                ),\n                raw_surface_answer=(\n                    raw_surface_answer\n                ),\n                final_answer=answer,\n                repair_count=(\n                    get_response_repair_count()\n                ),\n                emote_result=(\n                    evilnae_emote_result\n                ),\n                learning_result=(\n                    character_learning_result\n                ),\n                salience_result=(\n                    salience_result\n                ),\n            )\n        )\n'
COMPACT_STARTUP = '    print(\n        f"Compact Console v"\n        f"{CONSOLE_OUTPUT_VERSION}: "\n        f"{get_console_mode()} "\n        "(full file log unchanged)"\n    )\n'
TURN_STARTUP = '    print(\n        f"Turn Runtime v"\n        f"{TURN_RUNTIME_VERSION}: ACTIVE "\n        "(feelings + text changes + stage timing)"\n    )\n'


def ok(text):
    print(f"[OK] {text}")


def fail(text):
    print()
    print(f"[INSTALL ERROR] {text}")
    print("Nothing was overwritten by this installer.")
    raise SystemExit(1)


def replace_once(text, old, new, label):
    count = text.count(old)
    if count != 1:
        fail(f"{label}: expected exactly 1 match, found {count}")
    ok(label)
    return text.replace(old, new, 1)


def insert_after_once(text, marker, addition, label):
    count = text.count(marker)
    if count != 1:
        fail(f"{label}: expected exactly 1 marker, found {count}")
    ok(label)
    return text.replace(marker, marker + addition, 1)


def insert_before_once(text, marker, addition, label):
    count = text.count(marker)
    if count != 1:
        fail(f"{label}: expected exactly 1 marker, found {count}")
    ok(label)
    return text.replace(marker, addition + marker, 1)


def syntax_check(text, filename):
    try:
        ast.parse(text, filename=filename)
    except SyntaxError as error:
        fail(
            f"{filename}: syntax error after patch "
            f"line {error.lineno}: {error.msg}"
        )
    ok(f"{filename} syntax check")


print("=" * 78)
print("EVILNAE 4.0.1 — TURN CONSOLE + LATENCY TELEMETRY")
print("=" * 78)
print(f"Project: {PROJECT_ROOT}")
print()
print("WICHTIG: bot.py muss vollständig AUS sein.")
print()


for required in (BOT_PATH, LIVE_PATH):
    if not required.exists():
        fail(f"Missing required file: {required.name}")


bot = BOT_PATH.read_text(encoding="utf-8")
live = LIVE_PATH.read_text(encoding="utf-8")


if TARGET_BOT in bot and TURN_PATH.exists():
    print("4.0.1 is already installed.")
    raise SystemExit(0)

if EXPECTED_BOT not in bot:
    fail("Expected Bot 4.0.0-agency-server-awareness")
if EXPECTED_LIVE not in live:
    fail("Expected Live Stability 1.4-agency-server-awareness")
if EXPECTED_CONSOLE not in live:
    fail("Expected Compact Console v1.0")
if TURN_PATH.exists():
    fail("turn_runtime.py already exists unexpectedly.")


for path, marker, label in (
    (
        PROJECT_ROOT / "server_awareness.py",
        'SERVER_AWARENESS_VERSION = "1.0.1-sensitive-language"',
        "Server Awareness 1.0.1",
    ),
    (
        PROJECT_ROOT / "agency_initiative_v2.py",
        'AGENCY_INITIATIVE_V2_VERSION = "2.0"',
        "Agency / Initiative 2.0",
    ),
):
    if not path.exists():
        fail(f"Missing required file: {path.name}")
    if marker not in path.read_text(encoding="utf-8"):
        fail(f"Expected {label}")


ok("4.0.0 live base detected")


live = replace_once(
    live,
    EXPECTED_LIVE,
    TARGET_LIVE,
    "Live Stability -> 1.5-turn-console-latency",
)
live = replace_once(
    live,
    EXPECTED_CONSOLE,
    TARGET_CONSOLE,
    "Compact Console -> 1.1-turn-summary",
)
live = replace_once(
    live,
    OLD_COMPACT,
    NEW_COMPACT,
    "Compact output -> one consolidated turn block",
)
live = replace_once(
    live,
    LIVE_STARTUP_OLD,
    LIVE_STARTUP_NEW,
    "Compact console allows Turn Runtime startup",
)


bot = replace_once(
    bot,
    EXPECTED_BOT,
    TARGET_BOT,
    "Bot version -> 4.0.1-turn-console-latency",
)
bot = insert_after_once(
    bot,
    AGENCY_IMPORT,
    TURN_IMPORT,
    "Bot imports Turn Runtime",
)


bot = replace_once(
    bot,
    USER_LOCK_OLD,
    USER_LOCK_NEW,
    "Typing indicator spans full generated response turn",
)


bot = replace_once(
    bot,
    WRITER_HEADER_OLD,
    WRITER_HEADER_NEW,
    "Writer timer start",
)
bot = insert_before_once(
    bot,
    VALIDATION_MARKER,
    VALIDATION_TIMING,
    "Writer timer end + raw draft capture",
)


bot = insert_after_once(
    bot,
    LEARNING_DEBUG_MARKER,
    TURN_SUMMARY_BLOCK,
    "Consolidated [TURN] summary after delivered reply",
)
bot = insert_after_once(
    bot,
    COMPACT_STARTUP,
    TURN_STARTUP,
    "Startup Turn Runtime banner",
)


for marker in (
    TARGET_BOT,
    "TURN_RUNTIME_VERSION",
    "async with user_lock, message.channel.typing():",
    "writer_started_at",
    "writer_duration",
    "raw_surface_answer",
    "format_turn_summary(",
    "Turn Runtime v",
):
    if marker not in bot:
        fail(f"Patched bot.py missing invariant: {marker}")

for marker in (
    TARGET_LIVE,
    TARGET_CONSOLE,
    '"[TURN]"',
    '"[SILENT FINAL]"',
    '"Turn Runtime v"',
):
    if marker not in live:
        fail(f"Patched live_stability.py missing invariant: {marker}")

for marker in (
    'TURN_RUNTIME_VERSION = "1.0"',
    "format_turn_summary",
    "feel=",
    "toward-user:",
    "draft=",
    "brain=",
    "writer=",
    "post=",
):
    if marker not in TURN_SOURCE:
        fail(f"turn_runtime.py missing invariant: {marker}")


syntax_check(TURN_SOURCE, "turn_runtime.py")
syntax_check(live, "live_stability.py")
syntax_check(bot, "bot.py")


contract_tests = {
    "full file log unchanged":
        "Full diagnostics always go to file." in bot,
    "compact no duplicate LIVE OUT":
        '"[LIVE OUT]"' not in NEW_COMPACT,
    "incoming remains visible":
        '"[LIVE IN]"' in NEW_COMPACT,
    "silent remains visible":
        '"[SILENT FINAL]"' in NEW_COMPACT,
    "feelings visible":
        "feel=" in TURN_SOURCE and "toward-user:" in TURN_SOURCE,
    "plan visible":
        "plan=" in TURN_SOURCE,
    "draft to final visible":
        "draft=" in TURN_SOURCE and "final=" in TURN_SOURCE,
    "stage timings visible":
        "brain=" in TURN_SOURCE
        and "writer=" in TURN_SOURCE
        and "post=" in TURN_SOURCE,
    "typing spans post-writer work":
        "async with user_lock, message.channel.typing():" in bot,
    "no new model calls":
        "AsyncOpenAI" not in TURN_SOURCE
        and "run_local_model" not in TURN_SOURCE
        and "urllib.request" not in TURN_SOURCE,
    "no memory writes":
        ".write_text(" not in TURN_SOURCE
        and "json.dump" not in TURN_SOURCE,
}

failed = [
    name
    for name, success in contract_tests.items()
    if not success
]
if failed:
    fail("Contract self-test failed: " + ", ".join(failed))

ok(
    f"Contract self-test: "
    f"{len(contract_tests)}/{len(contract_tests)} PASS"
)


namespace = {"__name__": "_evilnae_turn_runtime_preflight_"}
exec(
    compile(
        TURN_SOURCE,
        "turn_runtime.py",
        "exec",
    ),
    namespace,
)
if namespace["_self_test"]() != 0:
    fail("Turn Runtime behavior self-test failed.")

ok("Turn Runtime behavior self-test: PASS")


timestamp = (
    datetime.now()
    .astimezone()
    .strftime("%Y%m%d-%H%M%S")
)
backup_dir = BACKUP_ROOT / timestamp
suffix = 1
while backup_dir.exists():
    backup_dir = BACKUP_ROOT / f"{timestamp}_{suffix:02d}"
    suffix += 1
backup_dir.mkdir(parents=True, exist_ok=False)

for path in (BOT_PATH, LIVE_PATH):
    shutil.copy2(path, backup_dir / path.name)
    ok(f"Backup: {path.name}")


def atomic_write(path, text):
    temp = Path(str(path) + ".tmp")
    temp.write_text(text, encoding="utf-8")
    temp.replace(path)


atomic_write(TURN_PATH, TURN_SOURCE)
ok("Created: turn_runtime.py")
atomic_write(LIVE_PATH, live)
ok("Updated: live_stability.py")
atomic_write(BOT_PATH, bot)
ok("Updated: bot.py")


compile_targets = [
    TURN_PATH,
    LIVE_PATH,
    BOT_PATH,
    PROJECT_ROOT / "server_awareness.py",
    PROJECT_ROOT / "agency_initiative_v2.py",
]
result = subprocess.run(
    [
        sys.executable,
        "-m",
        "py_compile",
        *[str(path) for path in compile_targets],
    ],
    cwd=str(PROJECT_ROOT),
    check=False,
)
if result.returncode != 0:
    print()
    print("[POST-INSTALL WARNING] py_compile failed.")
    print(f"Backup: {backup_dir}")
    raise SystemExit(result.returncode)

ok("Post-install py_compile: 5/5")


result = subprocess.run(
    [
        sys.executable,
        str(TURN_PATH),
    ],
    cwd=str(PROJECT_ROOT),
    check=False,
)
if result.returncode != 0:
    print()
    print("[POST-INSTALL WARNING] Turn Runtime self-test failed.")
    print(f"Backup: {backup_dir}")
    raise SystemExit(result.returncode)

ok("Post-install Turn Runtime self-test: PASS")


print()
print("=" * 78)
print("EVILNAE 4.0.1 TURN CONSOLE + LATENCY TELEMETRY INSTALLED")
print("=" * 78)
print()
print("Console (compact):")
print("  [✓] [LIVE IN] still visible")
print("  [✓] one six-line [TURN] block per completed reply")
print("  [✓] duplicate [LIVE OUT] hidden from compact terminal only")
print("  [✓] global feelings / Inner State visible")
print("  [✓] per-user Social Emotional State visible")
print("  [✓] Response Plan visible")
print("  [✓] draft -> final text change visible")
print("  [✓] emote / learning / salience visible")
print("  [✓] full logfile remains completely unfiltered")
print()
print("Latency:")
print("  [✓] delivery total")
print("  [✓] Brain time")
print("  [✓] Writer time")
print("  [✓] post-writer / guards / repairs time")
print("  [✓] Qwen duration")
print("  [✓] repair count")
print()
print("Discord typing:")
print("  [✓] typing indicator covers the complete generated reply turn")
print("  [✓] removes the Writer-finished -> dead gap before message")
print()
print("Important:")
print("  This does NOT blindly remove quality checks or model calls.")
print("  Ollama is running now, so first retest the real Qwen path.")
print("  The next [TURN] block tells us exactly which stage causes any remaining delay.")
print()
print("Versions:")
print("  Bot: 4.0.1-turn-console-latency")
print("  Live Stability: 1.5-turn-console-latency")
print("  Compact Console: 1.1-turn-summary")
print("  Turn Runtime: 1.0")
print()
print(f"Backup: {backup_dir}")
print()
print("NO MEMORY RESET REQUIRED.")
print()
print("NEXT:")
print("  Keep Ollama running.")
print("  Start: python bot.py")
print("  Send 2-4 normal messages and paste the [TURN] blocks.")
