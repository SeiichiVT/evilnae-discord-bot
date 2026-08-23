import json
import os
import time
import threading
from dataclasses import dataclass, asdict


# =========================================================
# VERSION
# =========================================================

INNER_STATE_VERSION = "1.1"


# =========================================================
# STORAGE
# =========================================================

STATE_FILE = "evilnae_inner_state.json"

STATE_TEMP_FILE = (
    STATE_FILE
    + ".tmp"
)


# =========================================================
# THREAD / TASK SAFETY
#
# Mehrere Discord-Interaktionen können
# nahezu gleichzeitig stattfinden.
#
# RLock erlaubt verschachtelte interne Calls.
# =========================================================

state_lock = threading.RLock()


# =========================================================
# DEFAULT VALUES
#
# 0.0 = sehr niedrig
# 1.0 = sehr hoch
#
# valence:
# -1.0 = sehr negativ
# +1.0 = sehr positiv
# =========================================================

DEFAULT_STATE = {

    "valence": 0.20,

    "energy": 0.55,

    "irritation": 0.08,

    "social_energy": 0.65,

    "curiosity": 0.55,

    "boredom": 0.20,

    "amusement": 0.30,

    "warmth": 0.45,

    "chaos_drive": 0.35,

    "confidence": 0.75,

    "last_updated": time.time(),
}


# =========================================================
# INNER STATE DATACLASS
# =========================================================

@dataclass
class InnerState:

    valence: float = 0.20

    energy: float = 0.55

    irritation: float = 0.08

    social_energy: float = 0.65

    curiosity: float = 0.55

    boredom: float = 0.20

    amusement: float = 0.30

    warmth: float = 0.45

    chaos_drive: float = 0.35

    confidence: float = 0.75

    last_updated: float = 0.0


# =========================================================
# CLAMP HELPERS
# =========================================================

def clamp(
    value,
    minimum=0.0,
    maximum=1.0
):

    return max(
        minimum,
        min(
            maximum,
            value
        )
    )


def clamp_valence(
    value
):

    return max(
        -1.0,
        min(
            1.0,
            value
        )
    )


# =========================================================
# DEFAULT STATE
# =========================================================

def create_default_state():

    return InnerState(

        valence=DEFAULT_STATE[
            "valence"
        ],

        energy=DEFAULT_STATE[
            "energy"
        ],

        irritation=DEFAULT_STATE[
            "irritation"
        ],

        social_energy=DEFAULT_STATE[
            "social_energy"
        ],

        curiosity=DEFAULT_STATE[
            "curiosity"
        ],

        boredom=DEFAULT_STATE[
            "boredom"
        ],

        amusement=DEFAULT_STATE[
            "amusement"
        ],

        warmth=DEFAULT_STATE[
            "warmth"
        ],

        chaos_drive=DEFAULT_STATE[
            "chaos_drive"
        ],

        confidence=DEFAULT_STATE[
            "confidence"
        ],

        last_updated=time.time()
    )


# =========================================================
# LOAD
# =========================================================

def load_inner_state():

    if not os.path.exists(
        STATE_FILE
    ):

        return create_default_state()

    try:

        with open(
            STATE_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            data = json.load(
                file
            )

        return InnerState(

            valence=float(
                data.get(
                    "valence",
                    DEFAULT_STATE[
                        "valence"
                    ]
                )
            ),

            energy=float(
                data.get(
                    "energy",
                    DEFAULT_STATE[
                        "energy"
                    ]
                )
            ),

            irritation=float(
                data.get(
                    "irritation",
                    DEFAULT_STATE[
                        "irritation"
                    ]
                )
            ),

            social_energy=float(
                data.get(
                    "social_energy",
                    DEFAULT_STATE[
                        "social_energy"
                    ]
                )
            ),

            curiosity=float(
                data.get(
                    "curiosity",
                    DEFAULT_STATE[
                        "curiosity"
                    ]
                )
            ),

            boredom=float(
                data.get(
                    "boredom",
                    DEFAULT_STATE[
                        "boredom"
                    ]
                )
            ),

            amusement=float(
                data.get(
                    "amusement",
                    DEFAULT_STATE[
                        "amusement"
                    ]
                )
            ),

            warmth=float(
                data.get(
                    "warmth",
                    DEFAULT_STATE[
                        "warmth"
                    ]
                )
            ),

            chaos_drive=float(
                data.get(
                    "chaos_drive",
                    DEFAULT_STATE[
                        "chaos_drive"
                    ]
                )
            ),

            confidence=float(
                data.get(
                    "confidence",
                    DEFAULT_STATE[
                        "confidence"
                    ]
                )
            ),

            last_updated=float(
                data.get(
                    "last_updated",
                    time.time()
                )
            )
        )

    except Exception as error:

        print(
            "[INNER STATE LOAD ERROR] "
            f"{type(error).__name__}: "
            f"{error}"
        )

        return create_default_state()


# =========================================================
# RUNTIME STATE
# =========================================================

evilnae_state = (
    load_inner_state()
)


# =========================================================
# NORMALIZE
# =========================================================

def normalize_state():

    with state_lock:

        evilnae_state.valence = (
            clamp_valence(
                evilnae_state.valence
            )
        )

        evilnae_state.energy = (
            clamp(
                evilnae_state.energy
            )
        )

        evilnae_state.irritation = (
            clamp(
                evilnae_state.irritation
            )
        )

        evilnae_state.social_energy = (
            clamp(
                evilnae_state.social_energy
            )
        )

        evilnae_state.curiosity = (
            clamp(
                evilnae_state.curiosity
            )
        )

        evilnae_state.boredom = (
            clamp(
                evilnae_state.boredom
            )
        )

        evilnae_state.amusement = (
            clamp(
                evilnae_state.amusement
            )
        )

        evilnae_state.warmth = (
            clamp(
                evilnae_state.warmth
            )
        )

        evilnae_state.chaos_drive = (
            clamp(
                evilnae_state.chaos_drive
            )
        )

        evilnae_state.confidence = (
            clamp(
                evilnae_state.confidence
            )
        )


# =========================================================
# SAVE
#
# Erst Temp-Datei schreiben,
# danach atomar ersetzen.
#
# Dadurch ist ein halbes / beschädigtes JSON
# bei einem ungünstigen Shutdown unwahrscheinlicher.
# =========================================================

def save_inner_state():

    with state_lock:

        try:

            normalize_state()

            with open(
                STATE_TEMP_FILE,
                "w",
                encoding="utf-8"
            ) as file:

                json.dump(
                    asdict(
                        evilnae_state
                    ),
                    file,
                    ensure_ascii=False,
                    indent=2
                )

                file.flush()

                os.fsync(
                    file.fileno()
                )

            os.replace(
                STATE_TEMP_FILE,
                STATE_FILE
            )

        except Exception as error:

            print(
                "[INNER STATE SAVE ERROR] "
                f"{type(error).__name__}: "
                f"{error}"
            )

            try:

                if os.path.exists(
                    STATE_TEMP_FILE
                ):

                    os.remove(
                        STATE_TEMP_FILE
                    )

            except OSError:

                pass


# =========================================================
# DECAY HELPERS
# =========================================================

def move_toward(
    value,
    target,
    amount
):

    if value < target:

        return min(
            target,
            value + amount
        )

    if value > target:

        return max(
            target,
            value - amount
        )

    return value


# =========================================================
# TIME DECAY
#
# Emotionen bleiben nicht dauerhaft
# auf einem Extremwert hängen.
#
# Sie bewegen sich langsam
# Richtung Evilnaes persönliche Baseline.
# =========================================================

def apply_time_decay():

    with state_lock:

        now = time.time()

        elapsed = max(
            0,
            now
            - evilnae_state.last_updated
        )

        if elapsed < 10:

            return

        minutes = (
            elapsed / 60
        )

        decay_strength = min(
            0.20,
            minutes * 0.003
        )

        # -------------------------------------------------
        # VALENCE
        # -------------------------------------------------

        evilnae_state.valence = (
            move_toward(
                evilnae_state.valence,
                DEFAULT_STATE[
                    "valence"
                ],
                decay_strength
            )
        )

        # -------------------------------------------------
        # ENERGY
        # -------------------------------------------------

        evilnae_state.energy = (
            move_toward(
                evilnae_state.energy,
                DEFAULT_STATE[
                    "energy"
                ],
                decay_strength
            )
        )

        # -------------------------------------------------
        # IRRITATION
        #
        # Gereiztheit darf etwas schneller abklingen.
        # -------------------------------------------------

        evilnae_state.irritation = (
            move_toward(
                evilnae_state.irritation,
                DEFAULT_STATE[
                    "irritation"
                ],
                decay_strength * 1.5
            )
        )

        # -------------------------------------------------
        # SOCIAL ENERGY
        # -------------------------------------------------

        evilnae_state.social_energy = (
            move_toward(
                evilnae_state.social_energy,
                DEFAULT_STATE[
                    "social_energy"
                ],
                decay_strength
            )
        )

        # -------------------------------------------------
        # CURIOSITY
        # -------------------------------------------------

        evilnae_state.curiosity = (
            move_toward(
                evilnae_state.curiosity,
                DEFAULT_STATE[
                    "curiosity"
                ],
                decay_strength
            )
        )

        # -------------------------------------------------
        # BOREDOM
        # -------------------------------------------------

        evilnae_state.boredom = (
            move_toward(
                evilnae_state.boredom,
                DEFAULT_STATE[
                    "boredom"
                ],
                decay_strength
            )
        )

        # -------------------------------------------------
        # AMUSEMENT
        # -------------------------------------------------

        evilnae_state.amusement = (
            move_toward(
                evilnae_state.amusement,
                DEFAULT_STATE[
                    "amusement"
                ],
                decay_strength
            )
        )

        # -------------------------------------------------
        # WARMTH
        #
        # Wärme verändert sich etwas langsamer,
        # damit ein nettes Gespräch nicht
        # sofort wieder "vergessen" wirkt.
        # -------------------------------------------------

        evilnae_state.warmth = (
            move_toward(
                evilnae_state.warmth,
                DEFAULT_STATE[
                    "warmth"
                ],
                decay_strength * 0.5
            )
        )

        # -------------------------------------------------
        # CHAOS
        # -------------------------------------------------

        evilnae_state.chaos_drive = (
            move_toward(
                evilnae_state.chaos_drive,
                DEFAULT_STATE[
                    "chaos_drive"
                ],
                decay_strength
            )
        )

        # -------------------------------------------------
        # CONFIDENCE
        # -------------------------------------------------

        evilnae_state.confidence = (
            move_toward(
                evilnae_state.confidence,
                DEFAULT_STATE[
                    "confidence"
                ],
                decay_strength * 0.5
            )
        )

        evilnae_state.last_updated = (
            now
        )

        normalize_state()


# =========================================================
# TEXT HELPERS
# =========================================================

def normalized_text(
    text
):

    return (
        text
        or ""
    ).strip().lower()


def contains_any(
    text,
    phrases
):

    text = (
        normalized_text(
            text
        )
    )

    return any(
        phrase in text
        for phrase
        in phrases
    )


# =========================================================
# EVENT ANALYSIS
#
# Das hier ist nur kurzfristige,
# schnelle emotionale Wahrnehmung.
#
# Es ist NICHT das spätere
# per-User Relationship-System.
#
# Langfristige Gefühle kommen später
# über Conversation Episodes.
# =========================================================

def analyze_interaction(
    *,
    text,
    is_hanae=False,
    relationship_text=""
):

    text_lower = (
        normalized_text(
            text
        )
    )

    events = []

    # -----------------------------------------------------
    # GREETING
    # -----------------------------------------------------

    if contains_any(
        text_lower,
        [
            "guten morgen",
            "guten abend",
            "gute nacht",
            "morgen evil",
            "moin",
            "hallo evil",
            "hey evil",
            "hi evil",
        ]
    ):

        events.append(
            "greeting"
        )

    # -----------------------------------------------------
    # POSITIVE SOCIAL SIGNAL
    #
    # Explizit positive soziale Signale,
    # nicht einfach jede normale nette Frage.
    # -----------------------------------------------------

    if contains_any(
        text_lower,
        [
            "danke",
            "lieb von dir",
            "hab dich lieb",
            "mag dich",
            "stolz auf dich",
            "gut gemacht",
            "du bist toll",
            "du bist süß",
            "freut mich",
            "freut mich für dich",
            "schön zu hören",
        ]
    ):

        events.append(
            "positive_social"
        )

    # -----------------------------------------------------
    # PLAYFUL / TEASING
    #
    # FIX v1.1:
    #
    # text_lower ist bereits lowercase.
    #
    # Deshalb:
    # "xd", NICHT "xD".
    #
    # Außerdem ist "schnippisch"
    # kein automatisches playful-Signal mehr.
    # -----------------------------------------------------

    if contains_any(
        text_lower,
        [
            "xd",
            "haha",
            "hehe",
            "kek",
            "lmao",
            "lol",
            "du bist mir eine",
            "was für bro",
            "frech",
        ]
    ):

        events.append(
            "playful"
        )

    # -----------------------------------------------------
    # PRESSURE
    #
    # Nur klarer Druck.
    #
    # Ein normales:
    #
    # "Ehm Evil..."
    #
    # ist NICHT automatisch Druck.
    # -----------------------------------------------------

    if contains_any(
        text_lower,
        [
            "hallo?",
            "antwort doch",
            "jetzt antwort",
            "komm schon",
            "mach jetzt",
            "warum antwortest du nicht",
            "antwortest du noch",
            "ignorierst du mich",
        ]
    ):

        events.append(
            "pressure"
        )

    # -----------------------------------------------------
    # HOSTILITY
    # -----------------------------------------------------

    if contains_any(
        text_lower,
        [
            "halt die fresse",
            "du nervst",
            "scheiß bot",
            "scheiss bot",
            "du bist nutzlos",
            "du bist ein idiot",
            "du idiot",
        ]
    ):

        events.append(
            "hostility"
        )

    # -----------------------------------------------------
    # INTERESTING QUESTION
    #
    # Eine Frage erhöht eher Neugier.
    #
    # Sie erhöht ausdrücklich NICHT Irritation.
    #
    # Normale soziale Fragen sind normal.
    # -----------------------------------------------------

    if (
        "?" in text_lower
        and
        len(
            text_lower
        ) > 25
    ):

        events.append(
            "interesting_question"
        )

    # -----------------------------------------------------
    # NORMAL SOCIAL QUESTION
    #
    # Hilft später dem Writer zu verstehen:
    # Das ist normale soziale Interaktion,
    # kein persönlicher Angriff.
    # -----------------------------------------------------

    normal_social_question_patterns = [
        "wie geht",
        "wie war dein tag",
        "was machst du",
        "was machst du heute",
        "was hast du heute",
        "was hast du gegessen",
        "was magst du",
        "was ist dein lieblings",
        "wie sieht dein tag",
        "wie sieht der rest",
        "hast du heute",
        "hast du gut geschlafen",
        "hast du geträumt",
    ]

    if (
        "?" in text_lower
        and
        contains_any(
            text_lower,
            normal_social_question_patterns
        )
    ):

        events.append(
            "normal_social_question"
        )

    # -----------------------------------------------------
    # VERY SHORT MESSAGE
    # -----------------------------------------------------

    if (
        len(
            text_lower
        )
        <= 5
    ):

        events.append(
            "short_message"
        )

    # -----------------------------------------------------
    # HANAE
    # -----------------------------------------------------

    if is_hanae:

        events.append(
            "hanae_interaction"
        )

    # -----------------------------------------------------
    # TRUSTED RELATIONSHIP
    # -----------------------------------------------------

    relationship_lower = (
        relationship_text
        or ""
    ).lower()

    if any(
        token
        in relationship_lower
        for token
        in [
            "vertraut",
            "enge",
            "freund",
            "mag",
            "humor",
            "vertrauter",
            "vertraute",
            "vertrauten",
            "freundschaft",
        ]
    ):

        events.append(
            "trusted_person"
        )

    return events


# =========================================================
# APPLY EVENTS
# =========================================================

def apply_events(
    events
):

    with state_lock:

        for event in events:

            # ---------------------------------------------
            # GREETING
            # ---------------------------------------------

            if event == "greeting":

                evilnae_state.social_energy += (
                    0.03
                )

                evilnae_state.warmth += (
                    0.03
                )

                evilnae_state.boredom -= (
                    0.03
                )

            # ---------------------------------------------
            # POSITIVE SOCIAL
            # ---------------------------------------------

            elif (
                event
                == "positive_social"
            ):

                evilnae_state.valence += (
                    0.07
                )

                evilnae_state.warmth += (
                    0.08
                )

                evilnae_state.irritation -= (
                    0.06
                )

                evilnae_state.amusement += (
                    0.02
                )

            # ---------------------------------------------
            # PLAYFUL
            # ---------------------------------------------

            elif (
                event
                == "playful"
            ):

                evilnae_state.amusement += (
                    0.08
                )

                evilnae_state.chaos_drive += (
                    0.05
                )

                evilnae_state.boredom -= (
                    0.05
                )

            # ---------------------------------------------
            # PRESSURE
            # ---------------------------------------------

            elif (
                event
                == "pressure"
            ):

                evilnae_state.irritation += (
                    0.06
                )

                evilnae_state.social_energy -= (
                    0.02
                )

            # ---------------------------------------------
            # HOSTILITY
            # ---------------------------------------------

            elif (
                event
                == "hostility"
            ):

                evilnae_state.irritation += (
                    0.15
                )

                evilnae_state.valence -= (
                    0.10
                )

                evilnae_state.warmth -= (
                    0.05
                )

            # ---------------------------------------------
            # INTERESTING QUESTION
            # ---------------------------------------------

            elif (
                event
                == "interesting_question"
            ):

                evilnae_state.curiosity += (
                    0.05
                )

                evilnae_state.boredom -= (
                    0.03
                )

            # ---------------------------------------------
            # NORMAL SOCIAL QUESTION
            #
            # Ein normales Gespräch ist eher
            # sozial verbindend als nervig.
            #
            # Effekt bewusst SEHR klein.
            # ---------------------------------------------

            elif (
                event
                == "normal_social_question"
            ):

                evilnae_state.social_energy += (
                    0.01
                )

                evilnae_state.irritation -= (
                    0.01
                )

            # ---------------------------------------------
            # SHORT MESSAGE
            # ---------------------------------------------

            elif (
                event
                == "short_message"
            ):

                evilnae_state.curiosity -= (
                    0.01
                )

            # ---------------------------------------------
            # HANAE
            # ---------------------------------------------

            elif (
                event
                == "hanae_interaction"
            ):

                evilnae_state.warmth += (
                    0.025
                )

                evilnae_state.social_energy += (
                    0.015
                )

                evilnae_state.irritation -= (
                    0.015
                )

            # ---------------------------------------------
            # TRUSTED PERSON
            #
            # Sehr kleiner kurzfristiger Bias.
            #
            # Das ist NICHT das spätere
            # langfristige per-User Gefühlssystem.
            # ---------------------------------------------

            elif (
                event
                == "trusted_person"
            ):

                evilnae_state.warmth += (
                    0.015
                )

        evilnae_state.last_updated = (
            time.time()
        )

        normalize_state()


# =========================================================
# PROCESS INTERACTION
# =========================================================

def process_interaction(
    *,
    text,
    is_hanae=False,
    relationship_text=""
):

    with state_lock:

        apply_time_decay()

        events = (
            analyze_interaction(

                text=text,

                is_hanae=is_hanae,

                relationship_text=(
                    relationship_text
                )
            )
        )

        apply_events(
            events
        )

        save_inner_state()

        return (
            evilnae_state,
            events
        )


# =========================================================
# DOMINANT FEELING
# =========================================================

def get_dominant_feeling(
    state=None
):

    if state is None:

        state = evilnae_state

    # -----------------------------------------------------
    # IRRITATED
    #
    # Erst bei wirklich hoher Gereiztheit
    # soll "irritated" dominant werden.
    # -----------------------------------------------------

    if (
        state.irritation
        >= 0.72
    ):

        return "irritated"

    # -----------------------------------------------------
    # VERY AMUSED
    # -----------------------------------------------------

    if (
        state.amusement
        >= 0.72
        and
        state.energy
        >= 0.50
    ):

        return "amused"

    # -----------------------------------------------------
    # CHAOTIC
    # -----------------------------------------------------

    if (
        state.chaos_drive
        >= 0.72
        and
        state.energy
        >= 0.60
    ):

        return "chaotic"

    # -----------------------------------------------------
    # WARM
    # -----------------------------------------------------

    if (
        state.warmth
        >= 0.70
        and
        state.irritation
        < 0.45
    ):

        return "warm"

    # -----------------------------------------------------
    # BORED
    # -----------------------------------------------------

    if (
        state.boredom
        >= 0.70
    ):

        return "bored"

    # -----------------------------------------------------
    # CURIOUS
    # -----------------------------------------------------

    if (
        state.curiosity
        >= 0.72
    ):

        return "curious"

    # -----------------------------------------------------
    # LOW ENERGY
    # -----------------------------------------------------

    if (
        state.energy
        <= 0.30
    ):

        return "tired"

    # -----------------------------------------------------
    # GOOD MOOD
    # -----------------------------------------------------

    if (
        state.valence
        >= 0.55
    ):

        return "good"

    # -----------------------------------------------------
    # NEGATIVE
    # -----------------------------------------------------

    if (
        state.valence
        <= -0.35
    ):

        return "negative"

    return "neutral"


# =========================================================
# RESPONSE CHARACTER GUIDANCE
# =========================================================

def build_inner_state_guidance(
    state=None,
    is_hanae=False
):

    if state is None:

        state = evilnae_state

    dominant = (
        get_dominant_feeling(
            state
        )
    )

    lines = []

    lines.append(
        f"Dominant feeling: "
        f"{dominant}"
    )

    # -----------------------------------------------------
    # IRRITATION
    # -----------------------------------------------------

    if (
        state.irritation
        >= 0.60
    ):

        lines.append(
            "Evilnae ist merklich genervt. "
            "Trockenere oder schärfere Reaktionen "
            "können nachvollziehbar sein."
        )

    elif (
        state.irritation
        >= 0.35
    ):

        lines.append(
            "Leichte Gereiztheit ist vorhanden, "
            "aber sie ist nicht dominant."
        )

    else:

        lines.append(
            "Evilnae ist aktuell nicht ernsthaft genervt."
        )

        lines.append(
            "Normale soziale Fragen sind deshalb "
            "kein Grund für defensive oder "
            "abweisende Formulierungen."
        )

    # -----------------------------------------------------
    # WARMTH
    # -----------------------------------------------------

    if (
        state.warmth
        >= 0.65
    ):

        lines.append(
            "Evilnae empfindet aktuell deutlich "
            "Wärme und soziale Nähe."
        )

    elif (
        state.warmth
        >= 0.40
    ):

        lines.append(
            "Evilnae ist sozial grundsätzlich zugänglich."
        )

    else:

        lines.append(
            "Evilnae wirkt aktuell etwas "
            "emotional distanzierter."
        )

    # -----------------------------------------------------
    # ENERGY
    # -----------------------------------------------------

    if (
        state.energy
        >= 0.70
    ):

        lines.append(
            "Hohe Energie: lebendigere "
            "Antworten sind möglich."
        )

    elif (
        state.energy
        <= 0.35
    ):

        lines.append(
            "Niedrige Energie: eher kompakt "
            "und weniger aufgedreht antworten."
        )

    # -----------------------------------------------------
    # AMUSEMENT
    # -----------------------------------------------------

    if (
        state.amusement
        >= 0.65
    ):

        lines.append(
            "Evilnae findet die aktuelle "
            "Situation ziemlich unterhaltsam."
        )

    # -----------------------------------------------------
    # BOREDOM
    # -----------------------------------------------------

    if (
        state.boredom
        >= 0.60
    ):

        lines.append(
            "Evilnae langweilt sich etwas "
            "und könnte spontaner oder frecher werden."
        )

    # -----------------------------------------------------
    # CURIOSITY
    # -----------------------------------------------------

    if (
        state.curiosity
        >= 0.65
    ):

        lines.append(
            "Evilnae ist aktuell genuinely neugierig."
        )

        lines.append(
            "Neugier soll eher Interesse erzeugen "
            "als grundlose Abwehr."
        )

    # -----------------------------------------------------
    # SOCIAL ENERGY
    # -----------------------------------------------------

    if (
        state.social_energy
        >= 0.60
    ):

        lines.append(
            "Evilnae hat aktuell genug soziale Energie "
            "für ein normales Gespräch."
        )

    elif (
        state.social_energy
        <= 0.30
    ):

        lines.append(
            "Evilnaes soziale Energie ist niedrig; "
            "sie kann knapper wirken, ohne feindselig zu sein."
        )

    # -----------------------------------------------------
    # HANAE RELATIONSHIP FLOOR
    # -----------------------------------------------------

    if is_hanae:

        lines.append(
            "Hanae ist Evilnaes Zwillingsschwester. "
            "Auch bei Gereiztheit liegt darunter "
            "eine stabile geschwisterliche Vertrautheit."
        )

        lines.append(
            "Genervtheit gegenüber Hanae darf wie "
            "Geschwister-Genervtheit wirken, "
            "nicht wie Ablehnung oder "
            "Fake-Friend-Distanz."
        )

    return "\n".join(
        f"- {line}"
        for line
        in lines
    )


# =========================================================
# STYLE HINT
# =========================================================

def get_inner_state_style_hint(
    state=None
):

    if state is None:

        state = evilnae_state

    dominant = (
        get_dominant_feeling(
            state
        )
    )

    mapping = {

        "irritated":
            "dry",

        "amused":
            "playful",

        "chaotic":
            "chaotic",

        "warm":
            "warm",

        "bored":
            "deadpan",

        "curious":
            "natural",

        "tired":
            "dry",

        "good":
            "playful",

        "negative":
            "dry",

        "neutral":
            "natural",
    }

    return mapping.get(
        dominant,
        "natural"
    )


# =========================================================
# DEBUG
# =========================================================

def format_inner_state_debug(
    state=None,
    events=None
):

    if state is None:

        state = evilnae_state

    if events is None:

        events = []

    return (
        "[INNER STATE] "
        f"v={INNER_STATE_VERSION} "
        f"feeling="
        f"{get_dominant_feeling(state)} "
        f"valence={state.valence:.2f} "
        f"energy={state.energy:.2f} "
        f"irritation={state.irritation:.2f} "
        f"social={state.social_energy:.2f} "
        f"curiosity={state.curiosity:.2f} "
        f"boredom={state.boredom:.2f} "
        f"amusement={state.amusement:.2f} "
        f"warmth={state.warmth:.2f} "
        f"chaos={state.chaos_drive:.2f} "
        f"confidence={state.confidence:.2f} "
        f"events={events}"
    )