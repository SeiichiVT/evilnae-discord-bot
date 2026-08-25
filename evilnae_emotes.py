import re
from dataclasses import dataclass
from typing import Optional


# =========================================================
# VERSION
# =========================================================

EVILNAE_EMOTE_VERSION = "1.0"


# =========================================================
# APPLICATION EMOJI NAMES
#
# Diese Namen entsprechen Evilnaes
# Application Emojis im Discord Developer Portal.
#
# "evilnae_nervouse" bleibt absichtlich so,
# solange das Emoji im Portal so heißt.
# =========================================================

EMOTE_NAMES = {

    "spray":
        "evilnae_spray",

    "rage":
        "evilnae_rage",

    "think":
        "evilnae_think",

    "cool":
        "evilnae_cool",

    "laugh":
        "evilnae_laugh",

    "knife":
        "evilnae_knife",

    "gun":
        "evilnae_gun",

    "shocked":
        "evilnae_shocked",

    "dance":
        "evilnae_dance",

    "cry":
        "evilnae_cry",

    "angry":
        "evilnae_angry",

    "nervous":
        "evilnae_nervouse",

    "love":
        "evilnae_love",

    "wave":
        "evilnae_wave",

    "gaming":
        "evilnae_gaming",

    "fire":
        "evilnae_fire",

    "dizzy":
        "evilnae_dizzy",

    "dead":
        "evilnae_dead",

    "party":
        "evilnae_party",

    "bonk":
        "evilnae_bonk",
}


# =========================================================
# FALLBACK IDS
#
# Falls fetch_application_emojis() auf einer
# discord.py-Version nicht verfügbar sein sollte,
# kann Evilnae die IDs trotzdem verwenden.
#
# Die IDs stammen aus eurem Developer Portal.
# =========================================================

FALLBACK_IDS = {

    "evilnae_spray":
        1541449490391629904,

    "evilnae_rage":
        1541449439502278707,

    "evilnae_think":
        1541449404039434372,

    "evilnae_cool":
        1541449361114927154,

    "evilnae_laugh":
        1541449323223457822,

    "evilnae_knife":
        1541449266738765915,

    "evilnae_gun":
        1541449232823881808,

    "evilnae_shocked":
        1541449181661634651,

    "evilnae_dance":
        1541449129857777695,

    "evilnae_cry":
        1541449088502071378,

    "evilnae_angry":
        1540716983274967140,

    "evilnae_nervouse":
        1541451372581617795,

    "evilnae_love":
        1541451265777737890,

    "evilnae_wave":
        1541451033392451654,

    "evilnae_gaming":
        1541450887791255553,

    "evilnae_fire":
        1541450806983786506,

    "evilnae_dizzy":
        1541450631326208131,

    "evilnae_dead":
        1541450527726895284,

    "evilnae_party":
        1541450351780167751,

    "evilnae_bonk":
        1541450204920946750,
}


# =========================================================
# CACHE
# =========================================================

_application_emojis = {}


# =========================================================
# RESULT
# =========================================================

@dataclass
class EvilnaeEmoteDecision:

    semantic: Optional[str] = None

    emoji_name: Optional[str] = None

    rendered: Optional[str] = None

    confidence: float = 0.0

    reason: str = "none"

    added: bool = False

    stripped_unicode: int = 0

    stripped_custom: int = 0


# =========================================================
# REGEX
# =========================================================

# Discord Custom Emoji:
#
# <:name:id>
# <a:name:id>
CUSTOM_EMOJI_RE = re.compile(
    r"<a?:[A-Za-z0-9_]+:\d+>"
)


# Unicode emoji ranges.
#
# Absichtlich konservativ:
# normale Satzzeichen / Herzen in Text
# sollen nicht kaputtgehen.
UNICODE_EMOJI_RE = re.compile(
    "["
    "\U0001F1E0-\U0001F1FF"
    "\U0001F300-\U0001F5FF"
    "\U0001F600-\U0001F64F"
    "\U0001F680-\U0001F6FF"
    "\U0001F700-\U0001F77F"
    "\U0001F780-\U0001F7FF"
    "\U0001F800-\U0001F8FF"
    "\U0001F900-\U0001F9FF"
    "\U0001FA00-\U0001FAFF"
    "\U00002600-\U000026FF"
    "\U00002700-\U000027BF"
    "]+",
    flags=re.UNICODE
)


# =========================================================
# SERIOUS TOPICS
#
# Bei ernsten Situationen lieber KEIN Emote.
#
# Das verhindert z.B.:
#
# "meine Katze ist gestorben"
# → evilnae_cry
#
# Das würde schnell künstlich wirken.
# =========================================================

SERIOUS_PATTERNS = [

    re.compile(
        r"\b(?:gestorben|verstorben|tod|"
        r"trauer|beerdigung)\b",
        re.IGNORECASE
    ),

    re.compile(
        r"\b(?:selbstmord|suizid|"
        r"selbstverletz|umbringen)\w*\b",
        re.IGNORECASE
    ),

    re.compile(
        r"\b(?:krebs|schwer krank|"
        r"krankenhaus|notaufnahme)\b",
        re.IGNORECASE
    ),

    re.compile(
        r"\b(?:missbrauch|vergewaltig|"
        r"trauma)\w*\b",
        re.IGNORECASE
    ),
]


# =========================================================
# TEXT SIGNALS
# =========================================================

LAUGH_PATTERNS = [

    re.compile(
        r"\b(?:lol|lmao|lmfao|haha+|"
        r"hahaha+|kekw)\b",
        re.IGNORECASE
    ),

    re.compile(
        r"\b(?:witzig|lustig|"
        r"ich kann nicht mehr)\b",
        re.IGNORECASE
    ),
]


DEAD_PATTERNS = [

    re.compile(
        r"\b(?:bro|bruh)\b",
        re.IGNORECASE
    ),

    re.compile(
        r"\b(?:was zur hölle|"
        r"was zum fick|ain'?t no way|"
        r"be serious)\b",
        re.IGNORECASE
    ),
]


THINK_PATTERNS = [

    re.compile(
        r"\b(?:hmm+|hm+|interessant|"
        r"warte mal|wait|"
        r"ich hab fragen|erklär dich)\b",
        re.IGNORECASE
    ),
]


SHOCK_PATTERNS = [

    re.compile(
        r"\b(?:was\?|wait was|"
        r"WHAT|ernsthaft|wirklich\?|"
        r"no way)\b",
        re.IGNORECASE
    ),
]


LOVE_PATTERNS = [

    re.compile(
        r"\b(?:danke|lieb von dir|"
        r"süß|suess|hab dich lieb|"
        r"love)\b",
        re.IGNORECASE
    ),
]


WAVE_PATTERNS = [

    re.compile(
        r"\b(?:hallo|hi|hey|moin|"
        r"guten morgen|bye|tschüss|"
        r"tschuess|bis später|"
        r"bis spaeter|gute nacht)\b",
        re.IGNORECASE
    ),
]


GAMING_PATTERNS = [

    re.compile(
        r"\b(?:game|gaming|zock|"
        r"boss|ranked|elo|"
        r"controller|steam|"
        r"playstation|xbox)\w*\b",
        re.IGNORECASE
    ),
]


FIRE_PATTERNS = [

    re.compile(
        r"\b(?:stark|clean|based|"
        r"krass|heftig|nice|"
        r"geschafft|gewonnen|"
        r"zerlegt|rasiert)\b",
        re.IGNORECASE
    ),
]


PARTY_PATTERNS = [

    re.compile(
        r"\b(?:party|feiern|"
        r"geburtstag|gewonnen|"
        r"geschafft|glückwunsch|"
        r"glueckwunsch)\b",
        re.IGNORECASE
    ),
]


ANGRY_PATTERNS = [

    re.compile(
        r"\b(?:nervt|nervig|"
        r"sauer|angry|wütend|"
        r"wuetend|abfuck|"
        r"scheiß|scheiss)\b",
        re.IGNORECASE
    ),
]


RAGE_PATTERNS = [

    re.compile(
        r"\b(?:ich raste|"
        r"ich schwöre|ich schwoere|"
        r"ich hasse das|"
        r"rage)\b",
        re.IGNORECASE
    ),
]


NERVOUS_PATTERNS = [

    re.compile(
        r"\b(?:nervös|nervoes|"
        r"awkward|peinlich|"
        r"oh gott|hilfe)\b",
        re.IGNORECASE
    ),
]


DIZZY_PATTERNS = [

    re.compile(
        r"\b(?:verwirrt|confused|"
        r"mein hirn|mein gehirn|"
        r"brainlag|brain lag|"
        r"was passiert)\b",
        re.IGNORECASE
    ),
]


BONK_PATTERNS = [

    re.compile(
        r"\b(?:hör auf|hoer auf|"
        r"benimm dich|"
        r"geh weg|"
        r"frech|"
        r"du dieb|diebin)\b",
        re.IGNORECASE
    ),
]


COOL_PATTERNS = [

    re.compile(
        r"\b(?:easy|locker|"
        r"natürlich|natuerlich|"
        r"obviously|"
        r"kein problem)\b",
        re.IGNORECASE
    ),
]


# =========================================================
# CLEAN OUTPUT
# =========================================================

def strip_non_evilnae_emojis(
    text: str
):

    text = str(
        text
        or ""
    )

    custom_matches = (
        CUSTOM_EMOJI_RE.findall(
            text
        )
    )

    unicode_matches = (
        UNICODE_EMOJI_RE.findall(
            text
        )
    )

    text = (
        CUSTOM_EMOJI_RE.sub(
            "",
            text
        )
    )

    text = (
        UNICODE_EMOJI_RE.sub(
            "",
            text
        )
    )

    # Variation selectors / ZWJ leftovers
    text = text.replace(
        "\ufe0f",
        ""
    )

    text = text.replace(
        "\u200d",
        ""
    )

    # Mehrfach-Leerzeichen aufräumen.
    text = re.sub(
        r"[ \t]+",
        " ",
        text
    )

    # Spaces vor Satzzeichen entfernen.
    text = re.sub(
        r"\s+([,.!?;:])",
        r"\1",
        text
    )

    # Zu viele Leerzeilen.
    text = re.sub(
        r"\n{3,}",
        "\n\n",
        text
    )

    return (
        text.strip(),
        len(
            unicode_matches
        ),
        len(
            custom_matches
        )
    )


# =========================================================
# CACHE APPLICATION EMOJIS
# =========================================================

async def load_application_emojis(
    bot
):

    global _application_emojis

    loaded = {}

    fetch_method = getattr(
        bot,
        "fetch_application_emojis",
        None
    )

    if fetch_method is not None:

        try:

            emojis = (
                await fetch_method()
            )

            for emoji in emojis:

                name = str(
                    getattr(
                        emoji,
                        "name",
                        ""
                    )
                )

                if (
                    name
                    and
                    name.startswith(
                        "evilnae_"
                    )
                ):

                    loaded[
                        name
                    ] = str(
                        emoji
                    )

        except Exception as error:

            print(
                "[EVILNAE EMOTES FETCH ERROR] "
                f"{type(error).__name__}: "
                f"{error}"
            )

    # -----------------------------------------------------
    # FALLBACK
    # -----------------------------------------------------

    for (
        name,
        emoji_id
    ) in FALLBACK_IDS.items():

        if name not in loaded:

            loaded[
                name
            ] = (
                f"<:{name}:{emoji_id}>"
            )

    _application_emojis = (
        loaded
    )

    print(
        "[EVILNAE EMOTES LOADED] "
        f"count={len(_application_emojis)} "
        f"source="
        f"{'discord+fallback' if fetch_method else 'fallback'}"
    )

    return dict(
        _application_emojis
    )


# =========================================================
# GET EMOTE
# =========================================================

def get_emote(
    semantic: str
) -> Optional[str]:

    emoji_name = (
        EMOTE_NAMES.get(
            semantic
        )
    )

    if not emoji_name:

        return None

    return (
        _application_emojis.get(
            emoji_name
        )
    )


# =========================================================
# SERIOUS CHECK
# =========================================================

def _is_serious(
    user_text: str,
    answer: str
) -> bool:

    combined = (
        f"{user_text}\n{answer}"
    )

    for pattern in SERIOUS_PATTERNS:

        if pattern.search(
            combined
        ):

            return True

    return False


# =========================================================
# MATCH SCORE
# =========================================================

def _score_patterns(
    text,
    patterns
):

    score = 0

    for pattern in patterns:

        if pattern.search(
            text
        ):

            score += 1

    return score


# =========================================================
# SELECT SEMANTIC
#
# Kein Random.
#
# Der Emote muss eine tatsächliche
# Reaktion im Text / Inner State stützen.
# =========================================================

def choose_emote_semantic(
    *,
    answer: str,
    user_text: str = "",
    mood: str = "normal",
    inner_state=None,
    is_hanae: bool = False
) -> tuple[Optional[str], float, str]:

    answer = str(
        answer
        or ""
    ).strip()

    user_text = str(
        user_text
        or ""
    ).strip()

    if not answer:

        return (
            None,
            0.0,
            "empty_answer"
        )

    if _is_serious(
        user_text,
        answer
    ):

        return (
            None,
            1.0,
            "serious_context"
        )

    combined = (
        f"{user_text}\n{answer}"
    )

    answer_lower = (
        answer.lower()
    )

    # -----------------------------------------------------
    # EXPLICIT LOVE / SOFT
    # -----------------------------------------------------

    love_score = (
        _score_patterns(
            answer,
            LOVE_PATTERNS
        )
    )

    if (
        mood == "soft"
        and
        love_score
        >= 1
    ):

        return (
            "love",
            0.95,
            "soft_explicit"
        )

    # -----------------------------------------------------
    # LAUGH
    # -----------------------------------------------------

    laugh_score = (
        _score_patterns(
            answer,
            LAUGH_PATTERNS
        )
    )

    if laugh_score >= 1:

        return (
            "laugh",
            0.90,
            "explicit_laughter"
        )

    # -----------------------------------------------------
    # SHOCK
    # -----------------------------------------------------

    shocked_score = (
        _score_patterns(
            answer,
            SHOCK_PATTERNS
        )
    )

    if shocked_score >= 1:

        return (
            "shocked",
            0.86,
            "explicit_shock"
        )

    # -----------------------------------------------------
    # THINK / SUSPICIOUS
    # -----------------------------------------------------

    think_score = (
        _score_patterns(
            answer,
            THINK_PATTERNS
        )
    )

    if (
        think_score
        >= 1
    ):

        return (
            "think",
            0.84,
            "thinking_or_suspicious"
        )

    # -----------------------------------------------------
    # RAGE / ANGRY
    # -----------------------------------------------------

    rage_score = (
        _score_patterns(
            answer,
            RAGE_PATTERNS
        )
    )

    if rage_score >= 1:

        return (
            "rage",
            0.90,
            "explicit_rage"
        )

    angry_score = (
        _score_patterns(
            answer,
            ANGRY_PATTERNS
        )
    )

    if (
        angry_score
        >= 1
        and
        mood
        in {
            "annoyed",
            "chaotic",
            "smug",
        }
    ):

        return (
            "angry",
            0.82,
            "annoyed_expression"
        )

    # -----------------------------------------------------
    # BONK
    #
    # Besonders für Hanae / playful teasing.
    # -----------------------------------------------------

    bonk_score = (
        _score_patterns(
            answer,
            BONK_PATTERNS
        )
    )

    if (
        bonk_score
        >= 1
        and
        (
            is_hanae
            or
            mood
            in {
                "smug",
                "chaotic",
            }
        )
    ):

        return (
            "bonk",
            0.84,
            "playful_bonk"
        )

    # -----------------------------------------------------
    # GAMING
    # -----------------------------------------------------

    gaming_score = (
        _score_patterns(
            combined,
            GAMING_PATTERNS
        )
    )

    if (
        gaming_score
        >= 1
        and
        (
            "game"
            in answer_lower
            or
            "zock"
            in answer_lower
            or
            "boss"
            in answer_lower
            or
            "gaming"
            in answer_lower
        )
    ):

        return (
            "gaming",
            0.78,
            "gaming_context"
        )

    # -----------------------------------------------------
    # PARTY
    # -----------------------------------------------------

    party_score = (
        _score_patterns(
            answer,
            PARTY_PATTERNS
        )
    )

    if party_score >= 1:

        return (
            "party",
            0.83,
            "celebration"
        )

    # -----------------------------------------------------
    # FIRE
    # -----------------------------------------------------

    fire_score = (
        _score_patterns(
            answer,
            FIRE_PATTERNS
        )
    )

    if fire_score >= 1:

        return (
            "fire",
            0.77,
            "strong_positive_reaction"
        )

    # -----------------------------------------------------
    # NERVOUS
    # -----------------------------------------------------

    nervous_score = (
        _score_patterns(
            answer,
            NERVOUS_PATTERNS
        )
    )

    if nervous_score >= 1:

        return (
            "nervous",
            0.80,
            "awkward_or_nervous"
        )

    # -----------------------------------------------------
    # DIZZY
    # -----------------------------------------------------

    dizzy_score = (
        _score_patterns(
            answer,
            DIZZY_PATTERNS
        )
    )

    if dizzy_score >= 1:

        return (
            "dizzy",
            0.79,
            "brainlag_or_confusion"
        )

    # -----------------------------------------------------
    # WAVE
    #
    # Nicht jede Begrüßung braucht automatisch eins.
    #
    # Nur wenn die Antwort wirklich selbst
    # eine Begrüßung / Verabschiedung enthält.
    # -----------------------------------------------------

    wave_score = (
        _score_patterns(
            answer,
            WAVE_PATTERNS
        )
    )

    if (
        wave_score
        >= 1
        and
        len(
            answer.split()
        )
        <= 12
    ):

        return (
            "wave",
            0.72,
            "greeting_or_goodbye"
        )

    # -----------------------------------------------------
    # DEAD
    #
    # Deadpan / "bro" Reaction.
    # -----------------------------------------------------

    dead_score = (
        _score_patterns(
            answer,
            DEAD_PATTERNS
        )
    )

    if (
        dead_score
        >= 1
        and
        len(
            answer.split()
        )
        <= 18
    ):

        return (
            "dead",
            0.74,
            "deadpan_disbelief"
        )

    # -----------------------------------------------------
    # COOL
    # -----------------------------------------------------

    cool_score = (
        _score_patterns(
            answer,
            COOL_PATTERNS
        )
    )

    if (
        cool_score
        >= 1
        and
        mood
        ==
        "smug"
    ):

        return (
            "cool",
            0.72,
            "smug_cool"
        )

    # -----------------------------------------------------
    # INNER STATE FALLBACK
    #
    # Nur sehr starke Zustände.
    #
    # Kein Emote einfach weil curiosity=0.55 etc.
    # -----------------------------------------------------

    if inner_state is not None:

        amusement = float(
            getattr(
                inner_state,
                "amusement",
                0.0
            )
            or 0.0
        )

        irritation = float(
            getattr(
                inner_state,
                "irritation",
                0.0
            )
            or 0.0
        )

        warmth = float(
            getattr(
                inner_state,
                "warmth",
                0.0
            )
            or 0.0
        )

        chaos = float(
            getattr(
                inner_state,
                "chaos",
                0.0
            )
            or 0.0
        )

        if (
            amusement
            >= 0.82
            and
            len(
                answer.split()
            )
            <= 16
        ):

            return (
                "laugh",
                0.70,
                "strong_inner_amusement"
            )

        if (
            irritation
            >= 0.82
            and
            len(
                answer.split()
            )
            <= 18
        ):

            return (
                "angry",
                0.70,
                "strong_inner_irritation"
            )

        if (
            warmth
            >= 0.88
            and
            len(
                answer.split()
            )
            <= 16
        ):

            return (
                "love",
                0.70,
                "strong_inner_warmth"
            )

        if (
            chaos
            >= 0.88
            and
            len(
                answer.split()
            )
            <= 14
        ):

            return (
                "fire",
                0.68,
                "strong_inner_chaos"
            )

    return (
        None,
        0.0,
        "no_strong_emote_signal"
    )


# =========================================================
# APPLY
# =========================================================

def apply_evilnae_emote_layer(
    answer: str,
    *,
    user_text: str = "",
    mood: str = "normal",
    inner_state=None,
    is_hanae: bool = False
):

    (
        cleaned,
        stripped_unicode,
        stripped_custom
    ) = strip_non_evilnae_emojis(
        answer
    )

    (
        semantic,
        confidence,
        reason
    ) = choose_emote_semantic(

        answer=cleaned,

        user_text=user_text,

        mood=mood,

        inner_state=inner_state,

        is_hanae=is_hanae
    )

    if not semantic:

        result = (
            EvilnaeEmoteDecision(

                semantic=None,

                emoji_name=None,

                rendered=None,

                confidence=confidence,

                reason=reason,

                added=False,

                stripped_unicode=(
                    stripped_unicode
                ),

                stripped_custom=(
                    stripped_custom
                )
            )
        )

        return (
            cleaned,
            result
        )

    emoji_name = (
        EMOTE_NAMES.get(
            semantic
        )
    )

    rendered = (
        get_emote(
            semantic
        )
    )

    if not rendered:

        result = (
            EvilnaeEmoteDecision(

                semantic=semantic,

                emoji_name=emoji_name,

                rendered=None,

                confidence=confidence,

                reason=(
                    "emoji_not_loaded"
                ),

                added=False,

                stripped_unicode=(
                    stripped_unicode
                ),

                stripped_custom=(
                    stripped_custom
                )
            )
        )

        return (
            cleaned,
            result
        )

    # -----------------------------------------------------
    # EXACTLY ONE
    # -----------------------------------------------------

    final_answer = (
        f"{cleaned} {rendered}"
        .strip()
    )

    result = (
        EvilnaeEmoteDecision(

            semantic=semantic,

            emoji_name=emoji_name,

            rendered=rendered,

            confidence=confidence,

            reason=reason,

            added=True,

            stripped_unicode=(
                stripped_unicode
            ),

            stripped_custom=(
                stripped_custom
            )
        )
    )

    return (
        final_answer,
        result
    )


# =========================================================
# DEBUG
# =========================================================

def format_evilnae_emote_debug(
    result: EvilnaeEmoteDecision
) -> str:

    return (

        "[EVILNAE EMOTE] "
        f"v={EVILNAE_EMOTE_VERSION} "
        f"semantic={result.semantic!r} "
        f"name={result.emoji_name!r} "
        f"confidence={result.confidence:.2f} "
        f"added={result.added} "
        f"stripped_unicode="
        f"{result.stripped_unicode} "
        f"stripped_custom="
        f"{result.stripped_custom} "
        f"reason={result.reason}"
    )


# =========================================================
# SELF TEST
# =========================================================

def _self_test():

    # Fake cache for tests.
    global _application_emojis

    _application_emojis = {

        name:
            f"<:{name}:123>"

        for name
        in EMOTE_NAMES.values()
    }

    tests = []

    # -----------------------------------------------------
    # 1. Unicode wird entfernt
    # -----------------------------------------------------

    answer, result = (
        apply_evilnae_emote_layer(

            "bro was 😭😂",

            user_text=(
                "ich esse ketchup "
                "auf nudeln"
            )
        )
    )

    tests.append(
        (
            "unicode stripped",

            "😭"
            not in answer
            and
            "😂"
            not in answer
        )
    )

    # -----------------------------------------------------
    # 2. Dead emote
    # -----------------------------------------------------

    tests.append(
        (
            "dead reaction selected",

            (
                "evilnae_dead"
                in answer
            )
        )
    )

    # -----------------------------------------------------
    # 3. Fremdes Custom Emoji raus
    # -----------------------------------------------------

    answer, result = (
        apply_evilnae_emote_layer(

            (
                "okay das war lustig "
                "<:HanaeLove:999999>"
            )
        )
    )

    tests.append(
        (
            "foreign custom emoji stripped",

            (
                "HanaeLove"
                not in answer
            )
        )
    )

    # -----------------------------------------------------
    # 4. Eigener laugh
    # -----------------------------------------------------

    tests.append(
        (
            "laugh application emoji added",

            (
                "evilnae_laugh"
                in answer
            )
        )
    )

    # -----------------------------------------------------
    # 5. Serious context -> none
    # -----------------------------------------------------

    answer, result = (
        apply_evilnae_emote_layer(

            (
                "fuck, das tut mir "
                "wirklich leid."
            ),

            user_text=(
                "meine katze ist "
                "gestorben"
            )
        )
    )

    tests.append(
        (
            "serious context no emote",

            not result.added
        )
    )

    # -----------------------------------------------------
    # 6. Gaming
    # -----------------------------------------------------

    answer, result = (
        apply_evilnae_emote_layer(

            "der boss ist cursed",

            user_text=(
                "bin wieder in "
                "elden ring"
            )
        )
    )

    tests.append(
        (
            "gaming selected",

            (
                result.semantic
                ==
                "gaming"
            )
        )
    )

    # -----------------------------------------------------
    # 7. Think
    # -----------------------------------------------------

    answer, result = (
        apply_evilnae_emote_layer(

            "hmm. erklär dich."
        )
    )

    tests.append(
        (
            "think selected",

            (
                result.semantic
                ==
                "think"
            )
        )
    )

    # -----------------------------------------------------
    # 8. Wave
    # -----------------------------------------------------

    answer, result = (
        apply_evilnae_emote_layer(

            "moin, du lebst ja noch"
        )
    )

    tests.append(
        (
            "wave selected",

            (
                result.semantic
                ==
                "wave"
            )
        )
    )

    # -----------------------------------------------------
    # 9. No forced emote
    # -----------------------------------------------------

    answer, result = (
        apply_evilnae_emote_layer(

            "ja, seh ich genauso."
        )
    )

    tests.append(
        (
            "neutral reply stays without emote",

            not result.added
        )
    )

    # -----------------------------------------------------
    # 10. exactly one custom emoji
    # -----------------------------------------------------

    answer, result = (
        apply_evilnae_emote_layer(

            "lmao das war dumm 😂 😭"
        )
    )

    count = len(
        CUSTOM_EMOJI_RE.findall(
            answer
        )
    )

    tests.append(
        (
            "maximum one Evilnae emote",

            count
            ==
            1
        )
    )

    # -----------------------------------------------------
    # RESULT
    # -----------------------------------------------------

    passed = 0

    print("")
    print(
        "============================================"
    )

    print(
        f"EVILNAE EMOTES v"
        f"{EVILNAE_EMOTE_VERSION} TEST"
    )

    print(
        "============================================"
    )

    print("")

    for (
        name,
        success
    ) in tests:

        if success:

            passed += 1

            status = (
                "PASS"
            )

        else:

            status = (
                "FAIL"
            )

        print(
            f"[{status}] {name}"
        )

    print("")

    print(
        "============================================"
    )

    print(
        f"RESULT: "
        f"{passed}/{len(tests)} passed"
    )

    print(
        "============================================"
    )

    return (
        passed
        ==
        len(tests)
    )


if __name__ == "__main__":

    _self_test()