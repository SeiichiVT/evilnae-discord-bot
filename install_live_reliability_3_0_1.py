from pathlib import Path
from datetime import datetime
import ast
import shutil
import sys


# =========================================================
# EVILNAE 3.0.1 LIVE RELIABILITY FIX
# =========================================================
#
# Fixes:
# - direct/continuation replies lost by question_salvage_empty
# - short recovery window after a failed direct reply attempt
# - third-person questions ABOUT Evilnae get proper participation weight
# - dangling comma/colon/semicolon after stripped Unicode emoji
#
# Already expected in the current 3.0.0 base:
# - UTF-8 stdout/stderr safety
# - Character Foundation 1.0
# =========================================================

PROJECT_ROOT = Path(__file__).resolve().parent
BOT_PATH = PROJECT_ROOT / "bot.py"
ROUTING_PATH = PROJECT_ROOT / "routing_hardening.py"
EMOTES_PATH = PROJECT_ROOT / "evilnae_emotes.py"
BACKUP_ROOT = PROJECT_ROOT / "live_fix_backups"

EXPECTED_BOT_VERSION = 'BOT_VERSION = "3.0.0-character-final"'
TARGET_BOT_VERSION = 'BOT_VERSION = "3.0.1-live-reliability"'


def fail(message):
    print()
    print(f"[INSTALL ERROR] {message}")
    print("Nothing was overwritten unless a later write error is explicitly shown.")
    print()
    raise SystemExit(1)


def ok(message):
    print(f"[OK] {message}")


def replace_once(text, old, new, label):
    count = text.count(old)
    if count != 1:
        fail(f"{label}: expected exactly 1 match, found {count}")
    ok(label)
    return text.replace(old, new, 1)


def insert_before_once(text, marker, block, label):
    count = text.count(marker)
    if count != 1:
        fail(f"{label}: expected exactly 1 marker, found {count}")
    ok(label)
    return text.replace(marker, block + marker, 1)


def syntax_check(text, filename):
    try:
        ast.parse(text, filename=filename)
    except SyntaxError as error:
        fail(
            f"{filename}: syntax error after patch at line "
            f"{error.lineno}: {error.msg}"
        )
    ok(f"{filename} syntax check")


def read_utf8(path):
    if not path.exists():
        fail(f"Missing required file: {path.name}")
    return path.read_text(encoding="utf-8")


def atomic_write(path, text):
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)


print()
print("=" * 60)
print("EVILNAE 3.0.1 LIVE RELIABILITY FIX")
print("=" * 60)
print(f"Project: {PROJECT_ROOT}")
print()
print("WICHTIG: bot.py muss vollständig AUS sein.")
print()

bot = read_utf8(BOT_PATH)
routing = read_utf8(ROUTING_PATH)
emotes = read_utf8(EMOTES_PATH)

if TARGET_BOT_VERSION in bot:
    print("Fix is already installed.")
    raise SystemExit(0)

if EXPECTED_BOT_VERSION not in bot:
    fail(
        "Unexpected bot version. Expected the pushed "
        "3.0.0-character-final base."
    )

if 'import sys' not in bot or 'errors="backslashreplace"' not in bot:
    fail(
        "UTF-8 console safety is missing from bot.py. "
        "Push/apply the current 3.0.0 base first."
    )

if 'ROUTING_HARDENING_VERSION = "1.0"' not in routing:
    fail("Unexpected routing_hardening.py version")

if 'EVILNAE_EMOTE_VERSION = "1.1"' not in emotes:
    fail("Unexpected evilnae_emotes.py version")

# =========================================================
# BOT.PY
# =========================================================

bot = replace_once(
    bot,
    EXPECTED_BOT_VERSION,
    TARGET_BOT_VERSION,
    "Bot version -> 3.0.1-live-reliability",
)

active_config_old = '''ACTIVE_CONVERSATION_WINDOW = (
    8 * 60
)

ACTIVE_CONVERSATION_CONTEXT_GAP = 8
'''

active_config_new = '''ACTIVE_CONVERSATION_WINDOW = (
    8 * 60
)

# If a DIRECT reply started but the response pipeline failed before send,
# keep a short continuity bridge so the user's immediate follow-up is not
# mistaken for an unrelated open-channel message.
FAILED_DIRECT_CONTINUATION_WINDOW = 90

ACTIVE_CONVERSATION_CONTEXT_GAP = 8
'''

bot = replace_once(
    bot,
    active_config_old,
    active_config_new,
    "Failed direct continuation window",
)

active_expiry_old = '''    if now > active["expires_at"]:
        end_active_conversation(
            channel_id,
            user_id,
            "expired"
        )
        return False

    # -----------------------------------------------------
    # B3C / ACTIVE CONVERSATION v2
'''

active_expiry_new = '''    if now > active["expires_at"]:
        end_active_conversation(
            channel_id,
            user_id,
            "expired"
        )
        return False

    # -----------------------------------------------------
    # 3.0.1 FAILED DIRECT ATTEMPT RECOVERY
    #
    # A direct user message can legitimately start a conversation even if
    # Writer/Qwen/guards fail before Discord receives Evilnae's reply.
    # Without this bridge the immediate complaint/follow-up was previously
    # routed as an unrelated participation message.
    # -----------------------------------------------------

    if active.get("source") == "direct_attempt":
        attempt_age = max(
            0.0,
            now - float(
                active.get(
                    "last_activity_at",
                    now
                )
            )
        )

        if attempt_age <= FAILED_DIRECT_CONTINUATION_WINDOW:
            print(
                "[ACTIVE CONVERSATION RECOVERY] "
                f"user_id={user_id} "
                f"channel={channel_id} "
                f"age={attempt_age:.1f}s "
                "source=failed_direct_attempt"
            )
            return True

        end_active_conversation(
            channel_id,
            user_id,
            "direct_attempt_expired"
        )
        return False

    # -----------------------------------------------------
    # B3C / ACTIVE CONVERSATION v2
'''

bot = replace_once(
    bot,
    active_expiry_old,
    active_expiry_new,
    "Failed direct attempt continuity recovery",
)

memory_marker = '''        # =================================================
        # MEMORY BUFFER
        #
        # Ab hier war Evilnae tatsächlich
        # Teil der Interaktion.
        # =================================================
'''

attempt_bridge = '''        # =================================================
        # 3.0.1 DIRECT ATTEMPT CONTINUITY BRIDGE
        #
        # This is intentionally recorded AFTER the safety exits above.
        # A successful send later replaces source=direct_attempt with
        # source=direct/continuation as usual.
        # =================================================

        if directly_addressed:
            mark_active_conversation(
                channel_id=channel_id,
                user_id=user_id,
                source="direct_attempt"
            )

'''

bot = insert_before_once(
    bot,
    memory_marker,
    attempt_bridge,
    "Direct attempt continuity bridge",
)

baseline_warning_old = '''        else:

            print(
                "[RELIABILITY BASELINE WARNING] "
                f"user={username} "
                "reason=no_clean_baseline"
            )
'''

baseline_warning_new = '''        else:

            print(
                "[RELIABILITY BASELINE WARNING] "
                f"user={username} "
                "reason=no_clean_baseline"
            )

            # -------------------------------------------------
            # 3.0.1 DIRECT/CONTINUATION BASELINE RESCUE
            #
            # Exact failure seen live:
            # question policy -> salvage_question_shape -> empty
            # -> no safe baseline -> pre_voice SILENT FINAL.
            #
            # For an actual conversation turn, spend one targeted repair
            # slot to create a substantive statement instead of silently
            # dropping a harmless reply. Participation stays conservative.
            # -------------------------------------------------

            if not autonomous_participation:

                direct_rescue_context = (
                    writer_context
                    + "\\n\\n"
                    + """
[DIRECT REPLY RELIABILITY RESCUE]

Die aktuelle Nachricht erwartet eine echte Antwort von Evilnae.
Der vorherige Entwurf konnte wegen der Question-Policy nicht sicher gesendet werden.

Formuliere eine kurze, inhaltliche Antwort auf die User-Nachricht.
Beantworte den Inhalt DIREKT.
Wenn das Brain keine Frage erlaubt, stelle KEINE Gegenfrage.
Die Nachricht darf nicht nur aus einer Frage bestehen.
Kein generischer Ersatz-Füllsatz.
""".strip()
                )

                direct_rescue = (
                    await repair_writer_answer(
                        original_answer=answer,
                        violation_reasons=[
                            "no_safe_reliability_baseline",
                            "answer_user_directly_without_counterquestion",
                        ],
                        writer_context=direct_rescue_context,
                        current_mood=current_mood,
                        username=username,
                        token_limit=writer_token_limit,
                        autonomous_participation=False,
                    )
                )

                if direct_rescue:
                    reliability_baseline_answer = (
                        choose_reliability_fallback(
                            candidates=[
                                (
                                    "direct_baseline_rescue",
                                    direct_rescue
                                ),
                            ],
                            curiosity_result=curiosity_result,
                            self_evidence=self_evidence,
                            knowledge_constraint=knowledge_constraint,
                            username=username,
                            stage="baseline_direct_rescue",
                        )
                    )

                if reliability_baseline_answer:
                    answer = reliability_baseline_answer
                    print(
                        "[RELIABILITY DIRECT RESCUE SUCCESS] "
                        f"user={username} "
                        f"answer={answer!r}"
                    )
                else:
                    print(
                        "[RELIABILITY DIRECT RESCUE FAILED] "
                        f"user={username}"
                    )
'''

bot = replace_once(
    bot,
    baseline_warning_old,
    baseline_warning_new,
    "Question-salvage direct reply rescue",
)

# =========================================================
# ROUTING_HARDENING.PY
# =========================================================

routing = replace_once(
    routing,
    'ROUTING_HARDENING_VERSION = "1.0"',
    'ROUTING_HARDENING_VERSION = "1.1"',
    "Routing Hardening version -> 1.1",
)

third_person_marker = '''THIRD_PERSON_LEAD_PATTERN = re.compile(
'''

self_query_pattern = '''# Third-person statements can still be direct social relevance when
# Evilnae herself is the grammatical subject of a question, e.g.
# "ist evil wieder eingeschlafen" or "was macht evil eigentlich".
EVILNAE_SELF_QUERY_LEAD_PATTERN = re.compile(
    r"^\\s*(?:ist|war|hat|wird|macht|mag|findet|kann|will|kommt|"
    r"schläft|schlaeft|was|wie|warum|wieso|wann|wo)\\b",
    re.IGNORECASE,
)

'''

routing = insert_before_once(
    routing,
    third_person_marker,
    self_query_pattern,
    "Third-person Evilnae self-query detector",
)

reason_old = '''NOT_DIRECT_REASON_PATTERNS = (
    "not directly",
    "nicht direkt",
    "not addressed",
    "nicht an evilnae",
    "third person",
    "dritte person",
    "nicht angesprochen",
)
'''

reason_new = '''NOT_DIRECT_REASON_PATTERNS = (
    "not directly",
    "nicht direkt",
    "not addressed",
    "nicht an evilnae",
    "third person",
    "dritte person",
    "nicht angesprochen",
    "keinen direkten",
    "kein direkter",
    "no direct need",
    "bezieht sich auf evilnae",
    "refers to evilnae",
)
'''

routing = replace_once(
    routing,
    reason_old,
    reason_new,
    "Participation not-direct reason coverage",
)

subject_old = '''    subject_is_evilnae = (
        bool(
            _name_spans(
                text
            )
        )
        and
        not bool(
            getattr(
                perception,
                "direct_address",
                False,
            )
        )
    )

    recent_thread = (
'''

subject_new = '''    subject_is_evilnae = (
        bool(
            _name_spans(
                text
            )
        )
        and
        not bool(
            getattr(
                perception,
                "direct_address",
                False,
            )
        )
    )

    evilnae_self_query = (
        subject_is_evilnae
        and
        (
            "?" in text
            or
            bool(
                EVILNAE_SELF_QUERY_LEAD_PATTERN.search(
                    text
                )
            )
        )
    )

    recent_thread = (
'''

routing = replace_once(
    routing,
    subject_old,
    subject_new,
    "Detect third-person question about Evilnae",
)

subject_boost_old = '''        reasons.append(
            "evilnae_is_subject"
        )

    if recent_thread:
'''

subject_boost_new = '''        reasons.append(
            "evilnae_is_subject"
        )

    if evilnae_self_query:

        relevance = float(
            getattr(
                decision,
                "relevance",
                0.0,
            )
            or
            0.0
        )

        social_value = float(
            getattr(
                decision,
                "social_value",
                0.0,
            )
            or
            0.0
        )

        involvement = float(
            getattr(
                decision,
                "conversation_involvement",
                0.0,
            )
            or
            0.0
        )

        decision.relevance = max(
            relevance,
            0.90,
        )

        decision.social_value = max(
            social_value,
            0.60,
        )

        decision.conversation_involvement = max(
            involvement,
            0.65,
        )

        if (
            decision.relevance != relevance
            or decision.social_value != social_value
            or decision.conversation_involvement != involvement
        ):
            changed = True

        reasons.append(
            "evilnae_self_query"
        )

    if recent_thread:
'''

routing = replace_once(
    routing,
    subject_boost_old,
    subject_boost_new,
    "Boost questions where Evilnae is the subject",
)

# =========================================================
# EVILNAE_EMOTES.PY
# =========================================================

emotes = replace_once(
    emotes,
    'EVILNAE_EMOTE_VERSION = "1.1"',
    'EVILNAE_EMOTE_VERSION = "1.2"',
    "Evilnae Emote version -> 1.2",
)

newline_marker = '''    # Zu viele Leerzeilen.
'''

punctuation_cleanup = '''    # If a stripped Unicode/custom emoji was the final element, remove
    # punctuation that only acted as a separator before that emoji.
    # Example: "hab okay geschlafen, 😊" -> "hab okay geschlafen"
    if unicode_matches or custom_matches:
        text = re.sub(
            r"[ \\t]*[,;:]+[ \\t]*$",
            "",
            text
        )

'''

emotes = insert_before_once(
    emotes,
    newline_marker,
    punctuation_cleanup,
    "Trailing punctuation cleanup after emoji stripping",
)

# =========================================================
# VALIDATE EVERYTHING BEFORE WRITING
# =========================================================

syntax_check(bot, "bot.py")
syntax_check(routing, "routing_hardening.py")
syntax_check(emotes, "evilnae_emotes.py")

# =========================================================
# BACKUP
# =========================================================

stamp = datetime.now().astimezone().strftime("%Y%m%d-%H%M%S")
backup_dir = BACKUP_ROOT / stamp
backup_dir.mkdir(parents=True, exist_ok=False)

for source in (BOT_PATH, ROUTING_PATH, EMOTES_PATH):
    shutil.copy2(source, backup_dir / source.name)
    ok(f"Backup: {source.name}")

# =========================================================
# WRITE
# =========================================================

try:
    atomic_write(BOT_PATH, bot)
    atomic_write(ROUTING_PATH, routing)
    atomic_write(EMOTES_PATH, emotes)
except Exception as error:
    print()
    print(f"[WRITE ERROR] {type(error).__name__}: {error}")
    print(f"Restore files from: {backup_dir}")
    raise

ok("bot.py updated")
ok("routing_hardening.py updated")
ok("evilnae_emotes.py updated")

print()
print("=" * 60)
print("EVILNAE 3.0.1 FIX INSTALLED")
print("=" * 60)
print()
print("Installed:")
print("  [✓] direct reply rescue after question_salvage_empty")
print("  [✓] failed-direct continuity bridge (90s)")
print("  [✓] third-person Evilnae self-query participation boost")
print("  [✓] trailing punctuation cleanup after emoji stripping")
print("  [✓] existing UTF-8 console safety preserved")
print()
print(f"Backup: {backup_dir}")
print()
print("NEXT:")
print("  python bot.py")
print()
