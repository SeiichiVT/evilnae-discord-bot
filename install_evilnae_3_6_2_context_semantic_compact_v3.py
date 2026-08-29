from pathlib import Path
from datetime import datetime
import ast
import shutil
import subprocess
import sys

PROJECT_ROOT = Path(__file__).resolve().parent
BOT_PATH = PROJECT_ROOT / "bot.py"
FOUNDATION_PATH = PROJECT_ROOT / "character_foundation.py"
STABILITY_PATH = PROJECT_ROOT / "live_stability.py"
BACKUP_ROOT = PROJECT_ROOT / "live_fix_backups"

EXPECTED_BOT = 'BOT_VERSION = "3.6.1-affect-repetition"'
TARGET_BOT = 'BOT_VERSION = "3.6.2-context-semantic"'
EXPECTED_FOUNDATION = 'CHARACTER_FOUNDATION_VERSION = "1.1-live-retrieval"'
TARGET_FOUNDATION = 'CHARACTER_FOUNDATION_VERSION = "1.2-relevance-floor"'

LIVE_SOURCE = 'from __future__ import annotations\n\nimport contextvars\nimport functools\nimport os\nimport re\nfrom typing import Any\n\nfrom participation import ParticipationDecision\nfrom character_state import extract_character_states\nfrom local_voice import LocalVoiceResult\n\n\nLIVE_STABILITY_VERSION = "1.0"\nCONSOLE_OUTPUT_VERSION = "1.0"\n\n_CURRENT_USER_TEXT = contextvars.ContextVar(\n    "evilnae_live_user_text",\n    default="",\n)\n\n_CURRENT_USERNAME = contextvars.ContextVar(\n    "evilnae_live_username",\n    default="unknown",\n)\n\n_SURFACE_FAILED = contextvars.ContextVar(\n    "evilnae_surface_failed",\n    default=False,\n)\n\n\n# =========================================================\n# COMPACT TERMINAL\n# =========================================================\n\ndef get_console_mode() -> str:\n    mode = str(\n        os.getenv(\n            "EVILNAE_CONSOLE_MODE",\n            "compact",\n        )\n        or "compact"\n    ).strip().lower()\n\n    if mode not in {\n        "compact",\n        "quiet",\n        "debug",\n    }:\n        mode = "compact"\n\n    return mode\n\n\nclass ConsoleOutputFilter:\n    """Filter only terminal output; file logging remains untouched."""\n\n    def __init__(self):\n        self._buffer = ""\n        self._traceback_budget = 0\n\n    def _errorish(self, line: str) -> bool:\n        value = line.lower()\n\n        return bool(\n            "[error" in value\n            or "[warn" in value\n            or " error " in value\n            or " warning " in value\n            or value.startswith("error:")\n            or value.startswith("warning:")\n        )\n\n    def _show_compact(self, line: str) -> bool:\n        stripped = line.strip()\n\n        if not stripped:\n            return False\n\n        if stripped.startswith(\n            (\n                "[LIVE IN]",\n                "[LIVE OUT]",\n                "[LIVE GUARD]",\n                "[LIVE WARN]",\n                "[AUTO FILE LOGGING]",\n                "[LOCAL VOICE WARM]",\n            )\n        ):\n            return True\n\n        if self._errorish(stripped):\n            return True\n\n        startup_prefixes = (\n            "Evilnae ist online als ",\n            "Bot Version:",\n            "Live Stability v",\n            "Compact Console v",\n            "Response Planner v",\n            "Conversation Episodes v",\n            "Emotional Salience v",\n            "Qwen Surface Writer v",\n            "Output Quality v",\n            "Routing Hardening v",\n            "Character Foundation v",\n            "Foundation Entries:",\n            "Character Learning v",\n            "Character Current State v",\n            "Local Voice v",\n            "Voice Memory v",\n        )\n\n        if stripped.startswith(\n            startup_prefixes\n        ):\n            return True\n\n        if stripped.startswith(\n            "Traceback (most recent call last):"\n        ):\n            self._traceback_budget = 24\n            return True\n\n        if self._traceback_budget > 0:\n            self._traceback_budget -= 1\n            return True\n\n        return False\n\n    def _show_quiet(self, line: str) -> bool:\n        stripped = line.strip()\n\n        if not stripped:\n            return False\n\n        if stripped.startswith(\n            (\n                "[LIVE OUT]",\n                "[LIVE WARN]",\n                "[AUTO FILE LOGGING]",\n                "Evilnae ist online als ",\n                "Bot Version:",\n            )\n        ):\n            return True\n\n        if self._errorish(stripped):\n            return True\n\n        if stripped.startswith(\n            "Traceback (most recent call last):"\n        ):\n            self._traceback_budget = 24\n            return True\n\n        if self._traceback_budget > 0:\n            self._traceback_budget -= 1\n            return True\n\n        return False\n\n    def _show_line(self, line: str) -> bool:\n        mode = get_console_mode()\n\n        if mode == "debug":\n            return True\n\n        if mode == "quiet":\n            return self._show_quiet(line)\n\n        return self._show_compact(line)\n\n    def filter_chunk(self, chunk: str) -> str:\n        value = str(\n            chunk\n            if chunk is not None\n            else ""\n        )\n\n        if get_console_mode() == "debug":\n            return value\n\n        self._buffer += value\n        output = []\n\n        while "\\n" in self._buffer:\n            line, self._buffer = (\n                self._buffer.split(\n                    "\\n",\n                    1,\n                )\n            )\n\n            if self._show_line(line):\n                output.append(\n                    line + "\\n"\n                )\n\n        return "".join(output)\n\n    def flush_pending(self) -> str:\n        if not self._buffer:\n            return ""\n\n        pending = self._buffer\n        self._buffer = ""\n\n        return (\n            pending\n            if self._show_line(pending)\n            else ""\n        )\n\n\n# =========================================================\n# TEXT HELPERS\n# =========================================================\n\nSTOPWORDS = {\n    "aber", "also", "auch", "auf", "aus", "bei", "bin", "bist",\n    "das", "dass", "dein", "deine", "dem", "den", "der", "die",\n    "dir", "dich", "du", "ein", "eine", "einen", "er", "es",\n    "für", "fuer", "hab", "habe", "hat", "ich", "im", "in",\n    "ist", "ja", "mal", "mein", "meine", "mit", "nach", "nicht",\n    "noch", "nur", "oder", "schon", "sie", "so", "und", "uns",\n    "von", "war", "was", "wie", "wir", "zu", "zum", "zur",\n    "gerade", "grad", "jetzt", "heute", "eigentlich", "denn",\n    "dann", "wenn", "weil", "mir", "mich", "ihr", "ihre",\n}\n\n\ndef _normalize(text: Any) -> str:\n    value = str(\n        text\n        or ""\n    ).lower()\n\n    value = re.sub(\n        r"<a?:[A-Za-z0-9_]+:\\d+>",\n        " ",\n        value,\n    )\n\n    value = re.sub(\n        r"[^a-z0-9äöüß]+",\n        " ",\n        value,\n    )\n\n    return re.sub(\n        r"\\s+",\n        " ",\n        value,\n    ).strip()\n\n\ndef _words(text: Any) -> list[str]:\n    return re.findall(\n        r"[A-Za-zÄÖÜäöüß0-9]+",\n        str(text or "").lower(),\n    )\n\n\ndef _tokens(text: Any) -> set[str]:\n    return {\n        token\n        for token in _words(text)\n        if (\n            len(token) >= 3\n            and token not in STOPWORDS\n        )\n    }\n\n\ndef _short(text: Any, limit: int = 180) -> str:\n    value = re.sub(\n        r"\\s+",\n        " ",\n        str(text or ""),\n    ).strip()\n\n    if len(value) <= limit:\n        return value\n\n    return value[: limit - 3] + "..."\n\n\ndef _merge_unique(\n    original,\n    additions,\n    *,\n    limit=16,\n):\n    result = []\n\n    for group in (\n        original or [],\n        additions or [],\n    ):\n        for item in group:\n            value = str(\n                item\n                or ""\n            ).strip()\n\n            if (\n                value\n                and value not in result\n            ):\n                result.append(value)\n\n            if len(result) >= limit:\n                return result\n\n    return result\n\n\n# =========================================================\n# SELF-STATE AUTHORITY 2.0\n# =========================================================\n\nSELF_STATE_WORDS = (\n    "müde",\n    "muede",\n    "verschlafen",\n    "verwirrt",\n    "durcheinander",\n    "planlos",\n    "beschäftigt",\n    "beschaeftigt",\n    "krank",\n    "kopfschmerzen",\n    "hungrig",\n    "traurig",\n    "sauer",\n    "genervt",\n)\n\nSELF_STATE_USER_PATTERN = re.compile(\n    r"\\b(?:"\n    r"du\\s+(?:bist|wirkst)\\s+"\n    r"|bist\\s+du\\s+"\n    r"|wirkst\\s+du\\s+"\n    r")"\n    r"(?:(?:heute|gerade|grad|irgendwie|echt|wirklich|"\n    r"voll|total|ziemlich|so)\\s+){0,4}"\n    r"(?P<state>"\n    + "|".join(SELF_STATE_WORDS)\n    + r")\\b",\n    re.IGNORECASE,\n)\n\nFIRST_PERSON_STATE_PATTERNS = {\n    "müde": re.compile(\n        r"\\bich\\s+bin\\s+.*\\bmüde\\b",\n        re.I,\n    ),\n    "muede": re.compile(\n        r"\\bich\\s+bin\\s+.*\\bmuede\\b",\n        re.I,\n    ),\n    "verschlafen": re.compile(\n        r"\\bich\\s+.*\\bverschlafen\\b",\n        re.I,\n    ),\n    "verwirrt": re.compile(\n        r"\\bich\\s+bin\\s+.*\\bverwirrt\\b",\n        re.I,\n    ),\n    "durcheinander": re.compile(\n        r"\\bich\\s+bin\\s+.*\\bdurcheinander\\b",\n        re.I,\n    ),\n    "planlos": re.compile(\n        r"\\bich\\s+.*\\bplanlos\\b",\n        re.I,\n    ),\n    "beschäftigt": re.compile(\n        r"\\bich\\s+bin\\s+.*\\bbeschäftigt\\b",\n        re.I,\n    ),\n    "beschaeftigt": re.compile(\n        r"\\bich\\s+bin\\s+.*\\bbeschaeftigt\\b",\n        re.I,\n    ),\n    "krank": re.compile(\n        r"\\bich\\s+bin\\s+.*\\bkrank\\b",\n        re.I,\n    ),\n    "kopfschmerzen": re.compile(\n        r"\\bich\\s+hab(?:e)?\\s+.*\\bkopfschmerzen\\b",\n        re.I,\n    ),\n    "hungrig": re.compile(\n        r"\\bich\\s+bin\\s+.*\\bhungrig\\b",\n        re.I,\n    ),\n    "traurig": re.compile(\n        r"\\bich\\s+bin\\s+.*\\btraurig\\b",\n        re.I,\n    ),\n    "sauer": re.compile(\n        r"\\bich\\s+bin\\s+.*\\bsauer\\b",\n        re.I,\n    ),\n    "genervt": re.compile(\n        r"\\bich\\s+bin\\s+.*\\bgenervt\\b",\n        re.I,\n    ),\n}\n\n\ndef _grounded(\n    state_word: str,\n    *,\n    inner_state_guidance: str = "",\n    evidence_context: str = "",\n    response_plan_text: str = "",\n) -> bool:\n    needle = _normalize(\n        state_word\n    )\n\n    # Only actual state/evidence may ground a current self-state.\n    # The Response Plan can mention a state merely to FORBID adopting it.\n    authority = _normalize(\n        " ".join(\n            (\n                inner_state_guidance or "",\n                evidence_context or "",\n            )\n        )\n    )\n\n    return bool(\n        needle\n        and needle in authority\n    )\n\n\ndef adopts_ungrounded_user_state(\n    *,\n    user_text: str,\n    candidate: str,\n    inner_state_guidance: str = "",\n    evidence_context: str = "",\n    response_plan_text: str = "",\n) -> bool:\n    match = SELF_STATE_USER_PATTERN.search(\n        str(user_text or "")\n    )\n\n    if not match:\n        return False\n\n    state_word = (\n        match.group("state")\n        .lower()\n    )\n\n    pattern = (\n        FIRST_PERSON_STATE_PATTERNS.get(\n            state_word\n        )\n    )\n\n    if not pattern:\n        return False\n\n    if not pattern.search(\n        str(candidate or "")\n    ):\n        return False\n\n    return not _grounded(\n        state_word,\n        inner_state_guidance=(\n            inner_state_guidance\n        ),\n        evidence_context=(\n            evidence_context\n        ),\n        response_plan_text=(\n            response_plan_text\n        ),\n    )\n\n\n# =========================================================\n# CARE / SENSITIVE CONTEXT\n# =========================================================\n\nCARE_CONTEXT_PATTERN = re.compile(\n    r"\\b(?:"\n    r"kopfschmerz(?:en)?|migräne|migraene|"\n    r"schmerzen|krank|fieber|"\n    r"mir\\s+geht(?:\'|’)?s\\s+nicht\\s+gut|"\n    r"geht\\s+es\\s+(?:ihr|ihm)\\s+nicht\\s+gut|"\n    r"bitte\\s+leiser|sei\\s+bitte\\s+leiser|"\n    r"kümmer(?:e)?\\s+dich|kuemmer(?:e)?\\s+dich|"\n    r"ruh\\s+dich\\s+aus|ausruhen"\n    r")\\b",\n    re.IGNORECASE,\n)\n\nPRACTICAL_HELP_PATTERN = re.compile(\n    r"\\b(?:"\n    r"tee\\s+(?:machen|mach|bringen)|"\n    r"mach(?:st)?\\s+.*\\btee\\b|"\n    r"bring(?:st)?\\s+.*\\b(?:tee|trinken|wasser)\\b|"\n    r"kümmer(?:e)?\\s+dich|kuemmer(?:e)?\\s+dich|"\n    r"bitte\\s+leiser|sei\\s+bitte\\s+leiser"\n    r")\\b",\n    re.IGNORECASE,\n)\n\n\n# =========================================================\n# INTENT FULFILLMENT\n# =========================================================\n\nHOW_ARE_YOU_PATTERN = re.compile(\n    r"\\b(?:wie\\s+geht(?:\'|’)?s\\s+dir|"\n    r"wie\\s+geht\\s+es\\s+dir|"\n    r"wie\\s+gehts\\s+dir)\\b",\n    re.IGNORECASE,\n)\n\nFOOD_HISTORY_PATTERN = re.compile(\n    r"\\b(?:was\\s+hast\\s+du(?:\\s+heute)?\\s+(?:alles\\s+)?gegessen|"\n    r"was\\s+du\\s+alles\\s+heute\\s+gegessen)\\b",\n    re.IGNORECASE,\n)\n\nCURRENT_ACTIVITY_PATTERN = re.compile(\n    r"\\b(?:was\\s+machst\\s+du|was\\s+treibst\\s+du|"\n    r"was\\s+zockst\\s+du|was\\s+spielst\\s+du|"\n    r"was\\s+schaust\\s+du|was\\s+guckst\\s+du)\\b",\n    re.IGNORECASE,\n)\n\nMUSIC_PREFERENCE_PATTERN = re.compile(\n    r"\\b(?:welche\\s+musik|was\\s+für\\s+musik|"\n    r"was\\s+fuer\\s+musik|musikart\\s+hörst\\s+du|"\n    r"musikart\\s+hoerst\\s+du)\\b",\n    re.IGNORECASE,\n)\n\nDIRECT_REQUEST_PATTERN = re.compile(\n    r"\\b(?:kannst\\s+du|könntest\\s+du|koenntest\\s+du|"\n    r"mach\\s+mir|mach\\s+ihr|bring\\s+mir|bring\\s+ihr|"\n    r"kümmer(?:e)?\\s+dich|kuemmer(?:e)?\\s+dich|"\n    r"sei\\s+bitte)\\b",\n    re.IGNORECASE,\n)\n\nSELF_INTENTION_QUERY_PATTERN = re.compile(\n    r"\\b(?:trollst\\s+du|willst\\s+du|"\n    r"möchtest\\s+du|moechtest\\s+du|"\n    r"hast\\s+du\\s+vor|"\n    r"bist\\s+du\\s+beschäftigt|"\n    r"bist\\s+du\\s+beschaeftigt)\\b",\n    re.IGNORECASE,\n)\n\nNONANSWER_UNCERTAINTY_PATTERN = re.compile(\n    r"\\b(?:weiß\\s+ich\\s+(?:grad|gerade)?\\s*nicht\\s+sicher|"\n    r"weiss\\s+ich\\s+(?:grad|gerade)?\\s*nicht\\s+sicher|"\n    r"bin\\s+mir\\s+(?:grad|gerade)?\\s*nicht\\s+sicher|"\n    r"keine\\s+ahnung,?\\s+das\\s+(?:ändert|aendert)\\s+sich|"\n    r"ka,?\\s+ob\\s+ich)\\b",\n    re.IGNORECASE,\n)\n\n\ndef intent_violation_reason(\n    user_text: str,\n    candidate: str,\n) -> str:\n    user = str(\n        user_text\n        or ""\n    )\n\n    answer = str(\n        candidate\n        or ""\n    )\n\n    if not _normalize(answer):\n        return "empty_answer"\n\n    if HOW_ARE_YOU_PATTERN.search(user):\n        if not re.search(\n            r"\\b(?:mir\\s+geht|geht\\s+so|"\n            r"geht\\s+(?:mir\\s+)?(?:gut|okay|schlecht)|"\n            r"ich\\s+bin|bin\\s+(?:gut|okay|fit|wach|"\n            r"müde|muede|entspannt|genervt)|"\n            r"alles\\s+(?:gut|okay)|ganz\\s+(?:gut|okay))\\b",\n            answer,\n            re.IGNORECASE,\n        ):\n            return "intent_how_are_you_not_answered"\n\n    if FOOD_HISTORY_PATTERN.search(user):\n        if not re.search(\n            r"\\b(?:gegessen|esse|essen|frühstück|fruehstueck|"\n            r"mittag|abendessen|snack|nudel|pizza|brot|toast|"\n            r"müsli|muesli|reis|pasta|burger|döner|doener|"\n            r"nugget|suppe|salat|noch\\s+nichts|"\n            r"nichts\\s+gegessen|weiß\\s+ich\\s+nicht|"\n            r"weiss\\s+ich\\s+nicht)\\b",\n            answer,\n            re.IGNORECASE,\n        ):\n            return "intent_food_history_not_answered"\n\n    if CURRENT_ACTIVITY_PATTERN.search(user):\n        if not re.search(\n            r"\\b(?:ich\\s+(?:zock|zocke|spiel|spiele|schau|"\n            r"schaue|guck|gucke|scroll|scrolle|hör|höre|"\n            r"hoer|hoere|les|lese|koch|koche|ess|esse|"\n            r"trink|trinke|arbeite|chill|hänge|haenge|"\n            r"mach|mache)|"\n            r"bin\\s+(?:gerade|grad)\\s+(?:am|beim|auf|in))\\b",\n            answer,\n            re.IGNORECASE,\n        ):\n            return "intent_current_activity_not_answered"\n\n    if DIRECT_REQUEST_PATTERN.search(user):\n        if NONANSWER_UNCERTAINTY_PATTERN.search(\n            answer\n        ):\n            return "intent_request_uncertainty"\n\n        if not re.search(\n            r"\\b(?:klar|ja|jap|jo|okay|ok|mach|mache|"\n            r"komm|komme|bring|bringe|kann\\s+ich|"\n            r"versuch|versuche|leiser|kümmere|kuemmere|"\n            r"nein|nee|nö|noe|geht\\s+(?:grad|gerade)\\s+nicht|"\n            r"später|spaeter)\\b",\n            answer,\n            re.IGNORECASE,\n        ):\n            return "intent_request_not_answered"\n\n    if SELF_INTENTION_QUERY_PATTERN.search(user):\n        if NONANSWER_UNCERTAINTY_PATTERN.search(\n            answer\n        ):\n            return "intent_self_intention_uncertainty"\n\n    if MUSIC_PREFERENCE_PATTERN.search(user):\n        if re.search(\n            r"\\b(?:gehört|gehoert)\\s+mir\\s+eher\\s+zu\\b",\n            answer,\n            re.IGNORECASE,\n        ):\n            return "intent_music_malformed"\n\n    return ""\n\n\n# =========================================================\n# SEMANTIC SANITY\n# =========================================================\n\nMALFORMED_PATTERNS = (\n    (\n        "semantic_bruederin",\n        re.compile(\n            r"\\bbrüderin\\b|\\bbruederin\\b",\n            re.IGNORECASE,\n        ),\n    ),\n    (\n        "semantic_die_gps",\n        re.compile(\n            r"\\bdie\\s+gps\\b",\n            re.IGNORECASE,\n        ),\n    ),\n    (\n        "semantic_gehoert_mir_zu",\n        re.compile(\n            r"\\b(?:gehört|gehoert)\\s+mir\\s+eher\\s+zu\\b",\n            re.IGNORECASE,\n        ),\n    ),\n    (\n        "semantic_busy_tea_logic",\n        re.compile(\n            r"\\bich\\s+mach(?:e|\'|’)?\\s+.{0,35}\\btee\\b"\n            r".{0,35}\\bwenn\\s+ich\\s+beschäftigt\\s+bin\\b",\n            re.IGNORECASE,\n        ),\n    ),\n)\n\n\ndef semantic_violation_reason(\n    candidate: str,\n    *,\n    user_text: str = "",\n    inner_state_guidance: str = "",\n    evidence_context: str = "",\n    response_plan_text: str = "",\n) -> str:\n    answer = str(\n        candidate\n        or ""\n    )\n\n    for name, pattern in MALFORMED_PATTERNS:\n        if pattern.search(answer):\n            return name\n\n    if adopts_ungrounded_user_state(\n        user_text=user_text,\n        candidate=answer,\n        inner_state_guidance=(\n            inner_state_guidance\n        ),\n        evidence_context=(\n            evidence_context\n        ),\n        response_plan_text=(\n            response_plan_text\n        ),\n    ):\n        return "semantic_ungrounded_self_state"\n\n    return intent_violation_reason(\n        user_text,\n        answer,\n    )\n\n\n# =========================================================\n# CONCEPT REPETITION\n# =========================================================\n\nCONCEPT_PATTERNS = {\n    "confusion_loop": re.compile(\n        r"\\b(?:verwirrt|durcheinander|planlos|"\n        r"in\\s+gedanken\\s+abdrift|im\\s+nebel|"\n        r"verschlafen|schlecht\\s+eingeschlafen)\\b",\n        re.IGNORECASE,\n    ),\n    "uncertainty_loop": re.compile(\n        r"\\b(?:nicht\\s+sicher|"\n        r"weiß\\s+ich\\s+(?:grad|gerade)?\\s*nicht|"\n        r"weiss\\s+ich\\s+(?:grad|gerade)?\\s*nicht|"\n        r"keine\\s+ahnung|ka,?\\s+ob)\\b",\n        re.IGNORECASE,\n    ),\n    "food_boss_loop": re.compile(\n        r"\\b(?:boss.{0,24}fressen|"\n        r"fressen.{0,24}boss|"\n        r"keine\\s+halben\\s+sachen.{0,20}fressen)\\b",\n        re.IGNORECASE,\n    ),\n    "morning_flat_loop": re.compile(\n        r"\\b(?:aufgestanden.{0,20}chill|"\n        r"morgen,?\\s+(?:läuft|laeuft))\\b",\n        re.IGNORECASE,\n    ),\n}\n\n\ndef repeated_concepts(\n    candidate: str,\n    recent_messages,\n) -> list[str]:\n    result = []\n\n    for name, pattern in (\n        CONCEPT_PATTERNS.items()\n    ):\n        if not pattern.search(\n            str(candidate or "")\n        ):\n            continue\n\n        if any(\n            pattern.search(\n                str(message or "")\n            )\n            for message\n            in list(\n                recent_messages\n                or []\n            )[-12:]\n        ):\n            result.append(name)\n\n    return result\n\n\ndef _user_echo_ratio(\n    user_text: str,\n    candidate: str,\n) -> float:\n    user_tokens = _tokens(\n        user_text\n    )\n\n    candidate_tokens = _tokens(\n        candidate\n    )\n\n    if (\n        len(user_tokens) < 3\n        or len(candidate_tokens) < 3\n    ):\n        return 0.0\n\n    return len(\n        user_tokens\n        &\n        candidate_tokens\n    ) / max(\n        1,\n        len(candidate_tokens),\n    )\n\n\n# =========================================================\n# EPISODE / THREAD RELEVANCE\n# =========================================================\n\nSHORT_CONTINUATION_PATTERN = re.compile(\n    r"^\\s*(?:ich\\s+glaube\\s+beides|beides|richtig|genau|"\n    r"stimmt|true|same|hä+|hae+|was\\??|wieso\\??|warum\\??|"\n    r"wie\\s+meinst\\s+du(?:\\s+das)?\\??|"\n    r"was\\s+meinst\\s+du\\??|"\n    r"brüderin\\s+was\\??|bruederin\\s+was\\??|"\n    r"nö|noe|nee|nein|aber\\s+.*|deshalb\\s+.*)"\n    r"\\s*[!.?]*\\s*$",\n    re.IGNORECASE,\n)\n\nBOT_REFERENCE_PATTERN = re.compile(\n    r"\\b(?:der\\s+bot|die\\s+bot|bott)\\b",\n    re.IGNORECASE,\n)\n\nPRONOUN_REPLY_PATTERN = re.compile(\n    r"^\\s*(?:ich\\s+glaube\\s+(?:sie|beides)|"\n    r"sie\\s+(?:ist|war|braucht|hat|kann)|"\n    r"ihr\\s+(?:geht|ist))\\b",\n    re.IGNORECASE,\n)\n\n\ndef _item_content(item) -> str:\n    if not isinstance(item, dict):\n        return ""\n\n    return str(\n        item.get(\n            "content",\n            "",\n        )\n        or ""\n    )\n\n\ndef filter_episode_snapshot(\n    channel_snapshot,\n    *,\n    limit=12,\n):\n    items = list(\n        channel_snapshot\n        or []\n    )\n\n    if len(items) <= 5:\n        return items[-limit:]\n\n    current = items[-1]\n    current_text = _item_content(\n        current\n    )\n\n    if (\n        len(_words(current_text)) <= 5\n        or SHORT_CONTINUATION_PATTERN.search(\n            current_text\n        )\n    ):\n        return items[-5:]\n\n    current_tokens = _tokens(\n        current_text\n    )\n\n    keep_indices = set(\n        range(\n            max(\n                0,\n                len(items) - 3,\n            ),\n            len(items),\n        )\n    )\n\n    current_user = str(\n        current.get(\n            "user_id",\n            "",\n        )\n        or ""\n    )\n\n    for index in range(\n        len(items) - 4,\n        -1,\n        -1,\n    ):\n        if len(keep_indices) >= min(\n            limit,\n            7,\n        ):\n            break\n\n        item = items[index]\n        overlap = (\n            current_tokens\n            &\n            _tokens(\n                _item_content(item)\n            )\n        )\n\n        same_user = (\n            current_user\n            and str(\n                item.get(\n                    "user_id",\n                    "",\n                )\n                or ""\n            )\n            ==\n            current_user\n        )\n\n        is_bot = (\n            str(\n                item.get(\n                    "type",\n                    "",\n                )\n            )\n            ==\n            "bot"\n        )\n\n        if (\n            overlap\n            or (\n                same_user\n                and len(keep_indices) < 5\n            )\n            or (\n                is_bot\n                and len(keep_indices) < 4\n            )\n        ):\n            keep_indices.add(\n                index\n            )\n\n    return [\n        items[index]\n        for index in sorted(\n            keep_indices\n        )\n    ][-limit:]\n\n\ndef _recent_context_mentions_evilnae(\n    channel_context: str,\n) -> bool:\n    return bool(\n        re.search(\n            r"\\bEvilnae\\b",\n            str(\n                channel_context\n                or ""\n            )[-1200:],\n            re.IGNORECASE,\n        )\n    )\n\n\ndef implicit_evilnae_continuation(\n    *,\n    current_message: str,\n    channel_context: str,\n    recent_evilnae_messages,\n) -> bool:\n    text = str(\n        current_message\n        or ""\n    ).strip()\n\n    if (\n        not text\n        or not recent_evilnae_messages\n        or not _recent_context_mentions_evilnae(\n            channel_context\n        )\n    ):\n        return False\n\n    word_count = len(\n        _words(text)\n    )\n\n    if (\n        word_count <= 14\n        and SHORT_CONTINUATION_PATTERN.search(\n            text\n        )\n    ):\n        return True\n\n    if (\n        word_count <= 16\n        and (\n            BOT_REFERENCE_PATTERN.search(\n                text\n            )\n            or PRONOUN_REPLY_PATTERN.search(\n                text\n            )\n        )\n    ):\n        return True\n\n    return False\n\n\n# =========================================================\n# CHARACTER STATE WRITE GUARD\n# =========================================================\n\nSUSPICIOUS_STATE_ANSWER_PATTERN = re.compile(\n    r"\\b(?:ich\\s+(?:schau|schaue|guck|gucke)\\s+mal,?\\s+ob|"\n    r"warte,?\\s+ich\\s+(?:schau|schaue|guck|gucke)\\s+mal|"\n    r"was\\s+brauchbares\\s+finden|"\n    r"bin\\s+mir\\s+(?:grad|gerade)?\\s*nicht\\s+sicher|"\n    r"weiß\\s+ich\\s+(?:grad|gerade)?\\s*nicht\\s+sicher|"\n    r"weiss\\s+ich\\s+(?:grad|gerade)?\\s*nicht\\s+sicher|"\n    r"in\\s+gedanken\\s+abdrift|planlos\\s+rumeier|"\n    r"ich\\s+(?:überlege|ueberlege)\\s+mal)\\b",\n    re.IGNORECASE,\n)\n\nSUSPICIOUS_ACTIVITY_VALUE_PATTERN = re.compile(\n    r"^(?:mal,?\\s+ob|ob\\s+ich|"\n    r"was\\s+brauchbares|mir\\s+.*|nach\\s+.*)",\n    re.IGNORECASE,\n)\n\n\ndef state_write_block_reason(\n    answer: str,\n) -> str:\n    text = str(\n        answer\n        or ""\n    )\n\n    if SUSPICIOUS_STATE_ANSWER_PATTERN.search(\n        text\n    ):\n        return "low_confidence_meta_activity"\n\n    for category, value in (\n        extract_character_states(\n            text\n        )\n    ):\n        if (\n            category == "activity"\n            and SUSPICIOUS_ACTIVITY_VALUE_PATTERN.search(\n                str(value or "")\n            )\n        ):\n            return "ambiguous_activity_capture"\n\n    return ""\n\n\n# =========================================================\n# WRAPPERS\n# =========================================================\n\ndef wrap_perceive_message(\n    original,\n):\n    @functools.wraps(original)\n    async def wrapped(\n        *args,\n        **kwargs,\n    ):\n        result = await original(\n            *args,\n            **kwargs,\n        )\n\n        username = str(\n            getattr(\n                result,\n                "username",\n                "unknown",\n            )\n            or "unknown"\n        )\n\n        text = str(\n            getattr(\n                result,\n                "text",\n                "",\n            )\n            or getattr(\n                result,\n                "raw_content",\n                "",\n            )\n            or ""\n        ).strip()\n\n        _CURRENT_USERNAME.set(\n            username\n        )\n\n        _CURRENT_USER_TEXT.set(\n            text\n        )\n\n        _SURFACE_FAILED.set(\n            False\n        )\n\n        if text:\n            print(\n                "[LIVE IN] "\n                f"{username}: "\n                f"{_short(text)}"\n            )\n\n        return result\n\n    return wrapped\n\n\ndef wrap_response_planner(\n    original,\n):\n    @functools.wraps(original)\n    def wrapped(\n        *args,\n        **kwargs,\n    ):\n        plan = original(\n            *args,\n            **kwargs,\n        )\n\n        user_text = str(\n            kwargs.get(\n                "user_text",\n                "",\n            )\n            or _CURRENT_USER_TEXT.get()\n            or ""\n        )\n\n        _CURRENT_USER_TEXT.set(\n            user_text\n        )\n\n        additions = []\n\n        direct_intent = bool(\n            HOW_ARE_YOU_PATTERN.search(\n                user_text\n            )\n            or FOOD_HISTORY_PATTERN.search(\n                user_text\n            )\n            or CURRENT_ACTIVITY_PATTERN.search(\n                user_text\n            )\n            or MUSIC_PREFERENCE_PATTERN.search(\n                user_text\n            )\n            or DIRECT_REQUEST_PATTERN.search(\n                user_text\n            )\n            or SELF_INTENTION_QUERY_PATTERN.search(\n                user_text\n            )\n        )\n\n        if direct_intent:\n            additions.extend(\n                [\n                    "aktuelle direkte Frage/Bitte zuerst konkret beantworten",\n                    "nicht auf einen älteren Episode-Nebengedanken ausweichen",\n                    "bei eigenem Verhalten/Zustand keine vage \'weiß ich nicht sicher\'-Antwort",\n                ]\n            )\n\n        state_match = (\n            SELF_STATE_USER_PATTERN.search(\n                user_text\n            )\n        )\n\n        if state_match:\n            state_word = (\n                state_match.group(\n                    "state"\n                )\n            )\n\n            plan.core_thought = (\n                "Auf die Beobachtung des Users reagieren, "\n                f"ohne \'{state_word}\' als bestätigten Selbstzustand "\n                "zu übernehmen. Der echte Inner/Current State hat Vorrang. "\n                "Wenn der Zustand nicht belegt ist, locker widersprechen "\n                "oder neutral bleiben."\n            )\n\n            additions.extend(\n                [\n                    "User-Spekulation über Evilnaes Zustand nicht als Fakt übernehmen",\n                    "Müdigkeit/Verwirrung/Beschäftigung/Krankheit nur aus echtem Inner/Current State behaupten",\n                ]\n            )\n\n            if getattr(\n                plan,\n                "stance",\n                "",\n            ) in {\n                "confused",\n                "annoyed",\n            }:\n                plan.stance = "playful"\n\n        if CARE_CONTEXT_PATTERN.search(\n            user_text\n        ):\n            plan.banter_intensity = min(\n                float(\n                    getattr(\n                        plan,\n                        "banter_intensity",\n                        0.0,\n                    )\n                    or 0.0\n                ),\n                0.12,\n            )\n\n            plan.warmth_intensity = max(\n                float(\n                    getattr(\n                        plan,\n                        "warmth_intensity",\n                        0.0,\n                    )\n                    or 0.0\n                ),\n                0.66,\n            )\n\n            if getattr(\n                plan,\n                "social_move",\n                "",\n            ) in {\n                "roast",\n                "tease",\n                "counter",\n                "challenge",\n                "curious_tease",\n            }:\n                plan.social_move = "support"\n\n            if getattr(\n                plan,\n                "stance",\n                "",\n            ) in {\n                "smug",\n                "competitive",\n                "annoyed",\n            }:\n                plan.stance = "warm"\n\n            additions.extend(\n                [\n                    "bei Schmerzen/Unwohlsein nicht gegen eine einfache Hilfe-Bitte argumentieren",\n                    "Rücksicht/Hilfe zuerst; Humor darf die Hilfe nicht untergraben",\n                ]\n            )\n\n            if PRACTICAL_HELP_PATTERN.search(\n                user_text\n            ):\n                plan.core_thought = (\n                    "Die praktische Bitte direkt beantworten "\n                    "und Rücksicht zeigen. Keine Gaming-/Chaos-Ausrede "\n                    "gegen Schmerzen oder Unwohlsein stellen."\n                )\n\n        recent = list(\n            kwargs.get(\n                "recent_evilnae_messages",\n                None,\n            )\n            or []\n        )\n\n        repeated = []\n\n        for name, pattern in (\n            CONCEPT_PATTERNS.items()\n        ):\n            count = sum(\n                1\n                for message in recent[-12:]\n                if pattern.search(\n                    str(message or "")\n                )\n            )\n\n            if count >= 2:\n                repeated.append(\n                    name\n                )\n\n        if repeated:\n            additions.append(\n                "bereits wiederholte Antwortidee komplett verlassen; nicht nur Synonyme austauschen"\n            )\n\n            additions.extend(\n                f"Konzept nicht erneut benutzen: {name}"\n                for name in repeated\n            )\n\n        plan.must_avoid = _merge_unique(\n            getattr(\n                plan,\n                "must_avoid",\n                [],\n            ),\n            additions,\n        )\n\n        return plan\n\n    return wrapped\n\n\ndef wrap_participation_brain(\n    original,\n):\n    @functools.wraps(original)\n    async def wrapped(\n        *args,\n        **kwargs,\n    ):\n        current_message = str(\n            kwargs.get(\n                "current_message",\n                "",\n            )\n            or ""\n        )\n\n        channel_context = str(\n            kwargs.get(\n                "channel_context",\n                "",\n            )\n            or ""\n        )\n\n        recent = list(\n            kwargs.get(\n                "recent_evilnae_messages",\n                None,\n            )\n            or []\n        )\n\n        if implicit_evilnae_continuation(\n            current_message=(\n                current_message\n            ),\n            channel_context=(\n                channel_context\n            ),\n            recent_evilnae_messages=(\n                recent\n            ),\n        ):\n            print(\n                "[LIVE GUARD] "\n                "implicit reply ownership -> Evilnae"\n            )\n\n            return ParticipationDecision(\n                action="join",\n                confidence="high",\n                relevance=0.90,\n                social_value=0.58,\n                conversation_involvement=0.96,\n                reason=(\n                    "implicit_recent_evilnae_continuation"\n                ),\n                response_goal=(\n                    "Auf die unmittelbare Fortsetzung "\n                    "des vorherigen Evilnae-Turns reagieren."\n                ),\n                notes=[\n                    "implicit_thread_ownership",\n                ],\n            )\n\n        return await original(\n            *args,\n            **kwargs,\n        )\n\n    return wrapped\n\n\ndef wrap_reference_context(\n    original,\n):\n    @functools.wraps(original)\n    def wrapped(\n        user_text,\n        channel_snapshot,\n        *args,\n        **kwargs,\n    ):\n        result = original(\n            user_text,\n            channel_snapshot,\n            *args,\n            **kwargs,\n        )\n\n        if (\n            SHORT_CONTINUATION_PATTERN.search(\n                str(user_text or "")\n            )\n            and channel_snapshot\n        ):\n            result = (\n                str(result)\n                +\n                "\\n\\n"\n                "[IMMEDIATE REPLY OWNERSHIP]\\n"\n                "- Kurze Reaktionen wie \'beides\', \'richtig\', \'hä?\' "\n                "oder \'was meinst du?\' gehören wahrscheinlich zum "\n                "unmittelbar vorherigen Turn.\\n"\n                "- Wenn dieser Turn von Evilnae stammt, ist Evilnae "\n                "weiterhin die Gesprächspartnerin, auch ohne Namen."\n            )\n\n        return result\n\n    return wrapped\n\n\ndef wrap_episode_focus(\n    original,\n):\n    @functools.wraps(original)\n    def wrapped(\n        channel_snapshot,\n        *args,\n        **kwargs,\n    ):\n        limit = int(\n            kwargs.get(\n                "limit",\n                12,\n            )\n            or 12\n        )\n\n        filtered = (\n            filter_episode_snapshot(\n                channel_snapshot,\n                limit=limit,\n            )\n        )\n\n        result = original(\n            filtered,\n            *args,\n            **kwargs,\n        )\n\n        return (\n            str(result)\n            +\n            "\\n"\n            "- RELEVANCE GATE: Der aktuelle User-Turn hat Vorrang. "\n            "Alte Episode-Themen nicht ohne aktuellen Bezug zur "\n            "neuen Antwortidee machen.\\n"\n            "- Frühere Evilnae-Sätze sind Dialoghistorie und kein "\n            "Beweis für ihren aktuellen Zustand."\n        )\n\n    return wrapped\n\n\ndef _add_issue(\n    analysis,\n    *,\n    issue,\n    penalty=5,\n    repetition=0,\n    grammar=0,\n    echo=0,\n):\n    issues = list(\n        getattr(\n            analysis,\n            "issues",\n            [],\n        )\n        or []\n    )\n\n    if issue in issues:\n        analysis.severe = True\n        return\n\n    issues.append(issue)\n    analysis.issues = issues\n\n    analysis.total_penalty = (\n        int(\n            getattr(\n                analysis,\n                "total_penalty",\n                0,\n            )\n            or 0\n        )\n        +\n        int(penalty)\n    )\n\n    analysis.repetition_score = (\n        int(\n            getattr(\n                analysis,\n                "repetition_score",\n                0,\n            )\n            or 0\n        )\n        +\n        int(repetition)\n    )\n\n    analysis.grammar_score = (\n        int(\n            getattr(\n                analysis,\n                "grammar_score",\n                0,\n            )\n            or 0\n        )\n        +\n        int(grammar)\n    )\n\n    analysis.echo_score = (\n        int(\n            getattr(\n                analysis,\n                "echo_score",\n                0,\n            )\n            or 0\n        )\n        +\n        int(echo)\n    )\n\n    analysis.severe = True\n\n\ndef wrap_response_quality_analyzer(\n    original,\n):\n    @functools.wraps(original)\n    def wrapped(\n        text,\n        *args,\n        **kwargs,\n    ):\n        analysis = original(\n            text,\n            *args,\n            **kwargs,\n        )\n\n        user_text = str(\n            kwargs.get(\n                "user_text",\n                "",\n            )\n            or _CURRENT_USER_TEXT.get()\n            or ""\n        )\n\n        recent = list(\n            kwargs.get(\n                "recent_evilnae_messages",\n                None,\n            )\n            or []\n        )\n\n        reason = (\n            semantic_violation_reason(\n                str(text or ""),\n                user_text=(\n                    user_text\n                ),\n            )\n        )\n\n        if reason:\n            _add_issue(\n                analysis,\n                issue=reason,\n                penalty=6,\n                grammar=(\n                    4\n                    if reason.startswith(\n                        "semantic_"\n                    )\n                    else 0\n                ),\n            )\n\n        for name in repeated_concepts(\n            str(text or ""),\n            recent,\n        ):\n            _add_issue(\n                analysis,\n                issue=(\n                    "repeated_concept:"\n                    +\n                    name\n                ),\n                penalty=5,\n                repetition=5,\n            )\n\n        if (\n            _user_echo_ratio(\n                user_text,\n                str(text or ""),\n            )\n            >= 0.78\n        ):\n            _add_issue(\n                analysis,\n                issue=(\n                    "user_idea_echo_takeover_v2"\n                ),\n                penalty=5,\n                echo=5,\n            )\n\n        return analysis\n\n    return wrapped\n\n\ndef wrap_character_state_observer(\n    original,\n):\n    @functools.wraps(original)\n    def wrapped(\n        *args,\n        **kwargs,\n    ):\n        answer = str(\n            kwargs.get(\n                "evilnae_answer",\n                "",\n            )\n            or (\n                args[0]\n                if args\n                else ""\n            )\n            or ""\n        )\n\n        reason = (\n            state_write_block_reason(\n                answer\n            )\n        )\n\n        if reason:\n            print(\n                "[LIVE GUARD] "\n                "character-state write blocked: "\n                f"{reason}"\n            )\n\n            result = {\n                "saved": 0,\n                "observations": [],\n                "blocked": reason,\n            }\n\n        else:\n            result = original(\n                *args,\n                **kwargs,\n            )\n\n        print(\n            "[LIVE OUT] "\n            f"{_CURRENT_USERNAME.get()} <- "\n            f"{_short(answer)}"\n        )\n\n        return result\n\n    return wrapped\n\n\ndef wrap_surface_writer(\n    original,\n):\n    @functools.wraps(original)\n    async def wrapped(\n        *args,\n        **kwargs,\n    ):\n        _SURFACE_FAILED.set(\n            False\n        )\n\n        try:\n            result = await original(\n                *args,\n                **kwargs,\n            )\n\n        except Exception as error:\n            _SURFACE_FAILED.set(\n                True\n            )\n\n            print(\n                "[LIVE WARN] "\n                "Qwen Surface exception -> "\n                f"{type(error).__name__}"\n            )\n\n            raise\n\n        candidate = str(\n            getattr(\n                result,\n                "output_text",\n                "",\n            )\n            or ""\n        )\n\n        reason = (\n            semantic_violation_reason(\n                candidate,\n                user_text=str(\n                    kwargs.get(\n                        "user_message",\n                        "",\n                    )\n                    or ""\n                ),\n                inner_state_guidance=str(\n                    kwargs.get(\n                        "inner_state_guidance",\n                        "",\n                    )\n                    or ""\n                ),\n                evidence_context=str(\n                    kwargs.get(\n                        "evidence_context",\n                        "",\n                    )\n                    or ""\n                ),\n                response_plan_text=str(\n                    kwargs.get(\n                        "response_plan_text",\n                        "",\n                    )\n                    or ""\n                ),\n            )\n        )\n\n        if (\n            candidate\n            and reason\n        ):\n            try:\n                result.success = False\n                result.reason = (\n                    "stability:"\n                    +\n                    reason\n                )\n            except Exception:\n                pass\n\n            _SURFACE_FAILED.set(\n                True\n            )\n\n            print(\n                "[LIVE GUARD] "\n                "Qwen Surface rejected: "\n                f"{reason}"\n            )\n\n            return result\n\n        if (\n            bool(\n                getattr(\n                    result,\n                    "used",\n                    False,\n                )\n            )\n            and not bool(\n                getattr(\n                    result,\n                    "success",\n                    False,\n                )\n            )\n        ):\n            _SURFACE_FAILED.set(\n                True\n            )\n\n            print(\n                "[LIVE WARN] "\n                "Qwen Surface fallback: "\n                f"{getattr(result, \'reason\', \'unknown\')}"\n            )\n\n        return result\n\n    return wrapped\n\n\ndef _local_passthrough(\n    draft: str,\n) -> LocalVoiceResult:\n    return LocalVoiceResult(\n        output_text=str(\n            draft\n            or ""\n        ),\n        used=False,\n        rewritten=False,\n        bot_likeness=0.0,\n        repetition=0.0,\n        evilnae_match=1.0,\n        meaning_preserved=1.0,\n        new_facts=False,\n        reason=(\n            "surface_failed_fast_fallback"\n        ),\n        duration=0.0,\n        context_coherence=1.0,\n    )\n\n\ndef wrap_local_voice(\n    original,\n):\n    @functools.wraps(original)\n    async def wrapped(\n        *args,\n        **kwargs,\n    ):\n        if _SURFACE_FAILED.get():\n            print(\n                "[LIVE WARN] "\n                "second local Qwen pass skipped "\n                "after Surface failure"\n            )\n\n            return _local_passthrough(\n                str(\n                    kwargs.get(\n                        "draft",\n                        "",\n                    )\n                    or ""\n                )\n            )\n\n        return await original(\n            *args,\n            **kwargs,\n        )\n\n    return wrapped\n\n\n# =========================================================\n# SELF TEST\n# =========================================================\n\ndef _self_test() -> int:\n    tests = [\n        (\n            "how-are-you non-answer",\n            intent_violation_reason(\n                "Evil, wie geht es dir?",\n                "Hab schon fast nicht mehr dran geglaubt, dass du noch da bist.",\n            )\n            ==\n            "intent_how_are_you_not_answered",\n        ),\n        (\n            "how-are-you valid",\n            intent_violation_reason(\n                "Evil, wie geht es dir?",\n                "Mir geht\'s gut, nur bisschen langsam heute.",\n            )\n            ==\n            "",\n        ),\n        (\n            "food boss non-answer",\n            intent_violation_reason(\n                "Was hast du heute alles gegessen?",\n                "Ich bin halt der Boss im Fressen, Deal with it.",\n            )\n            ==\n            "intent_food_history_not_answered",\n        ),\n        (\n            "tea uncertainty",\n            intent_violation_reason(\n                "Evil kannst du mir einen Tee machen?",\n                "weiß ich grad nicht sicher.",\n            )\n            ==\n            "intent_request_uncertainty",\n        ),\n        (\n            "Bruederin",\n            semantic_violation_reason(\n                "Ich dachte, du wärst meine eigene Brüderin.",\n                user_text="Evil du bist so ein Morgenmuffel",\n            )\n            ==\n            "semantic_bruederin",\n        ),\n        (\n            "ungrounded confused state with modifiers",\n            semantic_violation_reason(\n                "Ja, ich bin verwirrt.",\n                user_text="Evil du bist heute irgendwie echt verwirrt",\n                inner_state_guidance=(\n                    "feeling=neutral irritation=0.08"\n                ),\n                evidence_context="",\n                response_plan_text=(\n                    "User sagt verwirrt, aber nicht als Fakt übernehmen"\n                ),\n            )\n            ==\n            "semantic_ungrounded_self_state",\n        ),\n        (\n            "ungrounded confused state",\n            semantic_violation_reason(\n                "Ja, ich bin verwirrt.",\n                user_text="Evil du bist heute verwirrt",\n                inner_state_guidance=(\n                    "feeling=neutral irritation=0.08"\n                ),\n                evidence_context="",\n                response_plan_text=(\n                    "neutral reagieren"\n                ),\n            )\n            ==\n            "semantic_ungrounded_self_state",\n        ),\n        (\n            "confusion repeat",\n            "confusion_loop"\n            in repeated_concepts(\n                "Bin noch komplett im Nebel.",\n                [\n                    "Hab verschlafen und bin etwas verwirrt."\n                ],\n            ),\n        ),\n        (\n            "food boss repeat",\n            "food_boss_loop"\n            in repeated_concepts(\n                "Der Boss im Fressen macht keine halben Sachen.",\n                [\n                    "Ich bin halt der Boss im Fressen."\n                ],\n            ),\n        ),\n        (\n            "implicit beides",\n            implicit_evilnae_continuation(\n                current_message=(\n                    "Ich glaube beides"\n                ),\n                channel_context=(\n                    "Hanae: du bist verwirrt\\n"\n                    "Evilnae: bin ich verwirrt oder schlecht eingeschlafen"\n                ),\n                recent_evilnae_messages=[\n                    "bin ich verwirrt oder schlecht eingeschlafen"\n                ],\n            ),\n        ),\n        (\n            "state pollution",\n            state_write_block_reason(\n                "Warte, ich schaue mal, ob ich was Brauchbares finden kann."\n            )\n            ==\n            "low_confidence_meta_activity",\n        ),\n    ]\n\n    sample_episode = [\n        {\n            "type": "user",\n            "content": "Kopfschmerzen und Gaming",\n            "user_id": "1",\n        },\n        {\n            "type": "bot",\n            "content": "Ich bin leiser.",\n            "user_id": "",\n        },\n        {\n            "type": "user",\n            "content": "Einkaufen später",\n            "user_id": "2",\n        },\n        {\n            "type": "bot",\n            "content": "Klar.",\n            "user_id": "",\n        },\n        {\n            "type": "user",\n            "content": "Richtig",\n            "user_id": "2",\n        },\n        {\n            "type": "bot",\n            "content": "Genau.",\n            "user_id": "",\n        },\n        {\n            "type": "user",\n            "content": "Wie geht es dir?",\n            "user_id": "3",\n        },\n    ]\n\n    tests.append(\n        (\n            "episode relevance",\n            len(\n                filter_episode_snapshot(\n                    sample_episode,\n                    limit=12,\n                )\n            )\n            <= 5,\n        )\n    )\n\n    console = ConsoleOutputFilter()\n\n    tests.append(\n        (\n            "compact hides debug",\n            console.filter_chunk(\n                "[BRAIN DEBUG] huge thing\\n"\n            )\n            ==\n            "",\n        )\n    )\n\n    tests.append(\n        (\n            "compact shows live",\n            "[LIVE OUT]"\n            in console.filter_chunk(\n                "[LIVE OUT] Hanae <- passt\\n"\n            ),\n        )\n    )\n\n    passed = sum(\n        1\n        for _, success in tests\n        if success\n    )\n\n    print()\n    print("=" * 62)\n    print(\n        f"LIVE STABILITY v"\n        f"{LIVE_STABILITY_VERSION} TEST"\n    )\n    print("=" * 62)\n\n    for name, success in tests:\n        print(\n            f"[{\'PASS\' if success else \'FAIL\'}] "\n            f"{name}"\n        )\n\n    print(\n        f"RESULT: "\n        f"{passed}/{len(tests)} PASS"\n    )\n\n    return (\n        0\n        if passed == len(tests)\n        else 1\n    )\n\n\nif __name__ == "__main__":\n    raise SystemExit(\n        _self_test()\n    )\n'
STABILITY_IMPORT = 'from live_stability import (\n    LIVE_STABILITY_VERSION,\n    CONSOLE_OUTPUT_VERSION,\n    ConsoleOutputFilter,\n    get_console_mode,\n    wrap_perceive_message,\n    wrap_response_planner,\n    wrap_participation_brain,\n    wrap_reference_context,\n    wrap_episode_focus,\n    wrap_response_quality_analyzer,\n    wrap_character_state_observer,\n    wrap_surface_writer,\n    wrap_local_voice,\n)\n\n\n# =========================================================\n# 3.6.2 LIVE STABILITY WRAPPERS\n# =========================================================\n\nperceive_message = wrap_perceive_message(\n    perceive_message\n)\n\nbuild_response_plan = wrap_response_planner(\n    build_response_plan\n)\n\nrun_participation_brain = wrap_participation_brain(\n    run_participation_brain\n)\n\nbuild_reference_context = wrap_reference_context(\n    build_reference_context\n)\n\nbuild_episode_focus = wrap_episode_focus(\n    build_episode_focus\n)\n\nanalyze_response_quality = wrap_response_quality_analyzer(\n    analyze_response_quality\n)\n\nobserve_character_state = wrap_character_state_observer(\n    observe_character_state\n)\n\ngenerate_surface_response_from_plan = wrap_surface_writer(\n    generate_surface_response_from_plan\n)\n\nhumanize_evilnae_response = wrap_local_voice(\n    humanize_evilnae_response\n)\n\n\n'
OPENAI_IMPORT_END = 'from openai import (\n    AsyncOpenAI,\n    RateLimitError,\n    APITimeoutError,\n    APIConnectionError,\n    InternalServerError,\n)\n\n'
OLD_TEE_INIT = '    def __init__(self, console_stream, file_stream):\n        self._console_stream = console_stream\n        self._file_stream = file_stream\n'
NEW_TEE_INIT = '    def __init__(self, console_stream, file_stream):\n        self._console_stream = console_stream\n        self._file_stream = file_stream\n        self._console_filter = ConsoleOutputFilter()\n'
OLD_TEE_WRITE = '    def write(self, data):\n        value = str(data if data is not None else "")\n        with _AUTO_LOG_LOCK:\n            try:\n                self._console_stream.write(value)\n            except Exception:\n                pass\n            try:\n                self._file_stream.write(value)\n                self._file_stream.flush()\n            except Exception:\n                pass\n        return len(value)\n'
NEW_TEE_WRITE = '    def write(self, data):\n        value = str(data if data is not None else "")\n\n        with _AUTO_LOG_LOCK:\n            # Full diagnostics always go to file.\n            try:\n                self._file_stream.write(value)\n                self._file_stream.flush()\n            except Exception:\n                pass\n\n            # Terminal is filtered separately.\n            try:\n                console_value = (\n                    self._console_filter\n                    .filter_chunk(value)\n                )\n\n                if console_value:\n                    self._console_stream.write(\n                        console_value\n                    )\n\n            except Exception:\n                try:\n                    self._console_stream.write(\n                        value\n                    )\n                except Exception:\n                    pass\n\n        return len(value)\n'
OLD_TEE_FLUSH = '    def flush(self):\n        with _AUTO_LOG_LOCK:\n            try:\n                self._console_stream.flush()\n            except Exception:\n                pass\n            try:\n                self._file_stream.flush()\n            except Exception:\n                pass\n'
NEW_TEE_FLUSH = '    def flush(self):\n        with _AUTO_LOG_LOCK:\n            try:\n                pending = (\n                    self._console_filter\n                    .flush_pending()\n                )\n\n                if pending:\n                    self._console_stream.write(\n                        pending\n                    )\n\n                self._console_stream.flush()\n\n            except Exception:\n                pass\n\n            try:\n                self._file_stream.flush()\n            except Exception:\n                pass\n'
STARTUP_MARKER = '    print(\n        f"Output Quality v{OUTPUT_QUALITY_VERSION}: ACTIVE"\n    )\n\n'
STARTUP_INSERT = '    print(\n        f"Live Stability v"\n        f"{LIVE_STABILITY_VERSION}: ACTIVE"\n    )\n\n    print(\n        f"Compact Console v"\n        f"{CONSOLE_OUTPUT_VERSION}: "\n        f"{get_console_mode()} "\n        "(full file log unchanged)"\n    )\n\n'


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
        fail(
            f"{label}: expected exactly 1 match, "
            f"found {count}"
        )

    ok(label)

    return text.replace(
        old,
        new,
        1,
    )


def insert_after_once(text, marker, block, label):
    count = text.count(marker)

    if count != 1:
        fail(
            f"{label}: expected exactly 1 marker, "
            f"found {count}"
        )

    ok(label)

    return text.replace(
        marker,
        marker + block,
        1,
    )


def syntax_check(text, filename):
    try:
        ast.parse(
            text,
            filename=filename,
        )
    except SyntaxError as error:
        fail(
            f"{filename}: syntax error after patch at "
            f"line {error.lineno}: {error.msg}"
        )

    ok(
        f"{filename} syntax check"
    )


print("=" * 78)
print(
    "EVILNAE 3.6.2 — CONTEXT & SEMANTIC STABILITY + COMPACT CONSOLE V3"
)
print("=" * 78)
print(f"Project: {PROJECT_ROOT}")
print()
print("WICHTIG: bot.py muss vollständig AUS sein.")
print()


for required in (
    BOT_PATH,
    FOUNDATION_PATH,
):
    if not required.exists():
        fail(
            f"Missing required file: {required.name}"
        )


bot = BOT_PATH.read_text(
    encoding="utf-8"
)

foundation = FOUNDATION_PATH.read_text(
    encoding="utf-8"
)


if (
    TARGET_BOT in bot
    and STABILITY_PATH.exists()
):
    print(
        "3.6.2 is already installed."
    )
    raise SystemExit(0)


if EXPECTED_BOT not in bot:
    fail(
        "Expected Bot 3.6.1-affect-repetition"
    )


if EXPECTED_FOUNDATION not in foundation:
    fail(
        "Expected Character Foundation 1.1-live-retrieval"
    )


module_expectations = {
    "response_planner.py":
        'RESPONSE_PLANNER_VERSION = "1.1-affect-grounded"',
    "surface_writer.py":
        'SURFACE_WRITER_VERSION = "1.1-context-safe"',
    "response_quality.py":
        'OUTPUT_QUALITY_VERSION = "2.6-concept-repetition"',
    "routing_hardening.py":
        'ROUTING_HARDENING_VERSION = "1.3-trailing-vocative"',
    "conversation_episodes.py":
        'CONVERSATION_EPISODES_VERSION = "1.1-authority-safe"',
}


for filename, marker in (
    module_expectations.items()
):
    path = PROJECT_ROOT / filename

    if (
        not path.exists()
        or marker not in path.read_text(
            encoding="utf-8"
        )
    ):
        fail(
            f"Required 3.6.1 invariant missing: "
            f"{filename} -> {marker}"
        )


if STABILITY_PATH.exists():
    fail(
        "live_stability.py already exists unexpectedly."
    )


ok(
    "3.6.1 live base detected"
)


# =========================================================
# PATCH BOT
# =========================================================

bot = replace_once(
    bot,
    EXPECTED_BOT,
    TARGET_BOT,
    "Bot version -> 3.6.2-context-semantic",
)

bot = replace_once(
    bot,
    'AUTO_FILE_LOGGING_VERSION = "1.0"',
    'AUTO_FILE_LOGGING_VERSION = "1.1-compact-console"',
    "Auto file logging -> compact-console aware",
)

bot = insert_after_once(
    bot,
    OPENAI_IMPORT_END,
    STABILITY_IMPORT,
    "bot.py imports/installs Live Stability wrappers",
)

bot = replace_once(
    bot,
    OLD_TEE_INIT,
    NEW_TEE_INIT,
    "Console filter initialized in Tee stream",
)

bot = replace_once(
    bot,
    OLD_TEE_WRITE,
    NEW_TEE_WRITE,
    "Terminal filtered while file log remains full",
)

bot = replace_once(
    bot,
    OLD_TEE_FLUSH,
    NEW_TEE_FLUSH,
    "Compact console flush",
)

bot = insert_after_once(
    bot,
    STARTUP_MARKER,
    STARTUP_INSERT,
    "Startup Live Stability + Compact Console banner",
)


# =========================================================
# FOUNDATION RELEVANCE FLOOR
# =========================================================

foundation = replace_once(
    foundation,
    EXPECTED_FOUNDATION,
    TARGET_FOUNDATION,
    "Character Foundation version -> 1.2-relevance-floor",
)

foundation = replace_once(
    foundation,
    (
        "hits = search_foundation("
        "user_text, limit=limit, min_score=4.0)"
    ),
    (
        "hits = search_foundation("
        "user_text, limit=limit, min_score=6.5)"
    ),
    "Foundation relevance floor 4.0 -> 6.5",
)


# =========================================================
# PRE-WRITE INVARIANTS / SYNTAX
# =========================================================

for marker in (
    TARGET_BOT,
    'AUTO_FILE_LOGGING_VERSION = "1.1-compact-console"',
    "wrap_response_planner",
    "wrap_participation_brain",
    "wrap_episode_focus",
    "wrap_response_quality_analyzer",
    "wrap_character_state_observer",
    "wrap_surface_writer",
    "wrap_local_voice",
    "ConsoleOutputFilter()",
    "full file log unchanged",
):
    if marker not in bot:
        fail(
            f"Patched bot.py missing invariant: {marker}"
        )


for marker in (
    TARGET_FOUNDATION,
    "min_score=6.5",
):
    if marker not in foundation:
        fail(
            "Patched character_foundation.py "
            f"missing invariant: {marker}"
        )


for marker in (
    'LIVE_STABILITY_VERSION = "1.0"',
    "intent_violation_reason",
    "semantic_violation_reason",
    "implicit_evilnae_continuation",
    "filter_episode_snapshot",
    "state_write_block_reason",
    "ConsoleOutputFilter",
    "surface_failed_fast_fallback",
):
    if marker not in LIVE_SOURCE:
        fail(
            f"live_stability.py missing invariant: {marker}"
        )


syntax_check(
    LIVE_SOURCE,
    "live_stability.py",
)

syntax_check(
    foundation,
    "character_foundation.py",
)

syntax_check(
    bot,
    "bot.py",
)


contract_tests = {
    "no new OpenAI call":
        (
            "AsyncOpenAI"
            not in LIVE_SOURCE
            and "openai_client"
            not in LIVE_SOURCE
        ),
    "no new Ollama call":
        (
            "run_local_model"
            not in LIVE_SOURCE
            and "urllib.request"
            not in LIVE_SOURCE
        ),
    "full file log preserved":
        (
            "self._file_stream.write(value)"
            in bot
            and ".filter_chunk(value)"
            in bot
        ),
    "console modes":
        all(
            mode in LIVE_SOURCE
            for mode in (
                '"compact"',
                '"quiet"',
                '"debug"',
            )
        ),
    "self-state authority":
        "SELF_STATE_USER_PATTERN"
        in LIVE_SOURCE,
    "care context":
        "CARE_CONTEXT_PATTERN"
        in LIVE_SOURCE,
    "intent fulfillment":
        "intent_violation_reason"
        in LIVE_SOURCE,
    "semantic sanity":
        "semantic_bruederin"
        in LIVE_SOURCE,
    "concept repetition":
        (
            "confusion_loop"
            in LIVE_SOURCE
            and "food_boss_loop"
            in LIVE_SOURCE
        ),
    "implicit references":
        "implicit_recent_evilnae_continuation"
        in LIVE_SOURCE,
    "episode relevance":
        "filter_episode_snapshot"
        in LIVE_SOURCE,
    "state pollution guard":
        "low_confidence_meta_activity"
        in LIVE_SOURCE,
    "fast local fallback":
        "second local Qwen pass skipped"
        in LIVE_SOURCE,
    "foundation floor":
        "min_score=6.5"
        in foundation,
}


failed = [
    name
    for name, success
    in contract_tests.items()
    if not success
]


if failed:
    fail(
        "Contract self-test failed: "
        + ", ".join(failed)
    )


ok(
    f"Contract self-test: "
    f"{len(contract_tests)}/"
    f"{len(contract_tests)} PASS"
)


# =========================================================
# PRE-WRITE LIVE STABILITY BEHAVIOR TEST
# =========================================================

namespace = {
    "__name__": "_evilnae_362_preflight_",
}

try:
    exec(
        compile(
            LIVE_SOURCE,
            "live_stability.py",
            "exec",
        ),
        namespace,
    )
except Exception as error:
    fail(
        "Could not load live_stability.py for "
        f"preflight: {type(error).__name__}: {error}"
    )


self_test = namespace.get(
    "_self_test"
)

if self_test is None:
    fail(
        "live_stability.py self-test missing"
    )


if self_test() != 0:
    fail(
        "Live Stability behavior self-test failed"
    )


ok(
    "Live Stability behavior self-test: PASS"
)


# =========================================================
# BACKUP
# =========================================================

timestamp = (
    datetime.now()
    .astimezone()
    .strftime(
        "%Y%m%d-%H%M%S"
    )
)

backup_dir = (
    BACKUP_ROOT
    /
    timestamp
)

suffix = 1

while backup_dir.exists():
    backup_dir = (
        BACKUP_ROOT
        /
        f"{timestamp}_{suffix:02d}"
    )
    suffix += 1


backup_dir.mkdir(
    parents=True,
    exist_ok=False,
)


for path in (
    BOT_PATH,
    FOUNDATION_PATH,
):
    shutil.copy2(
        path,
        backup_dir / path.name,
    )

    ok(
        f"Backup: {path.name}"
    )


# =========================================================
# ATOMIC WRITE
# =========================================================

def atomic_write(path, text):
    temp = Path(
        str(path)
        + ".tmp"
    )

    temp.write_text(
        text,
        encoding="utf-8",
    )

    temp.replace(path)


atomic_write(
    STABILITY_PATH,
    LIVE_SOURCE,
)

ok(
    "Created: live_stability.py"
)


atomic_write(
    FOUNDATION_PATH,
    foundation,
)

ok(
    "Updated: character_foundation.py"
)


atomic_write(
    BOT_PATH,
    bot,
)

ok(
    "Updated: bot.py"
)


# =========================================================
# COMPILE
# =========================================================

compile_targets = [
    STABILITY_PATH,
    FOUNDATION_PATH,
    BOT_PATH,
    PROJECT_ROOT / "response_planner.py",
    PROJECT_ROOT / "surface_writer.py",
    PROJECT_ROOT / "response_quality.py",
    PROJECT_ROOT / "participation.py",
    PROJECT_ROOT / "conversation_understanding.py",
    PROJECT_ROOT / "character_state.py",
]


result = subprocess.run(
    [
        sys.executable,
        "-m",
        "py_compile",
        *[
            str(path)
            for path in compile_targets
        ],
    ],
    cwd=str(PROJECT_ROOT),
    check=False,
)


if result.returncode != 0:
    print()
    print(
        "[POST-INSTALL WARNING] py_compile failed."
    )
    print(
        f"Backup: {backup_dir}"
    )
    raise SystemExit(
        result.returncode
    )


ok(
    f"Post-install py_compile: "
    f"{len(compile_targets)}/"
    f"{len(compile_targets)}"
)


print()
print("=" * 78)
print(
    "EVILNAE 3.6.2 CONTEXT & SEMANTIC STABILITY INSTALLED"
)
print("=" * 78)

print()
print("Live fixes:")
print("  [✓] Self-State Authority 2.0")
print("  [✓] direct question/request fulfillment")
print("  [✓] Sensitive/Care Context")
print("  [✓] semantic sanity guard")
print("  [✓] confusion/uncertainty/food-boss concept loops")
print("  [✓] immediate short-reply thread ownership")
print("  [✓] Episode Relevance Gate")
print("  [✓] Character-State Write Guard")
print("  [✓] Foundation relevance floor")
print("  [✓] fast fallback after Qwen Surface failure")

print()
print("Terminal:")
print("  [✓] default = compact")
print("  [✓] logs/evilnae_*.log remains FULL / unfiltered")
print("  [✓] compact: IN / OUT / guards / warnings / errors / key startup")
print("  [✓] debug and quiet remain available")

print()
print("PowerShell console modes:")
print('  $env:EVILNAE_CONSOLE_MODE="compact"')
print('  $env:EVILNAE_CONSOLE_MODE="debug"')
print('  $env:EVILNAE_CONSOLE_MODE="quiet"')

print()
print("Unchanged:")
print("  [✓] Character Learning / DB / Memories")
print("  [✓] Episodes / Salience state")
print("  [✓] Inner State values")
print("  [✓] Canon data / Excel answers")
print("  [✓] Emote Layer")

print()
print(f"Backup: {backup_dir}")
print()
print("NO MEMORY RESET REQUIRED.")
print()
print("NEXT:")
print("  python bot.py")
print()
print("Expected compact startup:")
print("  [AUTO FILE LOGGING] ...")
print("  Evilnae ist online als ...")
print("  Bot Version: 3.6.2-context-semantic")
print("  Live Stability v1.0: ACTIVE")
print("  Compact Console v1.0: compact (full file log unchanged)")
print()
print("Expected runtime:")
print("  [LIVE IN] Hanae: Evil sis, wie geht es dir?")
print("  [LIVE OUT] Hanae <- ...")
print("  [LIVE GUARD] ...  (only when something is blocked)")
