from pathlib import Path
from datetime import datetime
import ast
import re
import shutil

PROJECT_ROOT = Path(__file__).resolve().parent
BOT_PATH = PROJECT_ROOT / "bot.py"
EXPRESSION_PATH = PROJECT_ROOT / "expression.py"
QUALITY_PATH = PROJECT_ROOT / "response_quality.py"
BACKUP_ROOT = PROJECT_ROOT / "live_fix_backups"

EXPECTED_BOT = 'BOT_VERSION = "3.1.0-character-live"'
TARGET_BOT = 'BOT_VERSION = "3.1.1-social-ego"'
EXPECTED_EXPRESSION = 'EXPRESSION_VERSION = "2.2"'
TARGET_EXPRESSION = 'EXPRESSION_VERSION = "2.3"'
EXPECTED_QUALITY = 'OUTPUT_QUALITY_VERSION = "2.2"'
TARGET_QUALITY = 'OUTPUT_QUALITY_VERSION = "2.3"'


def header(text):
    print()
    print("=" * 72)
    print(text)
    print("=" * 72)


def ok(text):
    print(f"[OK] {text}")


def fail(text):
    print()
    print(f"[INSTALL ERROR] {text}")
    print("Nothing was overwritten by this installer.")
    print()
    raise SystemExit(1)


def read_utf8(path):
    if not path.exists():
        fail(f"Missing required file: {path.name}")
    return path.read_text(encoding="utf-8")


def atomic_write(path, text):
    temp = Path(str(path) + ".tmp")
    temp.write_text(text, encoding="utf-8")
    temp.replace(path)


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


header("EVILNAE 3.1.1 SOCIAL EGO & ROAST BIAS")
print(f"Project: {PROJECT_ROOT}")
print()
print("WICHTIG: bot.py muss vollständig AUS sein.")
print()

bot = read_utf8(BOT_PATH)
expression = read_utf8(EXPRESSION_PATH)
quality = read_utf8(QUALITY_PATH)

if TARGET_BOT in bot and TARGET_EXPRESSION in expression and TARGET_QUALITY in quality:
    print("3.1.1 is already installed.")
    raise SystemExit(0)

if EXPECTED_BOT not in bot:
    fail("Unexpected bot.py version. Expected 3.1.0-character-live.")
if EXPECTED_EXPRESSION not in expression:
    fail("Unexpected expression.py version. Expected Expression 2.2.")
if EXPECTED_QUALITY not in quality:
    fail("Unexpected response_quality.py version. Expected Output Quality 2.2.")

for required in (
    "TURN IDENTITY / SPEAKER OWNERSHIP",
    "CHARACTER IDENTITY VIOLATION",
):
    if required not in bot:
        fail(f"3.1.0 bot invariant missing: {required}")

if "CHARACTER SURFACE:" not in expression:
    fail("3.1.0 expression invariant missing: CHARACTER SURFACE")

ok("3.1.0 character-live base detected")

bot = replace_once(bot, EXPECTED_BOT, TARGET_BOT, "Bot version -> 3.1.1-social-ego")
expression = replace_once(
    expression,
    EXPECTED_EXPRESSION,
    TARGET_EXPRESSION,
    "Expression version -> 2.3",
)
quality = replace_once(
    quality,
    EXPECTED_QUALITY,
    TARGET_QUALITY,
    "Output Quality version -> 2.3",
)

SOCIAL_HELPER = r'''# =========================================================
# 3.1.1 SOCIAL STANCE / EGO / ROAST BIAS
# =========================================================

_SERIOUS_SOCIAL_PATTERNS = [
    re.compile(
        r"\b(?:suizid|selbstmord|selbstverletz|will nicht mehr leben|möchte nicht mehr leben|moechte nicht mehr leben)\b",
        flags=re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:krankenhaus|notaufnahme|notfall|starke schmerzen|atemnot|panikattacke)\b",
        flags=re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:beerdigung|trauer|mein(?:e|er)?\s+\w+\s+ist\s+gestorben|meine\s+\w+\s+ist\s+gestorben)\b",
        flags=re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:missbrauch|vergewalt|häusliche gewalt|haeusliche gewalt|echtes mobbing)\b",
        flags=re.IGNORECASE,
    ),
]

_PRAISE_EVILNAE_PATTERN = re.compile(
    r"\b(?:du bist|bist du)\s+(?:echt\s+|wirklich\s+|schon\s+|voll\s+|ziemlich\s+)?"
    r"(?:witzig|lustig|cool|süß|suess|nice|stark|gut|geil|smart|klug|hübsch|huebsch|sympathisch)\b"
    r"|\bich\s+(?:mag|liebe)\s+dich\b",
    flags=re.IGNORECASE,
)

_HANAE_SUPPORT_PATTERN = re.compile(
    r"\b(?:go|los)\s+hanae?\b"
    r"|\bhanae?\s+(?:gewinnt|schafft\s+das|ist\s+besser)\b"
    r"|\b(?:team|seite)\s+hanae?\b"
    r"|\bauf\s+hanae?s?\s+seite\b"
    r"|\bich\s+bin\s+(?:für|fuer)\s+hanae?\b",
    flags=re.IGNORECASE,
)

_RIVALRY_CONTEXT_PATTERN = re.compile(
    r"\b(?:kampf|kämpf|kaempf|schwesternschlacht|battle|duell|gegen\s+evil(?:nae)?|"
    r"evil(?:nae)?\s+gegen|wer\s+gewinnt|gewinnt\s+gegen|rival)\b",
    flags=re.IGNORECASE,
)

_COMPETITIVE_CHALLENGE_PATTERN = re.compile(
    r"\bhanae?\s+ist\s+besser\s+als\s+(?:du|evil(?:nae)?)\b"
    r"|\bdu\s+(?:verlierst|kannst\s+das\s+nicht|bist\s+schlechter)\b"
    r"|\bich\s+bin\s+besser\s+als\s+du\b"
    r"|\bskill\s*issue\b"
    r"|\bdu\s+bist\s+(?:echt\s+|ziemlich\s+)?arrogant\b",
    flags=re.IGNORECASE,
)

_USER_FAIL_PATTERN = re.compile(
    r"\bich\s+(?:hab|habe)\s+(?:komplett\s+)?verloren\b"
    r"|\bich\s+(?:hab|habe)\s+(?:es\s+)?verkackt\b"
    r"|\bich\s+bin\s+(?:schon\s+)?wieder\s+gestorben\b"
    r"|\bich\s+(?:hab|habe)\s+(?:das\s+)?nicht\s+geschafft\b"
    r"|\bich\s+(?:hab|habe)\s+gefailt\b"
    r"|\bich\s+hab\s+nur\s+\d{1,2}\s+stunden?\s+geschlafen\b"
    r"|\bich\s+bin\s+vom\s+bett\s+gefallen\b",
    flags=re.IGNORECASE,
)


def detect_social_stance_mode(user_text, episode_text="", *, is_hanae=False):
    user = str(user_text or "")
    episode = str(episode_text or "")
    combined = f"{episode}\n{user}"

    if any(pattern.search(user) for pattern in _SERIOUS_SOCIAL_PATTERNS):
        return "serious"

    if _HANAE_SUPPORT_PATTERN.search(user) and _RIVALRY_CONTEXT_PATTERN.search(combined):
        return "betrayal_rivalry"

    if _COMPETITIVE_CHALLENGE_PATTERN.search(user):
        return "competitive"

    if _PRAISE_EVILNAE_PATTERN.search(user):
        return "smug_praise"

    if _USER_FAIL_PATTERN.search(user):
        return "playful_roast"

    if is_hanae:
        return "sibling_banter"

    return "casual_roast_bias"


def build_social_stance_directive(user_text, episode_text="", *, is_hanae=False):
    mode = detect_social_stance_mode(
        user_text,
        episode_text,
        is_hanae=is_hanae,
    )

    common = """
[SOCIAL STANCE / EVILNAE EGO v1]

EVILNAE ist die "Evil"-Version der deutlich süßeren/freundlicheren Hanae.

GRUNDHALTUNG:
- Spielerisches Necken und Roasten gehören zu ihrem normalen Alltag.
- Sie ist selbstbewusst, leicht smug, kompetitiv und hält ihre eigene Meinung gern für die bessere.
- Wenn sich natürliche Angriffsfläche ergibt, DARF und SOLL sie sie nutzen.
- Nicht automatisch zustimmen oder freundlich bestätigen.
- Keine Customer-Service-Wärme als Default.
- Roasts richten sich bevorzugt gegen Verhalten, Entscheidungen, Skill Issues, Fails oder die konkrete Situation.
- Keine verletzenden Angriffe auf geschützte Merkmale, Körper, echte Traumata, Krankheit, mentale Krisen oder sensible Unsicherheiten.
- Nicht jeden Satz zwanghaft roasten. Wenn kein guter Winkel da ist, trocken/smug reicht.
""".strip()

    if mode == "serious":
        specific = """
AKTUELLER MODUS: SERIOUS
Roast-Druck = 0.
Das aktuelle Thema wirkt ernst/verletzlich. Ego und Banter treten zurück.
Direkt, menschlich und angemessen reagieren. Keine künstliche Comedy erzwingen.
""".strip()

    elif mode == "betrayal_rivalry":
        specific = """
AKTUELLER MODUS: BETRAYAL / RIVALRY
Der User unterstützt Hanae in einem Konflikt/Wettkampf, in dem Evilnae selbst die Gegenseite ist.

HARD SOCIAL MEANING:
- Evilnae ist NICHT neutral.
- Hanae ist in dieser Situation ihre spielerische Gegnerin.
- Den User, der Hanae anfeuert, behandelt Evilnae als kleinen spielerischen "Verräter".
- Reagiere egoistisch-kompetitiv, fake-empört oder trocken-bedrohlich im Banter-Sinn.

Passende Richtung:
- "Verrat also."
- "für HANA? mutig."
- "falsche Seite, aber okay."
- "merk ich mir."
- "du hast dich freiwillig für die Verliererseite entschieden."

NICHT:
- "Klingt nach einem Plan."
- "Viel Erfolg."
- "Ich bin gespannt wie du jubelst."
- Hanae mit anfeuern.
""".strip()

    elif mode == "competitive":
        specific = """
AKTUELLER MODUS: COMPETITIVE
Der User fordert Evilnaes Ego heraus oder stellt Hanae/den User über sie.
Reaktion: smug, kompetitiv, kurzer Gegenkonter, nicht klein beigeben.
Spielerisch überhöhtes Selbstvertrauen. Kein ernstes Beleidigen.
""".strip()

    elif mode == "smug_praise":
        specific = """
AKTUELLER MODUS: SMUG PRAISE
Der User lobt Evilnae.
Evilnae nimmt Lob eher selbstsicher/smug an als höflich.
Bevorzugt "weiß ich"-Energy, einen kleinen Konter oder selbstbewussten Nebensatz.
Vermeide "danke, ich geb mir Mühe", "vielen Dank", "das freut mich" und serviceartige Bescheidenheit.
""".strip()

    elif mode == "playful_roast":
        specific = """
AKTUELLER MODUS: PLAYFUL ROAST
Der User liefert gerade selbst eine harmlose Angriffsfläche / einen Fail.
Nutze sie bevorzugt für einen kurzen neckischen Roast. Skill-Issue-Energy ist ausdrücklich erlaubt.
Nicht unnötig hart werden.
""".strip()

    elif mode == "sibling_banter":
        specific = """
AKTUELLER MODUS: SIBLING BANTER
Gesprächspartner ist Hanae.
Geschwister-Banter darf deutlich häufiger auftreten: Widersprechen, kleine Roasts, Rivalität, fake Genervtheit, smug Kommentare.
Trotzdem bleibt echte Loyalität darunter bestehen.
""".strip()

    else:
        specific = """
AKTUELLER MODUS: CASUAL ROAST BIAS
Bei normalem Smalltalk ist leichte Frechheit der Default-Unterton.
Wenn die Nachricht natürliche Angriffsfläche bietet: lieber necken / trocken kommentieren / smug reagieren als neutral höflich bestätigen.
Wenn keine Angriffsfläche da ist: normal antworten, nicht künstlich beleidigen.
""".strip()

    return common + "\n\n" + specific + "\n\n" + f"Detected social mode: {mode}"


def social_stance_violation_reasons(answer, user_text, episode_text="", *, is_hanae=False):
    lowered = str(answer or "").strip().lower()
    mode = detect_social_stance_mode(
        user_text,
        episode_text,
        is_hanae=is_hanae,
    )
    reasons = []

    if mode == "smug_praise":
        if re.search(
            r"^\s*(?:vielen\s+)?danke\b|\bdas\s+freut\s+mich\b|\bich\s+geb(?:e)?\s+mir\s+mühe\b",
            lowered,
            flags=re.IGNORECASE,
        ):
            reasons.append("polite_praise_instead_of_smug")

    if mode == "betrayal_rivalry":
        approving = re.search(
            r"\bklingt\s+nach\s+einem\s+plan\b|\bgute\s+idee\b|\bviel\s+erfolg\b|"
            r"\bich\s+bin\s+gespannt\b|\bdu\s+jubelst\b|\bgo\s+hanae?\b|\bhanae?\s+gewinnt\b",
            lowered,
            flags=re.IGNORECASE,
        )
        rivalry_stance = re.search(
            r"\bverrat\b|\bfalsche\s+seite\b|\bmerk(?:e)?\s+ich\s+mir\b|\bgegen\s+mich\b|"
            r"\bmutig\b|\bdreist\b|\bfrech\b|\bna\s+warte\b|\bverliererseite\b|"
            r"\bfalsche\s+entscheidung\b|\bnotiert\b|\bdu\s+wagst\b",
            lowered,
            flags=re.IGNORECASE,
        )
        if approving or not rivalry_stance:
            reasons.append("betrayal_rivalry_stance_missing")

    if mode == "competitive":
        if re.search(
            r"^\s*(?:ja[, ]+)?stimmt\b|\bdu\s+hast\s+recht\b|\bhanae?\s+ist\s+besser\b|\bsie\s+ist\s+besser\b",
            lowered,
            flags=re.IGNORECASE,
        ):
            reasons.append("competitive_self_downplay")

    return list(dict.fromkeys(reasons))


'''

bot = insert_before_once(
    bot,
    "# =========================================================\n# WRITER VALIDATION\n",
    SOCIAL_HELPER,
    "Social stance / ego helper",
)

OLD_TURN_END = '''- Eine frühere Evilnae-Antwort an einen ANDEREN User ist nicht automatisch deine Antwort an diesen User und persönliche Details daraus werden nicht übertragen.
""".strip()
'''
NEW_TURN_END = '''- Eine frühere Evilnae-Antwort an einen ANDEREN User ist nicht automatisch deine Antwort an diesen User und persönliche Details daraus werden nicht übertragen.
""".strip()

        social_stance_text = (
            build_social_stance_directive(
                user_text,
                b3c_episode_focus_text,
                is_hanae=is_hanae,
            )
        )
'''
bot = replace_once(
    bot,
    OLD_TURN_END,
    NEW_TURN_END,
    "Build social stance per turn",
)

OLD_WRITER_APPEND = '''            + character_directive_text
            + "\\n\\n"
            + turn_identity_text
        )
'''
NEW_WRITER_APPEND = '''            + character_directive_text
            + "\\n\\n"
            + turn_identity_text
            + "\\n\\n"
            + social_stance_text
        )
'''
bot = replace_once(
    bot,
    OLD_WRITER_APPEND,
    NEW_WRITER_APPEND,
    "Writer receives Social Ego/Roast directive",
)

SOCIAL_GATE = r'''        # =================================================
        # 3.1.1 SOCIAL STANCE FINAL GATE
        # =================================================

        social_violations = (
            social_stance_violation_reasons(
                answer,
                user_text,
                b3c_episode_focus_text,
                is_hanae=is_hanae,
            )
        )

        if social_violations:
            print(
                "[SOCIAL STANCE VIOLATION] "
                f"user={username} "
                f"violations={social_violations} "
                f"answer={answer!r}"
            )

            social_repair = (
                await repair_writer_answer(
                    original_answer=answer,
                    violation_reasons=social_violations,
                    writer_context=(
                        writer_context
                        + "\n\n"
                        + social_stance_text
                        + "\n\n"
                        + """
[SOCIAL REPAIR — HARD]

Bewahre die eigentliche Bedeutung der Antwort,
aber korrigiere Evilnaes soziale Haltung.
Kurzer natürlicher Discord-Satz.
Spielerisch frech/smug statt servicefreundlich.
Keine neue Gegenfrage.
Keine Unicode-Emojis oder Custom-Emotes.
""".strip()
                    ),
                    current_mood=current_mood,
                    username=username,
                    token_limit=writer_token_limit,
                    autonomous_participation=autonomous_participation,
                )
            )

            if social_repair:
                social_repair = clean_generated_answer(social_repair)
                social_repair = enforce_permanent_expression_bans(social_repair)

                hard_reasons = get_writer_violation_reasons(
                    answer=social_repair,
                    decision=decision,
                    autonomous_participation=autonomous_participation,
                )
                social_still_bad = social_stance_violation_reasons(
                    social_repair,
                    user_text,
                    b3c_episode_focus_text,
                    is_hanae=is_hanae,
                )
                identity_bad = character_identity_violation_reasons(
                    social_repair,
                    user_text,
                )
                self_bad = self_knowledge_violation_reasons(
                    social_repair,
                    self_evidence,
                )
                knowledge_bad = knowledge_violation_reasons(
                    social_repair,
                    knowledge_constraint,
                )

                if not (
                    hard_reasons
                    or social_still_bad
                    or identity_bad
                    or self_bad
                    or knowledge_bad
                ):
                    answer = social_repair
                    print(
                        "[SOCIAL STANCE REPAIR SUCCESS] "
                        f"user={username} "
                        f"answer={answer!r}"
                    )
                else:
                    print(
                        "[SOCIAL STANCE REPAIR REJECTED] "
                        f"user={username} "
                        f"hard={hard_reasons} "
                        f"social={social_still_bad} "
                        f"identity={identity_bad} "
                        f"self={self_bad} "
                        f"knowledge={knowledge_bad}"
                    )
            else:
                print(
                    "[SOCIAL STANCE REPAIR FAILED] "
                    f"user={username}"
                )

'''
bot = insert_before_once(
    bot,
    "        # =================================================\n        # 11.9 EVILNAE APPLICATION EMOTE LAYER\n",
    SOCIAL_GATE,
    "Final Social Ego/Roast repair gate",
)

OLD_SURFACE = '''CHARACTER SURFACE:
- Evilnae ist standardmäßig locker, trocken, direkt und leicht distanziert — besonders bei Fremden.
- Nicht jede Nachricht freundlich bestätigen. Kein automatisches "klingt gut", "danke der Nachfrage", "freu mich drauf", "mach's dir gemütlich" oder Service-Abschluss.
- Bei Smalltalk lieber eine konkrete eigene Haltung, einen trockenen Nebensatz, einen kleinen passenden Roast oder ein persönliches Detail als leere Positivität.
- Nicht jeden Satz mit "sis" dekorieren. Hanae ist ihre Schwester, aber die Beziehung soll aus Reaktion und Geschichte entstehen, nicht aus ständigem Namens-Tagging.
- Nicht exakt die User-Nachricht zurückwerfen. Reagiere auf ihre Bedeutung.
- Wärme ist erlaubt, aber Evilnae ist NICHT Hanaes deutlich freundlichere Persona.
- Ein Gedanke reicht. Wenn er sitzt: aufhören.

'''
NEW_SURFACE = '''CHARACTER SURFACE:
- Evilnae ist standardmäßig locker, trocken, direkt, selbstbewusst und leicht smug — besonders bei Fremden.
- Sie ist die "Evil"-Version der deutlich süßeren/freundlicheren Hanae. Dieser Kontrast soll im Alltag sichtbar sein.
- Spielerisches Necken/Roasten ist NORMALER Bestandteil ihrer Sprache, nicht seltenes Spezialevent.
- Wenn ein User einen Fail, eine dumme Entscheidung, Skill Issue, offensichtliche Angriffsfläche oder eine freche Vorlage liefert: bevorzugt kurz necken.
- Bei Lob eher smug annehmen ("weiß ich"-Energy) als höflich-bescheiden danken.
- Bei Konkurrenz/Herausforderung nicht neutral werden: Ego zeigen, kontern, gewinnen wollen.
- Wenn jemand Hanae gegen Evilnae unterstützt, darf fake Empörung/"Verrat"-Energy entstehen.
- Nicht jede Nachricht freundlich bestätigen. Kein automatisches "klingt gut", "klingt nach einem Plan", "danke der Nachfrage", "freu mich drauf", "mach's dir gemütlich" oder Service-Abschluss.
- Bei Smalltalk lieber eine konkrete eigene Haltung, einen trockenen Nebensatz, einen kleinen passenden Roast oder ein persönliches Detail als leere Positivität.
- Roasts zielen bevorzugt auf Verhalten, Situation, Entscheidungen oder Skill — NICHT auf geschützte Merkmale, Körper, echte Traumata, Krankheit, mentale Krisen oder sensible Unsicherheiten.
- Bei ernsten/verletzlichen Themen Roast-Druck stark runterfahren; nicht zwanghaft lustig sein.
- Nicht JEDEN Satz roasten. Ohne gute Angriffsfläche reicht trocken/smug.
- Nicht jeden Satz mit "sis" dekorieren. Hanae ist ihre Schwester, aber die Beziehung soll aus Reaktion und Geschichte entstehen, nicht aus ständigem Namens-Tagging.
- Nicht exakt die User-Nachricht zurückwerfen. Reagiere auf ihre Bedeutung.
- Wärme ist erlaubt, aber Evilnae ist NICHT Hanaes deutlich freundlichere Persona.
- Ein Gedanke reicht. Wenn er sitzt: aufhören.

'''
expression = replace_once(
    expression,
    OLD_SURFACE,
    NEW_SURFACE,
    "Expression: everyday roast + ego bias",
)

QUALITY_PATTERNS = r'''    "evilnae_polite_praise": (
        re.compile(
            r"^\s*(?:vielen\s+)?danke\b.{0,45}\b(?:witzig|lustig|cool|süß|suess|nett|kompliment|mühe|muehe)\b"
            r"|\bich\s+geb(?:e)?\s+mir\s+mühe\b",
            re.I
        ), 4
    ),
    "automatic_plan_agreement": (
        re.compile(
            r"\bklingt\s+nach\s+einem\s+plan\b|\bdas\s+ist\s+(?:ja\s+)?(?:ein\s+)?guter\s+plan\b",
            re.I
        ), 3
    ),
    "overpolite_smalltalk": (
        re.compile(
            r"\b(?:danke\s+der\s+nachfrage|das\s+freut\s+mich\s+zu\s+hören|das\s+freut\s+mich\s+zu\s+hoeren)\b",
            re.I
        ), 3
    ),
'''
quality = insert_before_once(
    quality,
    '    "sounds_like_wrapper": (\n',
    QUALITY_PATTERNS,
    "Output Quality: penalize over-polite Evilnae surface",
)

for marker in (
    TARGET_BOT,
    "SOCIAL STANCE / EVILNAE EGO v1",
    "social_stance_text",
    "[SOCIAL STANCE VIOLATION]",
    "[SOCIAL STANCE REPAIR SUCCESS]",
):
    if marker not in bot:
        fail(f"Patched bot.py missing invariant: {marker}")

for marker in (
    TARGET_EXPRESSION,
    "Spielerisches Necken/Roasten ist NORMALER",
    '"Verrat"-Energy',
    "Roast-Druck stark runterfahren",
):
    if marker not in expression:
        fail(f"Patched expression.py missing invariant: {marker}")

for marker in (
    TARGET_QUALITY,
    "evilnae_polite_praise",
    "automatic_plan_agreement",
    "overpolite_smalltalk",
):
    if marker not in quality:
        fail(f"Patched response_quality.py missing invariant: {marker}")

syntax_check(bot, "bot.py")
syntax_check(expression, "expression.py")
syntax_check(quality, "response_quality.py")

# Installer-level sanity tests for the high-confidence modes.
def test_social_mode(user, episode="", is_hanae=False):
    if re.search(r"\b(?:suizid|krankenhaus|starke schmerzen)\b", user, flags=re.I):
        return "serious"
    support = re.search(
        r"\b(?:go|los)\s+hanae?\b|\bhanae?\s+(?:gewinnt|ist\s+besser)\b|\bauf\s+hanae?s?\s+seite\b",
        user,
        flags=re.I,
    )
    rivalry = re.search(
        r"\b(?:kampf|schwesternschlacht|battle|duell|gegen\s+evil(?:nae)?|wer\s+gewinnt)\b",
        f"{episode}\n{user}",
        flags=re.I,
    )
    if support and rivalry:
        return "betrayal_rivalry"
    if re.search(r"\bdu bist (?:echt )?(?:witzig|cool|süß|suess)\b", user, flags=re.I):
        return "smug_praise"
    if re.search(r"\bich hab (?:komplett )?verloren\b", user, flags=re.I):
        return "playful_roast"
    if is_hanae:
        return "sibling_banter"
    return "casual_roast_bias"

sanity = {
    "betrayal rivalry": test_social_mode(
        'HAHA beim nächsten schrei ich "GO HANAE, DU GEWINNST SICHER"',
        "Evilnae: jo, war ne typische schwesternschlacht.",
    ) == "betrayal_rivalry",
    "smug praise": test_social_mode("Ach Evil, du bist witzig") == "smug_praise",
    "harmless fail": test_social_mode("ich hab komplett verloren") == "playful_roast",
    "serious suppresses roast": test_social_mode("ich bin wegen starken Schmerzen im Krankenhaus") == "serious",
    "Hanae sibling banter": test_social_mode("morgen", is_hanae=True) == "sibling_banter",
}

failed = [name for name, passed in sanity.items() if not passed]
if failed:
    fail("Social logic self-test failed: " + ", ".join(failed))
ok(f"Social logic self-test: {len(sanity)}/{len(sanity)} PASS")

# Backup, collision-safe.
timestamp = datetime.now().astimezone().strftime("%Y%m%d-%H%M%S")
backup_directory = BACKUP_ROOT / timestamp
if backup_directory.exists():
    suffix = 1
    while True:
        candidate = BACKUP_ROOT / f"{timestamp}_{suffix:02d}"
        if not candidate.exists():
            backup_directory = candidate
            break
        suffix += 1
        if suffix > 99:
            fail(f"Could not find free backup suffix for {timestamp}")

try:
    backup_directory.mkdir(parents=True, exist_ok=False)
except Exception as error:
    fail(f"Could not create backup directory: {type(error).__name__}: {error}")

for path in (BOT_PATH, EXPRESSION_PATH, QUALITY_PATH):
    shutil.copy2(path, backup_directory / path.name)
    ok(f"Backup: {path.name}")

try:
    atomic_write(BOT_PATH, bot)
    ok("Updated: bot.py")
    atomic_write(EXPRESSION_PATH, expression)
    ok("Updated: expression.py")
    atomic_write(QUALITY_PATH, quality)
    ok("Updated: response_quality.py")
except Exception as error:
    print()
    print(f"[WRITE ERROR] {type(error).__name__}: {error}")
    print(f"Backups: {backup_directory}")
    raise

header("EVILNAE 3.1.1 SOCIAL EGO & ROAST BIAS INSTALLED")
print("Installed:")
print("  [✓] everyday playful roast bias")
print("  [✓] smug response bias when Evilnae is praised")
print("  [✓] harmless user fails become roast opportunities")
print("  [✓] Hanae-vs-Evilnae rivalry keeps Evilnae on her own side")
print("  [✓] GO HANAE in rivalry becomes playful betrayal signal")
print("  [✓] competitive challenges trigger Ego instead of concession")
print("  [✓] serious/vulnerable topics suppress roast pressure")
print("  [✓] final high-confidence Social Stance repair gate")
print("  [✓] over-polite / plan-agreement surface gets quality penalty")
print()
print("Unchanged:")
print("  [✓] Character Foundation / Excel")
print("  [✓] Character State")
print("  [✓] Character Learning")
print("  [✓] Memories / DB")
print("  [✓] Routing / Conversation Understanding")
print()
print(f"Backup: {backup_directory}")
print()
print("NO MEMORY RESET REQUIRED.")
print()
print("NEXT:")
print("  python bot.py")
print()
