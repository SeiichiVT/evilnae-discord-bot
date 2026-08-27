from pathlib import Path
from datetime import datetime
import ast
import shutil
import subprocess
import sys

PROJECT_ROOT = Path(__file__).resolve().parent
BACKUP_ROOT = PROJECT_ROOT / "live_fix_backups"

FILES = {
    "bot": PROJECT_ROOT / "bot.py",
    "foundation": PROJECT_ROOT / "character_foundation.py",
    "state": PROJECT_ROOT / "character_state.py",
    "self_model": PROJECT_ROOT / "self_model.py",
    "understanding": PROJECT_ROOT / "understanding.py",
    "conversation_understanding": PROJECT_ROOT / "conversation_understanding.py",
    "quality": PROJECT_ROOT / "response_quality.py",
    "expression": PROJECT_ROOT / "expression.py",
    "learning": PROJECT_ROOT / "character_learning.py",
}

TARGET_BOT_VERSION = 'BOT_VERSION = "3.1.0-character-live"'


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
    print("No 3.1.0 files were written by this installer.")
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


def syntax_check(text, filename):
    try:
        ast.parse(text, filename=filename)
    except SyntaxError as error:
        fail(
            f"{filename}: syntax error after patch at line "
            f"{error.lineno}: {error.msg}"
        )
    ok(f"{filename} syntax check")


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


def insert_after_once(text, marker, block, label):
    count = text.count(marker)
    if count != 1:
        fail(f"{label}: expected exactly 1 marker, found {count}")
    ok(label)
    return text.replace(marker, marker + block, 1)


def replace_section(text, start_marker, end_marker, replacement, label):
    start = text.find(start_marker)
    if start < 0:
        fail(f"{label}: start marker not found")
    end = text.find(end_marker, start + len(start_marker))
    if end < 0:
        fail(f"{label}: end marker not found")
    ok(label)
    return text[:start] + replacement.rstrip() + "\n\n\n" + text[end:]


def replace_inside_section(text, start_marker, end_marker, old, new, label):
    start = text.find(start_marker)
    if start < 0:
        fail(f"{label}: section start not found")
    end = text.find(end_marker, start + len(start_marker))
    if end < 0:
        fail(f"{label}: section end not found")
    section = text[start:end]
    count = section.count(old)
    if count != 1:
        fail(f"{label}: expected exactly 1 match in section, found {count}")
    patched = section.replace(old, new, 1)
    ok(label)
    return text[:start] + patched + text[end:]


def ensure_302_base():
    bot = read_utf8(FILES["bot"])
    expression = read_utf8(FILES["expression"])
    quality = read_utf8(FILES["quality"])

    if TARGET_BOT_VERSION in bot:
        print("3.1.0 is already installed.")
        raise SystemExit(0)

    if (
        'BOT_VERSION = "3.0.2-output-integrity"' in bot
        and 'EXPRESSION_VERSION = "2.1"' in expression
        and 'OUTPUT_QUALITY_VERSION = "2.1"' in quality
    ):
        ok("3.0.2 output-integrity base detected")
        return

    if 'BOT_VERSION = "3.0.1-live-reliability"' not in bot:
        fail(
            "Unexpected bot version. Expected 3.0.1-live-reliability "
            "or 3.0.2-output-integrity."
        )

    prerequisite = PROJECT_ROOT / "install_output_integrity_3_0_2.py"
    if not prerequisite.exists():
        fail(
            "Local bot is still 3.0.1, but install_output_integrity_3_0_2.py "
            "is missing. Put the current GitHub files into this project first."
        )

    print("[INFO] Local base is 3.0.1.")
    print("[INFO] Applying 3.0.2 with compatibility fix for response_quality.py...")

    prerequisite_text = read_utf8(prerequisite)

    # The original 3.0.2 installer searched for a section header named
    # '# CONTENT TOKEN COUNT'. The current response_quality.py does not have
    # that header; it has def _content_tokens(...) directly.
    #
    # Only a TEMPORARY installer copy is patched. The user's original
    # install_output_integrity_3_0_2.py stays untouched.
    broken_marker = (
        "QUALITY_CONTENT_MARKER = '''# =========================================================\n"
        "# CONTENT TOKEN COUNT\n"
        "'''\n"
    )
    fixed_marker = (
        "QUALITY_CONTENT_MARKER = '''def _content_tokens(\n"
        "'''\n"
    )

    if broken_marker in prerequisite_text:
        prerequisite_text = prerequisite_text.replace(
            broken_marker,
            fixed_marker,
            1,
        )
        ok("3.0.2 compatibility: fixed Output Quality insertion marker")
    elif "QUALITY_CONTENT_MARKER = '''def _content_tokens(" in prerequisite_text:
        ok("3.0.2 compatibility marker already fixed")
    else:
        fail(
            "Could not locate the known 3.0.2 Output Quality marker in "
            "install_output_integrity_3_0_2.py."
        )

    try:
        ast.parse(
            prerequisite_text,
            filename="install_output_integrity_3_0_2_compat.py",
        )
    except SyntaxError as error:
        fail(
            "Temporary 3.0.2 compatibility installer has a syntax error at "
            f"line {error.lineno}: {error.msg}"
        )

    compat_installer = (
        PROJECT_ROOT
        / "_install_output_integrity_3_0_2_compat_temp.py"
    )

    result = None

    try:
        compat_installer.write_text(
            prerequisite_text,
            encoding="utf-8",
        )

        result = subprocess.run(
            [sys.executable, str(compat_installer)],
            cwd=str(PROJECT_ROOT),
            check=False,
        )
    finally:
        try:
            compat_installer.unlink(missing_ok=True)
        except Exception:
            pass

    if result is None or result.returncode != 0:
        code = "unknown" if result is None else result.returncode
        fail(
            "3.0.2 compatibility prerequisite failed with exit code "
            f"{code}"
        )

    bot = read_utf8(FILES["bot"])
    expression = read_utf8(FILES["expression"])
    quality = read_utf8(FILES["quality"])

    if not (
        'BOT_VERSION = "3.0.2-output-integrity"' in bot
        and 'EXPRESSION_VERSION = "2.1"' in expression
        and 'OUTPUT_QUALITY_VERSION = "2.1"' in quality
    ):
        fail("3.0.2 prerequisite did not leave the expected versions")

    ok("3.0.2 prerequisite applied successfully")


header("EVILNAE 3.1.0 CHARACTER LIVE FIX — V2")
print(f"Project: {PROJECT_ROOT}")
print()
print("WICHTIG: bot.py muss vollständig AUS sein.")
print()

ensure_302_base()

sources = {name: read_utf8(path) for name, path in FILES.items()}

# =====================================================================
# CHARACTER FOUNDATION 1.1
# =====================================================================
foundation = sources["foundation"]
foundation = replace_once(
    foundation,
    'CHARACTER_FOUNDATION_VERSION = "1.0"',
    'CHARACTER_FOUNDATION_VERSION = "1.1-live-retrieval"',
    "Character Foundation version -> 1.1-live-retrieval",
)

new_tokens = r'''def _tokens(text: str) -> set[str]:
    raw_tokens = [
        token
        for token in _normalize(text).split()
        if len(token) >= 2 and token not in STOPWORDS
    ]

    tokens = set(raw_tokens)

    # German compounds such as Lieblingssong / Lieblingsanime / Lieblingsspiel
    # need a shared intent token plus the concrete category suffix.
    for token in list(raw_tokens):
        if token.startswith("lieblings") and len(token) > len("lieblings"):
            suffix = token[len("lieblings"):].strip()
            tokens.add("lieblings")
            if suffix:
                tokens.add(suffix)
                if suffix.endswith("s") and len(suffix) > 3:
                    tokens.add(suffix[:-1])

        if token.endswith("s") and len(token) > 4:
            tokens.add(token[:-1])

    expanded = set(tokens)
    for token in list(tokens):
        expanded.update(QUERY_EXPANSIONS.get(token, set()))

    return expanded'''
foundation = replace_section(
    foundation,
    "def _tokens(text: str) -> set[str]:",
    "def _load() -> None:",
    new_tokens,
    "Foundation tokenization incl. Lieblings-compounds",
)

intent_helper = r'''def _intent_area_boost(entry: dict, query: str, query_tokens: set[str]) -> float:
    query_norm = _normalize(query)
    question_norm = _normalize(entry.get("question") or "")
    area_norm = _normalize(entry.get("area") or "")
    nr = int(entry.get("nr") or 0)

    boost = 0.0

    def has_any(values):
        return any(value in query_tokens or value in query_norm for value in values)

    if has_any({"musik", "song", "songs", "artist", "band", "metal", "rock"}):
        if area_norm.startswith("26 musik"):
            boost += 10.0

    if has_any({"game", "games", "gaming", "spiel", "spiele", "zocken", "valorant"}):
        if area_norm.startswith("23 gaming"):
            boost += 10.0

    if has_any({"anime", "manga"}):
        if area_norm.startswith("24 anime manga"):
            boost += 10.0

    if has_any({"film", "filme", "serie", "serien", "horror"}):
        if area_norm.startswith("25 filme serien horror"):
            boost += 9.0

    if has_any({"tiktok", "twitter", "youtube", "social", "socialmedia", "discord"}):
        if area_norm.startswith("27 internet social media"):
            boost += 9.0

    if has_any({"hobby", "hobbys", "freizeit"}):
        if area_norm.startswith("32 hobbys freizeit"):
            boost += 8.0

    if has_any({"kochen", "koch", "haushalt", "staubsaugen", "mull", "wäsche", "wasche"}):
        if area_norm.startswith("07 tagesablauf gewohnheiten"):
            boost += 8.0

    current_activity_query = bool(
        re.search(
            r"\b(?:was machst du|was treibst du|was bist du.*am machen|"
            r"was zockst du gerade|was schaust du gerade|was guckst du gerade|"
            r"was machst du grad|was machst du aktuell)\b",
            query_norm,
        )
    )

    day_query = bool(
        re.search(
            r"\b(?:wie war dein tag|was hast du heute gemacht|was hast du gemacht heute)\b",
            query_norm,
        )
    )

    if current_activity_query or day_query:
        if area_norm.startswith("07 tagesablauf gewohnheiten"):
            boost += 8.0
        if area_norm.startswith("39 offline leben"):
            boost += 11.0
        if nr in {120, 567, 569}:
            boost += 8.0

    if "lieblings" in query_tokens or "lieblings" in query_norm:
        if "lieblings" in question_norm:
            boost += 12.0
        else:
            boost -= 2.5

    return boost


'''
foundation = insert_before_once(
    foundation,
    "def _entry_score(entry: dict, query: str, query_tokens: set[str]) -> float:",
    intent_helper,
    "Foundation intent/area scoring helper",
)

new_entry_score = r'''def _entry_score(entry: dict, query: str, query_tokens: set[str]) -> float:
    answer = str(entry.get("answer") or "").strip()
    if not answer:
        return -1.0

    status = str(entry.get("status") or "FIXED").upper()
    if status == "N/A":
        return -1.0

    question = str(entry.get("question") or "")
    area = str(entry.get("area") or "")
    q_norm = _normalize(question)
    a_norm = _normalize(answer)
    q_tokens = _tokens(question)
    a_tokens = _tokens(answer)
    area_tokens = _tokens(area)

    overlap_q = query_tokens & q_tokens
    overlap_a = query_tokens & a_tokens
    overlap_area = query_tokens & area_tokens

    # The question/intent is much more trustworthy than incidental words
    # inside a long answer. This prevents broad lore paragraphs from winning.
    score = (
        5.4 * len(overlap_q)
        + 0.65 * len(overlap_a)
        + 0.8 * len(overlap_area)
    )

    meaningful = max(1, len(query_tokens))
    coverage = len(overlap_q | overlap_a) / meaningful
    score += min(5.5, coverage * 5.5)

    query_norm = _normalize(query)
    if query_norm and len(query_norm) >= 5 and query_norm in q_norm:
        score += 10.0

    score += _intent_area_boost(entry, query, query_tokens)

    priority = str(entry.get("priority") or "").upper()
    if priority == "MUSS":
        score += 1.5
    elif priority == "WICHTIG":
        score += 0.6

    # Subject ownership: "Hanae" inside an answer must not magically turn
    # an Evilnae fact into a fact ABOUT Hanae.
    hanae_in_query = "hanae" in query_tokens
    hanae_in_question = "hanae" in q_tokens or "hanae" in q_norm
    hanae_in_area = "hanae" in _normalize(area)

    if hanae_in_query:
        if hanae_in_question:
            score += 11.0
        elif hanae_in_area:
            score += 6.0
        elif "hanae" in a_tokens:
            score -= 7.0
    elif hanae_in_question:
        score -= 14.0

    if "error" in query_tokens and ("error" in q_tokens or "error" in a_tokens):
        score += 5.0

    if ("spinne" in query_tokens or "spinnen" in query_tokens) and "spinnen" in (q_tokens | a_tokens):
        score += 6.0

    return score'''
foundation = replace_section(
    foundation,
    "def _entry_score(entry: dict, query: str, query_tokens: set[str]) -> float:",
    "def search_foundation(",
    new_entry_score,
    "Foundation retrieval scoring v2",
)

new_self_query = r'''def _self_query(text: str) -> bool:
    norm = _normalize(text)
    patterns = (
        r"\bmagst du\b", r"\bliebst du\b", r"\bhasst du\b", r"\bfindest du\b",
        r"\bdein(?:e|er|en|em|es)?\b", r"\bhast du\b", r"\bbist du\b",
        r"\bkannst du\b", r"\bwie alt\b", r"\bwas zockst du\b", r"\bwas spielst du\b",
        r"\bwas schaust du\b", r"\bwas guckst du\b", r"\bwas horst du\b",
        r"\bwas trinkst du\b", r"\bwas isst du\b", r"\bwas denkst du\b",
        r"\bwer bist du\b", r"\bwas machst du\b", r"\bwas treibst du\b",
        r"\blieblings[a-z0-9]*\b", r"\bwas haltst du von\b",
    )
    return any(re.search(pattern, norm) for pattern in patterns)


def _favorite_subject(text: str) -> Optional[str]:
    norm = _normalize(text)
    match = re.search(
        r"\blieblings\s*(?P<kind>[a-z0-9]{2,40})\b",
        norm,
    )
    if match:
        return match.group("kind")

    for token in norm.split():
        if token.startswith("lieblings") and len(token) > len("lieblings"):
            return token[len("lieblings"):]

    return None


def resolve_foundation_self_query(user_text: str) -> Optional[FoundationHit]:
    text = str(user_text or "").strip()
    if not text or not _self_query(text):
        return None

    hits = search_foundation(text, limit=8, min_score=4.5)
    if not hits:
        return None

    favorite_subject = _favorite_subject(text)

    if favorite_subject:
        favorite_subject = favorite_subject.rstrip("s")
        category_hits = []

        for hit in hits:
            question_norm = _normalize(hit.question)
            question_tokens = _tokens(hit.question)

            subject_match = (
                favorite_subject in question_norm
                or favorite_subject in question_tokens
                or any(
                    token.startswith(favorite_subject)
                    or favorite_subject.startswith(token)
                    for token in question_tokens
                    if len(token) >= 3
                )
            )

            if subject_match and "lieblings" in question_norm:
                category_hits.append(hit)

        # Important: no matching favorite category means OPEN/LEARN.
        # Do not let a generic "which opinions are fixed" row become a fake
        # favorite answer for cars, food, etc.
        if not category_hits:
            return None

        return category_hits[0]

    top = hits[0]
    q_tokens = _tokens(top.question)
    u_tokens = _tokens(text)

    if not (q_tokens & u_tokens) and top.score < 9.0:
        return None

    return top'''
foundation = replace_section(
    foundation,
    "def _self_query(text: str) -> bool:",
    "def build_character_context(",
    new_self_query,
    "Foundation self-query/favorite-category resolver",
)

foundation_directive = r'''def build_direct_foundation_directive(user_text: str) -> str:
    text = str(user_text or "").strip()
    hit = resolve_foundation_self_query(text)

    favorite_subject = _favorite_subject(text)

    if hit is None:
        if favorite_subject:
            return (
                "[DIRECT FOUNDATION ANSWER]\n"
                f"Für die angefragte Lieblings-Kategorie '{favorite_subject}' gibt es "
                "keinen festen Canon-Favoriten. Das ist OPEN/LEARN. "
                "Erfinde deshalb KEINEN festen Lieblingswert. Evilnae darf einen "
                "spontanen Eindruck haben oder sagen, dass sie dort keinen festen "
                "Favoriten hat."
            )

        return (
            "[DIRECT FOUNDATION ANSWER]\n"
            "Keine einzelne direkte Foundation-Zeile ist für diese Self-Frage "
            "verbindlich genug. Nutze die relevante Foundation normal und erfinde "
            "keine feste persönliche Tatsache."
        )

    question_norm = _normalize(hit.question)
    answer = hit.answer.strip()

    concrete_required = bool(
        "lieblings" in question_norm
        or re.search(r"\bwelche\b", question_norm)
        or re.search(r"\bwas sind\b", question_norm)
    )

    concrete_rule = (
        "Nenne in der Discord-Antwort mindestens einen konkreten Canon-Namen/Wert "
        "aus dieser Antwort; bei Listenfragen normalerweise 2-4 passende Beispiele. "
        "Eine nur generische Paraphrase reicht NICHT."
        if concrete_required
        else
        "Beantworte genau die gefragte Eigenschaft zuerst und bleibe bei diesem Canon."
    )

    return f"""
[DIRECT FOUNDATION ANSWER — HARD PRIORITY]

Excel row: #{hit.nr}
Question: {hit.question}
Canon answer: {answer}

RULE:
{concrete_rule}

Keine plausiblere Modell-Erfindung anstelle des Canon benutzen.
Wenn du danach Persönlichkeit hinzufügst, darf sie den Canon nicht ersetzen.
""".strip()


'''
foundation = insert_before_once(
    foundation,
    "def build_character_context(",
    foundation_directive,
    "Direct Foundation answer directive",
)

new_foundation_violation = r'''def foundation_violation_reasons(answer: str, hit: Optional[FoundationHit]) -> list[str]:
    if hit is None:
        return []

    output = _normalize(answer)
    canon = _normalize(hit.answer)

    if not output:
        return ["empty_foundation_answer"]

    reasons = []

    canon_no = (
        canon.startswith("nein")
        or " selbst nie " in f" {canon} "
        or " nie wirklich gespielt" in canon
    )
    canon_yes = canon.startswith("ja") and not canon.startswith("ja aber nicht")

    positive_claim = bool(
        re.search(
            r"\b(ja|mag ich|liebe ich|find ich gut|hab ich|habe ich|gespielt|gezockt)\b",
            output,
        )
    )
    negative_claim = bool(
        re.search(
            r"\b(nein|mag ich nicht|nicht mein|nie gespielt|nie gezockt|hab ich nie|habe ich nie)\b",
            output,
        )
    )

    if canon_no and positive_claim and not negative_claim:
        reasons.append("foundation_polarity_contradiction")
    if canon_yes and negative_claim and not positive_claim:
        reasons.append("foundation_polarity_contradiction")

    if hit.nr == 10:
        numbers = re.findall(r"\b\d{1,3}\b", output)
        if numbers and "18" not in numbers:
            reasons.append("foundation_age_contradiction")

    if "nie wirklich gespielt" in canon or "selbst nie" in canon:
        if re.search(r"\b(ich hab|ich habe|hab ich|habe ich).{0,60}\b(gespielt|gezockt)\b", output):
            reasons.append("foundation_experience_contradiction")

    # Direct favorite/list facts must visibly use the Canon instead of merely
    # returning a generic answer that could belong to any character.
    question_norm = _normalize(hit.question)
    concrete_fact = bool(
        "lieblings" in question_norm
        or re.search(r"\bwelche\b", question_norm)
        or re.search(r"\bwas sind\b", question_norm)
    )

    if concrete_fact and hit.status.upper() == "FIXED":
        canon_tokens = {
            token
            for token in _tokens(hit.answer)
            if len(token) >= 4
            and token not in {
                "evilnae", "besonders", "generell", "dabei", "daran", "immer",
                "ziemlich", "wirklich", "festen", "feste", "gehort", "gehoren",
            }
        }
        output_tokens = _tokens(answer)

        # One concrete anchor is enough. This catches e.g. an invented
        # "Blinding Lights" while allowing concise canonical answers.
        if canon_tokens and not (canon_tokens & output_tokens):
            reasons.append("foundation_content_not_used")

    return list(dict.fromkeys(reasons))'''
foundation = replace_section(
    foundation,
    "def foundation_violation_reasons(",
    "def format_foundation_debug(",
    new_foundation_violation,
    "Foundation concrete-content guard",
)

sources["foundation"] = foundation

# =====================================================================
# CHARACTER STATE 1.1 — richer current activity
# =====================================================================
state = sources["state"]
state = replace_once(
    state,
    'CHARACTER_STATE_VERSION = "1.0"',
    'CHARACTER_STATE_VERSION = "1.1-current-activity"',
    "Character State version -> 1.1-current-activity",
)

state = insert_after_once(
    state,
    "from pathlib import Path\n",
    "\nfrom character_foundation import get_foundation_entry\n",
    "Character State imports Foundation examples",
)

extra_state_patterns = r'''
# Additional natural phrasings emitted by the Writer.
PATTERNS.extend(
    [
        (
            "activity",
            re.compile(
                r"\b(?:ich\s+)?(?:schaue|schau|gucke|guck)\s+(?:gerade\s+)?(?P<value>[^.!?\n]{2,90})",
                re.IGNORECASE,
            ),
        ),
        (
            "activity",
            re.compile(
                r"\b(?:ich\s+)?(?:scrolle|scroll|hänge|haenge|häng)\s+(?:gerade\s+)?(?:auf|durch)\s+(?P<value>[^.!?\n]{2,90})",
                re.IGNORECASE,
            ),
        ),
        (
            "activity",
            re.compile(
                r"\bich\s+bin\s+(?:gerade\s+)?auf\s+(?P<value>(?:tiktok|twitter|x|youtube|discord)[^.!?\n]{0,70})",
                re.IGNORECASE,
            ),
        ),
    ]
)

'''
state = insert_before_once(
    state,
    "def _load() -> dict:",
    extra_state_patterns,
    "Character State media/social activity patterns",
)

new_state_prompt = r'''def _asks_current_activity(user_text: str) -> bool:
    normalized = re.sub(r"\s+", " ", str(user_text or "").lower()).strip()
    return bool(
        re.search(
            r"\b(?:was machst du(?: gerade| grad| aktuell| jetzt)?|"
            r"was treibst du(?: gerade| grad| aktuell| jetzt)?|"
            r"was bist du(?: gerade| grad)? am machen|"
            r"was zockst du(?: gerade| grad| aktuell)?|"
            r"was schaust du(?: gerade| grad| aktuell)?|"
            r"was guckst du(?: gerade| grad| aktuell)?)\b",
            normalized,
            flags=re.IGNORECASE,
        )
    )


def _foundation_answer(nr: int) -> str:
    try:
        hit = get_foundation_entry(nr)
    except Exception:
        hit = None
    return hit.answer if hit is not None else ""


def format_character_state_for_prompt(user_text: str = "") -> str:
    states = _active_states()
    asks_activity = _asks_current_activity(user_text)

    lines = ["[CURRENT CHARACTER STATE]"]

    if states:
        lines.append(
            "Diese Zustände stammen aus Evilnaes eigenen tatsächlich gesendeten "
            "Nachrichten und gelten nur temporär."
        )
        for category, state in states.items():
            lines.append(f"- {category}: {state.get('value')}")
        lines.append(
            "Wenn neuer Gesprächskontext einen Zustand ausdrücklich ändert, darf er aktualisiert werden."
        )
    else:
        lines.append("Kein persistenter aktueller Alltagszustand gesetzt.")

    if asks_activity:
        has_activity = bool(states.get("activity") or states.get("game"))

        if has_activity:
            lines.extend(
                [
                    "Die aktuelle User-Frage fragt DIREKT, was Evilnae gerade macht.",
                    "Antworte deshalb konkret mit dem vorhandenen game/activity-State statt nur 'chillen' zu sagen.",
                    "Ein kleiner natürlicher Zusatz ist okay, aber der konkrete State muss vorkommen.",
                ]
            )
        else:
            games = _foundation_answer(341)
            anime = _foundation_answer(366)
            films = _foundation_answer(377)
            social = _foundation_answer(395)

            lines.extend(
                [
                    "Die aktuelle User-Frage fragt DIREKT, was Evilnae gerade macht.",
                    "FOUNDATION #567/#569 erlaubt ausdrücklich, für normalen Alltag eine konkrete harmlose Aktivität zu setzen.",
                    "Die allgemeine No-Invention-Regel gilt hier NICHT gegen solche erlaubten Alltagsaktivitäten.",
                    "Wähle GENAU EINE konkrete Sache, die sie gerade macht, statt vage 'chillen', 'nichts' oder 'rumhängen' zu antworten.",
                    "Geeignet sind z.B. ein konkretes festes Lieblingsgame, ein konkreter Canon-Anime/Film, TikTok/Twitter/YouTube, Musik oder Coding/PC-Kram.",
                    "Formuliere natürlich in erster Person, z.B. 'ich zocke gerade X' / 'ich schau gerade X' / 'häng gerade auf TikTok fest'.",
                    "Keine großen Ereignisse, neuen Personen, Reisen, Streit, Verletzungen oder neue Lore erfinden.",
                ]
            )

            if games:
                lines.append(f"Canon games: {games}")
            if anime:
                lines.append(f"Canon anime: {anime}")
            if films:
                lines.append(f"Canon films: {films}")
            if social:
                lines.append(f"Canon social platforms: {social}")

    elif not states:
        lines.append(
            "Erfinde keinen konkreten Ort, Essen, Drink, Game, Outfit oder Aktivität nur um irgendeine andere Antwort lebendiger zu machen. "
            "Die besondere Alltags-Erlaubnis greift nur, wenn tatsächlich nach ihrem aktuellen Alltag/Tag gefragt wird."
        )

    return "\n".join(lines)'''
state = replace_section(
    state,
    "def format_character_state_for_prompt() -> str:",
    "def format_character_state_debug(",
    new_state_prompt,
    "Current-activity prompt now concrete + Foundation-aware",
)
sources["state"] = state

# =====================================================================
# SELF MODEL 2.1 — generic favorite categories
# =====================================================================
self_model = sources["self_model"]
self_model = replace_once(
    self_model,
    'SELF_MODEL_VERSION = "2.0-character-foundation"',
    'SELF_MODEL_VERSION = "2.1-character-foundation"',
    "Self Model version -> 2.1-character-foundation",
)

generic_favorite = r'''
    # =====================================================
    # GENERIC FAVORITE CATEGORY GUARD v2.1
    #
    # Foundation had the first chance above. If no matching
    # Foundation row exists, ANY Lieblings-X category remains
    # unknown/OPEN instead of silently inventing a Tesla/song/etc.
    # =====================================================

    generic_favorite_match = re.search(
        r"\blieblings[\s_-]*(?P<kind>[a-zäöüß0-9]{2,40})\b",
        lowered,
        flags=re.IGNORECASE,
    )

    if generic_favorite_match:
        favorite_kind = _normalize(generic_favorite_match.group("kind"))
        key = f"favorite:{favorite_kind}"
        fact = get_self_fact(key)

        return SelfEvidence(
            matched=True,
            query_type="favorite",
            key=key,
            known=(fact is not None),
            strict_unknown=(fact is None),
            specificity_guard=False,
            fact=fact,
            reason=("known_favorite" if fact else "favorite_not_established"),
        )

'''
self_model = insert_before_once(
    self_model,
    "    # =====================================================\n    # FAVORITES\n",
    generic_favorite,
    "Generic favorite-category guard",
)

old_favorite_violation = '''        if (
            evidence.query_type
            ==
            "favorite"
            and
            FAVORITE_ASSERTION_PATTERN
            .search(
                answer
            )
        ):

            reasons.append(
                "unsupported_self_favorite"
            )
'''
new_favorite_violation = '''        if (
            evidence.query_type
            ==
            "favorite"
            and
            not uncertainty
        ):

            # The user explicitly asked for a fixed favorite, but no
            # Foundation/Learned fact exists. Any confident concrete answer
            # would create canon out of thin air, even if the Writer avoids
            # the literal words "mein Lieblings...".
            reasons.append(
                "unsupported_self_favorite"
            )
'''
self_model = replace_inside_section(
    self_model,
    "def self_knowledge_violation_reasons(",
    "# =========================================================\n# DEBUG",
    old_favorite_violation,
    new_favorite_violation,
    "Strict unknown favorite cannot invent a value",
)
sources["self_model"] = self_model

# =====================================================================
# UNDERSTANDING 1.1 — subject-specific Hanae authority
# =====================================================================
understanding = sources["understanding"]
understanding = replace_once(
    understanding,
    'UNDERSTANDING_VERSION = "1.0"',
    'UNDERSTANDING_VERSION = "1.1-subject-authority"',
    "Understanding version -> 1.1-subject-authority",
)
understanding = insert_after_once(
    understanding,
    "from typing import Any, Optional\n",
    "\nfrom character_foundation import search_foundation\n",
    "Understanding imports Foundation search",
)

subject_authority_helper = r'''def _foundation_authorizes_subject_fact(user_text: str, subject_name: str) -> bool:
    subject = str(subject_name or "").strip().lower()
    if not subject:
        return False

    try:
        hits = search_foundation(user_text, limit=6, min_score=5.0)
    except Exception:
        return False

    for hit in hits:
        question = str(hit.question or "").lower()
        area = str(hit.area or "").lower()

        explicitly_about_subject = (
            subject in question
            or (subject == "hanae" and "hanae" in area)
            or (subject == "error" and "error" in area)
        )

        if explicitly_about_subject and float(hit.score or 0.0) >= 8.0:
            return True

    return False


'''
understanding = insert_before_once(
    understanding,
    "def build_knowledge_constraint(\n",
    subject_authority_helper,
    "Subject-specific Foundation authority helper",
)

old_knowledge_available = '''    if knowledge_available:

        return KnowledgeConstraint(

            active=False,

            subject_name=(
                subject_name
            ),

            subject_id=(
                subject_id
            ),

            scope=(
                infer_knowledge_scope(
                    user_text
                )
            ),

            knowledge_available=True,

            knowledge_source=(
                knowledge_source
            ),

            reason=(
                "knowledge_available"
            )
        )
'''
new_knowledge_available = '''    if knowledge_available:

        # Knowledge availability is SUBJECT-SCOPED.
        # A random Self/Foundation fact about Evilnae must never authorize a
        # factual claim about Hanae merely because the Brain returned True.
        subject_authorized = (
            knowledge_source == "conversation_world"
            or _foundation_authorizes_subject_fact(
                user_text,
                subject_name,
            )
        )

        if subject_authorized:
            return KnowledgeConstraint(

                active=False,

                subject_name=(
                    subject_name
                ),

                subject_id=(
                    subject_id
                ),

                scope=(
                    infer_knowledge_scope(
                        user_text
                    )
                ),

                knowledge_available=True,

                knowledge_source=(
                    knowledge_source
                ),

                reason=(
                    "subject_scoped_knowledge_available"
                )
            )

        knowledge_available = False
        knowledge_source = "subject_scope_mismatch"
'''
understanding = replace_inside_section(
    understanding,
    "def build_knowledge_constraint(\n",
    "# =========================================================\n# KNOWLEDGE WRITER GUIDANCE",
    old_knowledge_available,
    new_knowledge_available,
    "Knowledge availability is subject-scoped",
)
sources["understanding"] = understanding

# =====================================================================
# CONVERSATION UNDERSTANDING 1.1 — cross-user ownership / self identity
# =====================================================================
cu = sources["conversation_understanding"]
cu = replace_once(
    cu,
    'CONVERSATION_UNDERSTANDING_VERSION = "1.0"',
    'CONVERSATION_UNDERSTANDING_VERSION = "1.1-thread-ownership"',
    "Conversation Understanding version -> 1.1-thread-ownership",
)

new_format_item = r'''def _format_item(item) -> str:
    item_type = str(item.get("type", ""))
    username = str(item.get("username", "Unbekannt"))
    content = _normalize(item.get("content", ""))

    if len(content) > 260:
        content = content[:257] + "..."

    if item_type == "bot":
        origin = str(item.get("origin") or "reply")
        reply_name = item.get("reply_to_name")

        if origin == "participation":
            return f"Evilnae [eigener Einwurf]: {content}"
        if origin == "initiative":
            return f"Evilnae [spontaner eigener Gedanke]: {content}"
        if reply_name:
            return f"Evilnae [antwortet auf {reply_name}]: {content}"
        return f"Evilnae: {content}"

    reply_name = item.get("reply_to_name")
    if reply_name:
        return f"{username} [antwortet auf {reply_name}]: {content}"

    return f"{username}: {content}"'''
cu = replace_section(
    cu,
    "def _format_item(\n",
    "# =========================================================\n# PREVIOUS ITEMS",
    new_format_item,
    "Episode lines preserve Evilnae reply ownership",
)

reference_rule = r'''
    # -----------------------------------------------------
    # PRONOUN -> EVILNAE SELF OWNERSHIP
    # -----------------------------------------------------

    if (
        re.search(r"\b(?:sie|ihr)\b", text, flags=re.IGNORECASE)
        and any(
            str(item.get("type", "")) == "bot"
            for item in relevant_items[-3:]
        )
    ):
        rules.append(
            (
                "Wenn 'sie/ihr' im unmittelbaren Verlauf grammatisch auf Evilnae "
                "zeigt, ist damit DU selbst gemeint. Antworte dann in der ersten "
                "Person (ich/mich/mir) und beschreibe Evilnae nicht wie eine dritte Person."
            )
        )

'''
cu = insert_before_once(
    cu,
    "    rules_text = \"\\n\".join(\n",
    reference_rule,
    "Reference resolver keeps Evilnae in first person",
)

new_episode = r'''def build_episode_focus(
    channel_snapshot,
    *,
    limit: int = 12
) -> str:

    if not channel_snapshot:
        return "Keine aktuelle Conversation Episode."

    items = list(channel_snapshot[-limit:])
    timeline = "\n".join(
        f"- {_format_item(item)}"
        for item in items
    )

    return f"""
[CURRENT CONVERSATION EPISODE v{CONVERSATION_UNDERSTANDING_VERSION}]

Behandle die folgenden Nachrichten als eine mögliche laufende soziale Situation,
nicht als isolierte Einzelprompts:

{timeline}

HARD THREAD-OWNERSHIP RULES:
- Mehrere User können Teil derselben Episode sein.
- Eine Zwischenmeldung beendet einen Gesprächsstrang nicht automatisch.
- Eine Evilnae-Antwort, die als [antwortet auf NAME] markiert ist, gehört zunächst zu DIESEM User/Thread.
- Ein persönliches Detail, Gag oder Wunsch aus der Antwort an User A darf NICHT automatisch in die Antwort an User B übertragen werden.
- Nur wenn der neue User das gemeinsame Thema ausdrücklich aufgreift, wird es zu einem gemeinsamen Channel-Thema.
- Trenne Geschehen IM DISCORD von Dingen, die ein User außerhalb des Channels gerade macht.
- Evilnae ist IMMER die Sprecherin der neuen Antwort. Wenn im Verlauf über "Evil/Evilnae" oder passend mit "sie" gesprochen wird, darf sie sich nicht selbst wie eine dritte Person behandeln.
- Wenn jemand Hanae gegen Evilnae anfeuert, ist Evilnae eine der beteiligten Seiten — nicht ein neutraler Kommentator, der automatisch Hanae anfeuert.
""".strip()'''
cu = replace_section(
    cu,
    "def build_episode_focus(\n",
    "# =========================================================\n# PARTICIPATION HINT",
    new_episode,
    "Cross-user episode ownership rules",
)
sources["conversation_understanding"] = cu

# =====================================================================
# OUTPUT QUALITY 2.2 — short echo + phrase repetition
# =====================================================================
quality = sources["quality"]
quality = replace_once(
    quality,
    'OUTPUT_QUALITY_VERSION = "2.1"',
    'OUTPUT_QUALITY_VERSION = "2.2"',
    "Output Quality version -> 2.2",
)

ngram_helper = r'''def _word_ngrams(text: str, n: int = 4) -> set[tuple[str, ...]]:
    words = _words(text)
    if len(words) < n:
        return set()
    return {
        tuple(words[index:index + n])
        for index in range(0, len(words) - n + 1)
    }


'''
quality = insert_before_once(
    quality,
    "def _sentence_count(\n",
    ngram_helper,
    "Output Quality phrase n-gram helper",
)

old_user_echo = '''    if (
        user_overlap >= 0.72
        and
        len(
            _content_tokens(
                text
            )
        )
        >=
        4
    ):

        issues.append(
            "high_user_restatement"
        )

        echo_score += 2
'''
new_user_echo = '''    normalized_user = _normalize(user_text)
    normalized_answer = _normalize(text)

    answer_words_for_echo = _words(text)

    exact_or_substring_echo = (
        len(answer_words_for_echo) >= 2
        and normalized_answer
        and normalized_user
        and (
            normalized_answer == normalized_user
            or (
                len(answer_words_for_echo) >= 3
                and normalized_answer in normalized_user
            )
        )
    )

    if exact_or_substring_echo:
        issues.append("direct_user_echo")
        echo_score += 5

    elif (
        user_overlap >= 0.72
        and len(_content_tokens(text)) >= 3
    ):
        issues.append("high_user_restatement")
        echo_score += 3
'''
quality = replace_inside_section(
    quality,
    "def analyze_response_quality(\n",
    "# =====================================================\n    # GRAMMAR / GARBLED",
    old_user_echo,
    new_user_echo,
    "Short user-echo detection",
)

repeat_block = r'''
    # =====================================================
    # EXACT PHRASE REPETITION
    # =====================================================

    candidate_4grams = _word_ngrams(text, 4)
    recent_4grams = set()

    for recent_message in recent[-12:]:
        recent_4grams.update(_word_ngrams(recent_message, 4))

    shared_4grams = candidate_4grams & recent_4grams

    if shared_4grams:
        issues.append("repeated_4word_phrase")
        repetition_score += 4

'''
quality = insert_before_once(
    quality,
    "    # =====================================================\n    # SEMANTIC REPETITION\n",
    repeat_block,
    "Exact repeated phrase detection",
)

old_severe = '''    severe = (
        grammar_score >= 3
        or
        repetition_score >= 4
        or
        total_penalty >= 7
    )
'''
new_severe = '''    severe = (
        grammar_score >= 3
        or repetition_score >= 4
        or echo_score >= 4
        or total_penalty >= 7
    )
'''
quality = replace_inside_section(
    quality,
    "def analyze_response_quality(\n",
    "def compare_response_candidates(\n",
    old_severe,
    new_severe,
    "Direct echo is severe output quality issue",
)
sources["quality"] = quality

# =====================================================================
# EXPRESSION 2.2 — less assistant-friendly, more Evilnae
# =====================================================================
expression = sources["expression"]
expression = replace_once(
    expression,
    'EXPRESSION_VERSION = "2.1"',
    'EXPRESSION_VERSION = "2.2"',
    "Expression version -> 2.2",
)

surface_rules = r'''
CHARACTER SURFACE:
- Evilnae ist standardmäßig locker, trocken, direkt und leicht distanziert — besonders bei Fremden.
- Nicht jede Nachricht freundlich bestätigen. Kein automatisches "klingt gut", "danke der Nachfrage", "freu mich drauf", "mach's dir gemütlich" oder Service-Abschluss.
- Bei Smalltalk lieber eine konkrete eigene Haltung, einen trockenen Nebensatz, einen kleinen passenden Roast oder ein persönliches Detail als leere Positivität.
- Nicht jeden Satz mit "sis" dekorieren. Hanae ist ihre Schwester, aber die Beziehung soll aus Reaktion und Geschichte entstehen, nicht aus ständigem Namens-Tagging.
- Nicht exakt die User-Nachricht zurückwerfen. Reagiere auf ihre Bedeutung.
- Wärme ist erlaubt, aber Evilnae ist NICHT Hanaes deutlich freundlichere Persona.
- Ein Gedanke reicht. Wenn er sitzt: aufhören.

'''
expression = insert_before_once(
    expression,
    "Ein interner Stil oder Inner State\n",
    surface_rules,
    "Evilnae-specific surface style rules",
)
sources["expression"] = expression

# =====================================================================
# CHARACTER LEARNING 1.1 — block junk interpersonal preferences
# =====================================================================
learning = sources["learning"]
learning = replace_once(
    learning,
    'CHARACTER_LEARNING_VERSION = "1.0"',
    'CHARACTER_LEARNING_VERSION = "1.1"',
    "Character Learning version -> 1.1",
)

valid_topic_helper = r'''def _valid_preference_topic(topic: str) -> bool:
    normalized = _normalize(topic)
    if not normalized:
        return False

    # Prevent lines such as "ich liebe dich trotzdem, sis" from becoming
    # a learned preference called "dich trotzdem sis".
    blocked_starts = (
        "dich", "dir", "euch", "euer", "eure", "ihn", "ihm", "sie", "ihr",
        "das", "es", "uns", "mich", "mir",
    )
    first = normalized.split()[0]
    if first in blocked_starts:
        return False

    if normalized in {
        "hanae", "sis", "schwester", "chat", "community", "leute", "menschen",
    }:
        return False

    return len(normalized) >= 2


'''
learning = insert_before_once(
    learning,
    "def _status_for_confirmations(count: int) -> str:",
    valid_topic_helper,
    "Character Learning preference-topic validity",
)

old_after_extract = '''    topic, sentiment = extracted
    result["topic"] = topic
    result["sentiment"] = sentiment

    blocked, hit = foundation_blocks_learning(topic)
'''
new_after_extract = '''    topic, sentiment = extracted
    result["topic"] = topic
    result["sentiment"] = sentiment

    if not _valid_preference_topic(topic):
        result["reason"] = "invalid_preference_topic"
        return result

    blocked, hit = foundation_blocks_learning(topic)
'''
learning = replace_once(
    learning,
    old_after_extract,
    new_after_extract,
    "Character Learning rejects interpersonal junk topic",
)

old_entries_line = '''        entries = list(data.get("entries", {}).values())

    if not entries:
'''
new_entries_line = '''        entries = [
            entry
            for entry in data.get("entries", {}).values()
            if _valid_preference_topic(str(entry.get("topic") or ""))
        ]

    if not entries:
'''
learning = replace_inside_section(
    learning,
    "def format_character_learning_for_prompt(",
    "def format_character_learning_debug(",
    old_entries_line,
    new_entries_line,
    "Existing junk learning hidden from Writer",
)
sources["learning"] = learning

# =====================================================================
# BOT 3.1.0 — integrate all live character directives
# =====================================================================
bot = sources["bot"]
bot = replace_once(
    bot,
    'BOT_VERSION = "3.0.2-output-integrity"',
    TARGET_BOT_VERSION,
    "Bot version -> 3.1.0-character-live",
)

old_foundation_import = '''from character_foundation import (
    CHARACTER_FOUNDATION_VERSION,
    build_character_context,
    format_foundation_debug,
    foundation_stats,
)
'''
new_foundation_import = '''from character_foundation import (
    CHARACTER_FOUNDATION_VERSION,
    build_character_context,
    build_direct_foundation_directive,
    format_foundation_debug,
    foundation_stats,
)
'''
bot = replace_once(
    bot,
    old_foundation_import,
    new_foundation_import,
    "Bot imports direct Foundation directive",
)

old_state_call = '''        character_state_text = (
            format_character_state_for_prompt()
        )
'''
new_state_call = '''        character_state_text = (
            format_character_state_for_prompt(
                user_text=user_text
            )
        )

        character_directive_text = (
            build_direct_foundation_directive(
                user_text
            )
        )

        turn_identity_text = f"""
[TURN IDENTITY / SPEAKER OWNERSHIP — HARD]

Du bist Evilnae. Du bist NIEMALS Hanae.
Die neue Discord-Nachricht wird von EVILNAE geschrieben.

Aktueller Gesprächspartner:
{username} [Discord-ID: {user_id}]

Ist der aktuelle Gesprächspartner Hanae:
{is_hanae}

REGELN:
- "Evil" und "Evilnae" bezeichnen DICH, nicht eine dritte Person.
- Wenn ein passendes "sie/ihr" im lokalen Kontext auf Evilnae zeigt, antworte über dich in erster Person: ich/mich/mir.
- Hanae bleibt Hanae. Du übernimmst niemals ihre Perspektive, Vorlieben, Handlungen oder Seite aus Versehen.
- Wenn jemand Hanae gegen Evilnae anfeuert, bist DU die Evilnae-Seite. Werde nicht zum neutralen Kommentator und feuere nicht versehentlich deine Gegnerin an.
- Eine frühere Evilnae-Antwort an einen ANDEREN User ist nicht automatisch deine Antwort an diesen User und persönliche Details daraus werden nicht übertragen.
""".strip()
'''
bot = replace_once(
    bot,
    old_state_call,
    new_state_call,
    "Bot builds current-activity + turn-identity directives",
)

old_character_append = '''        writer_context += (
            "\\n\\n"
            + character_context_text
            + "\\n\\n"
            + character_state_text
            + "\\n\\n"
            + character_learning_text
        )
'''
new_character_append = '''        writer_context += (
            "\\n\\n"
            + character_context_text
            + "\\n\\n"
            + character_state_text
            + "\\n\\n"
            + character_learning_text
            + "\\n\\n"
            + character_directive_text
            + "\\n\\n"
            + turn_identity_text
        )
'''
bot = replace_once(
    bot,
    old_character_append,
    new_character_append,
    "Writer receives direct Canon + immutable turn identity",
)

# Extra deterministic detector for the exact class of self-side mistake seen live.
identity_helper = r'''def character_identity_violation_reasons(answer, user_text):
    answer_text = str(answer or "").strip()
    user = str(user_text or "").strip().lower()
    lowered = answer_text.lower()

    reasons = []

    if re.search(r"\bgegen\s+evil(?:nae)?\b", user, flags=re.IGNORECASE):
        if re.search(
            r"\b(?:go|los)\s+hana(?:e)?\b|\bzeig\s+(?:ihnen|denen)\b",
            lowered,
            flags=re.IGNORECASE,
        ):
            reasons.append("self_side_confusion")

    if re.search(r"\b(?:evil|evilnae)\b", user, flags=re.IGNORECASE):
        if re.match(
            r"^\s*(?:evilnae|evil|sie)\s+(?:ist|hat|macht|will|kann|mag|findet)\b",
            lowered,
            flags=re.IGNORECASE,
        ):
            reasons.append("evilnae_third_person_self_reference")

    return list(dict.fromkeys(reasons))


'''
bot = insert_before_once(
    bot,
    "# =========================================================\n# WRITER VALIDATION\n",
    identity_helper,
    "Deterministic Evilnae/Hanae identity detector",
)

# Final repair after all candidate selection, immediately before the emote layer.
identity_gate = r'''        # =================================================
        # 3.1 CHARACTER IDENTITY FINAL GATE
        # =================================================

        identity_violations = (
            character_identity_violation_reasons(
                answer,
                user_text
            )
        )

        if identity_violations:
            print(
                "[CHARACTER IDENTITY VIOLATION] "
                f"user={username} "
                f"violations={identity_violations} "
                f"answer={answer!r}"
            )

            identity_repair = (
                await repair_writer_answer(
                    original_answer=answer,
                    violation_reasons=identity_violations,
                    writer_context=(
                        writer_context
                        + "\\n\\n"
                        + turn_identity_text
                    ),
                    current_mood=current_mood,
                    username=username,
                    token_limit=writer_token_limit,
                    autonomous_participation=autonomous_participation,
                )
            )

            if identity_repair:
                identity_repair = clean_generated_answer(identity_repair)
                identity_repair = enforce_permanent_expression_bans(identity_repair)

                hard_reasons = get_writer_violation_reasons(
                    answer=identity_repair,
                    decision=decision,
                    autonomous_participation=autonomous_participation,
                )

                identity_still_bad = character_identity_violation_reasons(
                    identity_repair,
                    user_text,
                )

                self_bad = self_knowledge_violation_reasons(
                    identity_repair,
                    self_evidence,
                )

                knowledge_bad = knowledge_violation_reasons(
                    identity_repair,
                    knowledge_constraint,
                )

                if not hard_reasons and not identity_still_bad and not self_bad and not knowledge_bad:
                    answer = identity_repair
                    print(
                        "[CHARACTER IDENTITY REPAIR SUCCESS] "
                        f"user={username}"
                    )
                else:
                    print(
                        "[CHARACTER IDENTITY REPAIR REJECTED] "
                        f"user={username} "
                        f"hard={hard_reasons} identity={identity_still_bad} "
                        f"self={self_bad} knowledge={knowledge_bad}"
                    )
            else:
                print(
                    "[CHARACTER IDENTITY REPAIR FAILED] "
                    f"user={username}"
                )

'''
bot = insert_before_once(
    bot,
    "        # =================================================\n        # 11.9 EVILNAE APPLICATION EMOTE LAYER\n",
    identity_gate,
    "Final Evilnae/Hanae identity repair gate",
)

sources["bot"] = bot

# =====================================================================
# PRE-WRITE INVARIANTS + SYNTAX
# =====================================================================
required = {
    "bot": [
        TARGET_BOT_VERSION,
        "TURN IDENTITY / SPEAKER OWNERSHIP",
        "character_directive_text",
        "CHARACTER IDENTITY VIOLATION",
    ],
    "foundation": [
        'CHARACTER_FOUNDATION_VERSION = "1.1-live-retrieval"',
        "build_direct_foundation_directive",
        "foundation_content_not_used",
    ],
    "state": [
        'CHARACTER_STATE_VERSION = "1.1-current-activity"',
        "FOUNDATION #567/#569",
    ],
    "self_model": [
        'SELF_MODEL_VERSION = "2.1-character-foundation"',
        "GENERIC FAVORITE CATEGORY GUARD",
    ],
    "understanding": [
        'UNDERSTANDING_VERSION = "1.1-subject-authority"',
        "subject_scope_mismatch",
    ],
    "conversation_understanding": [
        'CONVERSATION_UNDERSTANDING_VERSION = "1.1-thread-ownership"',
        "HARD THREAD-OWNERSHIP RULES",
    ],
    "quality": [
        'OUTPUT_QUALITY_VERSION = "2.2"',
        "direct_user_echo",
        "repeated_4word_phrase",
    ],
    "expression": [
        'EXPRESSION_VERSION = "2.2"',
        "CHARACTER SURFACE",
    ],
    "learning": [
        'CHARACTER_LEARNING_VERSION = "1.1"',
        "invalid_preference_topic",
    ],
}

for name, markers in required.items():
    for marker in markers:
        if marker not in sources[name]:
            fail(f"{FILES[name].name}: missing patched invariant {marker!r}")

for name, text in sources.items():
    syntax_check(text, FILES[name].name)

# =====================================================================
# BACKUP — only after every patch and syntax check passed
# =====================================================================
timestamp = datetime.now().astimezone().strftime("%Y%m%d-%H%M%S")
backup_directory = BACKUP_ROOT / timestamp

try:
    backup_directory.mkdir(parents=True, exist_ok=False)
except Exception as error:
    fail(f"Could not create backup directory: {type(error).__name__}: {error}")

for name, path in FILES.items():
    try:
        shutil.copy2(path, backup_directory / path.name)
    except Exception as error:
        fail(f"Backup failed for {path.name}: {type(error).__name__}: {error}")
    ok(f"Backup: {path.name}")

# =====================================================================
# WRITE
# =====================================================================
try:
    for name, path in FILES.items():
        atomic_write(path, sources[name])
        ok(f"Updated: {path.name}")
except Exception as error:
    print()
    print(f"[WRITE ERROR] {type(error).__name__}: {error}")
    print(f"Backups: {backup_directory}")
    raise

# =====================================================================
# OPTIONAL MODULE SELF-TESTS
# =====================================================================
header("POST-INSTALL SELF TESTS")

test_commands = [
    ("character_foundation.py", [sys.executable, "character_foundation.py"]),
    ("character_state.py", [sys.executable, "character_state.py"]),
    ("conversation_understanding.py", [sys.executable, "conversation_understanding.py"]),
    ("response_quality.py", [sys.executable, "response_quality.py"]),
]

for label, command in test_commands:
    result = subprocess.run(
        command,
        cwd=str(PROJECT_ROOT),
        check=False,
    )
    if result.returncode == 0:
        ok(f"Self-test: {label}")
    else:
        print(f"[WARN] Self-test returned {result.returncode}: {label}")

header("EVILNAE 3.1.0 CHARACTER LIVE FIX INSTALLED")
print("Installed:")
print("  [✓] stronger Excel/Foundation retrieval + direct-answer authority")
print("  [✓] fixed favorite categories cannot be replaced by model inventions")
print("  [✓] unknown favorite categories stay OPEN/LEARN")
print("  [✓] 'what are you doing?' now produces one concrete canon-safe activity")
print("  [✓] current game/anime/social activity persists more naturally")
print("  [✓] Evilnae/Hanae speaker identity and side ownership hardened")
print("  [✓] Hanae fact knowledge is subject-scoped; no unrelated lore authorization")
print("  [✓] cross-user personalized context no longer bleeds as easily")
print("  [✓] exact short user echoes are severe output issues")
print("  [✓] repeated 4-word phrases trigger repetition repair")
print("  [✓] Evilnae surface style is drier / less assistant-friendly")
print("  [✓] junk interpersonal phrases are blocked from Character Learning")
print("  [✓] all 3.0.2 output-integrity protections remain active")
print()
print(f"Backup: {backup_directory}")
print()
print("NO MEMORY RESET REQUIRED.")
print()
print("NEXT:")
print("  python bot.py")
print()
