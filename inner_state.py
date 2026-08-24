import json
import os
import time
import threading

from dataclasses import (
    dataclass,
    asdict,
)


# =========================================================
# VERSION
# =========================================================

INNER_STATE_VERSION = "1.2"


# =========================================================
# STORAGE
# =========================================================

STATE_FILE = (
    "evilnae_inner_state.json"
)

STATE_TEMP_FILE = (
    STATE_FILE
    + ".tmp"
)


# =========================================================
# THREAD / TASK SAFETY
# =========================================================

state_lock = (
    threading.RLock()
)


# =========================================================
# DEFAULT VALUES
#
# Inner State = momentaner globaler Zustand.
#
# NICHT:
#
# langfristige Beziehung zu einzelnen Usern.
#
# Das kommt später über:
#
# - Social Emotional State
# - Conversation Episodes
# - Experience / Reflection
# =========================================================

DEFAULT_STATE = {

    "valence":
        0.20,

    "energy":
        0.55,

    "irritation":
        0.08,

    "social_energy":
        0.65,

    "curiosity":
        0.55,

    "boredom":
        0.20,

    "amusement":
        0.30,

    "warmth":
        0.45,

    # -----------------------------------------------------
    # chaos_drive bedeutet:
    #
    # - Impulsivität
    # - Bereitschaft auf ungewöhnliche Ideen einzugehen
    # - etwas unberechenbarer zu reagieren
    #
    # Es bedeutet NICHT:
    #
    # "Benutze das Wort Chaos."
    # -----------------------------------------------------

    "chaos_drive":
        0.35,

    "confidence":
        0.75,

    "last_updated":
        time.time(),
}


# =========================================================
# HARD STATE LIMITS
#
# v1.1 konnte Werte auf 1.00 pumpen.
#
# Das führte zu:
#
# warmth=1.00
# amusement=0.99
#
# und dadurch permanenten Stil-Loops.
#
# v1.2 verhindert solche Extremzustände.
# =========================================================

STATE_LIMITS = {

    "valence":
        (-0.75, 0.80),

    "energy":
        (0.20, 0.88),

    "irritation":
        (0.02, 0.90),

    "social_energy":
        (0.20, 0.88),

    "curiosity":
        (0.20, 0.88),

    "boredom":
        (0.05, 0.82),

    "amusement":
        (0.10, 0.84),

    "warmth":
        (0.15, 0.84),

    "chaos_drive":
        (0.15, 0.78),

    "confidence":
        (0.35, 0.90),
}


# =========================================================
# TIME DECAY RATES
#
# Bewegung pro Minute Richtung Baseline.
#
# Unterschiedliche Emotionen
# normalisieren unterschiedlich schnell.
# =========================================================

TIME_DECAY_RATES = {

    "valence":
        0.008,

    "energy":
        0.005,

    "irritation":
        0.015,

    "social_energy":
        0.006,

    "curiosity":
        0.008,

    "boredom":
        0.010,

    "amusement":
        0.012,

    "warmth":
        0.005,

    "chaos_drive":
        0.010,

    "confidence":
        0.003,
}


# =========================================================
# ACTIVE INTERACTION NORMALIZATION
#
# Problem v1.1:
#
# Wenn alle paar Sekunden geschrieben wird,
# greift Time Decay kaum.
#
# Gleichzeitig feuern ständig neue Events.
#
# Dadurch können Zustände während
# aktiver Chats immer weiter steigen.
#
# Deshalb bewegt jede Interaktion
# den globalen State minimal Richtung Baseline.
# =========================================================

INTERACTION_NORMALIZATION = {

    "valence":
        0.003,

    "energy":
        0.002,

    "irritation":
        0.005,

    "social_energy":
        0.002,

    "curiosity":
        0.004,

    "boredom":
        0.004,

    "amusement":
        0.008,

    "warmth":
        0.003,

    "chaos_drive":
        0.007,

    "confidence":
        0.001,
}


# =========================================================
# EVENT COOLDOWNS
#
# Sekunden.
#
# Ein Event darf erkannt werden,
# ohne jedes Mal den State zu verändern.
#
# Beispiel:
#
# Ein vertrauter User schreibt 20 Messages.
#
# Das bedeutet NICHT:
#
# +20x Wärme.
# =========================================================

EVENT_COOLDOWNS = {

    "greeting":
        300,

    "positive_social":
        180,

    "playful":
        90,

    "pressure":
        60,

    "hostility":
        60,

    "interesting_question":
        60,

    "normal_social_question":
        300,

    "short_message":
        0,

    "hanae_interaction":
        600,

    "trusted_person":
        0,
}


# =========================================================
# EVENT DELTAS
#
# v1.2:
#
# Normale Gespräche verändern
# den persistenten globalen Zustand
# kaum oder überhaupt nicht.
#
# Bedeutende Signale dürfen etwas bewirken.
# =========================================================

EVENT_DELTAS = {

    "greeting": {

        "social_energy":
            0.015,

        "warmth":
            0.010,

        "boredom":
            -0.010,
    },


    "positive_social": {

        "valence":
            0.040,

        "warmth":
            0.045,

        "irritation":
            -0.025,

        "amusement":
            0.005,
    },


    "playful": {

        "amusement":
            0.050,

        "chaos_drive":
            0.025,

        "boredom":
            -0.025,
    },


    "pressure": {

        "irritation":
            0.040,

        "social_energy":
            -0.010,
    },


    "hostility": {

        "irritation":
            0.100,

        "valence":
            -0.070,

        "warmth":
            -0.025,
    },


    "interesting_question": {

        "curiosity":
            0.030,

        "boredom":
            -0.015,
    },


    # -----------------------------------------------------
    # Normale soziale Fragen
    #
    # werden erkannt,
    # verändern Evilnae aber nicht
    # jedes Mal emotional.
    # -----------------------------------------------------

    "normal_social_question": {},


    # -----------------------------------------------------
    # Short Message
    #
    # "lol"
    # "ja"
    # "oha"
    #
    # soll nicht permanent
    # Curiosity beeinflussen.
    # -----------------------------------------------------

    "short_message": {},


    # -----------------------------------------------------
    # Hanae
    #
    # Geschwister-Vertrautheit kommt hauptsächlich
    # über festen Character Context.
    #
    # Nicht durch +0.025 Wärme
    # bei jeder einzelnen Nachricht.
    # -----------------------------------------------------

    "hanae_interaction": {

        "warmth":
            0.005,

        "social_energy":
            0.005,

        "irritation":
            -0.005,
    },


    # -----------------------------------------------------
    # Trusted Person
    #
    # Sehr wichtig:
    #
    # Langfristige Beziehung gehört NICHT
    # in den globalen Inner State.
    #
    # Deshalb kein automatischer Delta mehr.
    #
    # Relationship Context wird weiterhin
    # separat an Writer/Brain gegeben.
    # -----------------------------------------------------

    "trusted_person": {},
}


# =========================================================
# RUNTIME EVENT COOLDOWNS
#
# Nicht persistent.
#
# Nach Neustart darf Evilnae emotional
# wieder frisch auf Situationen reagieren.
# =========================================================

_event_last_applied = {}


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
# GENERIC CLAMP
# =========================================================

def clamp(
    value,
    minimum,
    maximum
):

    return max(
        minimum,
        min(
            maximum,
            value
        )
    )


# =========================================================
# CREATE DEFAULT STATE
# =========================================================

def create_default_state():

    return InnerState(

        valence=(
            DEFAULT_STATE[
                "valence"
            ]
        ),

        energy=(
            DEFAULT_STATE[
                "energy"
            ]
        ),

        irritation=(
            DEFAULT_STATE[
                "irritation"
            ]
        ),

        social_energy=(
            DEFAULT_STATE[
                "social_energy"
            ]
        ),

        curiosity=(
            DEFAULT_STATE[
                "curiosity"
            ]
        ),

        boredom=(
            DEFAULT_STATE[
                "boredom"
            ]
        ),

        amusement=(
            DEFAULT_STATE[
                "amusement"
            ]
        ),

        warmth=(
            DEFAULT_STATE[
                "warmth"
            ]
        ),

        chaos_drive=(
            DEFAULT_STATE[
                "chaos_drive"
            ]
        ),

        confidence=(
            DEFAULT_STATE[
                "confidence"
            ]
        ),

        last_updated=(
            time.time()
        )
    )


# =========================================================
# NORMALIZE STATE OBJECT
#
# Funktioniert auch auf temporären
# Test-States.
# =========================================================

def normalize_state_object(
    state
):

    for attribute, limits in (
        STATE_LIMITS.items()
    ):

        minimum = (
            limits[0]
        )

        maximum = (
            limits[1]
        )

        current = float(
            getattr(
                state,
                attribute
            )
        )

        setattr(
            state,
            attribute,
            clamp(
                current,
                minimum,
                maximum
            )
        )

    return state


# =========================================================
# LOAD
#
# Alte v1.1-State-Dateien
# werden automatisch saniert.
#
# Wenn dort z. B.
#
# warmth = 1.00
#
# steht,
# wird der Wert beim Laden
# auf die neuen gesunden Limits gebracht.
# =========================================================

def load_inner_state():

    if not os.path.exists(
        STATE_FILE
    ):

        return (
            create_default_state()
        )

    try:

        with open(
            STATE_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            data = (
                json.load(
                    file
                )
            )

        state = InnerState(

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

        return (
            normalize_state_object(
                state
            )
        )

    except Exception as error:

        print(
            "[INNER STATE LOAD ERROR] "
            f"{type(error).__name__}: "
            f"{error}"
        )

        return (
            create_default_state()
        )


# =========================================================
# RUNTIME STATE
# =========================================================

evilnae_state = (
    load_inner_state()
)


# =========================================================
# NORMALIZE GLOBAL STATE
#
# Bestehender Funktionsname bleibt
# rückwärtskompatibel.
# =========================================================

def normalize_state():

    with state_lock:

        normalize_state_object(
            evilnae_state
        )


# =========================================================
# SAVE
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
# MOVE TOWARD
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
# DIMINISHING DELTA
#
# Je näher ein State-Wert
# seinem Limit kommt,
# desto schwächer wirken weitere Events.
#
# Beispiel:
#
# warmth 0.45 + positives Event
# -> deutlicher Effekt
#
# warmth 0.81 + positives Event
# -> nur noch sehr kleiner Effekt
# =========================================================

def apply_bounded_delta(
    state,
    attribute,
    delta
):

    if (
        not delta
        or
        attribute
        not in STATE_LIMITS
    ):

        return

    minimum, maximum = (
        STATE_LIMITS[
            attribute
        ]
    )

    current = float(
        getattr(
            state,
            attribute
        )
    )

    baseline = float(
        DEFAULT_STATE[
            attribute
        ]
    )

    # -----------------------------------------------------
    # POSITIVE DELTA
    # -----------------------------------------------------

    if delta > 0:

        total_headroom = max(
            0.001,
            maximum
            - baseline
        )

        remaining = max(
            0.0,
            maximum
            - current
        )

        factor = clamp(
            remaining
            / total_headroom,
            0.08,
            1.00
        )

        effective_delta = (
            delta
            * factor
        )

    # -----------------------------------------------------
    # NEGATIVE DELTA
    # -----------------------------------------------------

    else:

        total_headroom = max(
            0.001,
            baseline
            - minimum
        )

        remaining = max(
            0.0,
            current
            - minimum
        )

        factor = clamp(
            remaining
            / total_headroom,
            0.08,
            1.00
        )

        effective_delta = (
            delta
            * factor
        )

    new_value = (
        current
        + effective_delta
    )

    setattr(
        state,
        attribute,
        clamp(
            new_value,
            minimum,
            maximum
        )
    )


# =========================================================
# TIME DECAY
# =========================================================

def apply_time_decay():

    with state_lock:

        now = (
            time.time()
        )

        elapsed = max(
            0.0,
            now
            - evilnae_state.last_updated
        )

        if elapsed < 10:

            return

        minutes = (
            elapsed
            / 60.0
        )

        for attribute, rate in (
            TIME_DECAY_RATES.items()
        ):

            current = float(
                getattr(
                    evilnae_state,
                    attribute
                )
            )

            baseline = float(
                DEFAULT_STATE[
                    attribute
                ]
            )

            # ---------------------------------------------
            # Auch nach langer Offline-Zeit
            # keine riesigen Sprünge in einem Call.
            # ---------------------------------------------

            amount = min(
                0.35,
                minutes
                * rate
            )

            setattr(
                evilnae_state,
                attribute,
                move_toward(
                    current,
                    baseline,
                    amount
                )
            )

        evilnae_state.last_updated = (
            now
        )

        normalize_state()


# =========================================================
# ACTIVE INTERACTION NORMALIZATION
#
# Wird einmal pro verarbeiteter
# Interaktion ausgeführt.
#
# Dadurch kann ein schneller Channel
# den State nicht endlos hochpumpen.
# =========================================================

def apply_interaction_normalization(
    state=None
):

    if state is None:

        state = (
            evilnae_state
        )

    for attribute, amount in (
        INTERACTION_NORMALIZATION.items()
    ):

        current = float(
            getattr(
                state,
                attribute
            )
        )

        baseline = float(
            DEFAULT_STATE[
                attribute
            ]
        )

        setattr(
            state,
            attribute,
            move_toward(
                current,
                baseline,
                amount
            )
        )

    normalize_state_object(
        state
    )


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
# Erkennt kurzfristige emotionale Signale.
#
# Wichtig:
#
# Event erkannt
# !=
# State muss verändert werden.
#
# Normale Social Events können erkannt werden,
# ohne dauerhafte emotionale Wirkung.
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
            "du bist suess",
            "freut mich",
            "freut mich für dich",
            "freut mich fuer dich",
            "schön zu hören",
            "schoen zu hoeren",
        ]
    ):

        events.append(
            "positive_social"
        )

    # -----------------------------------------------------
    # PLAYFUL / TEASING
    #
    # Nur Signale,
    # die tatsächlich nach spielerischem
    # Umgang aussehen.
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
            "was fuer bro",
            "frech",
        ]
    ):

        events.append(
            "playful"
        )

    # -----------------------------------------------------
    # PRESSURE
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

        "hast du getraeumt",
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
        text_lower
        and
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

    return list(
        dict.fromkeys(
            events
        )
    )


# =========================================================
# EVENT COOLDOWN CHECK
# =========================================================

def event_is_available(
    event,
    *,
    now=None,
    event_last_applied=None
):

    if now is None:

        now = (
            time.time()
        )

    if event_last_applied is None:

        event_last_applied = (
            _event_last_applied
        )

    cooldown = float(
        EVENT_COOLDOWNS.get(
            event,
            0
        )
    )

    if cooldown <= 0:

        return True

    last_applied = (
        event_last_applied.get(
            event
        )
    )

    if last_applied is None:

        return True

    return (
        now
        - last_applied
        >= cooldown
    )


# =========================================================
# APPLY EVENTS
#
# Rückwärtskompatibel:
#
# apply_events(events)
#
# funktioniert weiterhin.
#
# Für Tests können State und Cooldown-Dict
# separat übergeben werden.
# =========================================================

def apply_events(
    events,
    *,
    state=None,
    now=None,
    event_last_applied=None
):

    if state is None:

        state = (
            evilnae_state
        )

    if now is None:

        now = (
            time.time()
        )

    if event_last_applied is None:

        event_last_applied = (
            _event_last_applied
        )

    applied_events = []

    with state_lock:

        for event in (
            events
        ):

            if not event_is_available(
                event,
                now=now,
                event_last_applied=(
                    event_last_applied
                )
            ):

                continue

            deltas = (
                EVENT_DELTAS.get(
                    event,
                    {}
                )
            )

            # ---------------------------------------------
            # Events ohne Deltas:
            #
            # z. B. trusted_person
            #
            # werden weiterhin erkannt,
            # pumpen aber den globalen State nicht.
            # ---------------------------------------------

            for (
                attribute,
                delta
            ) in (
                deltas.items()
            ):

                apply_bounded_delta(
                    state,
                    attribute,
                    delta
                )

            # ---------------------------------------------
            # Cooldown nur registrieren,
            # wenn der Event überhaupt
            # einen State-Effekt besitzt.
            # ---------------------------------------------

            if deltas:

                event_last_applied[
                    event
                ] = now

                applied_events.append(
                    event
                )

        state.last_updated = (
            now
        )

        normalize_state_object(
            state
        )

    return (
        applied_events
    )


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

        # -------------------------------------------------
        # NORMAL TIME DECAY
        # -------------------------------------------------

        apply_time_decay()

        # -------------------------------------------------
        # ACTIVE NORMALIZATION
        #
        # Wichtig bei schnellen Channels.
        # -------------------------------------------------

        apply_interaction_normalization(
            evilnae_state
        )

        # -------------------------------------------------
        # EVENT PERCEPTION
        # -------------------------------------------------

        events = (
            analyze_interaction(

                text=text,

                is_hanae=is_hanae,

                relationship_text=(
                    relationship_text
                )
            )
        )

        # -------------------------------------------------
        # EVENT EFFECT
        # -------------------------------------------------

        apply_events(
            events
        )

        # -------------------------------------------------
        # SAVE
        # -------------------------------------------------

        save_inner_state()

        # -------------------------------------------------
        # Rückwärtskompatibel:
        #
        # Es werden weiterhin die ERKANNTEN Events
        # zurückgegeben.
        #
        # Nicht nur Events,
        # deren Cooldown gerade frei war.
        # -------------------------------------------------

        return (
            evilnae_state,
            events
        )


# =========================================================
# NORMALIZED ACTIVATION SCORE
# =========================================================

def activation_score(
    value,
    threshold,
    maximum
):

    if value <= threshold:

        return 0.0

    if maximum <= threshold:

        return 0.0

    return clamp(
        (
            value
            - threshold
        )
        /
        (
            maximum
            - threshold
        ),
        0.0,
        1.0
    )


# =========================================================
# REVERSE ACTIVATION SCORE
#
# Für:
#
# tired
# negative
# =========================================================

def reverse_activation_score(
    value,
    threshold,
    minimum
):

    if value >= threshold:

        return 0.0

    if threshold <= minimum:

        return 0.0

    return clamp(
        (
            threshold
            - value
        )
        /
        (
            threshold
            - minimum
        ),
        0.0,
        1.0
    )


# =========================================================
# FEELING SCORES
#
# v1.1:
#
# feste if-Reihenfolge.
#
# Dadurch konnte "warm"
# einen großen Teil der Zeit gewinnen.
#
# v1.2:
#
# Zustände konkurrieren anhand
# ihrer tatsächlichen relativen Stärke.
# =========================================================

def get_feeling_scores(
    state=None
):

    if state is None:

        state = (
            evilnae_state
        )

    energy_support = clamp(
        (
            state.energy
            - 0.35
        )
        /
        0.40,
        0.25,
        1.00
    )

    scores = {

        "irritated":
            activation_score(
                state.irritation,
                0.42,
                STATE_LIMITS[
                    "irritation"
                ][1]
            ),

        "amused":
            activation_score(
                state.amusement,
                0.56,
                STATE_LIMITS[
                    "amusement"
                ][1]
            )
            * energy_support,

        "chaotic":
            activation_score(
                state.chaos_drive,
                0.60,
                STATE_LIMITS[
                    "chaos_drive"
                ][1]
            )
            * energy_support,

        "warm":
            activation_score(
                state.warmth,
                0.67,
                STATE_LIMITS[
                    "warmth"
                ][1]
            ),

        "bored":
            activation_score(
                state.boredom,
                0.62,
                STATE_LIMITS[
                    "boredom"
                ][1]
            ),

        "curious":
            activation_score(
                state.curiosity,
                0.67,
                STATE_LIMITS[
                    "curiosity"
                ][1]
            ),

        "tired":
            reverse_activation_score(
                state.energy,
                0.34,
                STATE_LIMITS[
                    "energy"
                ][0]
            ),

        "good":
            activation_score(
                state.valence,
                0.52,
                STATE_LIMITS[
                    "valence"
                ][1]
            ),

        "negative":
            reverse_activation_score(
                state.valence,
                -0.25,
                STATE_LIMITS[
                    "valence"
                ][0]
            ),
    }

    return scores


# =========================================================
# DOMINANT FEELING
#
# Kein "warm gewinnt zuerst" mehr.
#
# Nur deutlich aktivierte Zustände
# werden dominant.
# =========================================================

def get_dominant_feeling(
    state=None
):

    if state is None:

        state = (
            evilnae_state
        )

    scores = (
        get_feeling_scores(
            state
        )
    )

    # -----------------------------------------------------
    # Bei Gleichstand:
    #
    # kontextuell interessantere / akutere
    # Zustände vor globaler Wärme.
    # -----------------------------------------------------

    priority = [

        "irritated",

        "negative",

        "bored",

        "curious",

        "amused",

        "chaotic",

        "tired",

        "warm",

        "good",
    ]

    best_feeling = (
        "neutral"
    )

    best_score = (
        0.0
    )

    for feeling in (
        priority
    ):

        score = float(
            scores.get(
                feeling,
                0.0
            )
        )

        if score > (
            best_score
            + 0.0001
        ):

            best_feeling = (
                feeling
            )

            best_score = (
                score
            )

    # -----------------------------------------------------
    # Mindestaktivierung.
    #
    # Kleine Schwankungen
    # sollen nicht ständig einen
    # neuen "Mood Mode" auslösen.
    # -----------------------------------------------------

    if best_score < 0.35:

        return (
            "neutral"
        )

    return (
        best_feeling
    )


# =========================================================
# RESPONSE CHARACTER GUIDANCE
# =========================================================

def build_inner_state_guidance(
    state=None,
    is_hanae=False
):

    if state is None:

        state = (
            evilnae_state
        )

    dominant = (
        get_dominant_feeling(
            state
        )
    )

    lines = []

    lines.append(
        "Inner State ist ein subtiler "
        "Verhaltens-Bias, kein Rollenspiel-Modus."
    )

    lines.append(
        "Interne Zustandsnamen müssen niemals "
        "wortwörtlich in der Antwort erscheinen."
    )

    lines.append(
        f"Dominant feeling: {dominant}"
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
            "aber nicht dominant."
        )

    else:

        lines.append(
            "Evilnae ist aktuell nicht "
            "ernsthaft genervt."
        )

        lines.append(
            "Normale soziale Fragen sind "
            "kein Grund für defensive oder "
            "abweisende Formulierungen."
        )

    # -----------------------------------------------------
    # WARMTH
    # -----------------------------------------------------

    if (
        state.warmth
        >= 0.68
    ):

        lines.append(
            "Es gibt aktuell deutliche soziale "
            "Wärme. Das kann Antworten vertrauter "
            "machen, muss aber nicht jede Nachricht "
            "weich oder überschwänglich machen."
        )

    elif (
        state.warmth
        >= 0.40
    ):

        lines.append(
            "Evilnae ist sozial grundsätzlich "
            "zugänglich."
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
        >= 0.72
    ):

        lines.append(
            "Hohe Energie kann zu lebendigeren "
            "oder spontaneren Reaktionen führen."
        )

    elif (
        state.energy
        <= 0.35
    ):

        lines.append(
            "Niedrige Energie spricht eher für "
            "knappere und weniger aufgedrehte Antworten."
        )

    # -----------------------------------------------------
    # AMUSEMENT
    # -----------------------------------------------------

    if (
        state.amusement
        >= 0.62
    ):

        lines.append(
            "Evilnae findet die Situation "
            "wirklich unterhaltsam. "
            "Das darf sich im Timing oder Humor zeigen, "
            "nicht durch Emoji- oder Lachen-Zwang."
        )

    # -----------------------------------------------------
    # CHAOS DRIVE
    # -----------------------------------------------------

    if (
        state.chaos_drive
        >= 0.60
    ):

        lines.append(
            "Evilnaes Impulsivität ist erhöht. "
            "Sie darf eher auf eine ungewöhnliche "
            "Idee anspringen oder überraschender reagieren."
        )

        lines.append(
            "WICHTIG: chaos_drive beschreibt "
            "Impulsivität. Das Wort 'Chaos' "
            "oder ähnliche Persona-Schlagwörter "
            "sollen daraus NICHT abgeleitet werden."
        )

    # -----------------------------------------------------
    # BOREDOM
    # -----------------------------------------------------

    if (
        state.boredom
        >= 0.60
    ):

        lines.append(
            "Evilnae langweilt sich etwas. "
            "Sie könnte knapper, trockener oder "
            "spontaner reagieren."
        )

        lines.append(
            "Langeweile muss nicht wortwörtlich "
            "erwähnt werden."
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
            "Neugier bedeutet Interesse, "
            "aber nicht automatisch eine Gegenfrage."
        )

    # -----------------------------------------------------
    # SOCIAL ENERGY
    # -----------------------------------------------------

    if (
        state.social_energy
        >= 0.65
    ):

        lines.append(
            "Evilnae hat genug soziale Energie "
            "für normale Interaktion."
        )

    elif (
        state.social_energy
        <= 0.32
    ):

        lines.append(
            "Evilnaes soziale Energie ist niedrig. "
            "Sie kann knapper wirken, "
            "ohne feindselig zu sein."
        )

    # -----------------------------------------------------
    # HANAE RELATIONSHIP FLOOR
    # -----------------------------------------------------

    if is_hanae:

        lines.append(
            "Hanae ist Evilnaes Zwillingsschwester. "
            "Diese Beziehung ist fester Character Context "
            "und hängt NICHT vom aktuellen Warmth-Wert ab."
        )

        lines.append(
            "Genervtheit gegenüber Hanae darf wie "
            "Geschwister-Genervtheit wirken, "
            "nicht wie Ablehnung oder Fake-Friend-Distanz."
        )

    return "\n".join(

        f"- {line}"

        for line
        in lines
    )


# =========================================================
# STYLE HINT
#
# v1.2:
#
# Der Inner State soll die Sprache
# nur leicht beeinflussen.
#
# Deshalb werden "warm" und "good"
# nicht mehr automatisch zu
# starkem Persona-Styling.
# =========================================================

def get_inner_state_style_hint(
    state=None
):

    if state is None:

        state = (
            evilnae_state
        )

    dominant = (
        get_dominant_feeling(
            state
        )
    )

    mapping = {

        "irritated":
            "dry",

        "negative":
            "dry",

        "bored":
            "deadpan",

        "curious":
            "natural",

        "amused":
            "playful",

        # -------------------------------------------------
        # Chaos Drive beeinflusst Verhalten,
        # nicht Wortschatz.
        #
        # Kein Style namens "chaotic" mehr
        # aus diesem Layer.
        # -------------------------------------------------

        "chaotic":
            "playful",

        "tired":
            "dry",

        # -------------------------------------------------
        # Wärme ist ein Bias,
        # kein permanenter Warm-Mode.
        # -------------------------------------------------

        "warm":
            "natural",

        "good":
            "natural",

        "neutral":
            "natural",
    }

    return (
        mapping.get(
            dominant,
            "natural"
        )
    )


# =========================================================
# DEBUG
# =========================================================

def format_inner_state_debug(
    state=None,
    events=None
):

    if state is None:

        state = (
            evilnae_state
        )

    if events is None:

        events = []

    scores = (
        get_feeling_scores(
            state
        )
    )

    dominant = (
        get_dominant_feeling(
            state
        )
    )

    dominant_score = float(
        scores.get(
            dominant,
            0.0
        )
    )

    return (

        "[INNER STATE] "

        f"v={INNER_STATE_VERSION} "

        f"feeling="
        f"{dominant} "

        f"strength="
        f"{dominant_score:.2f} "

        f"valence="
        f"{state.valence:.2f} "

        f"energy="
        f"{state.energy:.2f} "

        f"irritation="
        f"{state.irritation:.2f} "

        f"social="
        f"{state.social_energy:.2f} "

        f"curiosity="
        f"{state.curiosity:.2f} "

        f"boredom="
        f"{state.boredom:.2f} "

        f"amusement="
        f"{state.amusement:.2f} "

        f"warmth="
        f"{state.warmth:.2f} "

        f"chaos="
        f"{state.chaos_drive:.2f} "

        f"confidence="
        f"{state.confidence:.2f} "

        f"events="
        f"{events}"
    )


# =========================================================
# SELF TEST
#
# python inner_state.py
#
# Verändert NICHT Evilnaes echte State-Datei.
# =========================================================

def _run_self_test():

    # -----------------------------------------------------
    # TEST STATE
    # -----------------------------------------------------

    test_state = (
        create_default_state()
    )

    test_cooldowns = {}

    # -----------------------------------------------------
    # TEST 1
    #
    # Trusted Person 20x
    #
    # darf Wärme NICHT hochpumpen.
    # -----------------------------------------------------

    original_warmth = (
        test_state.warmth
    )

    for index in range(
        20
    ):

        apply_events(

            [
                "trusted_person"
            ],

            state=test_state,

            now=(
                1000
                + index
            ),

            event_last_applied=(
                test_cooldowns
            )
        )

    trusted_stable = (

        abs(
            test_state.warmth
            - original_warmth
        )

        < 0.0001
    )

    # -----------------------------------------------------
    # TEST 2
    #
    # Hanae 20 Messages innerhalb kurzer Zeit.
    #
    # Cooldown verhindert Warmth-Farm.
    # -----------------------------------------------------

    hanae_state = (
        create_default_state()
    )

    hanae_cooldowns = {}

    for index in range(
        20
    ):

        apply_events(

            [
                "hanae_interaction"
            ],

            state=hanae_state,

            now=(
                2000
                + index
            ),

            event_last_applied=(
                hanae_cooldowns
            )
        )

    hanae_not_saturated = (

        hanae_state.warmth
        < 0.50
    )

    # -----------------------------------------------------
    # TEST 3
    #
    # Positive Social darf wirken,
    # aber nicht auf 1.0 schießen.
    # -----------------------------------------------------

    positive_state = (
        create_default_state()
    )

    positive_cooldowns = {}

    for index in range(
        30
    ):

        apply_events(

            [
                "positive_social"
            ],

            state=positive_state,

            now=(
                3000
                + (
                    index
                    * 200
                )
            ),

            event_last_applied=(
                positive_cooldowns
            )
        )

    positive_bounded = (

        positive_state.warmth
        <=
        STATE_LIMITS[
            "warmth"
        ][1]

        and

        positive_state.warmth
        < 0.85
    )

    # -----------------------------------------------------
    # TEST 4
    #
    # Alte kaputte 1.0-Werte
    # werden saniert.
    # -----------------------------------------------------

    legacy_state = (
        create_default_state()
    )

    legacy_state.warmth = (
        1.0
    )

    legacy_state.amusement = (
        1.0
    )

    legacy_state.chaos_drive = (
        1.0
    )

    normalize_state_object(
        legacy_state
    )

    legacy_repaired = (

        legacy_state.warmth
        ==
        STATE_LIMITS[
            "warmth"
        ][1]

        and

        legacy_state.amusement
        ==
        STATE_LIMITS[
            "amusement"
        ][1]

        and

        legacy_state.chaos_drive
        ==
        STATE_LIMITS[
            "chaos_drive"
        ][1]
    )

    # -----------------------------------------------------
    # TEST 5
    #
    # Normal Social Questions
    # ändern Wärme nicht.
    # -----------------------------------------------------

    social_state = (
        create_default_state()
    )

    social_cooldowns = {}

    social_before = (
        asdict(
            social_state
        )
    )

    for index in range(
        10
    ):

        apply_events(

            [
                "normal_social_question"
            ],

            state=social_state,

            now=(
                4000
                + index
            ),

            event_last_applied=(
                social_cooldowns
            )
        )

    normal_social_stable = (

        abs(
            social_state.warmth
            -
            social_before[
                "warmth"
            ]
        )
        < 0.0001

        and

        abs(
            social_state.amusement
            -
            social_before[
                "amusement"
            ]
        )
        < 0.0001

        and

        abs(
            social_state.chaos_drive
            -
            social_before[
                "chaos_drive"
            ]
        )
        < 0.0001
    )

    # -----------------------------------------------------
    # TEST 6
    #
    # Warmth allein darf dominant sein,
    # wenn sie wirklich deutlich ist.
    # -----------------------------------------------------

    warm_state = (
        create_default_state()
    )

    warm_state.warmth = (
        0.80
    )

    warm_dominant = (

        get_dominant_feeling(
            warm_state
        )

        ==
        "warm"
    )

    # -----------------------------------------------------
    # TEST 7
    #
    # Stärkere Curiosity soll Warmth
    # überstimmen können.
    #
    # Genau das konnte die alte
    # harte if-Reihenfolge schlecht.
    # -----------------------------------------------------

    curious_state = (
        create_default_state()
    )

    curious_state.warmth = (
        0.76
    )

    curious_state.curiosity = (
        0.87
    )

    curiosity_can_win = (

        get_dominant_feeling(
            curious_state
        )

        ==
        "curious"
    )

    # -----------------------------------------------------
    # TEST 8
    #
    # Baseline ist neutral.
    # -----------------------------------------------------

    baseline_state = (
        create_default_state()
    )

    baseline_neutral = (

        get_dominant_feeling(
            baseline_state
        )

        ==
        "neutral"
    )

    # -----------------------------------------------------
    # TEST 9
    #
    # Chaotic Feeling erzeugt keinen
    # Style namens chaotic mehr.
    # -----------------------------------------------------

    chaos_state = (
        create_default_state()
    )

    chaos_state.chaos_drive = (
        0.77
    )

    chaos_state.energy = (
        0.80
    )

    chaos_style_safe = (

        get_inner_state_style_hint(
            chaos_state
        )

        !=
        "chaotic"
    )

    tests = [

        (
            "trusted person does not farm warmth",
            trusted_stable
        ),

        (
            "hanae cooldown prevents warmth farming",
            hanae_not_saturated
        ),

        (
            "positive social remains bounded",
            positive_bounded
        ),

        (
            "legacy 1.0 states repaired",
            legacy_repaired
        ),

        (
            "normal social questions stay neutral",
            normal_social_stable
        ),

        (
            "strong warmth can still matter",
            warm_dominant
        ),

        (
            "curiosity can override warmth",
            curiosity_can_win
        ),

        (
            "baseline remains neutral",
            baseline_neutral
        ),

        (
            "chaos state does not force chaotic style",
            chaos_style_safe
        ),
    ]

    print("")

    print(
        "============================================"
    )

    print(
        f"INNER STATE v"
        f"{INNER_STATE_VERSION} "
        f"SELF TEST"
    )

    print(
        "============================================"
    )

    print("")

    print(
        "TRUSTED WARMTH:"
    )

    print(
        f"{original_warmth:.3f} "
        f"-> "
        f"{test_state.warmth:.3f}"
    )

    print("")

    print(
        "HANAE WARMTH AFTER 20 FAST EVENTS:"
    )

    print(
        f"{hanae_state.warmth:.3f}"
    )

    print("")

    print(
        "POSITIVE SOCIAL WARMTH:"
    )

    print(
        f"{positive_state.warmth:.3f}"
    )

    print("")

    print(
        "LEGACY REPAIRED:"
    )

    print(
        f"warmth="
        f"{legacy_state.warmth:.2f} "
        f"amusement="
        f"{legacy_state.amusement:.2f} "
        f"chaos="
        f"{legacy_state.chaos_drive:.2f}"
    )

    print("")

    print(
        "CURIOUS TEST:"
    )

    print(
        format_inner_state_debug(
            curious_state
        )
    )

    print("")

    passed = (
        0
    )

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
            f"[{status}] "
            f"{name}"
        )

    print("")

    print(
        "============================================"
    )

    print(
        f"RESULT: "
        f"{passed}/"
        f"{len(tests)} passed"
    )

    print(
        "============================================"
    )


# =========================================================
# ENTRYPOINT
# =========================================================

if __name__ == "__main__":

    _run_self_test()