import re
import threading
import time
import unicodedata

from dataclasses import dataclass, field
from typing import Any, Optional


# =========================================================
# VERSION
# =========================================================

WORLD_VERSION = "1.0"


# =========================================================
# CONFIG
# =========================================================

CURRENT_TTL = (
    30 * 60
)

SELF_AUTHORITY = (
    100
)

THIRD_AUTHORITY = (
    40
)

MAX_PER_KEY = (
    8
)


# =========================================================
# DATA MODELS
# =========================================================

@dataclass
class WorldClaim:

    subject_id: str

    subject_name: str

    predicate: str

    value: str

    scope: str

    source_user_id: str

    source_name: str

    source_type: str

    authority: int

    confidence: str

    timestamp: float

    raw_text: str


@dataclass
class WorldEvidence:

    matched: bool = False

    subject_name: Optional[str] = None

    predicate: Optional[str] = None

    selected_claim: Optional[
        WorldClaim
    ] = None

    competing_claims: list[
        WorldClaim
    ] = field(
        default_factory=list
    )

    authoritative: bool = False

    reason: str = "no_match"


# =========================================================
# RUNTIME STATE
# =========================================================

_lock = (
    threading.RLock()
)

_worlds: dict[
    str,
    dict[
        str,
        list[WorldClaim]
    ]
] = {}


# =========================================================
# NORMALIZATION
# =========================================================

def _norm(
    text: str
) -> str:

    text = unicodedata.normalize(
        "NFKD",
        str(
            text
            or ""
        ).lower()
    )

    text = "".join(

        character

        for character
        in text

        if not unicodedata.combining(
            character
        )
    )

    text = (
        text
        .replace(
            "ß",
            "ss"
        )
        .replace(
            "´",
            "'"
        )
        .replace(
            "`",
            "'"
        )
    )

    text = re.sub(
        r"[^a-z0-9]+",
        "_",
        text
    )

    return text.strip(
        "_"
    )


def _value(
    text: str
) -> str:

    text = re.sub(
        r"\s+",
        " ",
        str(
            text
            or ""
        ).strip()
    )

    text = re.split(
        r"\s+(?:aber|allerdings|jedoch)\s+",
        text,
        maxsplit=1,
        flags=re.IGNORECASE
    )[0]

    return text.strip(
        " ,;:-"
    )


def _canonical(
    text: str,
    hanae_user_id: Any
) -> str:

    text = str(
        text
        or ""
    )

    hanae_user_id = str(
        hanae_user_id
    )

    text = text.replace(
        f"<@{hanae_user_id}>",
        "Hanae"
    )

    text = text.replace(
        f"<@!{hanae_user_id}>",
        "Hanae"
    )

    return text


# =========================================================
# CLAIM KEY
# =========================================================

def _key(
    subject_id: Any,
    predicate: str
) -> str:

    return (
        f"{subject_id}"
        f"|"
        f"{predicate}"
    )


# =========================================================
# RESET
# =========================================================

def clear_all_worlds():

    with _lock:

        _worlds.clear()


# =========================================================
# CURRENT CLAIM VALIDITY
# =========================================================

def _active(
    claim: WorldClaim,
    now: Optional[float] = None
) -> bool:

    if (
        claim.scope
        !=
        "current"
    ):

        return True

    if now is None:

        now = (
            time.time()
        )

    return (
        now
        -
        claim.timestamp
        <=
        CURRENT_TTL
    )


# =========================================================
# REGISTER CLAIM
# =========================================================

def register_claim(
    *,
    channel_id: Any,
    subject_id: Any,
    subject_name: str,
    predicate: str,
    value: str,
    scope: str,
    source_user_id: Any,
    source_name: str,
    source_type: str,
    authority: int,
    confidence: str,
    raw_text: str,
    timestamp: Optional[float] = None
) -> Optional[WorldClaim]:

    value = (
        _value(
            value
        )
    )

    if not value:

        return None

    claim = WorldClaim(

        subject_id=str(
            subject_id
        ),

        subject_name=str(
            subject_name
        ),

        predicate=(
            predicate
        ),

        value=(
            value
        ),

        scope=(
            scope
        ),

        source_user_id=str(
            source_user_id
        ),

        source_name=str(
            source_name
        ),

        source_type=(
            source_type
        ),

        authority=(
            authority
        ),

        confidence=(
            confidence
        ),

        timestamp=(
            time.time()
            if timestamp is None
            else float(
                timestamp
            )
        ),

        raw_text=str(
            raw_text
            or ""
        )[:500]
    )

    channel_id = str(
        channel_id
    )

    key = (
        _key(
            subject_id,
            predicate
        )
    )

    with _lock:

        world = (
            _worlds.setdefault(
                channel_id,
                {}
            )
        )

        bucket = (
            world.setdefault(
                key,
                []
            )
        )

        # -------------------------------------------------
        # Exact duplicate from same source:
        # refresh instead of duplicating forever.
        # -------------------------------------------------

        for old_claim in reversed(
            bucket
        ):

            if (
                old_claim.source_user_id
                ==
                claim.source_user_id
                and
                old_claim.source_type
                ==
                claim.source_type
                and
                _norm(
                    old_claim.value
                )
                ==
                _norm(
                    claim.value
                )
            ):

                old_claim.timestamp = (
                    claim.timestamp
                )

                old_claim.raw_text = (
                    claim.raw_text
                )

                return old_claim

        bucket.append(
            claim
        )

        if (
            len(bucket)
            >
            MAX_PER_KEY
        ):

            del bucket[
                :-MAX_PER_KEY
            ]

    return claim


# =========================================================
# EFFECTIVE CLAIM
# =========================================================

def effective_claim(
    channel_id: Any,
    subject_id: Any,
    predicate: str
) -> Optional[WorldClaim]:

    with _lock:

        bucket = list(
            _worlds
            .get(
                str(
                    channel_id
                ),
                {}
            )
            .get(
                _key(
                    subject_id,
                    predicate
                ),
                []
            )
        )

    bucket = [

        claim

        for claim
        in bucket

        if _active(
            claim
        )
    ]

    if not bucket:

        return None

    # -----------------------------------------------------
    # PRIORITY:
    #
    # 1. Authority
    # 2. Recency
    #
    # Self-report therefore beats
    # newer third-party claims.
    # -----------------------------------------------------

    return max(

        bucket,

        key=lambda claim:
            (
                claim.authority,
                claim.timestamp
            )
    )


# =========================================================
# COMPETING CLAIMS
# =========================================================

def competing_claims(
    channel_id: Any,
    subject_id: Any,
    predicate: str,
    selected: Optional[
        WorldClaim
    ]
) -> list[WorldClaim]:

    with _lock:

        bucket = list(
            _worlds
            .get(
                str(
                    channel_id
                ),
                {}
            )
            .get(
                _key(
                    subject_id,
                    predicate
                ),
                []
            )
        )

    bucket = [

        claim

        for claim
        in bucket

        if _active(
            claim
        )
    ]

    result = []

    for claim in bucket:

        if (
            selected is not None
            and
            claim is selected
        ):

            continue

        if (
            selected is None
            or
            _norm(
                claim.value
            )
            !=
            _norm(
                selected.value
            )
        ):

            result.append(
                claim
            )

    result.sort(

        key=lambda claim:
            (
                claim.authority,
                claim.timestamp
            ),

        reverse=True
    )

    return result


# =========================================================
# OPINION PREDICATE
# =========================================================

def _opinion_predicate(
    item: str
) -> str:

    return (
        "opinion:"
        +
        _norm(
            item
        )
    )


# =========================================================
# OBSERVE MESSAGE
# =========================================================

def observe_world_message(
    *,
    channel_id: Any,
    user_id: Any,
    username: str,
    text: str,
    hanae_user_id: Any,
    timestamp: Optional[float] = None
) -> list[WorldClaim]:

    text = (
        _canonical(
            text,
            hanae_user_id
        )
    )

    claims: list[
        WorldClaim
    ] = []

    # =====================================================
    # FIRST-PERSON FAVORITE
    #
    # Meine Lieblingspizza ist Thunfisch.
    # Meine Lieblings Pizza ist Thunfisch.
    # =====================================================

    favorite_pattern = re.compile(

        r"\b(?:mein|meine)\s+"
        r"lieblings[\s_-]*"
        r"(?P<category>"
        r"[A-Za-zÄÖÜäöüß]{2,30}"
        r")"
        r"\s+"
        r"(?:ist|wäre|waere)"
        r"\s+"
        r"(?P<value>"
        r"[^.!?\n]{1,120}"
        r")",

        flags=re.IGNORECASE
    )

    for match in (
        favorite_pattern.finditer(
            text
        )
    ):

        claim = register_claim(

            channel_id=(
                channel_id
            ),

            subject_id=(
                user_id
            ),

            subject_name=(
                username
            ),

            predicate=(
                "favorite:"
                +
                _norm(
                    match.group(
                        "category"
                    )
                )
            ),

            value=(
                match.group(
                    "value"
                )
            ),

            scope="stable",

            source_user_id=(
                user_id
            ),

            source_name=(
                username
            ),

            source_type=(
                "self_report"
            ),

            authority=(
                SELF_AUTHORITY
            ),

            confidence="high",

            raw_text=(
                text
            ),

            timestamp=(
                timestamp
            )
        )

        if claim:

            claims.append(
                claim
            )

    # =====================================================
    # FIRST-PERSON DISLIKE
    #
    # Ich mag Mogelbaum nicht.
    # =====================================================

    dislike_pattern = re.compile(

        r"\bich\s+mag\s+"
        r"(?P<item>"
        r"[^.!?\n]{1,100}?"
        r")"
        r"\s+nicht\b",

        flags=re.IGNORECASE
    )

    for match in (
        dislike_pattern.finditer(
            text
        )
    ):

        item = (
            _value(
                match.group(
                    "item"
                )
            )
        )

        claim = register_claim(

            channel_id=(
                channel_id
            ),

            subject_id=(
                user_id
            ),

            subject_name=(
                username
            ),

            predicate=(
                _opinion_predicate(
                    item
                )
            ),

            value="dislike",

            scope="stable",

            source_user_id=(
                user_id
            ),

            source_name=(
                username
            ),

            source_type=(
                "self_report"
            ),

            authority=(
                SELF_AUTHORITY
            ),

            confidence="high",

            raw_text=(
                text
            ),

            timestamp=(
                timestamp
            )
        )

        if claim:

            claims.append(
                claim
            )

    # =====================================================
    # FIRST-PERSON OPINIONS
    # =====================================================

    opinion_mapping = {

        "mag":
            "like",

        "liebe":
            "love",

        "feier":
            "like",

        "feiere":
            "like",

        "hasse":
            "hate",

        "verabscheue":
            "hate",
    }

    opinion_pattern = re.compile(

        r"\bich\s+"
        r"(?P<verb>"
        r"liebe|mag|feier|feiere|"
        r"hasse|verabscheue"
        r")"
        r"\s+"
        r"(?P<item>"
        r"[^.!?\n]{1,100}"
        r")",

        flags=re.IGNORECASE
    )

    for match in (
        opinion_pattern.finditer(
            text
        )
    ):

        item = (
            _value(
                match.group(
                    "item"
                )
            )
        )

        # -------------------------------------------------
        # "Ich mag X nicht"
        # wurde oben bereits korrekt als dislike erfasst.
        # -------------------------------------------------

        if re.search(
            r"\bnicht$",
            item,
            flags=re.IGNORECASE
        ):

            continue

        verb = (
            match.group(
                "verb"
            )
            .lower()
        )

        claim = register_claim(

            channel_id=(
                channel_id
            ),

            subject_id=(
                user_id
            ),

            subject_name=(
                username
            ),

            predicate=(
                _opinion_predicate(
                    item
                )
            ),

            value=(
                opinion_mapping[
                    verb
                ]
            ),

            scope="stable",

            source_user_id=(
                user_id
            ),

            source_name=(
                username
            ),

            source_type=(
                "self_report"
            ),

            authority=(
                SELF_AUTHORITY
            ),

            confidence="high",

            raw_text=(
                text
            ),

            timestamp=(
                timestamp
            )
        )

        if claim:

            claims.append(
                claim
            )

    # =====================================================
    # CURRENT LOCATION / STATE
    #
    # Ich bin gerade im Wohnzimmer.
    # Ich bin gerade müde.
    # =====================================================

    current_state_pattern = re.compile(

        r"\bich\s+bin\s+"
        r"(?:gerade|grad|jetzt|momentan)"
        r"\s+"
        r"(?P<value>"
        r"[^.!?\n]{1,120}"
        r")",

        flags=re.IGNORECASE
    )

    location_prefixes = (

        "im ",

        "in ",

        "bei ",

        "auf ",

        "am ",

        "drau",

        "drin",

        "zuhause",

        "zu hause",
    )

    for match in (
        current_state_pattern.finditer(
            text
        )
    ):

        value = (
            _value(
                match.group(
                    "value"
                )
            )
        )

        is_location = (
            value.lower()
            .startswith(
                location_prefixes
            )
        )

        claim = register_claim(

            channel_id=(
                channel_id
            ),

            subject_id=(
                user_id
            ),

            subject_name=(
                username
            ),

            predicate=(
                "current_location"
                if is_location
                else
                "current_state"
            ),

            value=(
                value
            ),

            scope="current",

            source_user_id=(
                user_id
            ),

            source_name=(
                username
            ),

            source_type=(
                "self_report"
            ),

            authority=(
                SELF_AUTHORITY
            ),

            confidence="high",

            raw_text=(
                text
            ),

            timestamp=(
                timestamp
            )
        )

        if claim:

            claims.append(
                claim
            )

    # =====================================================
    # CURRENT ACTIVITY
    #
    # Ich spiele gerade Mario Kart.
    # =====================================================

    activity_pattern = re.compile(

        r"\bich\s+"
        r"(?P<verb>"
        r"mache|mach|spiele|spiel|"
        r"esse|trinke|"
        r"schaue|schau|"
        r"gucke|guck|"
        r"arbeite|"
        r"streame|stream"
        r")"
        r"\s+"
        r"(?:gerade|grad|jetzt|momentan)"
        r"\s+"
        r"(?P<value>"
        r"[^.!?\n]{1,120}"
        r")",

        flags=re.IGNORECASE
    )

    for match in (
        activity_pattern.finditer(
            text
        )
    ):

        claim = register_claim(

            channel_id=(
                channel_id
            ),

            subject_id=(
                user_id
            ),

            subject_name=(
                username
            ),

            predicate=(
                "current_activity"
            ),

            value=(
                f"{match.group('verb')} "
                f"{_value(match.group('value'))}"
            ),

            scope="current",

            source_user_id=(
                user_id
            ),

            source_name=(
                username
            ),

            source_type=(
                "self_report"
            ),

            authority=(
                SELF_AUTHORITY
            ),

            confidence="high",

            raw_text=(
                text
            ),

            timestamp=(
                timestamp
            )
        )

        if claim:

            claims.append(
                claim
            )

    # =====================================================
    # THIRD-PARTY HANAE CLAIMS
    #
    # Konservativ:
    #
    # User:
    # "Hanae liebt Mogelbaum."
    #
    # ist NICHT dasselbe wie:
    #
    # Hanae:
    # "Ich liebe Mogelbaum."
    # =====================================================

    if (
        str(
            user_id
        )
        !=
        str(
            hanae_user_id
        )
    ):

        third_favorite_pattern = re.compile(

            r"\bhanae"
            r"(?:s|['´`]s)?"
            r"\s+"
            r"lieblings[\s_-]*"
            r"(?P<category>"
            r"[A-Za-zÄÖÜäöüß]{2,30}"
            r")"
            r"\s+"
            r"(?:ist|wäre|waere)"
            r"\s+"
            r"(?P<value>"
            r"[^.!?\n]{1,120}"
            r")",

            flags=re.IGNORECASE
        )

        for match in (
            third_favorite_pattern.finditer(
                text
            )
        ):

            claim = register_claim(

                channel_id=(
                    channel_id
                ),

                subject_id=(
                    hanae_user_id
                ),

                subject_name="Hanae",

                predicate=(
                    "favorite:"
                    +
                    _norm(
                        match.group(
                            "category"
                        )
                    )
                ),

                value=(
                    match.group(
                        "value"
                    )
                ),

                scope="stable",

                source_user_id=(
                    user_id
                ),

                source_name=(
                    username
                ),

                source_type=(
                    "third_party"
                ),

                authority=(
                    THIRD_AUTHORITY
                ),

                confidence="low",

                raw_text=(
                    text
                ),

                timestamp=(
                    timestamp
                )
            )

            if claim:

                claims.append(
                    claim
                )

        third_opinion_mapping = {

            "mag":
                "like",

            "liebt":
                "love",

            "feiert":
                "like",

            "hasst":
                "hate",

            "verabscheut":
                "hate",
        }

        third_opinion_pattern = re.compile(

            r"\bhanae\s+"
            r"(?P<verb>"
            r"mag|liebt|feiert|"
            r"hasst|verabscheut"
            r")"
            r"\s+"
            r"(?P<item>"
            r"[^.!?\n]{1,100}"
            r")",

            flags=re.IGNORECASE
        )

        for match in (
            third_opinion_pattern.finditer(
                text
            )
        ):

            item = (
                _value(
                    match.group(
                        "item"
                    )
                )
            )

            verb = (
                match.group(
                    "verb"
                )
                .lower()
            )

            claim = register_claim(

                channel_id=(
                    channel_id
                ),

                subject_id=(
                    hanae_user_id
                ),

                subject_name="Hanae",

                predicate=(
                    _opinion_predicate(
                        item
                    )
                ),

                value=(
                    third_opinion_mapping[
                        verb
                    ]
                ),

                scope="stable",

                source_user_id=(
                    user_id
                ),

                source_name=(
                    username
                ),

                source_type=(
                    "third_party"
                ),

                authority=(
                    THIRD_AUTHORITY
                ),

                confidence="low",

                raw_text=(
                    text
                ),

                timestamp=(
                    timestamp
                )
            )

            if claim:

                claims.append(
                    claim
                )

    return claims


# =========================================================
# RESOLVE QUERY
# =========================================================

def resolve_world_query(
    *,
    channel_id: Any,
    user_text: str,
    hanae_user_id: Any
) -> WorldEvidence:

    text = (
        _canonical(
            user_text,
            hanae_user_id
        )
    )

    if (
        "hanae"
        not in text.lower()
    ):

        return WorldEvidence(
            reason=(
                "no_supported_subject"
            )
        )

    predicate = None

    # -----------------------------------------------------
    # Lieblings...
    # -----------------------------------------------------

    favorite_match = re.search(

        r"lieblings[\s_-]*"
        r"(?P<category>"
        r"[A-Za-zÄÖÜäöüß]{2,30}"
        r")",

        text,

        flags=re.IGNORECASE
    )

    if favorite_match:

        predicate = (
            "favorite:"
            +
            _norm(
                favorite_match.group(
                    "category"
                )
            )
        )

    # -----------------------------------------------------
    # Wo ist Hanae?
    # -----------------------------------------------------

    elif re.search(
        r"\bwo\s+ist\s+hanae\b",
        text,
        flags=re.IGNORECASE
    ):

        predicate = (
            "current_location"
        )

    # -----------------------------------------------------
    # Was macht Hanae?
    # -----------------------------------------------------

    elif re.search(
        r"\bwas\s+macht\s+hanae\b",
        text,
        flags=re.IGNORECASE
    ):

        predicate = (
            "current_activity"
        )

    # -----------------------------------------------------
    # Mag / liebt / hasst Hanae X?
    # -----------------------------------------------------

    else:

        opinion_match = re.search(

            r"\b(?:mag|liebt|hasst)"
            r"\s+hanae\s+"
            r"(?P<item>"
            r"[^.!?\n]{1,100}"
            r")",

            text,

            flags=re.IGNORECASE
        )

        if opinion_match:

            predicate = (
                _opinion_predicate(
                    _value(
                        opinion_match.group(
                            "item"
                        )
                    )
                )
            )

    if not predicate:

        return WorldEvidence(

            subject_name="Hanae",

            reason=(
                "unsupported_query_type"
            )
        )

    selected = (
        effective_claim(
            channel_id,
            hanae_user_id,
            predicate
        )
    )

    if selected is None:

        return WorldEvidence(

            matched=True,

            subject_name="Hanae",

            predicate=(
                predicate
            ),

            reason="no_claim"
        )

    competing = (
        competing_claims(
            channel_id,
            hanae_user_id,
            predicate,
            selected
        )
    )

    authoritative = (

        selected.source_type
        ==
        "self_report"

        and

        selected.authority
        >=
        SELF_AUTHORITY
    )

    return WorldEvidence(

        matched=True,

        subject_name="Hanae",

        predicate=(
            predicate
        ),

        selected_claim=(
            selected
        ),

        competing_claims=(
            competing
        ),

        authoritative=(
            authoritative
        ),

        reason=(

            "authoritative_self_report"

            if authoritative

            else

            "unverified_third_party_claim"
        )
    )


# =========================================================
# APPLY WORLD EVIDENCE TO BRAIN DECISION
# =========================================================

def apply_world_evidence_to_decision(
    decision,
    evidence: WorldEvidence
):

    selected = (
        evidence.selected_claim
    )

    if not evidence.matched:

        return decision

    # -----------------------------------------------------
    # Authoritative self-report.
    # -----------------------------------------------------

    if (
        selected is not None
        and
        evidence.authoritative
    ):

        decision.knowledge_available = (
            True
        )

        decision.knowledge_confidence = (
            "high"
        )

        decision.knowledge_source = (
            "conversation_world"
        )

        return decision

    # -----------------------------------------------------
    # Third-party claim alone must NOT become fact.
    #
    # But if Brain had real stable Memory,
    # we do not destroy that here.
    # -----------------------------------------------------

    if (
        selected is not None
        and
        not evidence.authoritative
        and
        getattr(
            decision,
            "knowledge_source",
            "unknown"
        )
        in {
            "current_context",
            "recent_context",
            "unknown",
            "not_applicable",
            "cohabitation_inference",
        }
    ):

        decision.knowledge_available = (
            False
        )

        decision.knowledge_confidence = (
            "low"
        )

        decision.knowledge_source = (
            "conversation_world_unverified"
        )

    return decision


# =========================================================
# CLAIM FORMAT
# =========================================================

def _format_claim(
    claim: WorldClaim
) -> str:

    return (

        f"{claim.subject_name} | "
        f"{claim.predicate}="
        f"{claim.value!r} | "
        f"source={claim.source_name} | "
        f"type={claim.source_type} | "
        f"authority={claim.authority} | "
        f"scope={claim.scope}"
    )


# =========================================================
# WORLD -> BRAIN
# =========================================================

def format_world_for_brain(
    channel_id: Any,
    limit: int = 12
) -> str:

    with _lock:

        world = {

            key:
                list(
                    value
                )

            for (
                key,
                value
            )
            in _worlds.get(
                str(
                    channel_id
                ),
                {}
            ).items()
        }

    effective = []

    conflicts = []

    for key in world:

        try:

            (
                subject_id,
                predicate
            ) = key.split(
                "|",
                1
            )

        except ValueError:

            continue

        selected = (
            effective_claim(
                channel_id,
                subject_id,
                predicate
            )
        )

        if not selected:

            continue

        effective.append(
            selected
        )

        lower_claims = (
            competing_claims(
                channel_id,
                subject_id,
                predicate,
                selected
            )
        )

        if lower_claims:

            conflicts.append(
                (
                    selected,
                    lower_claims[:2]
                )
            )

    effective.sort(

        key=lambda claim:
            (
                claim.authority,
                claim.timestamp
            ),

        reverse=True
    )

    lines = [

        "[CONVERSATION WORLD]",

        "STRICT SOURCE AUTHORITY:",

        (
            "- SELF_REPORT: "
            "a person's own statement about "
            "their preference/current state "
            "is authoritative."
        ),

        (
            "- THIRD_PARTY: "
            "someone else's claim about that "
            "person is unverified, not truth."
        ),

        (
            "- A later SELF_REPORT overrides "
            "lower-authority claims and speculation."
        ),

        (
            "- Do not turn trolling or repeated "
            "third-party claims into facts."
        ),
    ]

    if not effective:

        lines.append(
            "No structured claims yet."
        )

    else:

        lines.append(
            "Effective claims:"
        )

        for claim in effective[
            :limit
        ]:

            if (
                claim.source_type
                ==
                "self_report"
            ):

                label = (
                    "AUTHORITATIVE"
                )

            else:

                label = (
                    "UNVERIFIED"
                )

            lines.append(
                f"- {label}: "
                f"{_format_claim(claim)}"
            )

    if conflicts:

        lines.append(
            "Conflicts:"
        )

        for (
            selected,
            lower_claims
        ) in conflicts[:6]:

            for lower_claim in (
                lower_claims
            ):

                lines.append(

                    "- EFFECTIVE "
                    f"{_format_claim(selected)} "
                    "OVERRULES "
                    f"{_format_claim(lower_claim)}"
                )

    return "\n".join(
        lines
    )


# =========================================================
# WORLD -> WRITER
# =========================================================

def format_world_evidence_for_writer(
    evidence: WorldEvidence
) -> str:

    selected = (
        evidence.selected_claim
    )

    if not evidence.matched:

        return (
            "[WORLD EVIDENCE]\n"
            "No structured query evidence."
        )

    if selected is None:

        return f"""
[WORLD EVIDENCE]

Subject:
{evidence.subject_name}

Predicate:
{evidence.predicate}

No matching claim exists.

Do not invent the answer.
""".strip()

    if evidence.authoritative:

        return f"""
[AUTHORITATIVE WORLD EVIDENCE]

Subject:
{selected.subject_name}

Predicate:
{selected.predicate}

Value:
{selected.value}

Source:
{selected.source_name}

Source type:
SELF_REPORT

Confidence:
HIGH

This person's own statement outranks
third-party claims and speculation.

If this fact is relevant,
use the self-report as the source of truth.

Do not hedge as if it were a guess.
""".strip()

    return f"""
[UNVERIFIED WORLD CLAIM]

Subject:
{selected.subject_name}

Predicate:
{selected.predicate}

Claimed value:
{selected.value}

Claim source:
{selected.source_name}

Source type:
THIRD_PARTY

This is NOT confirmed truth.

Do not present it as a fact about
{selected.subject_name}.

At most say that
{selected.source_name}
claimed it.
""".strip()


# =========================================================
# DEBUG
# =========================================================

def format_world_observation_debug(
    claims: list[WorldClaim]
) -> str:

    data = [

        (
            f"{claim.subject_name}:"
            f"{claim.predicate}="
            f"{claim.value!r}/"
            f"{claim.source_type}"
        )

        for claim
        in claims
    ]

    return (

        f"[WORLD OBSERVE] "
        f"v={WORLD_VERSION} "
        f"claims={len(claims)} "
        f"data={data}"
    )


def format_world_evidence_debug(
    evidence: WorldEvidence
) -> str:

    selected = (
        evidence.selected_claim
    )

    value = (
        repr(
            selected.value
        )
        if selected
        else
        None
    )

    source = (
        repr(
            selected.source_name
        )
        if selected
        else
        None
    )

    return (

        f"[WORLD EVIDENCE] "
        f"v={WORLD_VERSION} "
        f"matched={evidence.matched} "
        f"subject={evidence.subject_name!r} "
        f"predicate={evidence.predicate!r} "
        f"authoritative="
        f"{evidence.authoritative} "
        f"value={value} "
        f"source={source} "
        f"reason={evidence.reason}"
    )


# =========================================================
# SELF TEST
# =========================================================

class _Decision:

    def __init__(
        self,
        available=False,
        source="not_applicable",
        confidence="unknown"
    ):

        self.knowledge_available = (
            available
        )

        self.knowledge_source = (
            source
        )

        self.knowledge_confidence = (
            confidence
        )


def _self_test():

    clear_all_worlds()

    channel = (
        "test"
    )

    hanae = (
        "568096551948255242"
    )

    user = (
        "225324315824881665"
    )

    tests = []

    # -----------------------------------------------------
    # THIRD PARTY FAVORITE
    # -----------------------------------------------------

    claims = (
        observe_world_message(

            channel_id=channel,

            user_id=user,

            username="Seiichi",

            text=(
                "Hanaes Lieblingspizza "
                "ist Margherita"
            ),

            hanae_user_id=hanae,

            timestamp=100
        )
    )

    tests.append(
        (
            "third party favorite extracted",

            (
                len(claims)
                ==
                1

                and

                claims[0].source_type
                ==
                "third_party"
            )
        )
    )

    evidence = (
        resolve_world_query(

            channel_id=channel,

            user_text=(
                "Was ist Hanaes "
                "Lieblingspizza?"
            ),

            hanae_user_id=hanae
        )
    )

    tests.append(
        (
            "third party remains unverified",

            (
                evidence.matched

                and

                not evidence.authoritative

                and

                evidence.selected_claim.value
                ==
                "Margherita"
            )
        )
    )

    # -----------------------------------------------------
    # HANAE SELF REPORT OVERRIDES
    # -----------------------------------------------------

    observe_world_message(

        channel_id=channel,

        user_id=hanae,

        username="Hanae",

        text=(
            "Meine Lieblings Pizza "
            "ist Thunfisch"
        ),

        hanae_user_id=hanae,

        timestamp=200
    )

    evidence = (
        resolve_world_query(

            channel_id=channel,

            user_text=(
                "Was ist Hanae´s "
                "Lieblingspizza?"
            ),

            hanae_user_id=hanae
        )
    )

    tests.append(
        (
            "self report overrides favorite",

            (
                evidence.authoritative

                and

                evidence.selected_claim.value
                ==
                "Thunfisch"
            )
        )
    )

    tests.append(
        (
            "old favorite remains competing",

            any(

                claim.value
                ==
                "Margherita"

                for claim
                in evidence.competing_claims
            )
        )
    )

    # -----------------------------------------------------
    # MOGELBAUM
    # -----------------------------------------------------

    observe_world_message(

        channel_id=channel,

        user_id=user,

        username="Seiichi",

        text=(
            "Hanae liebt Mogelbaum"
        ),

        hanae_user_id=hanae,

        timestamp=300
    )

    evidence = (
        resolve_world_query(

            channel_id=channel,

            user_text=(
                "Mag Hanae Mogelbaum?"
            ),

            hanae_user_id=hanae
        )
    )

    tests.append(
        (
            "troll claim unverified",

            (
                not evidence.authoritative

                and

                evidence.selected_claim.value
                ==
                "love"
            )
        )
    )

    observe_world_message(

        channel_id=channel,

        user_id=hanae,

        username="Hanae",

        text=(
            "Ich hasse Mogelbaum"
        ),

        hanae_user_id=hanae,

        timestamp=400
    )

    evidence = (
        resolve_world_query(

            channel_id=channel,

            user_text=(
                "Mag Hanae Mogelbaum?"
            ),

            hanae_user_id=hanae
        )
    )

    tests.append(
        (
            "self report wins mogelbaum",

            (
                evidence.authoritative

                and

                evidence.selected_claim.value
                ==
                "hate"
            )
        )
    )

    # -----------------------------------------------------
    # DECISION AUTHORITY
    # -----------------------------------------------------

    decision = (
        _Decision()
    )

    apply_world_evidence_to_decision(
        decision,
        evidence
    )

    tests.append(
        (
            "authoritative promotes knowledge",

            (
                decision.knowledge_available

                and

                decision.knowledge_source
                ==
                "conversation_world"
            )
        )
    )

    # -----------------------------------------------------
    # THIRD PARTY MUST NOT BECOME TRUTH
    # -----------------------------------------------------

    second_channel = (
        "third"
    )

    observe_world_message(

        channel_id=second_channel,

        user_id=user,

        username="Seiichi",

        text=(
            "Hanae liebt Lakritz"
        ),

        hanae_user_id=hanae,

        timestamp=500
    )

    evidence = (
        resolve_world_query(

            channel_id=second_channel,

            user_text=(
                "Mag Hanae Lakritz?"
            ),

            hanae_user_id=hanae
        )
    )

    decision = (
        _Decision(
            available=True,
            source="current_context",
            confidence="high"
        )
    )

    apply_world_evidence_to_decision(
        decision,
        evidence
    )

    tests.append(
        (
            "third party cannot become truth",

            (
                not decision
                .knowledge_available

                and

                decision.knowledge_source
                ==
                "conversation_world_unverified"
            )
        )
    )

    # -----------------------------------------------------
    # REAL MEMORY IS NOT BLINDLY DESTROYED
    # -----------------------------------------------------

    decision = (
        _Decision(
            available=True,
            source="memory",
            confidence="high"
        )
    )

    apply_world_evidence_to_decision(
        decision,
        evidence
    )

    tests.append(
        (
            "memory not demoted by third party",

            (
                decision.knowledge_available

                and

                decision.knowledge_source
                ==
                "memory"
            )
        )
    )

    # -----------------------------------------------------
    # CURRENT LOCATION
    # -----------------------------------------------------

    now = (
        time.time()
    )

    observe_world_message(

        channel_id=channel,

        user_id=hanae,

        username="Hanae",

        text=(
            "Ich bin gerade im Wohnzimmer"
        ),

        hanae_user_id=hanae,

        timestamp=now
    )

    evidence = (
        resolve_world_query(

            channel_id=channel,

            user_text=(
                "Wo ist Hanae gerade?"
            ),

            hanae_user_id=hanae
        )
    )

    tests.append(
        (
            "current location",

            (
                evidence.authoritative

                and

                evidence.selected_claim.value
                ==
                "im Wohnzimmer"
            )
        )
    )

    # -----------------------------------------------------
    # CURRENT ACTIVITY
    # -----------------------------------------------------

    observe_world_message(

        channel_id=channel,

        user_id=hanae,

        username="Hanae",

        text=(
            "Ich spiele gerade Mario Kart"
        ),

        hanae_user_id=hanae,

        timestamp=now
    )

    evidence = (
        resolve_world_query(

            channel_id=channel,

            user_text=(
                "Was macht Hanae gerade?"
            ),

            hanae_user_id=hanae
        )
    )

    tests.append(
        (
            "current activity",

            (
                evidence.authoritative

                and

                "Mario Kart"
                in
                evidence.selected_claim.value
            )
        )
    )

    # -----------------------------------------------------
    # UNSUPPORTED QUERY
    # -----------------------------------------------------

    evidence = (
        resolve_world_query(

            channel_id=channel,

            user_text=(
                "Ist Hanae lustig?"
            ),

            hanae_user_id=hanae
        )
    )

    tests.append(
        (
            "unsupported query stays unsupported",

            (
                not evidence.matched

                and

                evidence.reason
                ==
                "unsupported_query_type"
            )
        )
    )

    # -----------------------------------------------------
    # BRAIN FORMAT
    # -----------------------------------------------------

    world_text = (
        format_world_for_brain(
            channel
        )
    )

    tests.append(
        (
            "brain authority guidance",

            (
                "STRICT SOURCE AUTHORITY"
                in world_text

                and

                "SELF_REPORT"
                in world_text
            )
        )
    )

    # -----------------------------------------------------
    # WRITER FORMAT
    # -----------------------------------------------------

    evidence = (
        resolve_world_query(

            channel_id=channel,

            user_text=(
                "Was ist Hanaes "
                "Lieblingspizza?"
            ),

            hanae_user_id=hanae
        )
    )

    writer_text = (
        format_world_evidence_for_writer(
            evidence
        )
    )

    tests.append(
        (
            "writer gets self report",

            (
                "Thunfisch"
                in writer_text

                and

                "SELF_REPORT"
                in writer_text
            )
        )
    )

    passed = 0

    print("")
    print(
        "============================================"
    )
    print(
        f"CONVERSATION WORLD "
        f"v{WORLD_VERSION} TEST"
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

            status = (
                "PASS"
            )

            passed += 1

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