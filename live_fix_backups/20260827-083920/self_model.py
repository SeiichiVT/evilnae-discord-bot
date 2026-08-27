import json
import re
import threading
import time
import unicodedata

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Optional

from character_foundation import (
    foundation_violation_reasons,
    get_foundation_entry,
    resolve_foundation_self_query,
)


# =========================================================
# VERSION
# =========================================================

SELF_MODEL_VERSION = "2.0-character-foundation"


# =========================================================
# STORAGE
# =========================================================

SELF_MODEL_PATH = Path(
    "evilnae_self_model.json"
)


# =========================================================
# DATA
# =========================================================

@dataclass
class SelfFact:

    key: str

    value: str

    category: str

    source: str

    confidence: str

    stability: str

    updated_at: float = 0.0


@dataclass
class SelfEvidence:

    matched: bool = False

    query_type: str = "none"

    key: Optional[str] = None

    known: bool = False

    strict_unknown: bool = False

    specificity_guard: bool = False

    fact: Optional[SelfFact] = None

    reason: str = "no_self_query"


# =========================================================
# CORE SELF SEEDS
#
# Diese Facts gehören zu Evilnaes festem Charakter.
#
# WICHTIG:
#
# Keine spezifischen Games.
# Keine erfundenen Gaming-Erfahrungen.
# Keine zufälligen Lieblingsessen.
# Keine spontanen "ich hab X erlebt"-Facts.
# =========================================================

SEED_FACTS = (

    SelfFact(
        key="identity:name",
        value="Evilnae",
        category="identity",
        source="foundation_fallback",
        confidence="high",
        stability="fixed",
    ),
)


# =========================================================
# NORMALIZATION
# =========================================================

def _normalize(
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


# =========================================================
# SELF MODEL
# =========================================================

class SelfModel:

    def __init__(
        self,
        path: Path = SELF_MODEL_PATH
    ):

        self.path = Path(
            path
        )

        self._lock = (
            threading.RLock()
        )

        self._seed_facts = {

            fact.key:
                fact

            for fact
            in SEED_FACTS
        }

        self._learned_facts: dict[
            str,
            SelfFact
        ] = {}

        self.load()

    # =====================================================
    # LOAD
    # =====================================================

    def load(
        self
    ):

        with self._lock:

            self._learned_facts = {}

            if not self.path.exists():

                return

            try:

                data = json.loads(

                    self.path.read_text(
                        encoding="utf-8"
                    )
                )

            except Exception as error:

                print(
                    "[SELF MODEL LOAD ERROR] "
                    f"{type(error).__name__}: "
                    f"{error}"
                )

                return

            facts = data.get(
                "facts",
                []
            )

            if not isinstance(
                facts,
                list
            ):

                return

            for raw in facts:

                if not isinstance(
                    raw,
                    dict
                ):

                    continue

                key = str(
                    raw.get(
                        "key",
                        ""
                    )
                ).strip()

                value = str(
                    raw.get(
                        "value",
                        ""
                    )
                ).strip()

                if not (
                    key
                    and
                    value
                ):

                    continue

                # -----------------------------------------
                # Fixed Core Facts können niemals
                # durch Learned State überschrieben werden.
                # -----------------------------------------

                seed = (
                    self._seed_facts
                    .get(
                        key
                    )
                )

                if (
                    seed is not None
                    and
                    seed.stability
                    ==
                    "fixed"
                ):

                    continue

                try:

                    updated_at = float(
                        raw.get(
                            "updated_at",
                            0.0
                        )
                        or
                        0.0
                    )

                except (
                    TypeError,
                    ValueError
                ):

                    updated_at = 0.0

                self._learned_facts[
                    key
                ] = SelfFact(

                    key=key,

                    value=value,

                    category=str(
                        raw.get(
                            "category",
                            "learned"
                        )
                    )[:80],

                    source=str(
                        raw.get(
                            "source",
                            "learned"
                        )
                    )[:80],

                    confidence=str(
                        raw.get(
                            "confidence",
                            "medium"
                        )
                    )[:30],

                    stability=str(
                        raw.get(
                            "stability",
                            "stable"
                        )
                    )[:30],

                    updated_at=(
                        updated_at
                    )
                )

    # =====================================================
    # SAVE
    # =====================================================

    def save(
        self
    ):

        with self._lock:

            payload = {

                "version":
                    SELF_MODEL_VERSION,

                "facts":
                    [

                        asdict(
                            fact
                        )

                        for fact
                        in self._learned_facts
                        .values()
                    ]
            }

            temp_path = Path(

                str(
                    self.path
                )
                +
                ".tmp"
            )

            temp_path.write_text(

                json.dumps(
                    payload,
                    ensure_ascii=False,
                    indent=2
                ),

                encoding="utf-8"
            )

            temp_path.replace(
                self.path
            )

    # =====================================================
    # EFFECTIVE FACTS
    # =====================================================

    def effective_facts(
        self
    ) -> dict[str, SelfFact]:

        with self._lock:

            facts = dict(
                self._seed_facts
            )

            for (
                key,
                fact
            ) in (
                self._learned_facts
                .items()
            ):

                seed = (
                    self._seed_facts
                    .get(
                        key
                    )
                )

                if (
                    seed is not None
                    and
                    seed.stability
                    ==
                    "fixed"
                ):

                    continue

                facts[
                    key
                ] = fact

            return facts

    # =====================================================
    # GET
    # =====================================================

    def get(
        self,
        key: str
    ) -> Optional[SelfFact]:

        return (

            self.effective_facts()
            .get(
                key
            )
        )

    # =====================================================
    # LEARNED COUNT
    # =====================================================

    def learned_count(
        self
    ) -> int:

        with self._lock:

            return len(
                self._learned_facts
            )

    # =====================================================
    # REGISTER FUTURE LEARNED FACT
    #
    # Diese Funktion wird JETZT noch nicht automatisch
    # vom Bot benutzt.
    #
    # Später dürfen Episodes / Reflection hier bewusst
    # bestätigte Self Facts ablegen.
    # =====================================================

    def register_fact(
        self,
        *,
        key: str,
        value: str,
        category: str = "learned",
        source: str = "episode_learning",
        confidence: str = "medium",
        stability: str = "stable",
        persist: bool = True
    ) -> bool:

        key = str(
            key
            or ""
        ).strip()

        value = str(
            value
            or ""
        ).strip()

        if not (
            key
            and
            value
        ):

            return False

        seed = (
            self._seed_facts
            .get(
                key
            )
        )

        if (
            seed is not None
            and
            seed.stability
            ==
            "fixed"
        ):

            return False

        with self._lock:

            self._learned_facts[
                key
            ] = SelfFact(

                key=key,

                value=value,

                category=category,

                source=source,

                confidence=confidence,

                stability=stability,

                updated_at=time.time()
            )

            if persist:

                self.save()

        return True


# =========================================================
# GLOBAL MODEL
# =========================================================

evilnae_self_model = (
    SelfModel()
)


# =========================================================
# PUBLIC HELPERS
# =========================================================

def get_self_fact(
    key: str
) -> Optional[SelfFact]:

    return (
        evilnae_self_model.get(
            key
        )
    )


def register_learned_self_fact(
    *,
    key: str,
    value: str,
    category: str = "learned",
    source: str = "episode_learning",
    confidence: str = "medium",
    stability: str = "stable"
) -> bool:

    return (

        evilnae_self_model
        .register_fact(

            key=key,

            value=value,

            category=category,

            source=source,

            confidence=confidence,

            stability=stability,

            persist=True
        )
    )


# =========================================================
# FIND KNOWN GAME EXPERIENCE
# =========================================================

def _find_game_experience(
    text: str
) -> Optional[SelfFact]:

    normalized_text = (
        _normalize(
            text
        )
    )

    facts = (
        evilnae_self_model
        .effective_facts()
    )

    for (
        key,
        fact
    ) in facts.items():

        if not key.startswith(
            "experience:game:"
        ):

            continue

        value_key = (
            _normalize(
                fact.value
            )
        )

        if (
            value_key
            and
            value_key
            in normalized_text
        ):

            return fact

        slug = key.split(
            "experience:game:",
            1
        )[1]

        if (
            slug
            and
            slug
            in normalized_text
        ):

            return fact

    return None


# =========================================================
# RESOLVE SELF QUERY
# =========================================================

def resolve_self_query(
    user_text: str
) -> SelfEvidence:

    text = str(
        user_text
        or ""
    )

    lowered = (
        text.lower()
    )

    normalized = (
        _normalize(
            text
        )
    )

    # =====================================================
    # CHARACTER FOUNDATION FIRST
    #
    # Die Excel ist die höchste Character-Autorität.
    # Legacy Self Model läuft nur als Fallback, wenn die
    # Foundation für diese Self-Frage keinen Treffer hat.
    # =====================================================

    foundation_hit = (
        resolve_foundation_self_query(
            text
        )
    )

    if foundation_hit is not None:

        foundation_fact = SelfFact(
            key=f"foundation:{foundation_hit.nr}",
            value=foundation_hit.answer,
            category=foundation_hit.area or "foundation",
            source="excel_character_foundation",
            confidence="high",
            stability="fixed",
        )

        return SelfEvidence(
            matched=True,
            query_type="foundation",
            key=foundation_fact.key,
            known=True,
            strict_unknown=False,
            specificity_guard=False,
            fact=foundation_fact,
            reason=f"foundation_row_{foundation_hit.nr}",
        )

    # =====================================================
    # FAVORITES
    #
    # Was ist deine Lieblingspizza?
    # Was ist dein Lieblingsspiel?
    # =====================================================

    favorite_map = {

        "pizza":
            "favorite:pizza",

        "essen":
            "favorite:food",

        "food":
            "favorite:food",

        "spiel":
            "favorite:game",

        "game":
            "favorite:game",
    }

    favorite_match = re.search(

        r"\b(?:dein|deine)\s+"
        r"lieblings[\s_-]*"
        r"(?P<kind>"
        r"pizza|essen|food|spiel|game"
        r")\b",

        lowered,

        flags=re.IGNORECASE
    )

    if (
        favorite_match is None
        and
        re.search(
            r"\blieblingspizza\b",
            lowered,
            flags=re.IGNORECASE
        )
        and
        re.search(
            r"\b(?:du|dein|deine)\b",
            lowered,
            flags=re.IGNORECASE
        )
    ):

        favorite_kind = (
            "pizza"
        )

    elif favorite_match:

        favorite_kind = (
            favorite_match
            .group(
                "kind"
            )
            .lower()
        )

    else:

        favorite_kind = None

    if favorite_kind:

        key = (
            favorite_map[
                favorite_kind
            ]
        )

        fact = (
            get_self_fact(
                key
            )
        )

        return SelfEvidence(

            matched=True,

            query_type="favorite",

            key=key,

            known=(
                fact is not None
            ),

            strict_unknown=(
                fact is None
            ),

            specificity_guard=False,

            fact=fact,

            reason=(
                "known_favorite"
                if fact
                else
                "favorite_not_established"
            )
        )

    # =====================================================
    # GAMING EXPERIENCE
    #
    # Hast du Elden Ring gespielt?
    # Hast du den Boss besiegt?
    # Hast du das durchgespielt?
    # =====================================================

    game_experience = re.search(

        r"\bhast\s+du\b"
        r"[^?]{0,220}"
        r"\b(?:"
        r"gespielt|"
        r"gezockt|"
        r"durchgespielt|"
        r"besiegt|"
        r"gelegt|"
        r"geschafft"
        r")\b",

        lowered,

        flags=re.IGNORECASE
    )

    if game_experience:

        fact = (
            _find_game_experience(
                text
            )
        )

        return SelfEvidence(

            matched=True,

            query_type=(
                "game_experience"
            ),

            key=(
                fact.key
                if fact
                else
                "experience:game:unknown"
            ),

            known=(
                fact is not None
            ),

            strict_unknown=(
                fact is None
            ),

            specificity_guard=False,

            fact=fact,

            reason=(
                "known_game_experience"
                if fact
                else
                "game_experience_not_established"
            )
        )

    # =====================================================
    # GENERAL GAMING
    #
    # Was zockst du so?
    #
    # Known:
    # Gaming allgemein.
    #
    # Unknown:
    # konkrete Titel / Gewohnheiten.
    # =====================================================

    general_gaming = (

        re.search(
            r"\b(?:zockst|spielst)\s+du\b",
            lowered,
            flags=re.IGNORECASE
        )
        is not None

        or

        re.search(
            r"\bwas\s+zockst\s+du\b",
            lowered,
            flags=re.IGNORECASE
        )
        is not None
    )

    if general_gaming:

        fact = (
            get_self_fact(
                "interest:gaming"
            )
        )

        return SelfEvidence(

            matched=True,

            query_type=(
                "gaming_general"
            ),

            key="interest:gaming",

            known=(
                fact is not None
            ),

            strict_unknown=False,

            # Gaming allgemein ist bekannt.
            #
            # Konkrete Games sind es nicht.
            specificity_guard=True,

            fact=fact,

            reason=(
                "broad_gaming_interest_only"
            )
        )

    # =====================================================
    # BROAD INTERESTS
    # =====================================================

    direct_interest_map = {

        "gaming":
            "interest:gaming",

        "games":
            "interest:gaming",

        "zocken":
            "interest:gaming",

        "anime":
            "interest:anime",

        "filme":
            "interest:movies_series",

        "serien":
            "interest:movies_series",

        "tiere":
            "interest:animals",

        "schlangen":
            "interest:creepy_animals",

        "spinnen":
            "interest:creepy_animals",
    }

    if (
        "magst_du"
        in normalized
        or
        "interessierst_du_dich"
        in normalized
    ):

        for (
            token,
            key
        ) in direct_interest_map.items():

            if (
                _normalize(
                    token
                )
                in normalized
            ):

                fact = (
                    get_self_fact(
                        key
                    )
                )

                return SelfEvidence(

                    matched=True,

                    query_type=(
                        "known_interest"
                    ),

                    key=key,

                    known=(
                        fact is not None
                    ),

                    strict_unknown=(
                        fact is None
                    ),

                    specificity_guard=False,

                    fact=fact,

                    reason=(
                        "seed_interest"
                        if fact
                        else
                        "interest_not_established"
                    )
                )

    return SelfEvidence()


# =========================================================
# APPLY SELF EVIDENCE TO BRAIN
# =========================================================

def apply_self_evidence_to_decision(
    decision,
    evidence: SelfEvidence
):

    if not evidence.matched:

        return decision

    # -----------------------------------------------------
    # Authoritative Self Fact
    # -----------------------------------------------------

    if (
        evidence.known
        and
        evidence.fact is not None
    ):

        decision.knowledge_available = (
            True
        )

        decision.knowledge_confidence = (

            evidence.fact.confidence

            if evidence.fact.confidence
            in {
                "high",
                "medium",
                "low",
            }

            else
            "high"
        )

        decision.knowledge_source = (
            "self_model"
        )

        return decision

    # -----------------------------------------------------
    # STRICT UNKNOWN
    #
    # Besonders wichtig:
    #
    # recent_context darf nicht plötzlich beweisen,
    # dass Evilnae etwas selbst erlebt hat.
    # -----------------------------------------------------

    if evidence.strict_unknown:

        decision.knowledge_available = (
            False
        )

        decision.knowledge_confidence = (
            "unknown"
        )

        decision.knowledge_source = (
            "self_model_unknown"
        )

    return decision


# =========================================================
# SELF MODEL -> BRAIN
# =========================================================

def format_self_model_for_brain() -> str:

    facts = (
        evilnae_self_model
        .effective_facts()
    )

    lines = [

        (
            "[EVILNAE SELF MODEL "
            f"v{SELF_MODEL_VERSION}]"
        ),

        (
            "Diese Fakten beschreiben "
            "Evilnae selbst."
        ),

        (
            "SELF MODEL hat höhere Autorität "
            "als spontane Writer-Erfindungen."
        ),

        (
            "Wenn eine konkrete eigene Erfahrung "
            "oder ein Favorit NICHT hier steht, "
            "darf er nicht einfach erfunden werden."
        ),

        (
            "Breites Interesse an Gaming bedeutet "
            "NICHT automatisch, dass Evilnae "
            "bestimmte Spiele gespielt hat."
        ),

        (
            "Keine spezifischen Games, Boss-Kills "
            "oder Lieblingsspiele annehmen, "
            "wenn sie nicht explizit gelistet sind."
        ),

        "Bekannte Self Facts:",
    ]

    for fact in (
        facts.values()
    ):

        lines.append(

            "- "
            f"{fact.key} = "
            f"{fact.value} "
            f"[source={fact.source}, "
            f"confidence={fact.confidence}]"
        )

    experiences = [

        fact

        for (
            key,
            fact
        ) in facts.items()

        if key.startswith(
            "experience:"
        )
    ]

    if not experiences:

        lines.append(
            "- Spezifische eigene Erfahrungen: "
            "keine etabliert."
        )

    return "\n".join(
        lines
    )


# =========================================================
# SELF EVIDENCE -> WRITER
# =========================================================

def format_self_evidence_for_writer(
    evidence: SelfEvidence
) -> str:

    if not evidence.matched:

        return (
            "[SELF KNOWLEDGE]\n"
            "Keine spezielle Self-Knowledge-Regel."
        )

    # =====================================================
    # KNOWN
    # =====================================================

    if (
        evidence.known
        and
        evidence.fact is not None
    ):

        if (
            evidence.query_type
            ==
            "gaming_general"
        ):

            return f"""
[SELF KNOWLEDGE]

Bekannter Fakt:

{evidence.fact.value}

WICHTIG:

Evilnae mag Gaming allgemein.

Es sind aber KEINE konkreten
Game-Titel als ihre üblichen Spiele
oder eigenen Spielerfahrungen etabliert.

Deshalb darfst du sagen:

- dass sie generell gern zockt
- dass Gaming zu ihren Interessen gehört
- dass sie keinen festen Go-To nennen muss

Aber NICHT spontan konkrete Spiele
wie persönliche Gewohnheiten aufzählen.

Keine erfundenen:

- "ich spiele meistens X"
- "ich hab X durchgespielt"
- "mein Go-To ist X"
""".strip()

        return f"""
[AUTHORITATIVE SELF KNOWLEDGE]

Key:
{evidence.fact.key}

Value:
{evidence.fact.value}

Source:
{evidence.fact.source}

Confidence:
{evidence.fact.confidence}

Das ist ein etablierter Fakt
über Evilnae selbst.

Nutze ihn konsistent.
""".strip()

    # =====================================================
    # UNKNOWN GAME EXPERIENCE
    # =====================================================

    if (
        evidence.query_type
        ==
        "game_experience"
    ):

        return """
[SELF KNOWLEDGE GUARD]

Die Frage betrifft Evilnaes
eigene Gaming-Erfahrung.

Dafür existiert aktuell
KEIN etablierter Self-Fact.

STRICT:

Nicht behaupten, dass Evilnae:

- das Spiel gespielt hat
- es nie gespielt hat
- einen Boss besiegt hat
- etwas durchgespielt hat
- einen bestimmten Run erlebt hat

Recent Conversation ist dafür
KEIN Beweis.

Natürlich reagieren, z.B.:

- "dazu hab ich grad keine klare Erinnerung"
- "weiß ich bei mir tatsächlich nicht sicher"
- "hab ich grad nicht im Kopf"

Keine neue Vergangenheit erfinden.
""".strip()

    # =====================================================
    # UNKNOWN FAVORITE
    # =====================================================

    if (
        evidence.query_type
        ==
        "favorite"
    ):

        return """
[SELF KNOWLEDGE GUARD]

Die Frage betrifft einen
persönlichen Favoriten von Evilnae.

Dafür existiert aktuell
KEIN etablierter Self-Fact.

STRICT:

Keinen konkreten Favoriten erfinden.

Natürlich möglich:

- "hab da keine feste"
- "hab tatsächlich keinen festen Favoriten"
- "wechselt bei mir eher"

Nicht spontan einen Titel,
ein Essen oder eine Pizza
als festen Favoriten festlegen.
""".strip()

    # =====================================================
    # OTHER UNKNOWN SELF FACT
    # =====================================================

    return """
[SELF KNOWLEDGE GUARD]

Die angefragte Eigenschaft
ist aktuell nicht als Self-Fact etabliert.

Nicht als sichere persönliche Tatsache
über Evilnae erfinden.
""".strip()


# =========================================================
# UNCERTAINTY
# =========================================================

UNCERTAINTY_PATTERNS = [

    re.compile(
        r"\bkeine ahnung\b",
        flags=re.IGNORECASE
    ),

    re.compile(
        r"\bkp\b",
        flags=re.IGNORECASE
    ),

    re.compile(
        r"\bweiß ich\b.{0,30}\bnicht\b",
        flags=re.IGNORECASE
    ),

    re.compile(
        r"\bweiss ich\b.{0,30}\bnicht\b",
        flags=re.IGNORECASE
    ),

    re.compile(
        r"\bnicht sicher\b",
        flags=re.IGNORECASE
    ),

    re.compile(
        r"\bsoweit ich "
        r"(?:weiß|weiss)\b"
        r".{0,30}"
        r"\bnicht\b",
        flags=re.IGNORECASE
    ),

    re.compile(
        r"\bkeine "
        r"(?:klare |eigene )?"
        r"erinnerung\b",
        flags=re.IGNORECASE
    ),

    re.compile(
        r"\bhab ich\b"
        r".{0,30}"
        r"\bnicht im kopf\b",
        flags=re.IGNORECASE
    ),

    re.compile(
        r"\bkeinen festen\b",
        flags=re.IGNORECASE
    ),

    re.compile(
        r"\bkeine feste\b",
        flags=re.IGNORECASE
    ),

    re.compile(
        r"\bkein fester\b",
        flags=re.IGNORECASE
    ),

    re.compile(
        r"\bkeine "
        r"(?:richtige|wirkliche) "
        r"lieblings"
        r"(?:pizza|essen|spiel)\b",
        flags=re.IGNORECASE
    ),

    re.compile(
        r"\bkeine lieblings"
        r"(?:pizza|essen|spiel)\b",
        flags=re.IGNORECASE
    ),

    re.compile(
        r"\bwechselt bei mir\b",
        flags=re.IGNORECASE
    ),
]


# =========================================================
# SELF EXPERIENCE ASSERTIONS
# =========================================================

SELF_EXPERIENCE_ASSERTION_PATTERNS = [

    re.compile(

        r"\b(?:ich\s+)?"
        r"hab(?:e)?\s+"
        r"[^.!?\n]{0,80}"
        r"\b(?:"
        r"gespielt|"
        r"gezockt|"
        r"durchgespielt|"
        r"besiegt|"
        r"gelegt|"
        r"geschafft"
        r")\b",

        flags=re.IGNORECASE
    ),

    re.compile(

        r"\bhab\s+ich\s+"
        r"[^.!?\n]{0,80}"
        r"\b(?:"
        r"gespielt|"
        r"gezockt|"
        r"durchgespielt|"
        r"besiegt|"
        r"gelegt|"
        r"geschafft"
        r")\b",

        flags=re.IGNORECASE
    ),

    re.compile(

        r"\bich\s+"
        r"(?:kenne|spielte|zockte)\s+"
        r"[^.!?\n]{2,80}",

        flags=re.IGNORECASE
    ),
]


# =========================================================
# SPECIFIC GAME CLAIMS
# =========================================================

SPECIFIC_GAME_EXAMPLE_PATTERN = re.compile(

    r"\b(?:"
    r"zocke|zock|spiele|spiel"
    r")\b"
    r"[^.!?\n]{0,100}"
    r"\b(?:"
    r"wie|"
    r"zum beispiel|"
    r"beispielsweise|"
    r"z\.?\s*b\.?"
    r")\b",

    flags=re.IGNORECASE
)


HABITUAL_SPECIFIC_GAME_PATTERN = re.compile(

    r"\b(?:"
    r"meist|"
    r"meistens|"
    r"normalerweise"
    r")\s+"
    r"(?:so\s+)?"
    r"(?!(?:"
    r"einfach|"
    r"generell|"
    r"irgendwas|"
    r"eher|"
    r"nur|"
    r"ein"
    r")\b)"
    r"[A-Za-zÄÖÜäöüß0-9]"
    r"[^,.!?\n]{2,50}",

    flags=re.IGNORECASE
)


TITLE_SEQUENCE_PATTERN = re.compile(

    r"\b"
    r"[A-ZÄÖÜ]"
    r"[A-Za-zÄÖÜäöüß0-9'’:-]+"
    r"(?:\s+"
    r"[A-ZÄÖÜ]"
    r"[A-Za-zÄÖÜäöüß0-9'’:-]+"
    r")+"
    r"\b"
)


# =========================================================
# FAVORITE ASSERTION
# =========================================================

FAVORITE_ASSERTION_PATTERN = re.compile(

    r"\b(?:"
    r"mein|meine"
    r")\s+"
    r"lieblings"
    r"[\s_-]*"
    r"(?:"
    r"pizza|"
    r"essen|"
    r"food|"
    r"spiel|"
    r"game"
    r")\b",

    flags=re.IGNORECASE
)


# =========================================================
# HAS UNCERTAINTY
# =========================================================

def _has_uncertainty(
    answer: str
) -> bool:

    return any(

        pattern.search(
            answer
            or ""
        )

        for pattern
        in UNCERTAINTY_PATTERNS
    )


# =========================================================
# SELF KNOWLEDGE VIOLATIONS
# =========================================================

def self_knowledge_violation_reasons(
    answer: str,
    evidence: SelfEvidence
) -> list[str]:

    if not evidence.matched:

        return []

    answer = str(
        answer
        or ""
    ).strip()

    if not answer:

        return [
            "empty_self_answer"
        ]

    reasons = []

    # =====================================================
    # CHARACTER FOUNDATION CONTRADICTION GUARD
    # =====================================================

    if (
        evidence.query_type
        ==
        "foundation"
        and
        evidence.key
        and
        str(evidence.key).startswith("foundation:")
    ):

        try:
            foundation_nr = int(
                str(evidence.key).split(":", 1)[1]
            )
        except (TypeError, ValueError, IndexError):
            foundation_nr = 0

        foundation_hit = (
            get_foundation_entry(
                foundation_nr
            )
            if foundation_nr
            else None
        )

        return foundation_violation_reasons(
            answer,
            foundation_hit
        )

    # =====================================================
    # GENERAL GAMING
    #
    # Broad gaming interest does not authorize
    # random specific titles.
    # =====================================================

    if (
        evidence.query_type
        ==
        "gaming_general"
        and
        evidence.specificity_guard
    ):

        if (
            SPECIFIC_GAME_EXAMPLE_PATTERN
            .search(
                answer
            )
        ):

            reasons.append(
                "unsupported_specific_game_preference"
            )

        if (
            HABITUAL_SPECIFIC_GAME_PATTERN
            .search(
                answer
            )
        ):

            reasons.append(
                "unsupported_specific_game_habit"
            )

        title_sequences = [

            match.group(
                0
            )

            for match
            in TITLE_SEQUENCE_PATTERN
            .finditer(
                answer
            )

            if (
                match.group(
                    0
                ).lower()
                not in {
                    "evilnae",
                    "hanae",
                }
            )
        ]

        if title_sequences:

            reasons.append(
                "unsupported_specific_game_title"
            )

    # =====================================================
    # STRICT UNKNOWN
    # =====================================================

    if evidence.strict_unknown:

        uncertainty = (
            _has_uncertainty(
                answer
            )
        )

        # -------------------------------------------------
        # Own experience
        # -------------------------------------------------

        if (
            evidence.query_type
            ==
            "game_experience"
        ):

            experience_assertion = any(

                pattern.search(
                    answer
                )

                for pattern
                in (
                    SELF_EXPERIENCE_ASSERTION_PATTERNS
                )
            )

            if (
                experience_assertion
                and
                not uncertainty
            ):

                reasons.append(
                    "unsupported_self_experience"
                )

        # -------------------------------------------------
        # Favorite
        # -------------------------------------------------

        if (
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

        # -------------------------------------------------
        # Unknown must stay unknown.
        # -------------------------------------------------

        if not uncertainty:

            reasons.append(
                "unknown_self_fact_not_acknowledged"
            )

    return list(
        dict.fromkeys(
            reasons
        )
    )


# =========================================================
# DEBUG
# =========================================================

def format_self_model_debug() -> str:

    return (

        "[SELF MODEL] "
        f"v={SELF_MODEL_VERSION} "
        f"seed={len(SEED_FACTS)} "
        f"learned="
        f"{evilnae_self_model.learned_count()}"
    )


def format_self_evidence_debug(
    evidence: SelfEvidence
) -> str:

    fact_value = (

        evidence.fact.value

        if evidence.fact

        else
        None
    )

    return (

        "[SELF EVIDENCE] "
        f"v={SELF_MODEL_VERSION} "
        f"matched={evidence.matched} "
        f"type={evidence.query_type} "
        f"key={evidence.key!r} "
        f"known={evidence.known} "
        f"strict_unknown="
        f"{evidence.strict_unknown} "
        f"specificity_guard="
        f"{evidence.specificity_guard} "
        f"value={fact_value!r} "
        f"reason={evidence.reason}"
    )


# =========================================================
# SELF TEST
# =========================================================

class _Decision:

    def __init__(
        self,
        *,
        available=False,
        confidence="unknown",
        source="not_applicable"
    ):

        self.knowledge_available = (
            available
        )

        self.knowledge_confidence = (
            confidence
        )

        self.knowledge_source = (
            source
        )


def _self_test():

    tests = []

    # -----------------------------------------------------
    # Seed
    # -----------------------------------------------------

    gaming = (
        get_self_fact(
            "interest:gaming"
        )
    )

    tests.append(
        (
            "gaming seed exists",

            gaming is not None
        )
    )

    experiences = [

        key

        for key
        in (
            evilnae_self_model
            .effective_facts()
        )

        if key.startswith(
            "experience:game:"
        )
    ]

    tests.append(
        (
            "no seeded game experiences",

            len(
                experiences
            )
            ==
            0
        )
    )

    # -----------------------------------------------------
    # General Gaming
    # -----------------------------------------------------

    evidence = (
        resolve_self_query(
            "Was zockst du so im Normalfall?"
        )
    )

    tests.append(
        (
            "general gaming query recognized",

            (
                evidence.matched

                and
                evidence.known

                and
                evidence.query_type
                ==
                "gaming_general"
            )
        )
    )

    tests.append(
        (
            "general gaming broad answer allowed",

            not self_knowledge_violation_reasons(

                (
                    "ich zock generell gern, "
                    "hab aber keinen festen go-to."
                ),

                evidence
            )
        )
    )

    tests.append(
        (
            "specific game list blocked",

            (
                "unsupported_specific_game_preference"

                in

                self_knowledge_violation_reasons(

                    (
                        "ich zocke oft so Sachen "
                        "wie Dark Souls oder "
                        "Stardew Valley."
                    ),

                    evidence
                )
            )
        )
    )

    # -----------------------------------------------------
    # Game Experience
    # -----------------------------------------------------

    evidence = (
        resolve_self_query(

            (
                "hast du den schon besiegt "
                "oder hast du Elden Ring "
                "nie gespielt?"
            )
        )
    )

    tests.append(
        (
            "game experience recognized unknown",

            (
                evidence.matched

                and
                evidence.query_type
                ==
                "game_experience"

                and
                evidence.strict_unknown
            )
        )
    )

    decision = (
        _Decision(

            available=True,

            confidence="high",

            source="recent_context"
        )
    )

    apply_self_evidence_to_decision(
        decision,
        evidence
    )

    tests.append(
        (
            "recent context cannot invent self experience",

            (
                not decision
                .knowledge_available

                and

                decision
                .knowledge_source
                ==
                "self_model_unknown"
            )
        )
    )

    tests.append(
        (
            "boss victory blocked",

            (
                "unsupported_self_experience"

                in

                self_knowledge_violation_reasons(

                    (
                        "ja, hab ich besiegt, "
                        "war ein harter Kampf."
                    ),

                    evidence
                )
            )
        )
    )

    tests.append(
        (
            "uncertain experience answer allowed",

            not self_knowledge_violation_reasons(

                (
                    "dazu hab ich grad "
                    "keine klare Erinnerung."
                ),

                evidence
            )
        )
    )

    # -----------------------------------------------------
    # Favorite
    # -----------------------------------------------------

    evidence = (
        resolve_self_query(
            "Was ist deine Lieblingspizza?"
        )
    )

    tests.append(
        (
            "favorite pizza unknown",

            (
                evidence.matched

                and
                evidence.query_type
                ==
                "favorite"

                and
                evidence.strict_unknown
            )
        )
    )

    tests.append(
        (
            "invented favorite blocked",

            (
                "unknown_self_fact_not_acknowledged"

                in

                self_knowledge_violation_reasons(

                    (
                        "Pizza Hawaii ist meine "
                        "Lieblingspizza."
                    ),

                    evidence
                )
            )
        )
    )

    tests.append(
        (
            "no fixed favorite allowed",

            not self_knowledge_violation_reasons(

                (
                    "hab da tatsächlich "
                    "keine feste."
                ),

                evidence
            )
        )
    )

    # -----------------------------------------------------
    # Known Interest
    # -----------------------------------------------------

    evidence = (
        resolve_self_query(
            "Magst du Anime?"
        )
    )

    tests.append(
        (
            "seed interest query known",

            (
                evidence.matched

                and
                evidence.known

                and
                evidence.key
                ==
                "interest:anime"
            )
        )
    )

    # -----------------------------------------------------
    # Brain Context
    # -----------------------------------------------------

    brain_text = (
        format_self_model_for_brain()
    )

    tests.append(
        (
            "brain text warns against game invention",

            (
                "Keine spezifischen Games"
                in brain_text

                and
                "interest:gaming"
                in brain_text
            )
        )
    )

    # -----------------------------------------------------
    # Result
    # -----------------------------------------------------

    passed = 0

    print("")
    print(
        "============================================"
    )
    print(
        f"SELF MODEL v"
        f"{SELF_MODEL_VERSION} TEST"
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