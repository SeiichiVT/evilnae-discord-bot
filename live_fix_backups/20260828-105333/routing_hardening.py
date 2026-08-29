import re
from dataclasses import dataclass, field
from typing import Optional

ROUTING_HARDENING_VERSION = "1.2"

EVIL_VARIANT_PATTERN = re.compile(
    r"(?<![A-Za-zÄÖÜäöüß0-9_])e+v+i+l+(?:\s*n+a+e+)?(?![A-Za-zÄÖÜäöüß0-9_])",
    re.IGNORECASE,
)

SECOND_PERSON_PATTERN = re.compile(
    r"\b(?:du|dir|dich|dein|deine|deiner|deinen|deinem|deins|bist|hast|"
    r"kannst|könntest|koenntest|willst|würdest|wuerdest|magst|meinst|"
    r"denkst|findest|weißt|weisst|sollst|darfst|brauchst|möchtest|moechtest)\b",
    re.IGNORECASE,
)

DIRECT_ACTION_PATTERN = re.compile(
    r"\b(?:hilf|sag|erklär|erklaer|erzähl|erzaehl|guck|schau|hör|hoer|"
    r"komm|warte|lies|rate|mach|nimm|gib)\b",
    re.IGNORECASE,
)

QUESTIONISH_PATTERN = re.compile(
    r"\b(?:was|wer|wie|warum|wieso|wann|wo|welche|welcher|welches|"
    r"kannst|willst|würdest|wuerdest|magst|findest|meinst|denkst|"
    r"weißt|weisst|hast|bist)\b",
    re.IGNORECASE,
)

# Third-person statements can still be direct social relevance when
# Evilnae herself is the grammatical subject of a question, e.g.
# "ist evil wieder eingeschlafen" or "was macht evil eigentlich".
EVILNAE_SELF_QUERY_LEAD_PATTERN = re.compile(
    r"^\s*(?:ist|war|hat|wird|macht|mag|findet|kann|will|kommt|"
    r"schläft|schlaeft|was|wie|warum|wieso|wann|wo)\b",
    re.IGNORECASE,
)

THIRD_PERSON_LEAD_PATTERN = re.compile(
    r"^\s*(?:arme|armer|armes|typisch|wegen|über|ueber|bei|mit|ohne|"
    r"gegen|für|fuer)\s+",
    re.IGNORECASE,
)


# =========================================================
# v1.2 SOCIAL VOCATIVE ADDRESSING
# =========================================================
#
# DIRECT:
#   "WOW Evil WOW..."
#   "Ach Evil..."
#   "Wow evil.. mehr nicht?"
#
# THIRD PERSON:
#   "Wow, Evil ist heute ruhig."
#   "Evil hat das gestern gesagt."
# =========================================================

SOCIAL_VOCATIVE_PREFIX_PATTERN = re.compile(
    r"^\s*(?:(?:"
    r"wow+|ach+|ey+|hey+|yo+|boah+|bro+|bruh+|"
    r"alter+|wtf+|lol+|haha+|hahaha+|uff+|pff+"
    r")[\s,;:!?._\-–—]*)+$",
    re.IGNORECASE,
)

THIRD_PERSON_AFTER_EVIL_PATTERN = re.compile(
    r"^\s*(?:"
    r"ist|war|hat|hatte|wird|macht|mag|findet|kann|"
    r"will|kommt|geht|schläft|schlaeft|sagt|meint|"
    r"denkt|braucht|sollte|würde|wuerde|hätte|haette"
    r")\b",
    re.IGNORECASE,
)

DIRECT_SOCIAL_FOLLOWUP_PATTERN = re.compile(
    r"^\s*(?:"
    r"wow+|wtf+|bro+|bruh+|mehr\s+nicht|ernsthaft|"
    r"echt\s+jetzt|really|aha|okay|ok|ach\s+komm|"
    r"komm\s+schon|was\s+soll\s+das|na\s+toll|"
    r"nicht\s+dein\s+ernst"
    r")\b",
    re.IGNORECASE,
)


REFERENCE_PATTERNS = {
    "predicate_inheritance": re.compile(
        r"^\s*(?:und\s+)?(?:meine|meiner|meins|deine|deiner|deins|"
        r"ihre|ihrer|ihres)\s*[?!.,]*\s*$",
        re.IGNORECASE,
    ),
    "self_parallel": re.compile(
        r"\b(?:würdest|wuerdest|willst|magst)\s+du\b.{0,35}\b(?:das|auch)\b"
        r"|^\s*(?:und\s+)?du\s*[?!.,]*\s*$",
        re.IGNORECASE,
    ),
    "demonstrative": re.compile(
        r"\b(?:das|dies|dieses|damit|davon|daran|darüber|darueber|"
        r"der\s+da|die\s+da|das\s+da|das\s+von\s+eben)\b",
        re.IGNORECASE,
    ),
    "causal_short": re.compile(
        r"^\s*(?:warum|wieso)\s+(?:das|denn|so)\s*[?!.,]*\s*$",
        re.IGNORECASE,
    ),
    "meaning_short": re.compile(
        r"\bwas\s+meinst\s+du\s+damit\b",
        re.IGNORECASE,
    ),
    "discourse_link": re.compile(
        r"^\s*(?:also\s+doch|trotzdem|und\s+dann|dann|also)\b",
        re.IGNORECASE,
    ),
    "channel_here": re.compile(
        r"\b(?:was\s+ist\s+hier\s+los|was\s+geht\s+hier\s+ab|"
        r"was\s+war\s+hier\s+los)\b",
        re.IGNORECASE,
    ),
}

NOT_DIRECT_REASON_PATTERNS = (
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


@dataclass
class RoutingSignals:
    changed: bool = False
    direct: bool = False
    reply_to_evilnae: bool = False
    name_variant: bool = False
    stretched_name: bool = False
    subject_is_evilnae: bool = False
    recent_thread: bool = False
    reference_types: list[str] = field(default_factory=list)
    reason: str = "unchanged"


@dataclass
class ParticipationBoostResult:
    changed: bool = False
    old_action: str = ""
    new_action: str = ""
    old_relevance: float = 0.0
    new_relevance: float = 0.0
    old_involvement: float = 0.0
    new_involvement: float = 0.0
    reason: str = "unchanged"


def _text(perception) -> str:
    return str(
        getattr(perception, "raw_content", "")
        or getattr(perception, "trigger_text", "")
        or getattr(perception, "text", "")
        or ""
    ).strip()


def _normalize(text: str) -> str:
    return re.sub(
        r"\s+",
        " ",
        str(text or ""),
    ).strip()


def _reply_author_id(perception) -> str:
    reply = getattr(
        perception,
        "reply",
        None,
    )

    return (
        str(
            getattr(
                reply,
                "author_id",
                "",
            )
            or ""
        )
        if reply
        else ""
    )


def _name_spans(text: str):
    return list(
        EVIL_VARIANT_PATTERN.finditer(
            text or ""
        )
    )


def _is_stretched_name(text: str) -> bool:
    compact = re.sub(
        r"\s+",
        "",
        str(text or "").lower(),
    )

    return compact not in {
        "evil",
        "evilnae",
    }


def _looks_like_direct_vocative(
    text: str,
    match,
) -> bool:

    raw_before = text[
        :match.start()
    ]

    raw_after = text[
        match.end():
    ]

    before = raw_before.strip(
        " \t,;:!?._-–—"
    )

    after = raw_after.strip(
        " \t,;:!?._-–—"
    )

    is_start = not before
    is_end = not after

    # -----------------------------------------------------
    # v1.2 INTERJECTION + NAME = SOCIAL VOCATIVE
    #
    # "WOW Evil WOW..." addresses Evilnae.
    #
    # "Wow, Evil ist heute ruhig" remains third-person.
    # -----------------------------------------------------

    if SOCIAL_VOCATIVE_PREFIX_PATTERN.fullmatch(
        raw_before
    ):
        after_social = raw_after.lstrip(
            " \t,;:!?._-–—"
        )

        if not after_social:
            return True

        if DIRECT_SOCIAL_FOLLOWUP_PATTERN.search(
            after_social
        ):
            return True

        if not THIRD_PERSON_AFTER_EVIL_PATTERN.search(
            after_social
        ):
            return True

    if is_start:

        raw_after = text[
            match.end():
        ].strip()

        if (
            not raw_after
            or
            re.fullmatch(
                r"[\s!?.,_\-–—]+",
                raw_after,
            )
        ):
            return True

        if (
            SECOND_PERSON_PATTERN.search(
                raw_after
            )
            or
            DIRECT_ACTION_PATTERN.search(
                raw_after
            )
            or
            QUESTIONISH_PATTERN.search(
                raw_after
            )
            or
            raw_after.lower().startswith(
                (
                    "wow",
                    "wtf",
                    "bro",
                    "bruh",
                    "ey",
                    "hey",
                    "yo",
                )
            )
        ):
            return True

    if (
        is_end
        and
        (
            SECOND_PERSON_PATTERN.search(
                text[
                    :match.start()
                ]
            )
            or
            DIRECT_ACTION_PATTERN.search(
                text[
                    :match.start()
                ]
            )
            or
            QUESTIONISH_PATTERN.search(
                text[
                    :match.start()
                ]
            )
        )
    ):
        return True

    words = re.findall(
        r"[A-Za-zÄÖÜäöüß]+",
        text,
    )

    if len(words) <= 6:

        lowered = text.lower()

        if any(
            token in lowered
            for token in (
                "wow",
                "wtf",
                "bro",
                "bruh",
                "ey ",
                "hey ",
                "yo ",
            )
        ):
            return True

    return False


def detect_reference_types(
    text: str,
) -> list[str]:

    text = _normalize(
        text
    )

    return [
        name

        for (
            name,
            pattern,
        )
        in REFERENCE_PATTERNS.items()

        if pattern.search(
            text
        )
    ]


def harden_perception_addressing(
    perception,
    *,
    bot_user_id: Optional[str] = None,
) -> RoutingSignals:

    text = _text(
        perception
    )

    refs = detect_reference_types(
        text
    )

    reply_to_bot = bool(
        getattr(
            perception,
            "replied_to_bot",
            False,
        )
    )

    if (
        not reply_to_bot
        and
        bot_user_id is not None
        and
        _reply_author_id(
            perception
        )
        ==
        str(
            bot_user_id
        )
    ):
        reply_to_bot = True

    if reply_to_bot:

        changed = not bool(
            getattr(
                perception,
                "should_reply",
                False,
            )
        )

        perception.replied_to_bot = True
        perception.direct_address = True
        perception.trigger_detected = True
        perception.should_reply = True

        perception.address_reason = (
            "b3f_reply_to_evilnae_priority"
        )

        return RoutingSignals(
            changed=changed,
            direct=True,
            reply_to_evilnae=True,
            name_variant=bool(
                _name_spans(
                    text
                )
            ),
            reference_types=refs,
            reason=(
                "reply_to_evilnae_priority"
            ),
        )

    matches = _name_spans(
        text
    )

    if not matches:

        return RoutingSignals(
            reference_types=refs
        )

    stretched = any(
        _is_stretched_name(
            match.group(0)
        )
        for match
        in matches
    )

    if bool(
        getattr(
            perception,
            "direct_address",
            False,
        )
    ):

        return RoutingSignals(
            direct=True,
            name_variant=True,
            stretched_name=stretched,
            reference_types=refs,
            reason="already_direct",
        )

    for match in matches:

        if not _looks_like_direct_vocative(
            text,
            match,
        ):
            continue

        if THIRD_PERSON_LEAD_PATTERN.search(
            text[
                :match.start()
            ]
        ):
            continue

        perception.name_mentioned = True
        perception.direct_address = True
        perception.trigger_detected = True
        perception.should_reply = True

        perception.address_reason = (
            "b3f_stretched_direct_vocative"
            if
            _is_stretched_name(
                match.group(0)
            )
            else
            "b3f_direct_vocative"
        )

        return RoutingSignals(
            changed=True,
            direct=True,
            name_variant=True,
            stretched_name=stretched,
            reference_types=refs,
            reason=(
                perception.address_reason
            ),
        )

    perception.name_mentioned = True

    return RoutingSignals(
        direct=False,
        name_variant=True,
        stretched_name=stretched,
        subject_is_evilnae=True,
        reference_types=refs,
        reason=(
            "evilnae_subject_not_direct"
        ),
    )


def has_recent_thread_with_user(
    channel_snapshot,
    *,
    current_user_id: str,
    scan_limit: int = 8,
) -> bool:

    if not channel_snapshot:
        return False

    current_user_id = str(
        current_user_id
    )

    previous = list(
        channel_snapshot
    )[:-1]

    for item in reversed(
        previous[
            -scan_limit:
        ]
    ):

        if str(
            item.get(
                "type",
                "",
            )
        ) != "bot":
            continue

        if str(
            item.get(
                "reply_to_id"
            )
            or ""
        ) == current_user_id:
            return True

    return False


def _extract_last_question_slot(
    channel_snapshot,
    *,
    current_user_id: Optional[str] = None,
) -> str:

    if not channel_snapshot:
        return ""

    wanted_user = (
        str(
            current_user_id
        )
        if
        current_user_id is not None
        else
        None
    )

    for item in reversed(
        list(
            channel_snapshot
        )[:-1][-10:]
    ):

        if item.get(
            "type"
        ) != "user":
            continue

        if (
            wanted_user is not None
            and
            str(
                item.get(
                    "user_id"
                )
                or ""
            )
            !=
            wanted_user
        ):
            continue

        content = _normalize(
            item.get(
                "content",
                "",
            )
        )

        if not content:
            continue

        favorite = re.search(
            r"\blieblings([A-Za-zÄÖÜäöüß]+)\b",
            content,
            re.IGNORECASE,
        )

        if favorite:

            return (
                "Lieblings"
                +
                favorite.group(1)
            )

        topic = re.search(
            r"\bwas\s+hältst\s+du\s+von\s+(.+?)[?!.]*$",
            content,
            re.IGNORECASE,
        )

        if topic:

            return (
                topic.group(1)
                .strip()
            )

        if "?" in content:

            words = [
                word

                for word
                in re.findall(
                    r"[A-Za-zÄÖÜäöüß]+",
                    content,
                )

                if len(
                    word
                ) >= 4
            ]

            if words:
                return words[-1]

    return ""


def build_routing_context(
    perception,
    channel_snapshot,
    *,
    current_user_id: Optional[str] = None,
    bot_user_id: Optional[str] = None,
) -> str:

    text = _text(
        perception
    )

    refs = detect_reference_types(
        text
    )

    matches = _name_spans(
        text
    )

    name_variant = bool(
        matches
    )

    stretched = any(
        _is_stretched_name(
            match.group(0)
        )
        for match
        in matches
    )

    direct = bool(
        getattr(
            perception,
            "direct_address",
            False,
        )
    )

    reply_to_evilnae = bool(
        getattr(
            perception,
            "replied_to_bot",
            False,
        )
    )

    if (
        not reply_to_evilnae
        and
        bot_user_id is not None
        and
        _reply_author_id(
            perception
        )
        ==
        str(
            bot_user_id
        )
    ):
        reply_to_evilnae = True

    recent_thread = (
        has_recent_thread_with_user(
            channel_snapshot,
            current_user_id=str(
                current_user_id
            ),
            scan_limit=8,
        )
        if
        current_user_id is not None
        else
        False
    )

    subject_is_evilnae = (
        name_variant
        and
        not direct
    )

    lines = [
        (
            f"[ROUTING HARDENING "
            f"v{ROUTING_HARDENING_VERSION}]"
        ),
        (
            f"reply_to_evilnae="
            f"{reply_to_evilnae}"
        ),
        (
            f"direct_address="
            f"{direct}"
        ),
        (
            f"evilnae_name_variant="
            f"{name_variant}"
        ),
        (
            f"stretched_evilnae_name="
            f"{stretched}"
        ),
        (
            f"evilnae_is_subject="
            f"{subject_is_evilnae}"
        ),
        (
            f"recent_thread_with_current_user="
            f"{recent_thread}"
        ),
        (
            f"reference_types="
            f"{refs or ['none']}"
        ),
    ]

    guidance = []

    if reply_to_evilnae:

        guidance.append(
            (
                "Discord Reply auf Evilnae hat höchste "
                "Adressierungs-Priorität; nur eine explizite "
                "Ansprache an jemand anderen kann das überstimmen."
            )
        )

    if (
        stretched
        and
        direct
    ):

        guidance.append(
            (
                "Die gedehnte Schreibweise von Evil/Evilnae "
                "ist ein normaler Vocative."
            )
        )

    if subject_is_evilnae:

        guidance.append(
            (
                "Evilnae ist Thema der Nachricht: "
                "Participation-Relevanz, aber nicht automatisch "
                "direkte Ansprache."
            )
        )

    if recent_thread:

        guidance.append(
            (
                "Zwischenmeldungen anderer User löschen den "
                "laufenden Strang mit diesem User nicht; "
                "semantische Fortsetzung prüfen."
            )
        )

    if (
        "predicate_inheritance"
        in refs
    ):

        slot = (
            _extract_last_question_slot(
                channel_snapshot,
                current_user_id=(
                    current_user_id
                ),
            )
        )

        if slot:

            guidance.append(
                (
                    "Die Kurzfrage erbt den vorherigen Slot "
                    f"'{slot}'. Nicht auf eine allgemeinere "
                    "Kategorie wechseln."
                )
            )

        else:

            guidance.append(
                (
                    "Die Kurzfrage erbt das exakte "
                    "Prädikat/Thema der vorherigen Frage."
                )
            )

    if (
        "self_parallel"
        in refs
    ):

        guidance.append(
            (
                "Bei 'und du?' / 'würdest du das auch?' "
                "wechselt das Subjekt zu Evilnae; "
                "Gegenstand/Aktion bleiben aus dem vorherigen Turn."
            )
        )

    if (
        "demonstrative"
        in refs
    ):

        guidance.append(
            (
                "das/damit/davon/der da/die da bevorzugt "
                "an den unmittelbaren lokalen Gesprächsgegenstand "
                "binden."
            )
        )

    if (
        "causal_short"
        in refs
    ):

        guidance.append(
            (
                "'warum das?' fragt nach der Begründung "
                "der unmittelbar vorherigen Aussage oder Entscheidung."
            )
        )

    if (
        "meaning_short"
        in refs
    ):

        guidance.append(
            (
                "'was meinst du damit?' bezieht sich auf Evilnaes "
                "unmittelbar vorherige Aussage im aktiven Strang."
            )
        )

    if (
        "discourse_link"
        in refs
    ):

        guidance.append(
            (
                "also/trotzdem/dann setzen den aktuellen Thread fort; "
                "kein neues Thema erfinden."
            )
        )

    if (
        "channel_here"
        in refs
    ):

        guidance.append(
            (
                "'hier' meint in diesem Muster primär "
                "den Discord-Channel bzw. die aktuelle Gruppenepisode."
            )
        )

    if guidance:

        lines.append(
            "ROUTING / REFERENCE GUIDANCE:"
        )

        lines.extend(
            f"- {item}"
            for item
            in guidance
        )

    return "\n".join(
        lines
    )


def _reason_says_only_not_direct(
    reason: str,
) -> bool:

    reason = str(
        reason
        or ""
    ).lower()

    return any(
        marker in reason

        for marker
        in NOT_DIRECT_REASON_PATTERNS
    )


def apply_participation_routing_boost(
    decision,
    *,
    perception,
    channel_snapshot,
    current_user_id: Optional[str] = None,
) -> ParticipationBoostResult:

    old_action = str(
        getattr(
            decision,
            "action",
            "stay_silent",
        )
    )

    old_relevance = float(
        getattr(
            decision,
            "relevance",
            0.0,
        )
        or
        0.0
    )

    old_involvement = float(
        getattr(
            decision,
            "conversation_involvement",
            0.0,
        )
        or
        0.0
    )

    text = _text(
        perception
    )

    subject_is_evilnae = (
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
        has_recent_thread_with_user(
            channel_snapshot,
            current_user_id=str(
                current_user_id
            ),
            scan_limit=8,
        )
        if
        current_user_id is not None
        else
        False
    )

    changed = False
    reasons = []

    if subject_is_evilnae:

        new_relevance = max(
            old_relevance,
            0.70,
        )

        if (
            new_relevance
            !=
            float(
                getattr(
                    decision,
                    "relevance",
                    0.0,
                )
                or
                0.0
            )
        ):

            decision.relevance = (
                new_relevance
            )

            changed = True

        reasons.append(
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

        current = float(
            getattr(
                decision,
                "conversation_involvement",
                0.0,
            )
            or
            0.0
        )

        new_involvement = max(
            current,
            0.68,
        )

        if (
            new_involvement
            !=
            current
        ):

            decision.conversation_involvement = (
                new_involvement
            )

            changed = True

        reasons.append(
            "recent_thread"
        )

    if (
        str(
            getattr(
                decision,
                "action",
                "stay_silent",
            )
        )
        ==
        "stay_silent"

        and

        str(
            getattr(
                decision,
                "confidence",
                "low",
            )
        )
        !=
        "low"

        and

        _reason_says_only_not_direct(
            getattr(
                decision,
                "reason",
                "",
            )
        )

        and

        float(
            getattr(
                decision,
                "relevance",
                0.0,
            )
            or
            0.0
        )
        >=
        0.60

        and

        float(
            getattr(
                decision,
                "social_value",
                0.0,
            )
            or
            0.0
        )
        >=
        0.40

        and

        float(
            getattr(
                decision,
                "conversation_involvement",
                0.0,
            )
            or
            0.0
        )
        >=
        0.55
    ):

        decision.action = (
            "join"
        )

        if not getattr(
            decision,
            "response_goal",
            "",
        ):

            decision.response_goal = (
                "kurz und natürlich auf die laufende Situation reagieren"
            )

        changed = True

        reasons.append(
            "corrected_not_direct_only_failure"
        )

    return ParticipationBoostResult(
        changed=changed,
        old_action=old_action,
        new_action=str(
            getattr(
                decision,
                "action",
                "stay_silent",
            )
        ),
        old_relevance=old_relevance,
        new_relevance=float(
            getattr(
                decision,
                "relevance",
                0.0,
            )
            or
            0.0
        ),
        old_involvement=old_involvement,
        new_involvement=float(
            getattr(
                decision,
                "conversation_involvement",
                0.0,
            )
            or
            0.0
        ),
        reason=(
            "+".join(
                reasons
            )
            if reasons
            else
            "unchanged"
        ),
    )


def format_routing_debug(
    signals: RoutingSignals,
) -> str:

    return (
        "[ROUTING HARDENING] "
        f"v={ROUTING_HARDENING_VERSION} "
        f"changed={signals.changed} "
        f"direct={signals.direct} "
        f"reply_to_evilnae={signals.reply_to_evilnae} "
        f"name_variant={signals.name_variant} "
        f"stretched={signals.stretched_name} "
        f"subject_is_evilnae={signals.subject_is_evilnae} "
        f"references={signals.reference_types} "
        f"reason={signals.reason}"
    )


def format_participation_boost_debug(
    result: ParticipationBoostResult,
) -> str:

    return (
        "[PARTICIPATION ROUTING BOOST] "
        f"v={ROUTING_HARDENING_VERSION} "
        f"changed={result.changed} "
        f"action={result.old_action}->{result.new_action} "
        f"relevance={result.old_relevance:.2f}->{result.new_relevance:.2f} "
        f"involvement={result.old_involvement:.2f}->{result.new_involvement:.2f} "
        f"reason={result.reason}"
    )


# =========================================================
# SELF TEST
# =========================================================

class _Reply:
    def __init__(
        self,
        author_id="",
    ):
        self.author_id = (
            author_id
        )


class _Perception:
    def __init__(
        self,
        text,
        *,
        reply_author_id="",
    ):

        self.raw_content = (
            text
        )

        self.trigger_text = (
            text
        )

        self.text = (
            text
        )

        self.direct_address = (
            False
        )

        self.replied_to_bot = (
            False
        )

        self.name_mentioned = (
            False
        )

        self.trigger_detected = (
            False
        )

        self.should_reply = (
            False
        )

        self.address_reason = (
            "ambiguous"
        )

        self.reply = (
            _Reply(
                reply_author_id
            )
            if reply_author_id
            else None
        )


class _Decision:
    def __init__(
        self,
        *,
        action="stay_silent",
        confidence="medium",
        relevance=0.0,
        social_value=0.0,
        conversation_involvement=0.0,
        reason="",
    ):

        self.action = (
            action
        )

        self.confidence = (
            confidence
        )

        self.relevance = (
            relevance
        )

        self.social_value = (
            social_value
        )

        self.conversation_involvement = (
            conversation_involvement
        )

        self.reason = (
            reason
        )

        self.response_goal = (
            ""
        )


def _self_test():

    tests = []

    perception = _Perception(
        "Eviilllllllll ? kannst du mir ein gefallen tun?"
    )

    result = (
        harden_perception_addressing(
            perception,
            bot_user_id="999",
        )
    )

    tests.append(
        (
            "stretched Evil direct call",
            (
                result.direct
                and
                perception.should_reply
            ),
        )
    )

    perception = _Perception(
        "Arme evil"
    )

    result = (
        harden_perception_addressing(
            perception,
            bot_user_id="999",
        )
    )

    tests.append(
        (
            "Arme Evil stays third person",
            (
                not result.direct
                and
                result.subject_is_evilnae
            ),
        )
    )

    perception = _Perception(
        "evil ist heute still"
    )

    result = (
        harden_perception_addressing(
            perception,
            bot_user_id="999",
        )
    )

    tests.append(
        (
            "Evil is quiet stays third person",
            not result.direct,
        )
    )

    perception = _Perception(
        "evil die klauen deine pizza"
    )

    result = (
        harden_perception_addressing(
            perception,
            bot_user_id="999",
        )
    )

    tests.append(
        (
            "start vocative + second person direct",
            result.direct,
        )
    )

    perception = _Perception(
        "WOW evillllll WOW"
    )

    result = (
        harden_perception_addressing(
            perception,
            bot_user_id="999",
        )
    )

    tests.append(
        (
            "stretched exclamation direct",
            result.direct,
        )
    )

    perception = _Perception(
        "jo was meinst du",
        reply_author_id="999",
    )

    result = (
        harden_perception_addressing(
            perception,
            bot_user_id="999",
        )
    )

    tests.append(
        (
            "reply to Evilnae priority",
            (
                result.direct
                and
                result.reply_to_evilnae
            ),
        )
    )

    tests.append(
        (
            "predicate inheritance detected",
            (
                "predicate_inheritance"
                in
                detect_reference_types(
                    "Und meine?"
                )
            ),
        )
    )

    tests.append(
        (
            "self parallel detected",
            (
                "self_parallel"
                in
                detect_reference_types(
                    "Würdest du das auch probieren?"
                )
            ),
        )
    )

    tests.append(
        (
            "meaning short detected",
            (
                "meaning_short"
                in
                detect_reference_types(
                    "Was meinst du damit?"
                )
            ),
        )
    )

    snapshot = [
        {
            "type": "user",
            "user_id": "1",
            "content": "Evil hi",
        },
        {
            "type": "bot",
            "reply_to_id": "1",
            "content": "yo",
        },
        {
            "type": "user",
            "user_id": "2",
            "content": "x",
        },
        {
            "type": "user",
            "user_id": "3",
            "content": "y",
        },
        {
            "type": "user",
            "user_id": "4",
            "content": "z",
        },
        {
            "type": "user",
            "user_id": "1",
            "content": "und jetzt?",
        },
    ]

    tests.append(
        (
            "group interjections keep thread",
            has_recent_thread_with_user(
                snapshot,
                current_user_id="1",
                scan_limit=8,
            ),
        )
    )

    perception = _Perception(
        "Arme evil"
    )

    decision = _Decision(
        action="stay_silent",
        confidence="medium",
        relevance=0.2,
        social_value=0.1,
        conversation_involvement=0.1,
        reason="not directly addressed",
    )

    apply_participation_routing_boost(
        decision,
        perception=perception,
        channel_snapshot=snapshot,
        current_user_id="9",
    )

    tests.append(
        (
            "third-person mention does not force join",
            decision.action
            ==
            "stay_silent",
        )
    )

    perception = _Perception(
        "evil bekommt ihre pizza eh nie zurück"
    )

    decision = _Decision(
        action="stay_silent",
        confidence="medium",
        relevance=0.55,
        social_value=0.55,
        conversation_involvement=0.60,
        reason=(
            "not directly addressed to Evilnae"
        ),
    )

    apply_participation_routing_boost(
        decision,
        perception=perception,
        channel_snapshot=snapshot,
        current_user_id="9",
    )

    tests.append(
        (
            "not-direct-only failure corrected",
            decision.action
            ==
            "join",
        )
    )

    passed = 0

    print("")
    print(
        "============================================"
    )
    print(
        f"ROUTING HARDENING "
        f"v{ROUTING_HARDENING_VERSION} TEST"
    )
    print(
        "============================================"
    )
    print("")

    for (
        name,
        success,
    ) in tests:

        status = (
            "PASS"
            if success
            else
            "FAIL"
        )

        passed += int(
            bool(
                success
            )
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