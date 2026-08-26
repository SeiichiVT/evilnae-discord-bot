from pathlib import Path
from datetime import datetime
import ast
import shutil
import sys
BOT_PATH = Path('bot.py')
PARTICIPATION_PATH = Path('participation.py')
EMOTE_PATH = Path('evilnae_emotes.py')
UNDERSTANDING_PATH = Path('conversation_understanding.py')
EXPECTED_BOT_VERSION = '2.11.9-evilnae-emotes-v1'
TARGET_BOT_VERSION = '2.12.0-context-b3c'
TARGET_PARTICIPATION_VERSION = '1.1'
TARGET_EMOTE_VERSION = '1.1'

def fail(message):
    print(f'\n[INSTALL ERROR] {message}\n')
    sys.exit(1)

def ok(message):
    print(f'[OK] {message}')

def replace_once(text, old, new, label):
    if new in text:
        print(f'[SKIP] {label}')
        return text
    count = text.count(old)
    if count != 1:
        fail(f'{label}: expected 1 match, found {count}')
    result = text.replace(old, new, 1)
    ok(label)
    return result

def replace_section(text, start_marker, end_marker, replacement, label):
    if replacement in text:
        print(f'[SKIP] {label}')
        return text
    start = text.find(start_marker)
    if start < 0:
        fail(f'{label}: start marker not found')
    end = text.find(end_marker, start + len(start_marker))
    if end < 0:
        fail(f'{label}: end marker not found')
    result = text[:start] + replacement + text[end:]
    ok(label)
    return result

def syntax_check(text, filename):
    try:
        ast.parse(text, filename=filename)
    except SyntaxError as error:
        fail(f'{filename} syntax error after patch: line={error.lineno} {error.msg}. Nothing overwritten.')
    ok(f'{filename} syntax check')
print('[B3C CONTEXT FIX PACK] starting...')
for path in (BOT_PATH, PARTICIPATION_PATH, EMOTE_PATH, UNDERSTANDING_PATH):
    if not path.exists():
        fail(f'{path} missing')
bot = BOT_PATH.read_text(encoding='utf-8')
participation = PARTICIPATION_PATH.read_text(encoding='utf-8')
emotes = EMOTE_PATH.read_text(encoding='utf-8')
understanding = UNDERSTANDING_PATH.read_text(encoding='utf-8')
if f'BOT_VERSION = "{TARGET_BOT_VERSION}"' in bot:
    print('B3C already installed.')
    sys.exit(0)
if f'BOT_VERSION = "{EXPECTED_BOT_VERSION}"' not in bot:
    fail(f'Unexpected bot version. Expected {EXPECTED_BOT_VERSION}. Push/restore the current 2.11.9 state first.')
if 'CONVERSATION_UNDERSTANDING_VERSION = "1.0"' not in understanding:
    fail('conversation_understanding.py is not v1.0')
bot = replace_once(bot, 'from evilnae_emotes import (\n    EVILNAE_EMOTE_VERSION,\n    load_application_emojis,\n    apply_evilnae_emote_layer,\n    format_evilnae_emote_debug,\n)\n\nfrom dotenv import load_dotenv\n', 'from evilnae_emotes import (\n    EVILNAE_EMOTE_VERSION,\n    load_application_emojis,\n    apply_evilnae_emote_layer,\n    format_evilnae_emote_debug,\n)\n\nfrom conversation_understanding import (\n    CONVERSATION_UNDERSTANDING_VERSION,\n    upgrade_perception_addressing,\n    format_address_upgrade_debug,\n    build_reference_context,\n    build_episode_focus,\n    build_participation_hint,\n    salvage_question_shape,\n    analyze_garbled_output,\n    format_garbled_debug,\n)\n\nfrom dotenv import load_dotenv\n', 'Conversation Understanding imports')
bot = replace_once(bot, f'BOT_VERSION = "{EXPECTED_BOT_VERSION}"', f'BOT_VERSION = "{TARGET_BOT_VERSION}"', 'Bot version')
bot = replace_once(bot, '    print(\n        "Maximum One Evilnae Emote Per Reply: ACTIVE"\n    )\n\n    print(\n        f"Response Agency v"\n', '    print(\n        "Maximum One Evilnae Emote Per Reply: ACTIVE"\n    )\n\n    print(\n        f"Conversation Understanding v"\n        f"{CONVERSATION_UNDERSTANDING_VERSION}: ACTIVE"\n    )\n\n    print(\n        "Direct Address Resolver v2: ACTIVE"\n    )\n\n    print(\n        "Reference / Ellipsis Resolver: ACTIVE"\n    )\n\n    print(\n        "Group Thread Continuity v2: ACTIVE"\n    )\n\n    print(\n        "Question Guard Fail-Safe: ACTIVE"\n    )\n\n    print(\n        "Garbled Output Guard: ACTIVE"\n    )\n\n    print(\n        f"Response Agency v"\n', 'B3C startup status')
bot = replace_once(bot, '    print(\n        format_perception_debug(\n            perception\n        )\n    )\n', '    # =====================================================\n    # B3C DIRECT ADDRESS RESOLVER v2\n    #\n    # Perception v2.0.1 ist bewusst konservativ.\n    # Diese zweite Stufe fängt soziale Vocatives ab wie:\n    #\n    # "schönen tag dir noch evil"\n    # "WOW EVIL WOW"\n    #\n    # ohne echte Third-Person-Erwähnungen pauschal direkt\n    # zu machen.\n    # =====================================================\n\n    address_upgrade = (\n        upgrade_perception_addressing(\n            perception\n        )\n    )\n\n    if address_upgrade.changed:\n        print(\n            format_address_upgrade_debug(\n                address_upgrade\n            )\n        )\n\n    print(\n        format_perception_debug(\n            perception\n        )\n    )\n', 'Direct Address Resolver integration')
world_marker = '    # =====================================================\n    # 2.11B2 CONVERSATION WORLD OBSERVATION\n'
reference_block = '    # =====================================================\n    # B3C REFERENCE / EPISODE CONTEXT\n    # =====================================================\n\n    b3c_reference_context_text = (\n        build_reference_context(\n            perception.text or perception.raw_content or "",\n            channel_snapshot,\n            current_user_id=user_id,\n        )\n    )\n\n    b3c_episode_focus_text = (\n        build_episode_focus(\n            channel_snapshot,\n            limit=10,\n        )\n    )\n\n'
if reference_block not in bot:
    idx = bot.find(world_marker)
    if idx < 0:
        fail('Reference/Episode integration marker not found')
    bot = bot[:idx] + reference_block + bot[idx:]
    ok('Reference / Episode context integration')
else:
    print('[SKIP] Reference / Episode context integration')
active_start = 'def is_active_conversation_continuation(\n'
active_end = '# =========================================================\n# PARTICIPANT CACHE\n'
active_replacement = 'def is_active_conversation_continuation(\n    *,\n    channel_id,\n    user_id,\n    channel_snapshot\n):\n\n    key = get_active_conversation_key(\n        channel_id,\n        user_id\n    )\n\n    active = active_conversations.get(\n        key\n    )\n\n    if not active:\n        return False\n\n    now = time.time()\n\n    if now > active["expires_at"]:\n        end_active_conversation(\n            channel_id,\n            user_id,\n            "expired"\n        )\n        return False\n\n    # -----------------------------------------------------\n    # B3C / ACTIVE CONVERSATION v2\n    #\n    # Discord ist ein Gruppengespräch.\n    # Eine andere Person, die kurz dazwischen schreibt,\n    # beendet den Strang NICHT automatisch.\n    #\n    # Der Target Guard entscheidet anschließend weiterhin,\n    # ob die aktuelle Nachricht explizit an jemand anderen\n    # gerichtet ist.\n    # -----------------------------------------------------\n\n    previous_items = channel_snapshot[:-1]\n    checked = 0\n\n    for item in reversed(previous_items):\n        if checked >= ACTIVE_CONVERSATION_CONTEXT_GAP:\n            break\n\n        checked += 1\n        item_type = item.get("type")\n\n        if item_type != "bot":\n            # Andere User dürfen sich einmischen, ohne den\n            # laufenden Strang zu töten.\n            continue\n\n        reply_to_id = str(\n            item.get("reply_to_id") or ""\n        )\n\n        if reply_to_id == str(user_id):\n            return True\n\n        # Participation ohne Reply-ID gehört nicht automatisch\n        # zu diesem User. Wir laufen einfach weiter zurück.\n\n    return False\n\n\n'
bot = replace_section(bot, active_start, active_end, active_replacement, 'Active Conversation v2')
part_hint_start = '    # -----------------------------------------------------\n    # THIRD-PERSON EVILNAE MENTION\n'
part_hint_end = '    participant_context_text = (\n'
part_hint_replacement = '    # -----------------------------------------------------\n    # B3C PARTICIPATION CONTEXT\n    #\n    # Third-person mention != direct address,\n    # aber auch NICHT "irrelevant".\n    # Außerdem kann Evilnae mitten in einer gemeinsamen\n    # Gruppenepisode stecken, obwohl gerade jemand anderes\n    # spricht.\n    # -----------------------------------------------------\n\n    participation_hint_text = (\n        build_participation_hint(\n            perception,\n            channel_snapshot,\n            hanae_user_id=HANAE_USER_ID,\n        )\n    )\n\n    if participation_hint_text:\n        channel_context_text += (\n            "\\n\\n"\n            + participation_hint_text\n        )\n\n'
bot = replace_section(bot, part_hint_start, part_hint_end, part_hint_replacement, 'Participation context v2')
bot = replace_once(bot, '        group_context_text += (\n            "\\n\\n"\n            +\n            world_brain_text\n            +\n            "\\n\\n"\n            +\n            self_model_brain_text\n        )\n', '        group_context_text += (\n            "\\n\\n"\n            + world_brain_text\n            + "\\n\\n"\n            + self_model_brain_text\n            + "\\n\\n"\n            + b3c_reference_context_text\n            + "\\n\\n"\n            + b3c_episode_focus_text\n        )\n', 'Brain gets Reference / Episode context')
writer_world_marker = '        # =====================================================\n        # 2.11B2 WORLD EVIDENCE -> WRITER\n'
writer_context_block = '        # =====================================================\n        # B3C REFERENCE / EPISODE -> WRITER\n        # =====================================================\n\n        writer_context += (\n            "\\n\\n"\n            + b3c_reference_context_text\n            + "\\n\\n"\n            + b3c_episode_focus_text\n        )\n\n'
if writer_context_block not in bot:
    idx = bot.find(writer_world_marker)
    if idx < 0:
        fail('Writer B3C context marker not found')
    bot = bot[:idx] + writer_context_block + bot[idx:]
    ok('Writer gets Reference / Episode context')
else:
    print('[SKIP] Writer gets Reference / Episode context')
bot = replace_once(bot, '    print(\n        "[WRITER VALIDATION FAILED] "\n        f"user={username}"\n    )\n\n    return ""\n', '    # -----------------------------------------------------\n    # B3C QUESTION FAIL-SAFE\n    #\n    # A harmless direct reply must not disappear only because\n    # the Writer kept appending an unapproved question.\n    # -----------------------------------------------------\n\n    if (\n        reasons\n        and\n        set(reasons).issubset({"question_not_allowed"})\n    ):\n        salvaged = salvage_question_shape(\n            current_answer,\n            allow_question=bool(decision.ask_question),\n        )\n\n        if salvaged:\n            salvage_reasons = get_writer_violation_reasons(\n                answer=salvaged,\n                decision=decision,\n                autonomous_participation=autonomous_participation,\n            )\n\n            if not salvage_reasons:\n                print(\n                    "[WRITER QUESTION FAILSAFE SUCCESS] "\n                    f"user={username} "\n                    f"before={current_answer!r} "\n                    f"after={salvaged!r}"\n                )\n                return salvaged\n\n    print(\n        "[WRITER VALIDATION FAILED] "\n        f"user={username}"\n    )\n\n    return ""\n', 'Writer question fail-safe')
q_start = '        # =====================================================\n        # B3B.1A.1 PRE-VOICE QUESTION SHAPE GUARD\n'
q_end = '        original_writer_answer = (\n'
q_replacement = '        # =====================================================\n        # B3C PRE-VOICE QUESTION SHAPE GUARD + FAIL-SAFE\n        # =====================================================\n\n        pre_voice_question_violations = (\n            question_output_violation_reasons(\n                answer,\n                curiosity_result\n            )\n        )\n\n        if pre_voice_question_violations:\n            print(\n                "[QUESTION SHAPE VIOLATION] "\n                f"user={username} "\n                f"violations={pre_voice_question_violations} "\n                f"answer={answer!r}"\n            )\n\n            source_before_question_repair = answer\n\n            question_repair_context = (\n                writer_context\n                + "\\n\\n"\n                + format_curiosity_for_writer(\n                    curiosity_result\n                )\n            )\n\n            question_repair = await repair_writer_answer(\n                original_answer=answer,\n                violation_reasons=pre_voice_question_violations,\n                writer_context=question_repair_context,\n                current_mood=current_mood,\n                username=username,\n                token_limit=writer_token_limit,\n                autonomous_participation=autonomous_participation,\n            )\n\n            repair_ok = False\n\n            if question_repair:\n                question_repair = clean_generated_answer(\n                    question_repair\n                )\n                question_repair = enforce_permanent_expression_bans(\n                    question_repair\n                )\n\n                question_repair_hard = get_writer_violation_reasons(\n                    answer=question_repair,\n                    decision=decision,\n                    autonomous_participation=autonomous_participation,\n                )\n                question_repair_violations = (\n                    question_output_violation_reasons(\n                        question_repair,\n                        curiosity_result\n                    )\n                )\n\n                repair_ok = (\n                    not question_repair_hard\n                    and\n                    not question_repair_violations\n                )\n\n            if repair_ok:\n                answer = question_repair\n                print(\n                    "[QUESTION SHAPE REPAIR SUCCESS] "\n                    f"user={username}"\n                )\n            else:\n                # Deterministic salvage from the original draft first.\n                # Example:\n                # "pizza? jetzt hast du mich hungrig gemacht. lief\'s gut?"\n                # -> "jetzt hast du mich hungrig gemacht."\n                salvage_sources = [\n                    source_before_question_repair,\n                    question_repair or "",\n                ]\n\n                salvaged = ""\n\n                for salvage_source in salvage_sources:\n                    candidate = salvage_question_shape(\n                        salvage_source,\n                        allow_question=bool(curiosity_result.allowed),\n                    )\n\n                    if not candidate:\n                        continue\n\n                    candidate_hard = get_writer_violation_reasons(\n                        answer=candidate,\n                        decision=decision,\n                        autonomous_participation=autonomous_participation,\n                    )\n                    candidate_questions = (\n                        question_output_violation_reasons(\n                            candidate,\n                            curiosity_result\n                        )\n                    )\n\n                    if not candidate_hard and not candidate_questions:\n                        salvaged = candidate\n                        break\n\n                if salvaged:\n                    print(\n                        "[QUESTION SHAPE FAILSAFE SUCCESS] "\n                        f"user={username} "\n                        f"answer={salvaged!r}"\n                    )\n                    answer = salvaged\n                else:\n                    print(\n                        "[QUESTION SHAPE ABORT] "\n                        f"user={username} "\n                        "reason=repair_and_failsafe_failed"\n                    )\n                    return\n\n'
bot = replace_section(bot, q_start, q_end, q_replacement, 'Question Shape Fail-Safe')
voice_guard_marker = '            # ---------------------------------------------\n            # FINAL EVILNAE HARD GUARD\n'
voice_garbled_block = '            # ---------------------------------------------\n            # B3C LOCAL VOICE GARBLED GUARD\n            #\n            # Qwen darf einen semantisch guten Writer-Draft\n            # nicht durch Komma-/Fragment-Salat ersetzen.\n            # ---------------------------------------------\n\n            voice_garbled_analysis = analyze_garbled_output(\n                voice_candidate\n            )\n\n            if voice_garbled_analysis.garbled:\n                print(\n                    "[LOCAL VOICE GARBLED REJECT] "\n                    f"user={username} "\n                    f"score={voice_garbled_analysis.score} "\n                    f"matches={voice_garbled_analysis.matches} "\n                    f"candidate={voice_candidate!r}"\n                )\n                voice_candidate = ""\n\n'
if voice_garbled_block not in bot:
    idx = bot.find(voice_guard_marker)
    if idx < 0:
        fail('Local Voice garbled marker not found')
    bot = bot[:idx] + voice_garbled_block + bot[idx:]
    ok('Local Voice Garbled Guard')
else:
    print('[SKIP] Local Voice Garbled Guard')
emote_layer_marker = '        # =================================================\n        # 11.9 EVILNAE APPLICATION EMOTE LAYER\n'
final_garbled_block = '        # =================================================\n        # B3C FINAL GARBLED OUTPUT GUARD\n        # =================================================\n\n        final_garbled_analysis = analyze_garbled_output(\n            answer\n        )\n\n        if final_garbled_analysis.garbled:\n            print(\n                format_garbled_debug(\n                    final_garbled_analysis\n                )\n            )\n\n            fallback_candidate = clean_generated_answer(\n                original_writer_answer\n            )\n\n            fallback_garbled = analyze_garbled_output(\n                fallback_candidate\n            )\n\n            fallback_questions = (\n                question_output_violation_reasons(\n                    fallback_candidate,\n                    curiosity_result\n                )\n            )\n\n            fallback_self = self_knowledge_violation_reasons(\n                fallback_candidate,\n                self_evidence\n            )\n\n            fallback_knowledge = knowledge_violation_reasons(\n                fallback_candidate,\n                knowledge_constraint\n            )\n\n            if (\n                fallback_candidate\n                and\n                not fallback_garbled.garbled\n                and\n                not fallback_questions\n                and\n                not fallback_self\n                and\n                not fallback_knowledge\n            ):\n                print(\n                    "[GARBLED OUTPUT REVERT SUCCESS] "\n                    f"user={username}"\n                )\n                answer = fallback_candidate\n            else:\n                garbled_repair = await repair_writer_answer(\n                    original_answer=answer,\n                    violation_reasons=[\n                        "garbled_or_grammatically_broken_output",\n                        *final_garbled_analysis.matches,\n                    ],\n                    writer_context=writer_context,\n                    current_mood=current_mood,\n                    username=username,\n                    token_limit=writer_token_limit,\n                    autonomous_participation=autonomous_participation,\n                )\n\n                garbled_repair = clean_generated_answer(\n                    garbled_repair\n                )\n\n                repair_garbled = analyze_garbled_output(\n                    garbled_repair\n                )\n\n                repair_questions = (\n                    question_output_violation_reasons(\n                        garbled_repair,\n                        curiosity_result\n                    )\n                )\n\n                repair_self = self_knowledge_violation_reasons(\n                    garbled_repair,\n                    self_evidence\n                )\n\n                repair_knowledge = knowledge_violation_reasons(\n                    garbled_repair,\n                    knowledge_constraint\n                )\n\n                if (\n                    garbled_repair\n                    and\n                    not repair_garbled.garbled\n                    and\n                    not repair_questions\n                    and\n                    not repair_self\n                    and\n                    not repair_knowledge\n                ):\n                    print(\n                        "[GARBLED OUTPUT REPAIR SUCCESS] "\n                        f"user={username}"\n                    )\n                    answer = garbled_repair\n                else:\n                    print(\n                        "[GARBLED OUTPUT ABORT] "\n                        f"user={username} "\n                        "reason=no_safe_fallback"\n                    )\n                    return\n\n'
if final_garbled_block not in bot:
    idx = bot.find(emote_layer_marker)
    if idx < 0:
        fail('Final Garbled Guard / Emote marker not found')
    bot = bot[:idx] + final_garbled_block + bot[idx:]
    ok('Final Garbled Output Guard')
else:
    print('[SKIP] Final Garbled Output Guard')
participation = replace_once(participation, 'PARTICIPATION_VERSION = "1.0"', 'PARTICIPATION_VERSION = "1.1"', 'Participation version')
participation = replace_once(participation, '        elif (\n            relevance < 0.45\n            and\n            conversation_involvement < 0.55\n        ):\n', '        elif (\n            relevance < 0.35\n            and\n            conversation_involvement < 0.45\n        ):\n', 'Participation relevance gate')
participation = replace_once(participation, '        elif (\n            social_value < 0.35\n            and\n            conversation_involvement < 0.70\n        ):\n', '        elif (\n            social_value < 0.25\n            and\n            conversation_involvement < 0.60\n        ):\n', 'Participation social gate')
participation = replace_once(participation, 'Das bedeutet NICHT automatisch,\ndass Evilnae schweigen muss.\n\nAber:\n', 'Das bedeutet NICHT automatisch,\ndass Evilnae schweigen muss.\n\nWICHTIG FÜR GRUPPENCHATS:\n\n- "nicht direkt angesprochen" ist NICHT dasselbe wie "irrelevant"\n- wenn über Evilnae gesprochen wird, kann relevance hoch sein\n- "Arme Evil", "Evil mag Hanae" oder Kommentare über ihre Pizza\n  betreffen Evilnae eindeutig, auch in dritter Person\n- wenn Evilnae wenige Nachrichten vorher Teil derselben Situation war,\n  darf conversation_involvement hoch bleiben, obwohl jemand dazwischen schrieb\n- besonders bei laufenden Bits/Ereignissen mit Hanae darf eine Zwischenmeldung\n  den sozialen Zusammenhang nicht automatisch auf null setzen\n- trotzdem muss Evilnae nicht auf jede Erwähnung reagieren\n\nAber:\n', 'Participation group-chat semantics')
emotes = replace_once(emotes, 'EVILNAE_EMOTE_VERSION = "1.0"', 'EVILNAE_EMOTE_VERSION = "1.1"', 'Emote version')
fire_marker = 'FIRE_PATTERNS = [\n'
negative_block = 'NEGATIVE_CONTEXT_PATTERNS = [\n    re.compile(\n        r"\\b(?:nervt|nervig|nerven|scheiße|scheisse|scheiß|scheiss|"\n        r"kotzen|frust|frustriert|schlimm|ätzend|aetzend|abfuck|"\n        r"unangenehm|nicht gut|kaputt)\\w*\\b",\n        re.IGNORECASE\n    ),\n]\n\n\n'
if negative_block not in emotes:
    idx = emotes.find(fire_marker)
    if idx < 0:
        fail('Emote FIRE_PATTERNS marker not found')
    emotes = emotes[:idx] + negative_block + emotes[idx:]
    ok('Negative emote context patterns')
else:
    print('[SKIP] Negative emote context patterns')
emotes = replace_once(emotes, '    fire_score = (\n        _score_patterns(\n            answer,\n            FIRE_PATTERNS\n        )\n    )\n\n    if fire_score >= 1:\n', '    fire_score = (\n        _score_patterns(\n            answer,\n            FIRE_PATTERNS\n        )\n    )\n\n    negative_context_score = (\n        _score_patterns(\n            combined,\n            NEGATIVE_CONTEXT_PATTERNS\n        )\n    )\n\n    if (\n        fire_score >= 1\n        and\n        negative_context_score == 0\n    ):\n', 'Emote fire valence guard')
syntax_check(bot, 'bot.py')
syntax_check(participation, 'participation.py')
syntax_check(emotes, 'evilnae_emotes.py')
syntax_check(understanding, 'conversation_understanding.py')
required_bot_markers = [f'BOT_VERSION = "{TARGET_BOT_VERSION}"', 'CONVERSATION_UNDERSTANDING_VERSION', 'Direct Address Resolver v2: ACTIVE', 'Reference / Ellipsis Resolver: ACTIVE', 'Group Thread Continuity v2: ACTIVE', 'Question Guard Fail-Safe: ACTIVE', 'Garbled Output Guard: ACTIVE', '[QUESTION SHAPE FAILSAFE SUCCESS]', '[LOCAL VOICE GARBLED REJECT]', '[GARBLED OUTPUT REVERT SUCCESS]']
missing = [marker for marker in required_bot_markers if marker not in bot]
if missing:
    fail('Bot verification missing: ' + ', '.join(missing))
if 'PARTICIPATION_VERSION = "1.1"' not in participation:
    fail('Participation v1.1 verification failed')
if 'EVILNAE_EMOTE_VERSION = "1.1"' not in emotes:
    fail('Emote v1.1 verification failed')
stamp = datetime.now().strftime('%Y%m%d-%H%M%S')
backups = []
for path in (BOT_PATH, PARTICIPATION_PATH, EMOTE_PATH):
    backup = Path(f'{path.name}.before-B3C-{stamp}.bak')
    shutil.copy2(path, backup)
    backups.append(backup)
    print(f'[BACKUP] {backup}')
for path, content in ((BOT_PATH, bot), (PARTICIPATION_PATH, participation), (EMOTE_PATH, emotes)):
    tmp = Path(f'{path.name}.B3C.tmp')
    tmp.write_text(content, encoding='utf-8')
    tmp.replace(path)
    ok(f'{path} written')
print('\n============================================')
print('EVILNAE B3C CONTEXT FIX PACK COMPLETE')
print('============================================')
print(f'Bot Version: {TARGET_BOT_VERSION}')
print('Conversation Understanding: 1.0')
print(f'Participation: {TARGET_PARTICIPATION_VERSION}')
print(f'Evilnae Emotes: {TARGET_EMOTE_VERSION}')
print('')
print('Installed:')
print('  [✓] Direct Address Resolver v2')
print('  [✓] Reference / Ellipsis Context')
print('  [✓] Discord Episode Focus')
print('  [✓] Group Thread Continuity v2')
print('  [✓] Participation group-chat semantics')
print('  [✓] Question Guard deterministic fail-safe')
print('  [✓] Local Voice Garbled Output rejection')
print('  [✓] Final Garbled Output fallback')
print('  [✓] Emote positive/negative valence guard')
print('')
print('Character/Self/Lore data: UNCHANGED')
print('')
print('Backups:')
for backup in backups:
    print(f'  {backup}')
print('')
print('NEXT:')
print('python conversation_understanding.py')
print('python -m py_compile bot.py participation.py evilnae_emotes.py conversation_understanding.py brain.py curiosity.py self_model.py agency.py conversation_world.py understanding.py perception.py natural_response.py naturalness.py coherence.py expression.py inner_state.py local_voice.py')
print('python bot.py')
print('============================================')
