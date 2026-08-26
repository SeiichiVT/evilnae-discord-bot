from pathlib import Path
from datetime import datetime
import ast
import shutil

PROJECT_ROOT = Path(__file__).resolve().parent
BOT_PATH = PROJECT_ROOT / "bot.py"
EXPRESSION_PATH = PROJECT_ROOT / "expression.py"
QUALITY_PATH = PROJECT_ROOT / "response_quality.py"
BACKUP_ROOT = PROJECT_ROOT / "live_fix_backups"

EXPECTED_BOT_VERSION = 'BOT_VERSION = "3.0.1-live-reliability"'
TARGET_BOT_VERSION = 'BOT_VERSION = "3.0.2-output-integrity"'
EXPECTED_EXPRESSION_VERSION = 'EXPRESSION_VERSION = "2.0"'
TARGET_EXPRESSION_VERSION = 'EXPRESSION_VERSION = "2.1"'
EXPECTED_QUALITY_VERSION = 'OUTPUT_QUALITY_VERSION = "2.0"'
TARGET_QUALITY_VERSION = 'OUTPUT_QUALITY_VERSION = "2.1"'


def header(text):
    print()
    print("=" * 64)
    print(text)
    print("=" * 64)


def ok(text):
    print(f"[OK] {text}")


def fail(text):
    print()
    print(f"[INSTALL ERROR] {text}")
    print("Nothing was overwritten.")
    print()
    raise SystemExit(1)


def read_utf8(path):
    if not path.exists():
        fail(f"Missing required file: {path.name}")
    return path.read_text(encoding="utf-8")


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


def replace_in_section_once(text, start_marker, end_marker, old, new, label):
    start = text.find(start_marker)
    if start < 0:
        fail(f"{label}: start marker not found")
    end = text.find(end_marker, start + len(start_marker))
    if end < 0:
        fail(f"{label}: end marker not found")
    section = text[start:end]
    count = section.count(old)
    if count != 1:
        fail(f"{label}: expected exactly 1 match in section, found {count}")
    patched = section.replace(old, new, 1)
    ok(label)
    return text[:start] + patched + text[end:]


def syntax_check(text, filename):
    try:
        ast.parse(text, filename=filename)
    except SyntaxError as error:
        fail(f"{filename}: syntax error after patch at line {error.lineno}: {error.msg}")
    ok(f"{filename} syntax check")


def atomic_write(path, text):
    temp = Path(str(path) + ".tmp")
    temp.write_text(text, encoding="utf-8")
    temp.replace(path)


header("EVILNAE 3.0.2 OUTPUT INTEGRITY FIX")
print(f"Project: {PROJECT_ROOT}")
print()
print("WICHTIG: bot.py muss vollständig AUS sein.")
print()

bot = read_utf8(BOT_PATH)
expression = read_utf8(EXPRESSION_PATH)
quality = read_utf8(QUALITY_PATH)

if TARGET_BOT_VERSION in bot and TARGET_EXPRESSION_VERSION in expression and TARGET_QUALITY_VERSION in quality:
    print("3.0.2 is already installed.")
    raise SystemExit(0)

if EXPECTED_BOT_VERSION not in bot:
    fail("Unexpected bot.py version. Expected 3.0.1-live-reliability.")
if EXPECTED_EXPRESSION_VERSION not in expression:
    fail("Unexpected expression.py version. Expected Expression 2.0.")
if EXPECTED_QUALITY_VERSION not in quality:
    fail("Unexpected response_quality.py version. Expected Output Quality 2.0.")
if 'errors="backslashreplace"' not in bot or "FAILED_DIRECT_CONTINUATION_WINDOW = 90" not in bot:
    fail("Current 3.0.1 reliability/UTF-8 base is incomplete.")

ok("3.0.1 base detected")

# Versions
bot = replace_once(bot, EXPECTED_BOT_VERSION, TARGET_BOT_VERSION, "Bot version -> 3.0.2-output-integrity")
expression = replace_once(expression, EXPECTED_EXPRESSION_VERSION, TARGET_EXPRESSION_VERSION, "Expression version -> 2.1")
quality = replace_once(quality, EXPECTED_QUALITY_VERSION, TARGET_QUALITY_VERSION, "Output Quality version -> 2.1")

# ---------------------------------------------------------
# BOT: textual content helper
# ---------------------------------------------------------
PERMANENT_MARKER = '''# =========================================================
# PERMANENT EXPRESSION GUARD
# =========================================================
'''

TEXT_HELPER = r'''# =========================================================
# 3.0.2 TEXTUAL REPLY INTEGRITY
# =========================================================
# Writer replies must contain actual textual content.
# Unicode emoji/custom-emote only output is not a text reply.
# =========================================================

_CUSTOM_EMOJI_ONLY_TOKEN_RE = re.compile(
    r"<a?:[A-Za-z0-9_]+:\d+>"
)
_DISCORD_MENTION_ONLY_TOKEN_RE = re.compile(
    r"<(?:@!?|@&|#)\d+>"
)
_COLON_EMOJI_ALIAS_RE = re.compile(
    r"(?<!\w):[A-Za-z0-9_+\-]{2,}:(?!\w)"
)


def has_textual_reply_content(answer):
    text = str(answer or "").strip()
    if not text:
        return False
    text = _CUSTOM_EMOJI_ONLY_TOKEN_RE.sub(" ", text)
    text = _DISCORD_MENTION_ONLY_TOKEN_RE.sub(" ", text)
    text = _COLON_EMOJI_ALIAS_RE.sub(" ", text)
    return bool(
        re.search(
            r"[^\W_]",
            text,
            flags=re.UNICODE,
        )
    )


'''

bot = insert_before_once(bot, PERMANENT_MARKER, TEXT_HELPER, "Textual reply integrity helper")

# ---------------------------------------------------------
# BOT: writer hard validation
# ---------------------------------------------------------
OLD = '''    if not answer:

        reasons.append(
            "empty_answer"
        )

        return reasons

    lowered = (
        answer.lower()
    )
'''
NEW = '''    if not answer:

        reasons.append(
            "empty_answer"
        )

        return reasons

    if not has_textual_reply_content(
        answer
    ):

        reasons.append(
            "no_textual_content"
        )

        return reasons

    lowered = (
        answer.lower()
    )
'''
bot = replace_in_section_once(
    bot,
    "def get_writer_violation_reasons(",
    "# =========================================================\n# WRITER REPAIR",
    OLD,
    NEW,
    "Writer rejects emoji/symbol-only replies",
)

# ---------------------------------------------------------
# BOT: repair prompt
# ---------------------------------------------------------
OLD = '''- keine gesamte Antwort in Anführungszeichen
- keine Frage wenn das Brain keine erlaubt
- keine erfundenen aktuellen Fakten
'''
NEW = '''- keine gesamte Antwort in Anführungszeichen
- die Antwort muss echten Text mit mindestens einem Wort enthalten
- keine Unicode-Emojis oder Discord-Custom-Emotes; der Emote-Layer kommt danach
- keine Frage wenn das Brain keine erlaubt
- keine erfundenen aktuellen Fakten
'''
bot = replace_in_section_once(
    bot,
    "async def repair_writer_answer(",
    "# =========================================================\n# FINALIZE WRITER ANSWER",
    OLD,
    NEW,
    "Writer repair requires real text",
)

# ---------------------------------------------------------
# BOT: reliability candidate content floor
# ---------------------------------------------------------
OLD = '''        if not candidate:

            continue

        if candidate in seen:

            continue
'''
NEW = '''        if not candidate:

            continue

        if not has_textual_reply_content(
            candidate
        ):

            print(
                "[RELIABILITY CANDIDATE REJECTED] "
                f"user={username} "
                f"stage={stage} "
                f"source={source_name} "
                "reason=no_textual_content"
            )

            continue

        if candidate in seen:

            continue
'''
bot = replace_in_section_once(
    bot,
    "def choose_reliability_fallback(",
    "# =========================================================\n# B3I CONSOLIDATED PIPELINE CANDIDATE CHOOSER",
    OLD,
    NEW,
    "Reliability rejects no-text candidates",
)

# ---------------------------------------------------------
# BOT: primary writer instruction
# ---------------------------------------------------------
OLD = '''                            input=(
                                "Formuliere jetzt "
                                "Evilnaes tatsächliche "
                                "Discord-Nachricht."
                            ),
'''
NEW = '''                            input=(
                                "Formuliere jetzt "
                                "Evilnaes tatsächliche "
                                "Discord-Nachricht. "
                                "Die Antwort muss echten Text "
                                "mit mindestens einem Wort enthalten. "
                                "Schreibe selbst keine Unicode-Emojis "
                                "oder Discord-Custom-Emotes; "
                                "der Emote-Layer kommt danach."
                            ),
'''
bot = replace_once(bot, OLD, NEW, "Primary Writer instruction requires text")

# ---------------------------------------------------------
# BOT: second rescue if writer finalization still fails
# ---------------------------------------------------------
OLD = '''            if not answer:

                print(
                    "[SILENT FINAL] "
                    f"user={username} "
                    "stage=writer_finalize "
                    "reason=no_safe_fallback"
                )

                return
'''
NEW = '''            if (
                not answer
                and
                not autonomous_participation
            ):

                writer_finalize_rescue_context = (
                    writer_context
                    + "\\n\\n"
                    + """
[WRITER OUTPUT INTEGRITY RESCUE]

Die aktuelle Nachricht erwartet eine echte Textantwort von Evilnae.
Der bisherige Entwurf enthielt keinen sicher sendbaren Text.

Antworte direkt auf den Inhalt der aktuellen User-Nachricht.
Benutze mindestens ein echtes Wort.
Keine Unicode-Emojis.
Keine Discord-Custom-Emotes.
Wenn das Brain keine Gegenfrage erlaubt, stelle keine Gegenfrage.
""".strip()
                )

                writer_finalize_rescue = (
                    await repair_writer_answer(
                        original_answer=(response.output_text or ""),
                        violation_reasons=[
                            "no_textual_content",
                            "reply_requires_real_text",
                        ],
                        writer_context=writer_finalize_rescue_context,
                        current_mood=current_mood,
                        username=username,
                        token_limit=writer_token_limit,
                        autonomous_participation=False,
                    )
                )

                if writer_finalize_rescue:
                    answer = choose_reliability_fallback(
                        candidates=[
                            (
                                "writer_finalize_text_rescue",
                                writer_finalize_rescue,
                            ),
                        ],
                        curiosity_result=curiosity_result,
                        self_evidence=self_evidence,
                        knowledge_constraint=knowledge_constraint,
                        username=username,
                        stage="writer_finalize_text_rescue",
                    )

                if answer:
                    print(
                        "[WRITER TEXT RESCUE SUCCESS] "
                        f"user={username} "
                        f"answer={answer!r}"
                    )
                else:
                    print(
                        "[WRITER TEXT RESCUE FAILED] "
                        f"user={username}"
                    )

            if not answer:

                print(
                    "[SILENT FINAL] "
                    f"user={username} "
                    "stage=writer_finalize "
                    "reason=no_safe_fallback"
                )

                return
'''
bot = replace_once(bot, OLD, NEW, "Writer-finalize text rescue")

# ---------------------------------------------------------
# BOT: post-emote final empty guard
# ---------------------------------------------------------
FRESHNESS_MARKER = '''        # =================================================
        # 12. CONTEXT FRESHNESS + SEND
'''
FINAL_EMPTY_GUARD = '''        # =================================================
        # 3.0.2 FINAL POST-EMOTE OUTPUT INVARIANT
        # Discord error 50006 must never be possible.
        # =================================================

        if not str(
            answer
            or ""
        ).strip():

            print(
                "[FINAL EMPTY GUARD] "
                f"user={username} "
                "reason=empty_after_emote_layer"
            )

            print(
                "[SILENT FINAL] "
                f"user={username} "
                "stage=post_emote "
                "reason=empty_after_emote_layer"
            )

            return

'''
bot = insert_before_once(bot, FRESHNESS_MARKER, FINAL_EMPTY_GUARD, "Final empty-send invariant")

# ---------------------------------------------------------
# EXPRESSION 2.1: remove writer/emote contradiction
# ---------------------------------------------------------
expression = replace_once(
    expression,
    '''Emoji level:
{plan.emoji_level}
''',
    '''Downstream emote tendency (NICHT vom Writer ausgeben):
{plan.emoji_level}
''',
    "Remove Writer/emoji-level ambiguity",
)
expression = replace_once(
    expression,
    '''Avoid emojis:
{avoid_emojis}
''',
    '''Avoid emotes (nur Hinweis für den downstream Emote-Layer):
{avoid_emojis}
''',
    "Clarify avoid-emotes ownership",
)
OLD = '''WICHTIG:

Ein interner Stil oder Inner State
ist keine Aufforderung,
dessen Namen in die Nachricht zu schreiben.
'''
NEW = '''WICHTIG:

EMOTE-PIPELINE:
- Schreibe selbst KEINE Unicode-Emojis.
- Schreibe selbst KEINE Discord-Custom-Emotes.
- "Downstream emote tendency" ist nur ein internes Signal für den späteren Emote-Layer.
- Deine Discord-Textantwort muss echten Text mit mindestens einem Wort enthalten.
- Eine reine Emoji-/Emote-Antwort ist keine gültige Writer-Antwort.

Ein interner Stil oder Inner State
ist keine Aufforderung,
dessen Namen in die Nachricht zu schreiben.
'''
expression = replace_once(expression, OLD, NEW, "Expression plan explicitly delegates emotes")

# ---------------------------------------------------------
# OUTPUT QUALITY 2.1: no-text is severe
# ---------------------------------------------------------
QUALITY_CONTENT_MARKER = '''# =========================================================
# CONTENT TOKEN COUNT
'''
QUALITY_HELPER = r'''# =========================================================
# 2.1 TEXTUAL CONTENT CHECK
# =========================================================

_QUALITY_CUSTOM_EMOJI_RE = re.compile(
    r"<a?:[A-Za-z0-9_]+:\d+>"
)
_QUALITY_MENTION_RE = re.compile(
    r"<(?:@!?|@&|#)\d+>"
)
_QUALITY_COLON_EMOJI_RE = re.compile(
    r"(?<!\w):[A-Za-z0-9_+\-]{2,}:(?!\w)"
)


def _has_textual_content(text: str) -> bool:
    value = str(text or "").strip()
    if not value:
        return False
    value = _QUALITY_CUSTOM_EMOJI_RE.sub(" ", value)
    value = _QUALITY_MENTION_RE.sub(" ", value)
    value = _QUALITY_COLON_EMOJI_RE.sub(" ", value)
    return bool(
        re.search(
            r"[^\W_]",
            value,
            flags=re.UNICODE,
        )
    )


'''
quality = insert_before_once(quality, QUALITY_CONTENT_MARKER, QUALITY_HELPER, "Output Quality textual-content helper")

OLD = '''    sentence_count = (
        _sentence_count(
            text
        )
    )

    # =====================================================
    # GENERIC / BOT STYLE
'''
NEW = '''    sentence_count = (
        _sentence_count(
            text
        )
    )

    # =====================================================
    # TEXTUAL CONTENT FLOOR
    # =====================================================

    if not _has_textual_content(
        text
    ):

        issues.append(
            "no_textual_content"
        )

        grammar_score += 10

    # =====================================================
    # GENERIC / BOT STYLE
'''
quality = replace_in_section_once(
    quality,
    "def analyze_response_quality(",
    "def compare_response_candidates(",
    OLD,
    NEW,
    "Output Quality penalizes no-text output",
)

# Severe check must happen before same-content acceptance.
OLD = '''    if (
        _normalize(
            candidate
        )
        ==
        _normalize(
            baseline
        )
        and
        candidate
    ):

        return result(
            True,
            "same_content"
        )

    if not candidate:

        return result(
            False,
            "empty_candidate"
        )

    if candidate_analysis.severe:

        return result(
            False,
            "candidate_severe_quality_issue"
        )
'''
NEW = '''    if not candidate:

        return result(
            False,
            "empty_candidate"
        )

    if candidate_analysis.severe:

        return result(
            False,
            "candidate_severe_quality_issue"
        )

    if (
        _normalize(
            candidate
        )
        ==
        _normalize(
            baseline
        )
        and
        candidate
    ):

        return result(
            True,
            "same_content"
        )
'''
quality = replace_in_section_once(
    quality,
    "def compare_response_candidates(",
    "def select_best_quality_candidate(",
    OLD,
    NEW,
    "Qwen severe-output check before same-content acceptance",
)

OLD = '''- Keine kaputten Satzfragmente oder Komma-Wortketten.
- Wenn der Gedanke fertig ist: aufhören.
'''
NEW = '''- Keine kaputten Satzfragmente oder Komma-Wortketten.
- Die Antwort braucht echten Text mit mindestens einem Wort.
- Keine Unicode-Emojis oder Discord-Custom-Emotes; der Emote-Layer kommt später.
- Wenn der Gedanke fertig ist: aufhören.
'''
quality = replace_once(quality, OLD, NEW, "Quality repair requires textual output")

# ---------------------------------------------------------
# Verify before writing
# ---------------------------------------------------------
for marker in (
    TARGET_BOT_VERSION,
    "def has_textual_reply_content(",
    "no_textual_content",
    "[WRITER TEXT RESCUE SUCCESS]",
    "[FINAL EMPTY GUARD]",
):
    if marker not in bot:
        fail(f"Patched bot.py missing invariant: {marker}")

for marker in (
    TARGET_EXPRESSION_VERSION,
    "Downstream emote tendency",
    "Eine reine Emoji-/Emote-Antwort",
):
    if marker not in expression:
        fail(f"Patched expression.py missing invariant: {marker}")

for marker in (
    TARGET_QUALITY_VERSION,
    "def _has_textual_content(",
    "no_textual_content",
):
    if marker not in quality:
        fail(f"Patched response_quality.py missing invariant: {marker}")

syntax_check(bot, "bot.py")
syntax_check(expression, "expression.py")
syntax_check(quality, "response_quality.py")

# Logic sanity check independent from bot imports.
import re
custom = re.compile(r"<a?:[A-Za-z0-9_]+:\d+>")
mention = re.compile(r"<(?:@!?|@&|#)\d+>")
alias = re.compile(r"(?<!\w):[A-Za-z0-9_+\-]{2,}:(?!\w)")

def has_text(value):
    value = str(value or "").strip()
    value = custom.sub(" ", value)
    value = mention.sub(" ", value)
    value = alias.sub(" ", value)
    return bool(re.search(r"[^\W_]", value, flags=re.UNICODE))

assert not has_text("😊")
assert not has_text("😊!!!")
assert not has_text("<:evilnae_love:123456>")
assert not has_text(":smile:")
assert not has_text("<@123456>")
assert has_text("bin noch da lol")
assert has_text("mir gehts gut 😊")
assert has_text("日本語")
ok("Textual-content self-test")

# ---------------------------------------------------------
# Backup + write
# ---------------------------------------------------------
timestamp = datetime.now().astimezone().strftime("%Y%m%d-%H%M%S")
backup_directory = BACKUP_ROOT / timestamp
backup_directory.mkdir(parents=True, exist_ok=False)

for path in (BOT_PATH, EXPRESSION_PATH, QUALITY_PATH):
    shutil.copy2(path, backup_directory / path.name)
    ok(f"Backup: {path.name}")

atomic_write(BOT_PATH, bot)
ok("bot.py updated")
atomic_write(EXPRESSION_PATH, expression)
ok("expression.py updated")
atomic_write(QUALITY_PATH, quality)
ok("response_quality.py updated")

header("EVILNAE 3.0.2 OUTPUT INTEGRITY INSTALLED")
print("Installed:")
print("  [✓] Writer rejects emoji-/symbol-only replies")
print("  [✓] Reliability rejects no-text candidates")
print("  [✓] Writer prompt no longer conflicts with Emote Layer")
print("  [✓] Writer-finalize targeted text rescue")
print("  [✓] Output Quality treats no-text as severe")
print("  [✓] Qwen cannot accept severe output as same-content")
print("  [✓] Final post-emote empty-send guard")
print("  [✓] Discord 50006 empty-message path blocked")
print()
print("Unchanged:")
print("  [✓] Character Foundation / Character Learning")
print("  [✓] User Memories / DB")
print("  [✓] Routing Hardening 1.1")
print("  [✓] Evilnae Emote Layer 1.2")
print()
print("Backup:")
print(f"  {backup_directory}")
print()
print("NEXT:")
print("  python bot.py")
print()
