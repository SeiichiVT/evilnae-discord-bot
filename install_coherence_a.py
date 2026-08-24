from pathlib import Path
from datetime import datetime
import ast
import re
import shutil
import sys


# =========================================================
# CONFIG
# =========================================================

BOT_PATH = Path(
    "bot.py"
)

TARGET_VERSION = (
    "2.11.0-coherence-a"
)

EXPECTED_OLD_VERSION = (
    "2.10.0-local-voice"
)


# =========================================================
# HELPERS
# =========================================================

def fail(
    message
):

    print("")
    print(
        f"[INSTALL ERROR] {message}"
    )
    print("")

    sys.exit(
        1
    )


def ok(
    message
):

    print(
        f"[OK] {message}"
    )


def replace_once(
    text,
    old,
    new,
    label
):

    if new in text:

        print(
            f"[SKIP] {label} already installed"
        )

        return text

    count = (
        text.count(
            old
        )
    )

    if count != 1:

        fail(
            f"{label}: expected marker "
            f"exactly once, found {count}"
        )

    text = text.replace(
        old,
        new,
        1
    )

    ok(
        label
    )

    return text


def insert_before_once(
    text,
    marker,
    insertion,
    label
):

    if insertion in text:

        print(
            f"[SKIP] {label} already installed"
        )

        return text

    count = (
        text.count(
            marker
        )
    )

    if count != 1:

        fail(
            f"{label}: marker expected "
            f"once, found {count}"
        )

    text = text.replace(
        marker,
        insertion
        +
        marker,
        1
    )

    ok(
        label
    )

    return text


def replace_between_markers(
    text,
    start_marker,
    end_marker,
    replacement,
    label
):

    start_count = (
        text.count(
            start_marker
        )
    )

    end_count = (
        text.count(
            end_marker
        )
    )

    if start_count != 1:

        fail(
            f"{label}: start marker expected "
            f"once, found {start_count}"
        )

    if end_count != 1:

        fail(
            f"{label}: end marker expected "
            f"once, found {end_count}"
        )

    start = (
        text.find(
            start_marker
        )
    )

    end = (
        text.find(
            end_marker,
            start
            +
            len(
                start_marker
            )
        )
    )

    if (
        start == -1
        or
        end == -1
        or
        end <= start
    ):

        fail(
            f"{label}: invalid marker order"
        )

    text = (
        text[:start]
        +
        replacement
        +
        text[end:]
    )

    ok(
        label
    )

    return text


# =========================================================
# LOAD BOT
# =========================================================

if not BOT_PATH.exists():

    fail(
        "bot.py not found. "
        "Run this installer from "
        "the Evilnae project folder."
    )


bot = BOT_PATH.read_text(
    encoding="utf-8"
)


# =========================================================
# VERSION CHECK
# =========================================================

if (
    f'BOT_VERSION = "{TARGET_VERSION}"'
    in bot
):

    print("")
    print(
        "============================================"
    )
    print(
        "2.11A is already installed."
    )
    print(
        "============================================"
    )
    print("")

    sys.exit(
        0
    )


if (
    f'BOT_VERSION = "{EXPECTED_OLD_VERSION}"'
    not in bot
):

    fail(
        "Unexpected bot.py version. "
        f"Expected {EXPECTED_OLD_VERSION}. "
        "Installer aborted so nothing gets damaged."
    )


# =========================================================
# BACKUP
# =========================================================

stamp = (
    datetime.now()
    .strftime(
        "%Y%m%d-%H%M%S"
    )
)

backup_path = Path(
    f"bot.py.before-2.11A-{stamp}.bak"
)

shutil.copy2(
    BOT_PATH,
    backup_path
)

print(
    f"[BACKUP] {backup_path}"
)


# =========================================================
# 1. EXPRESSION IMPORTS
# =========================================================

old_expression_import = '''from expression import (
    build_expression_plan,
    format_expression_plan,
    format_expression_debug,
    expression_violation_reasons,
)
'''


new_expression_import = '''from expression import (
    EXPRESSION_VERSION,
    build_expression_plan,
    format_expression_plan,
    format_expression_debug,
    expression_violation_reasons,
    apply_expression_final_guard,
    format_expression_guard_debug,
)
'''


bot = replace_once(
    bot,
    old_expression_import,
    new_expression_import,
    "Expression v2 imports"
)


# =========================================================
# 2. COHERENCE IMPORTS
# =========================================================

coherence_import = '''from coherence import (
    COHERENCE_VERSION,
    extract_evilnae_messages,
    analyze_coherence,
    bump_channel_revision,
    get_revision_delta,
    is_context_fresh,
)

'''


inner_state_marker = '''from inner_state import (
'''


bot = insert_before_once(
    bot,
    inner_state_marker,
    coherence_import,
    "Coherence imports"
)


# =========================================================
# 3. LOCAL VOICE IMPORT
#
# count_genuine_questions fixes the old:
#
# every "?" = real question
#
# problem.
# =========================================================

old_local_voice_import = '''from local_voice import (
    LOCAL_VOICE_VERSION,
    LOCAL_VOICE_ENABLED,
    humanize_evilnae_response,
    format_local_voice_debug,
    warm_local_voice,
)
'''


new_local_voice_import = '''from local_voice import (
    LOCAL_VOICE_VERSION,
    LOCAL_VOICE_ENABLED,
    humanize_evilnae_response,
    format_local_voice_debug,
    warm_local_voice,
    count_genuine_questions,
)
'''


bot = replace_once(
    bot,
    old_local_voice_import,
    new_local_voice_import,
    "Question Guard v2 import"
)


# =========================================================
# 4. BOT VERSION
# =========================================================

bot = replace_once(
    bot,
    f'BOT_VERSION = "{EXPECTED_OLD_VERSION}"',
    f'BOT_VERSION = "{TARGET_VERSION}"',
    "Bot version -> 2.11.0-coherence-a"
)


# =========================================================
# 5. EXPRESSION HISTORY
#
# ALT:
# per-user 8
#
# NEU:
# channel-wide 20
# =========================================================

bot = replace_once(
    bot,
    '''EXPRESSION_HISTORY_LIMIT = 8
''',
    '''EXPRESSION_HISTORY_LIMIT = 20
''',
    "Expression history -> 20"
)


# =========================================================
# 6. CONTEXT FRESHNESS CONFIG
# =========================================================

old_expression_config = '''EXPRESSION_VIOLATION_LOGGING = True
'''


new_expression_config = '''EXPRESSION_VIOLATION_LOGGING = True


# =========================================================
# CONTEXT FRESHNESS CONFIG
#
# Wie viele neue Channel-Ereignisse
# während Brain/Writer/Qwen entstehen dürfen,
# bevor eine Antwort als zu alt gilt.
#
# Participation ist später noch strenger.
# =========================================================

CONTEXT_FRESHNESS_MAX_NEW_MESSAGES = int(
    os.getenv(
        "CONTEXT_FRESHNESS_MAX_NEW_MESSAGES",
        "2"
    )
)
'''


bot = replace_once(
    bot,
    old_expression_config,
    new_expression_config,
    "Context freshness config"
)


# =========================================================
# 7. CHANNEL SEND LOCK STATE
#
# Generation bleibt parallel.
#
# Nur der finale:
#
# freshness check + Discord send
#
# wird pro Channel serialisiert.
# =========================================================

old_runtime_state = '''response_locks = {}

channel_contexts = {}
'''


new_runtime_state = '''response_locks = {}

channel_send_locks = {}

channel_contexts = {}
'''


bot = replace_once(
    bot,
    old_runtime_state,
    new_runtime_state,
    "Channel send lock state"
)


# =========================================================
# 8. CHANNEL SEND LOCK HELPER
# =========================================================

channel_lock_helper = '''# =========================================================
# CHANNEL SEND LOCK
#
# Wichtig:
#
# Brain/Writer/Qwen dürfen weiterhin
# für mehrere User parallel laufen.
#
# Wir serialisieren nur den letzten
# Freshness-Check + Discord-Send.
#
# Dadurch können zwei Antworten nicht
# gleichzeitig auf einem veralteten
# Channel-Zustand durchrutschen.
# =========================================================

def get_channel_send_lock(
    channel_id
):

    key = str(
        channel_id
    )

    lock = (
        channel_send_locks.get(
            key
        )
    )

    if lock is None:

        lock = (
            asyncio.Lock()
        )

        channel_send_locks[
            key
        ] = lock

    return lock


'''


legacy_mood_marker = '''# =========================================================
# INNER STATE -> LEGACY MOOD BRIDGE
# =========================================================
'''


bot = insert_before_once(
    bot,
    legacy_mood_marker,
    channel_lock_helper,
    "Channel send lock helper"
)


# =========================================================
# 9. QUESTION GUARD 2.0
#
# ALT:
#
# if "?" in answer:
#
# Das blockiert:
#
# ich? niemals.
#
# NEU:
#
# nur echte informationssuchende Fragen.
# =========================================================

old_question_guard = '''    if (
        not decision.ask_question
        and
        "?" in answer
    ):

        reasons.append(
            "question_not_allowed"
        )
'''


new_question_guard = '''    if (
        not decision.ask_question
        and
        count_genuine_questions(
            answer
        )
        > 0
    ):

        reasons.append(
            "question_not_allowed"
        )
'''


bot = replace_once(
    bot,
    old_question_guard,
    new_question_guard,
    "Question Guard 2.0"
)


# =========================================================
# 10. WRITER CONTEXT SIGNATURE
#
# Writer bekommt jetzt zusätzlich
# channelweite Evilnae-Ausgaben.
# =========================================================

old_writer_signature = '''def build_writer_context(
    *,
    state,
    decision,
    expression_plan,
    inner_state_guidance,
    learned_behavior_text,
    participation_context_text,
    username,
    user_text,
    emoji_context_text,
    reply_context_text,
    special_user_prompt
):
'''


new_writer_signature = '''def build_writer_context(
    *,
    state,
    decision,
    expression_plan,
    inner_state_guidance,
    learned_behavior_text,
    participation_context_text,
    channel_recent_evilnae_messages=None,
    username,
    user_text,
    emoji_context_text,
    reply_context_text,
    special_user_prompt
):
'''


bot = replace_once(
    bot,
    old_writer_signature,
    new_writer_signature,
    "Writer channel-history parameter"
)


# =========================================================
# 11. WRITER HISTORY SOURCE
# =========================================================

old_writer_history = '''    recent_evilnae = (
        state.history
        .recent_evilnae_messages
    )
'''


new_writer_history = '''    recent_evilnae = list(
        channel_recent_evilnae_messages
        or
        state.history
        .recent_evilnae_messages
    )
'''


bot = replace_once(
    bot,
    old_writer_history,
    new_writer_history,
    "Writer uses channel-wide Evilnae history"
)


# =========================================================
# 12. THIRD-PERSON NAME MENTION -> PARTICIPATION HINT
#
# Perception 2.0 erkennt jetzt:
#
# "Evil sagt da was anderes"
#
# als Mention, NICHT direkte Ansprache.
#
# Participation bekommt einen leichten Hinweis.
# =========================================================

old_participation_context = '''    channel_context_text = (
        format_channel_context(
            channel_snapshot
        )
    )

    participant_context_text = (
'''


new_participation_context = '''    channel_context_text = (
        format_channel_context(
            channel_snapshot
        )
    )

    # -----------------------------------------------------
    # THIRD-PERSON EVILNAE MENTION
    #
    # Beispiel:
    #
    # "Sicher? Evil sagt da was anderes."
    #
    # Das ist KEINE direkte Ansprache.
    #
    # Es erhöht aber natürlich die Relevanz,
    # falls Evilnae sich freiwillig einmischen will.
    # -----------------------------------------------------

    if (
        getattr(
            perception,
            "name_mentioned",
            False
        )
        and
        not getattr(
            perception,
            "direct_address",
            False
        )
    ):

        channel_context_text += """
        
[PERCEPTION HINWEIS]
Evilnae wurde in der aktuellen Nachricht
in dritter Person erwähnt.

Das ist KEINE direkte Ansprache.

Es ist nur ein leichtes Relevanzsignal
für freiwillige Participation.

Nicht allein deshalb antworten.
""".rstrip()

    participant_context_text = (
'''


bot = replace_once(
    bot,
    old_participation_context,
    new_participation_context,
    "Third-person mention participation hint"
)


# =========================================================
# 13. STARTUP DISPLAY
# =========================================================

old_expression_ready = '''    print(
        "Expression Layer v1: ACTIVE"
    )
'''


new_expression_ready = '''    print(
        f"Expression Layer v"
        f"{EXPRESSION_VERSION}: ACTIVE"
    )

    print(
        f"Coherence v"
        f"{COHERENCE_VERSION}: ACTIVE"
    )

    print(
        "Channel-wide Repetition Guard: ACTIVE"
    )

    print(
        "Expression Final Guard: ACTIVE"
    )

    print(
        "Context Freshness Guard: ACTIVE "
        f"(max={CONTEXT_FRESHNESS_MAX_NEW_MESSAGES})"
    )
'''


bot = replace_once(
    bot,
    old_expression_ready,
    new_expression_ready,
    "Startup 2.11A status"
)


# =========================================================
# 14. INCOMING CHANNEL REVISION
#
# Jede echte User-Nachricht bewegt
# die Revision des Channels.
# =========================================================

old_username_block = '''    username = (
        perception.username
    )

    # =====================================================
    # 2. OBSERVE EVERYTHING
'''


new_username_block = '''    username = (
        perception.username
    )

    # =====================================================
    # CONTEXT REVISION
    #
    # Diese Revision gehört zum Zustand,
    # auf dessen Basis diese Antwort startet.
    #
    # Wenn während Brain/Writer/Qwen
    # zu viel Neues passiert,
    # wird die Antwort später verworfen.
    # =====================================================

    response_start_revision = (
        bump_channel_revision(
            channel_id
        )
    )

    # =====================================================
    # 2. OBSERVE EVERYTHING
'''


bot = replace_once(
    bot,
    old_username_block,
    new_username_block,
    "Incoming channel revision"
)


# =========================================================
# 15. CHANNEL-WIDE EVILNAE HISTORY
# =========================================================

old_snapshot_block = '''    channel_snapshot = list(
        get_channel_context(
            channel_id
        )
    )

    # =====================================================
    # FEEDBACK TEXT
'''


new_snapshot_block = '''    channel_snapshot = list(
        get_channel_context(
            channel_id
        )
    )

    # =====================================================
    # CHANNEL-WIDE EVILNAE HISTORY
    #
    # Nicht mehr:
    #
    # "Was hat Evilnae zuletzt nur
    #  zu DIESEM User gesagt?"
    #
    # Sondern:
    #
    # "Was hat Evilnae zuletzt
    #  im gesamten Channel gesagt?"
    # =====================================================

    channel_evilnae_messages = (
        extract_evilnae_messages(
            channel_snapshot,
            limit=30
        )
    )

    channel_coherence_analysis = (
        analyze_coherence(
            channel_evilnae_messages
        )
    )

    # =====================================================
    # FEEDBACK TEXT
'''


bot = replace_once(
    bot,
    old_snapshot_block,
    new_snapshot_block,
    "Channel-wide Evilnae history"
)


# =========================================================
# 16. EXPRESSION HISTORY SOURCE
# =========================================================

old_expression_history = '''        recent_expression_messages = (
            state.history
            .recent_evilnae_messages[
                -EXPRESSION_HISTORY_LIMIT:
            ]
        )
'''


new_expression_history = '''        recent_expression_messages = (
            channel_evilnae_messages[
                -EXPRESSION_HISTORY_LIMIT:
            ]
        )
'''


bot = replace_once(
    bot,
    old_expression_history,
    new_expression_history,
    "Expression uses channel-wide history"
)


# =========================================================
# 17. EXPRESSION GETS COHERENCE ANALYSIS
# =========================================================

old_expression_call_end = '''                is_hanae=(
                    is_hanae
                )
            )
        )

        if (
            inner_style_hint
'''


new_expression_call_end = '''                is_hanae=(
                    is_hanae
                ),

                coherence_analysis=(
                    channel_coherence_analysis
                )
            )
        )

        if (
            inner_style_hint
'''


bot = replace_once(
    bot,
    old_expression_call_end,
    new_expression_call_end,
    "Expression receives Coherence analysis"
)


# =========================================================
# 18. WRITER GETS CHANNEL-WIDE HISTORY
# =========================================================

old_writer_call = '''                participation_context_text=(
                    participation_context_text
                ),

                username=username,
'''


new_writer_call = '''                participation_context_text=(
                    participation_context_text
                ),

                channel_recent_evilnae_messages=(
                    channel_evilnae_messages[
                        -20:
                    ]
                ),

                username=username,
'''


bot = replace_once(
    bot,
    old_writer_call,
    new_writer_call,
    "Writer receives channel-wide history"
)


# =========================================================
# 19. REFRESH HISTORY BEFORE LOCAL VOICE
#
# Zwischen Brain und Qwen können bereits
# neue Evilnae-Antworten entstanden sein.
#
# Deshalb bekommt Qwen eine frische Snapshot-History.
# =========================================================

old_voice_start = '''        original_writer_answer = (
            answer
        )

        try:
'''


new_voice_start = '''        # -------------------------------------------------
        # FRESH CHANNEL HISTORY FOR LOCAL VOICE
        # -------------------------------------------------

        voice_channel_snapshot = list(
            get_channel_context(
                channel_id
            )
        )

        voice_channel_evilnae_messages = (
            extract_evilnae_messages(
                voice_channel_snapshot,
                limit=30
            )
        )

        voice_coherence_analysis = (
            analyze_coherence(
                voice_channel_evilnae_messages,
                candidate=answer
            )
        )

        original_writer_answer = (
            answer
        )

        try:
'''


bot = replace_once(
    bot,
    old_voice_start,
    new_voice_start,
    "Fresh Local Voice channel history"
)


# =========================================================
# 20. LOCAL VOICE ARGUMENTS
# =========================================================

old_voice_arguments = '''                    recent_evilnae_messages=(
                        state.history
                        .recent_evilnae_messages
                    )
                )
'''


new_voice_arguments = '''                    recent_evilnae_messages=(
                        state.history
                        .recent_evilnae_messages
                    ),

                    channel_recent_evilnae_messages=(
                        voice_channel_evilnae_messages
                    ),

                    coherence_analysis=(
                        voice_coherence_analysis
                    )
                )
'''


bot = replace_once(
    bot,
    old_voice_arguments,
    new_voice_arguments,
    "Local Voice receives channel-wide Coherence"
)


# =========================================================
# 21. EXPRESSION FINAL GUARD
#
# Das alte bot.py hat Verstöße nur geloggt:
#
# [EXPRESSION VIOLATION]
#
# und die Antwort TROTZDEM gesendet.
#
# Jetzt:
#
# 1. sichere Reparaturen deterministisch
# 2. wenn nötig Writer Repair
# 3. erneut prüfen
# 4. nur dann send()
# =========================================================

expression_logging_start = '''        # =================================================
        # EXPRESSION LOGGING
        # =================================================
'''


send_marker = '''        # =================================================
        # 12. SEND
'''


new_expression_final = '''        # =================================================
        # 11.6 EXPRESSION FINAL GUARD
        #
        # Jetzt wird nicht mehr nur geloggt.
        #
        # Dieser Layer darf sicher:
        #
        # - überbenutzte Emojis entfernen
        # - Emoji-Budget durchsetzen
        # - überbenutzte Opener entfernen
        #
        # Bedeutungsrelevante Probleme:
        #
        # - Assistant Structure
        # - Concept Cooldown
        # - Generic Filler
        # - Semantic Repetition
        #
        # werden NICHT mechanisch gelöscht.
        #
        # Dafür gibt es genau einen
        # echten Writer-Repair-Durchlauf.
        # =================================================

        final_channel_snapshot = list(
            get_channel_context(
                channel_id
            )
        )

        final_channel_evilnae_messages = (
            extract_evilnae_messages(
                final_channel_snapshot,
                limit=30
            )
        )

        final_coherence_analysis = (
            analyze_coherence(
                final_channel_evilnae_messages
            )
        )

        final_expression_plan = (
            build_expression_plan(

                recent_messages=(
                    final_channel_evilnae_messages[
                        -EXPRESSION_HISTORY_LIMIT:
                    ]
                ),

                tone=(
                    decision.tone
                ),

                mood=(
                    current_mood
                ),

                relationship_text=(
                    state.memory.relationship
                ),

                is_hanae=(
                    is_hanae
                ),

                coherence_analysis=(
                    final_coherence_analysis
                )
            )
        )

        if (
            inner_style_hint
            in {
                "dry",
                "playful",
                "chaotic",
                "warm",
                "deadpan",
                "natural",
            }
        ):

            final_expression_plan.style = (
                inner_style_hint
            )

        final_expression_plan = (
            apply_learned_behavior_to_expression_plan(

                final_expression_plan,

                is_hanae=is_hanae
            )
        )

        expression_guard = (
            apply_expression_final_guard(
                answer,
                final_expression_plan
            )
        )

        print(
            format_expression_guard_debug(
                expression_guard
            )
        )

        # -------------------------------------------------
        # SAFE DETERMINISTIC CLEANUP SUCCESS
        # -------------------------------------------------

        if expression_guard.send_allowed:

            answer = (
                expression_guard.cleaned
            )

        # -------------------------------------------------
        # MEANING-RELEVANT EXPRESSION PROBLEM
        #
        # Nicht einfach senden.
        #
        # Writer bekommt EINEN echten Repair.
        # -------------------------------------------------

        else:

            expression_repair_context = (
                writer_context
                + "\\n\\n"
                + "==================================================\\n"
                + "FINAL CHANNEL-WIDE EXPRESSION PLAN\\n"
                + "==================================================\\n\\n"
                + format_expression_plan(
                    final_expression_plan
                )
            )

            expression_repair = (
                await repair_writer_answer(

                    original_answer=(
                        expression_guard.cleaned
                        or
                        answer
                    ),

                    violation_reasons=(
                        expression_guard
                        .violations_after
                    ),

                    writer_context=(
                        expression_repair_context
                    ),

                    current_mood=(
                        current_mood
                    ),

                    username=(
                        username
                    ),

                    token_limit=(
                        writer_token_limit
                    ),

                    autonomous_participation=(
                        autonomous_participation
                    )
                )
            )

            if not expression_repair:

                print(
                    "[EXPRESSION FINAL ABORT] "
                    f"user={username} "
                    "reason=repair_failed "
                    f"violations="
                    f"{expression_guard.violations_after}"
                )

                return

            expression_repair = (
                clean_generated_answer(
                    expression_repair
                )
            )

            expression_repair = (
                enforce_permanent_expression_bans(
                    expression_repair
                )
            )

            # ---------------------------------------------
            # HARD WRITER RULES AGAIN
            # ---------------------------------------------

            repair_hard_violations = (
                get_writer_violation_reasons(

                    answer=(
                        expression_repair
                    ),

                    decision=(
                        decision
                    ),

                    autonomous_participation=(
                        autonomous_participation
                    )
                )
            )

            if repair_hard_violations:

                print(
                    "[EXPRESSION FINAL ABORT] "
                    f"user={username} "
                    "reason=hard_guard_after_repair "
                    f"violations="
                    f"{repair_hard_violations}"
                )

                return

            # ---------------------------------------------
            # EXPRESSION GUARD AGAIN
            # ---------------------------------------------

            second_expression_guard = (
                apply_expression_final_guard(
                    expression_repair,
                    final_expression_plan
                )
            )

            print(
                format_expression_guard_debug(
                    second_expression_guard
                )
            )

            if not (
                second_expression_guard
                .send_allowed
            ):

                print(
                    "[EXPRESSION FINAL ABORT] "
                    f"user={username} "
                    "reason=still_blocked_after_repair "
                    f"violations="
                    f"{second_expression_guard.violations_after}"
                )

                return

            answer = (
                second_expression_guard.cleaned
            )

'''


bot = replace_between_markers(
    bot,
    expression_logging_start,
    send_marker,
    new_expression_final,
    "Expression Final Guard integration"
)


# =========================================================
# 22. CONTEXT FRESHNESS + SERIALIZED SEND
#
# Der alte SEND-Block wird vollständig ersetzt.
#
# Wichtig:
#
# Wir serialisieren NICHT Brain/Qwen.
#
# Nur:
#
# final freshness check
# +
# Discord send
#
# Dadurch bleibt der Bot schnell,
# aber veraltete Antworten kommen
# deutlich schwerer durch.
# =========================================================

send_start = '''        # =================================================
        # 12. SEND
'''


context_update_marker = '''        # =================================================
        # 13. DIRECT USER CONTEXT UPDATE
'''


new_send_block = '''        # =================================================
        # 12. CONTEXT FRESHNESS + SEND
        #
        # DIRECT / CONTINUATION:
        #
        # maximal normale Freshness-Toleranz.
        #
        # PARTICIPATION:
        #
        # strenger, weil ein freiwilliger Einwurf
        # sehr schnell unpassend werden kann.
        # =================================================

        channel_send_lock = (
            get_channel_send_lock(
                channel_id
            )
        )

        async with channel_send_lock:

            if autonomous_participation:

                freshness_limit = (
                    min(
                        1,
                        CONTEXT_FRESHNESS_MAX_NEW_MESSAGES
                    )
                )

            else:

                freshness_limit = (
                    CONTEXT_FRESHNESS_MAX_NEW_MESSAGES
                )

            freshness_delta = (
                get_revision_delta(
                    channel_id,
                    response_start_revision
                )
            )

            if not (
                is_context_fresh(

                    channel_id,
                    response_start_revision,
                    max_new_messages=(
                        freshness_limit
                    )
                )
            ):

                print(
                    "[CONTEXT STALE] "
                    f"user={username} "
                    f"mode="
                    f"{voice_conversation_mode} "
                    f"start_revision="
                    f"{response_start_revision} "
                    f"delta="
                    f"{freshness_delta} "
                    f"limit="
                    f"{freshness_limit} "
                    f"answer="
                    f"{answer!r}"
                )

                return

            try:

                if (
                    autonomous_participation
                    or
                    conversation_continuation
                ):

                    sent_message = (
                        await message.channel.send(
                            answer[:1900]
                        )
                    )

                else:

                    sent_message = (
                        await message.reply(
                            answer[:1900],
                            mention_author=False
                        )
                    )

            except discord.HTTPException as error:

                print(
                    "[DISCORD SEND ERROR] "
                    f"user={username} "
                    f"error={error}"
                )

                return

            # ---------------------------------------------
            # Eigene Nachricht verändert ebenfalls
            # den Channel-Zustand.
            #
            # Dadurch sehen parallel generierte
            # Antworten diese Änderung.
            # ---------------------------------------------

            bump_channel_revision(
                channel_id
            )

            register_channel_message(
                is_bot=True
            )

'''


bot = replace_between_markers(
    bot,
    send_start,
    context_update_marker,
    new_send_block,
    "Context Freshness + serialized send"
)


# =========================================================
# 23. INITIATIVE REVISION
#
# Initiative v2 kommt später.
#
# Für 2.11A muss eine Initiative
# aber wenigstens die Channel-Revision
# verändern.
# =========================================================

old_initiative_register = '''    register_initiative()

    register_channel_message(
        is_bot=True
    )
'''


new_initiative_register = '''    bump_channel_revision(
        str(
            channel.id
        )
    )

    register_initiative()

    register_channel_message(
        is_bot=True
    )
'''


bot = replace_once(
    bot,
    old_initiative_register,
    new_initiative_register,
    "Initiative revision tracking"
)


# =========================================================
# 24. SOCIAL ACTION REVISION
# =========================================================

old_social_register = '''    register_autonomous_ping(
        target_user_id
    )
'''


new_social_register = '''    bump_channel_revision(
        channel_id
    )

    register_autonomous_ping(
        target_user_id
    )
'''


bot = replace_once(
    bot,
    old_social_register,
    new_social_register,
    "Social action revision tracking"
)


# =========================================================
# 25. SYNTAX CHECK
#
# WICHTIG:
#
# Noch bevor bot.py überschrieben wird.
# =========================================================

try:

    ast.parse(
        bot,
        filename=str(
            BOT_PATH
        )
    )

except SyntaxError as error:

    print("")
    print(
        "============================================"
    )
    print(
        "SYNTAX CHECK FAILED"
    )
    print(
        "============================================"
    )

    print(
        f"Line: {error.lineno}"
    )

    print(
        f"Offset: {error.offset}"
    )

    print(
        f"Error: {error.msg}"
    )

    print("")

    print(
        "bot.py was NOT overwritten."
    )

    print(
        f"Backup is still available: "
        f"{backup_path}"
    )

    sys.exit(
        1
    )


ok(
    "Python syntax check"
)


# =========================================================
# 26. ATOMIC WRITE
# =========================================================

temp_path = Path(
    "bot.py.2.11A.tmp"
)

temp_path.write_text(
    bot,
    encoding="utf-8"
)

temp_path.replace(
    BOT_PATH
)

ok(
    "bot.py written"
)


# =========================================================
# 27. POST-INSTALL VERIFY
# =========================================================

installed = (
    BOT_PATH.read_text(
        encoding="utf-8"
    )
)

required_markers = {

    "bot version":
        f'BOT_VERSION = "{TARGET_VERSION}"',

    "coherence import":
        "COHERENCE_VERSION",

    "expression final":
        "apply_expression_final_guard",

    "freshness":
        "CONTEXT_FRESHNESS_MAX_NEW_MESSAGES",

    "send lock":
        "get_channel_send_lock",

    "channel history":
        "channel_evilnae_messages",

    "local voice channel history":
        "channel_recent_evilnae_messages",

    "question guard":
        "count_genuine_questions",

    "context stale":
        "[CONTEXT STALE]",
}


missing = [

    name

    for (
        name,
        marker
    )
    in required_markers.items()

    if marker not in installed
]


if missing:

    fail(
        "Post-install verification failed: "
        +
        ", ".join(
            missing
        )
    )


# =========================================================
# SUCCESS
# =========================================================

print("")
print(
    "============================================"
)
print(
    "EVILNAE 2.11A INSTALL COMPLETE"
)
print(
    "============================================"
)

print(
    f"Bot Version: {TARGET_VERSION}"
)

print(
    f"Backup: {backup_path}"
)

print("")
print(
    "Installed:"
)
print(
    "  [✓] Channel-wide Evilnae history"
)
print(
    "  [✓] Coherence v1 integration"
)
print(
    "  [✓] Expression v2 integration"
)
print(
    "  [✓] Expression Final Guard"
)
print(
    "  [✓] Local Voice channel-wide history"
)
print(
    "  [✓] Question Guard 2.0"
)
print(
    "  [✓] Direct mention vs third-person mention bridge"
)
print(
    "  [✓] Context Freshness Guard"
)
print(
    "  [✓] Per-channel final send lock"
)
print(
    "  [✓] Initiative revision tracking"
)
print(
    "  [✓] Social-action revision tracking"
)

print("")
print(
    "NEXT:"
)
print(
    "python -m py_compile "
    "bot.py coherence.py perception.py "
    "expression.py inner_state.py "
    "local_voice.py"
)

print("")
print(
    "Then:"
)
print(
    "python bot.py"
)

print(
    "============================================"
)