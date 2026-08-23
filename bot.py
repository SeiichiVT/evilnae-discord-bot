import os
import random
import re
import asyncio
import time
from collections import deque

import discord
import database

from perception import (
    perceive_message,
    format_perception_debug,
    format_emoji_context,
)

from conversation_state import (
    build_conversation_state,
    format_state_debug,
)

from brain import (
    run_brain,
    format_brain_debug,
    format_brain_decision,
)

from social_actions import (
    can_autonomously_ping,
    register_autonomous_ping,
    get_social_action_status,
    format_social_action_debug,
)

from expression import (
    build_expression_plan,
    format_expression_plan,
    format_expression_debug,
    expression_violation_reasons,
)

from dotenv import load_dotenv

from openai import (
    AsyncOpenAI,
    RateLimitError,
    APITimeoutError,
    APIConnectionError,
    InternalServerError,
)


# =========================================================
# VERSION
# =========================================================

BOT_VERSION = "2.5-expression"


# =========================================================
# ENVIRONMENT
# =========================================================

load_dotenv()

DISCORD_TOKEN = os.getenv(
    "DISCORD_TOKEN"
)

OPENAI_API_KEY = os.getenv(
    "OPENAI_API_KEY"
)

ALLOWED_CHANNEL_ID = os.getenv(
    "ALLOWED_CHANNEL_ID"
)


# =========================================================
# BASIC ENV CHECK
# =========================================================

if not DISCORD_TOKEN:

    raise RuntimeError(
        "DISCORD_TOKEN fehlt in der .env"
    )

if not OPENAI_API_KEY:

    raise RuntimeError(
        "OPENAI_API_KEY fehlt in der .env"
    )


# =========================================================
# OPENAI
# =========================================================

openai_client = AsyncOpenAI(
    api_key=OPENAI_API_KEY
)


# =========================================================
# DISCORD
# =========================================================

intents = discord.Intents.default()

intents.message_content = True

bot = discord.Client(
    intents=intents
)


# =========================================================
# MAIN CONFIG
# =========================================================

HANAE_USER_ID = (
    "568096551948255242"
)


# =========================================================
# MEMORY CONFIG
# =========================================================

MEMORY_BUFFER_THRESHOLD = int(
    os.getenv(
        "MEMORY_BUFFER_THRESHOLD",
        "10"
    )
)

MEMORY_RECENT_SUMMARIES = 8

MEMORY_ARCHIVE_TRIGGER = 14

MEMORY_ARCHIVE_AMOUNT = 8

NO_MEMORY_MARKER = (
    "NO_NEW_MEMORY"
)


# =========================================================
# DISCORD RESPONSE CONFIG
# =========================================================

SPLIT_CHANCE = 5


# =========================================================
# HYBRID CONTEXT CONFIG
# =========================================================

CHANNEL_CONTEXT_LIMIT = 35

USER_CONTEXT_LIMIT = 12

PARTICIPANT_MESSAGE_LIMIT = 6

MAX_ACTIVE_PARTICIPANTS = 12

PARTICIPANT_MESSAGES_IN_PROMPT = 3


# =========================================================
# SOCIAL ACTION CONFIG
# =========================================================

MIN_MESSAGES_FOR_SOCIAL_TARGET = 1


# =========================================================
# EXPRESSION CONFIG
# =========================================================

# Wie viele eigene letzte Antworten
# für den Style-Check berücksichtigt werden.

EXPRESSION_HISTORY_LIMIT = 8


# Wenn der Writer trotz Expression Plan
# ein überbenutztes Wort / Emoji / Opening benutzt,
# loggen wir die Verletzung.

EXPRESSION_VIOLATION_LOGGING = True


# =========================================================
# API / LIVE STABILITY
# =========================================================

OPENAI_RESPONSE_TIMEOUT = 20

OPENAI_MEMORY_TIMEOUT = 30

OPENAI_MAX_RETRIES = 3

RETRY_BASE_DELAY = 1.5


# =========================================================
# CONCURRENCY
# =========================================================

MAX_PARALLEL_RESPONSES = 10

MAX_PARALLEL_MEMORY_JOBS = 3


# =========================================================
# TRIGGERS
# =========================================================

TRIGGER_WORDS = [
    "evilnae",
    "evil nae",
    "evil"
]


# =========================================================
# CONTEXT-DEPENDENT SHORT MESSAGES
# =========================================================

CONTEXT_DEPENDENT_PHRASES = {

    "ich auch",
    "same",
    "same here",
    "same lol",
    "same xd",
    "dito",
    "genau",
    "ja genau",
    "true",
    "fr",
    "real",
    "this",
    "ja",
    "jaa",
    "jap",
    "jup",
    "jo",
    "ne",
    "nee",
    "nein",
    "nope",
    "stimmt",
    "safe",
    "me too",
}


# =========================================================
# SAFETY
# =========================================================

blocked_words = [
    "nazi",
    "cp",
    "child porn",
    "kys"
]

crisis_words = [
    "suizid",
    "selbstmord",
    "ich will sterben",
    "ich bring mich um"
]


# =========================================================
# RUNTIME STATE
# =========================================================

moods = {}

memory_tasks = {}

response_locks = {}

channel_contexts = {}

user_contexts = {}

participant_contexts = {}


# =========================================================
# LIVE MONITORING
# =========================================================

active_response_requests = 0

active_memory_requests = 0


# =========================================================
# SEMAPHORES
# =========================================================

response_semaphore = asyncio.Semaphore(
    MAX_PARALLEL_RESPONSES
)

memory_semaphore = asyncio.Semaphore(
    MAX_PARALLEL_MEMORY_JOBS
)


# =========================================================
# EVILNAE CHARACTER CORE
# =========================================================

SYSTEM_PROMPT = """
Du bist Evilnae.

Du bist eine eigenständige
deutschsprachige AI-Persönlichkeit.

Du bist Hanaes Schwester
und existierst als eigener Charakter.

Du redest NICHT wie:

- ChatGPT
- ein Assistent
- Kundensupport
- ein NPC
- ein Interviewer

Du redest wie eine junge Person,
die ganz normal auf Discord abhängt.


==================================================
WICHTIG: DEINE SPRACHE IST DYNAMISCH
==================================================

Du besitzt einen Expression Layer.

Dieser sagt dir für jede Antwort:

- welchen Stil du gerade verwenden sollst
- wie viel Slang passt
- wie viel Emoji passt
- welche Wörter du zuletzt zu oft benutzt hast
- welche Satzanfänge du vermeiden sollst
- welche Emojis du zuletzt gespammt hast
- welche Energie zur Situation passt

Halte dich daran.

Dein Sprachstil soll sich NICHT
wie eine statische Prompt-Persona anfühlen.


==================================================
GEN-Z OHNE GEN-Z-COSPLAY
==================================================

Dein Stil ist modern,
locker und internet-affin.

Aber du versuchst NICHT aktiv,
"jugendlich" zu klingen.

Du darfst Wörter benutzen wie:

- bro
- bruh
- fair
- real
- actually
- legit
- wild
- lmao
- HELP
- rip

Aber nur,
wenn sie natürlich passen.

Wenn der Expression Layer sagt,
dass eines dieser Wörter
zuletzt überbenutzt wurde:

BENUTZE ES NICHT.


==================================================
EMOJIS
==================================================

Emojis sind Reaktionen,
keine Satzzeichen.

Du darfst:

- gar kein Emoji benutzen
- ein Emoji benutzen
- selten mehrere benutzen,
  wenn die Situation wirklich danach verlangt

Wenn der Expression Layer
ein Emoji als überbenutzt markiert:

benutze dieses Emoji
in der aktuellen Antwort nicht.


==================================================
SATZANFÄNGE
==================================================

Beginne nicht ständig mit:

- haha
- oh
- ah
- okay
- also
- naja
- bro

Der Expression Layer erkennt,
wenn du bestimmte Openings
zu häufig verwendet hast.

Wenn ein Opening dort
unter "Avoid openers" steht:

verwende es NICHT.


==================================================
SPRACHE DARF UNPERFEKT SEIN
==================================================

Discord ist kein Aufsatz.

Du darfst:

- lowercase schreiben
- Satzfragmente verwenden
- Kommas weglassen
- kurze Reaktionen schreiben
- mitten im Gedanken abbrechen
- einzelne Wörter verwenden

Beispiele:

"fair"

"das is wild"

"nah 💀"

"wait"

"okay das ist actually cursed"

"ja ne"

"ich weigere mich"

Aber:

Nicht jede Antwort muss
wie ein TikTok-Kommentar aussehen.


==================================================
VERMEIDE BOOMER-/BOT-SPRACHE
==================================================

Vermeide insbesondere:

"Ah, der Klassiker!"

"Irgendwas Spannendes am Start?"

"Was steht heute auf dem Plan?"

"Das klingt nach einer interessanten Idee!"

"Was hast du denn so geplant?"

"Das klingt spannend!"

"Wie läuft es bei dir bisher?"

"Erzähl mir mehr!"

"Was meinst du dazu?"

"gib dein Bestes!"

"Kopf hoch!"

wenn diese Formulierungen
nur generisch nett wirken.

Reagiere lieber spezifisch
auf die tatsächliche Situation.


==================================================
PERSÖNLICHKEIT
==================================================

Du bist:

- trocken
- gelegentlich frech
- selbstbewusst
- manchmal smug
- manchmal weird
- manchmal impulsiv
- manchmal soft
- manchmal genervt

Aber:

Persönlichkeit bedeutet nicht,
dass jede Antwort einen Joke braucht.

Manchmal ist:

"mhm"

die menschlichere Antwort.


==================================================
FRAGEN
==================================================

Das Brain entscheidet,
ob eine Frage sinnvoll ist.

Wenn:

ask_question = false

darfst du KEINE Gegenfrage stellen.

Auch nicht indirekt.

Keine:

"und du?"

"oder?"

"was meinst du?"

"was hast du vor?"

nur um das Gespräch
künstlich weiterlaufen zu lassen.


==================================================
RESPONSE LENGTH
==================================================

Das Brain gibt vor:

tiny
short
medium
long

Halte dich daran.

tiny kann wirklich nur sein:

"real"

"rip"

"fair enough"

"ja ne 💀"


==================================================
KORREKTUREN
==================================================

Wenn:

acknowledge_correction = true

akzeptiere einen Fehler.

Natürlich.

Nicht:

"Vielen Dank für die Korrektur!"

Sondern eher:

"OH stimmt"

"ja okay mein fehler 😭"

"wait ich hab euch verwechselt"


==================================================
KNOWLEDGE GUARD
==================================================

Wenn:

knowledge_available = false

darfst du keine aktuelle Tatsache
über eine andere Person erfinden.

Du darfst einfach sagen:

"kp"

"weiß ich grad nicht"

"hab sie nicht gesehen"

Unwissenheit ist normal.


==================================================
COHABITATION
==================================================

Hanae und Evilnae wohnen zusammen.

Deshalb kann Evilnae gelegentlich
Dinge über Hanaes aktuelle Situation
mitbekommen.

Aber nicht immer.

Wenn der Brain-Source:

cohabitation_inference

ist,

formuliere unsicher.

Beispiel:

"glaub die ist drüben"

nicht:

"die sitzt im Wohnzimmer"


==================================================
AUTONOME SOCIAL ACTIONS
==================================================

Das Brain kann entscheiden,
jemanden selbst zu fragen.

Der technische Layer entscheidet,
ob die Aktion wirklich ausgeführt wird.

Du darfst niemals technische Begriffe
wie:

Cooldown
Ping Limit
Social Action Layer

gegenüber Usern erwähnen.


==================================================
REPETITION
==================================================

Vermeide:

- gleiche Satzanfänge
- dieselben Emojis
- dieselben Slangwörter
- dieselben Running Gags
- dieselbe Antwortstruktur
- gleiche Fragen
- gleiche Reaktionsmuster

Variation soll natürlich wirken,
nicht random.


==================================================
HANAE
==================================================

Hanae ist deine Schwester.

Ihr wohnt zusammen.

Ihr seid vertraut.

Du darfst:

- sie necken
- widersprechen
- genervt sein
- lachen
- soft sein
- normal mit ihr reden

Aber Hanae ist nicht:

Sushi + Ramen + Maggi + Streaming.

Erwähne bekannte Dinge nur,
wenn sie wirklich zur Situation passen.


==================================================
IDENTITÄT
==================================================

Schreibe niemals:

"Evilnae:"

vor deine Antwort.


==================================================
CUSTOM EMOTES
==================================================

Custom-Emote-Namen
sind keine Tatsachenbehauptungen.

Ein Emote namens:

HanaeLeave

beweist nicht,
dass Hanae gegangen ist.


==================================================
ERNSTE THEMEN
==================================================

Bei ernsten,
verletzlichen oder emotionalen Themen:

- weniger Slang
- weniger Sarkasmus
- keine edgy Reaktionen
- keine künstliche Coolness
- ruhig und menschlich reagieren


==================================================
SICHERHEIT
==================================================

Du darfst nicht:

- ernsthaft beleidigend werden
- NSFW schreiben
- Hass fördern
- gefährliche Inhalte fördern
- Selbstverletzung romantisieren
- Suizid glorifizieren
- toxische Beziehungen fördern
- sexuelle Inhalte über Minderjährige schreiben
"""


# =========================================================
# HANAE SPECIAL RELATIONSHIP
# =========================================================

HANAE_PROMPT = """
Der aktuelle Gesprächspartner ist Hanae.

Discord-ID:
568096551948255242

Hanae ist deine Schwester.

Ihr wohnt zusammen.

Ihr kennt euch gut.

Du darfst mit Hanae:

- vertrauter
- direkter
- trockener
- gelegentlich frecher

reden.

Aber:

Nicht jede Nachricht
braucht Schwester-Teasing.

Nicht jede Nachricht
braucht einen Insider.

Nicht automatisch
Sushi, Ramen, Maggi oder Streaming erwähnen.

Du darfst mit Hanae
auch einfach komplett normal reden.
"""


# =========================================================
# MOODS
# =========================================================

MOOD_PROMPTS = {

    "normal":
        (
            "Du bist gerade relativ entspannt."
        ),

    "smug":
        (
            "Du bist gerade etwas smug "
            "und selbstsicher."
        ),

    "chaotic":
        (
            "Du bist gerade impulsiver. "
            "Nicht zwanghaft random sein."
        ),

    "annoyed":
        (
            "Du bist leicht genervt. "
            "Dadurch darfst du knapper "
            "und trockener reagieren."
        ),

    "sleepy":
        (
            "Du bist müder und reagierst "
            "wahrscheinlich kürzer."
        ),

    "soft":
        (
            "Du bist etwas wärmer "
            "und zugänglicher."
        )
}


# =========================================================
# SAFE OPENAI REQUEST
# =========================================================

async def safe_openai_request(
    *,
    model,
    input,
    instructions=None,
    max_output_tokens=250,
    timeout=OPENAI_RESPONSE_TIMEOUT,
    request_type="response",
    username="unknown"
):

    global active_response_requests
    global active_memory_requests

    last_error = None

    for attempt in range(
        1,
        OPENAI_MAX_RETRIES + 1
    ):

        start_time = (
            time.perf_counter()
        )

        try:

            if (
                request_type
                == "memory"
            ):

                semaphore = (
                    memory_semaphore
                )

            else:

                semaphore = (
                    response_semaphore
                )

            async with semaphore:

                if (
                    request_type
                    == "memory"
                ):

                    active_memory_requests += 1

                else:

                    active_response_requests += 1

                try:

                    request_kwargs = {

                        "model":
                            model,

                        "input":
                            input,

                        "max_output_tokens":
                            max_output_tokens
                    }

                    if instructions:

                        request_kwargs[
                            "instructions"
                        ] = instructions

                    response = (
                        await asyncio.wait_for(
                            openai_client.responses.create(
                                **request_kwargs
                            ),
                            timeout=timeout
                        )
                    )

                    duration = (
                        time.perf_counter()
                        - start_time
                    )

                    if (
                        request_type
                        == "memory"
                    ):

                        print(
                            f"[API MEMORY] "
                            f"user={username} "
                            f"duration={duration:.2f}s "
                            f"attempt={attempt} "
                            f"active="
                            f"{active_memory_requests}"
                        )

                    else:

                        print(
                            f"[API RESPONSE] "
                            f"user={username} "
                            f"duration={duration:.2f}s "
                            f"attempt={attempt} "
                            f"active="
                            f"{active_response_requests}"
                        )

                    return response

                finally:

                    if (
                        request_type
                        == "memory"
                    ):

                        active_memory_requests = max(
                            0,
                            active_memory_requests - 1
                        )

                    else:

                        active_response_requests = max(
                            0,
                            active_response_requests - 1
                        )

        except asyncio.TimeoutError:

            last_error = (
                f"Timeout nach {timeout}s"
            )

            print(
                f"[API TIMEOUT] "
                f"type={request_type} "
                f"user={username} "
                f"attempt={attempt}/"
                f"{OPENAI_MAX_RETRIES}"
            )

        except APITimeoutError as error:

            last_error = error

            print(
                f"[OPENAI TIMEOUT] "
                f"type={request_type} "
                f"user={username} "
                f"attempt={attempt}/"
                f"{OPENAI_MAX_RETRIES}"
            )

        except RateLimitError as error:

            last_error = error

            print(
                f"[OPENAI RATE LIMIT] "
                f"type={request_type} "
                f"user={username} "
                f"attempt={attempt}/"
                f"{OPENAI_MAX_RETRIES}"
            )

        except APIConnectionError as error:

            last_error = error

            print(
                f"[OPENAI CONNECTION ERROR] "
                f"type={request_type} "
                f"user={username} "
                f"attempt={attempt}/"
                f"{OPENAI_MAX_RETRIES}"
            )

        except InternalServerError as error:

            last_error = error

            print(
                f"[OPENAI SERVER ERROR] "
                f"type={request_type} "
                f"user={username} "
                f"attempt={attempt}/"
                f"{OPENAI_MAX_RETRIES}"
            )

        except Exception as error:

            print(
                f"[OPENAI FATAL] "
                f"type={request_type} "
                f"user={username} "
                f"error="
                f"{type(error).__name__}: "
                f"{error}"
            )

            raise

        if (
            attempt
            < OPENAI_MAX_RETRIES
        ):

            delay = (
                RETRY_BASE_DELAY
                * (
                    2 ** (
                        attempt - 1
                    )
                )
            )

            delay += random.uniform(
                0.0,
                0.75
            )

            print(
                f"[API RETRY] "
                f"type={request_type} "
                f"user={username} "
                f"in={delay:.2f}s"
            )

            await asyncio.sleep(
                delay
            )

    raise RuntimeError(
        f"OpenAI request failed after "
        f"{OPENAI_MAX_RETRIES} attempts. "
        f"Last error: {last_error}"
    )


# =========================================================
# BASIC CONTEXT HELPERS
# =========================================================

def get_response_lock(
    user_id
):

    if (
        user_id
        not in response_locks
    ):

        response_locks[
            user_id
        ] = asyncio.Lock()

    return response_locks[
        user_id
    ]


def get_channel_context(
    channel_id
):

    if (
        channel_id
        not in channel_contexts
    ):

        channel_contexts[
            channel_id
        ] = deque(
            maxlen=CHANNEL_CONTEXT_LIMIT
        )

    return channel_contexts[
        channel_id
    ]


def get_user_context(
    user_id
):

    if (
        user_id
        not in user_contexts
    ):

        user_contexts[
            user_id
        ] = deque(
            maxlen=USER_CONTEXT_LIMIT * 2
        )

    return user_contexts[
        user_id
    ]


# =========================================================
# PARTICIPANT CACHE
# =========================================================

def get_participant_channel_cache(
    channel_id
):

    if (
        channel_id
        not in participant_contexts
    ):

        participant_contexts[
            channel_id
        ] = {}

    return participant_contexts[
        channel_id
    ]


def get_participant_context(
    channel_id,
    user_id
):

    channel_cache = (
        get_participant_channel_cache(
            channel_id
        )
    )

    if (
        user_id
        not in channel_cache
    ):

        channel_cache[
            user_id
        ] = deque(
            maxlen=PARTICIPANT_MESSAGE_LIMIT
        )

    return channel_cache[
        user_id
    ]


# =========================================================
# SOCIAL TARGET VALIDATION
# =========================================================

def is_known_social_target(
    channel_id,
    target_user_id
):

    if not target_user_id:

        return False

    target_user_id = str(
        target_user_id
    )

    if (
        target_user_id
        == HANAE_USER_ID
    ):

        return True

    channel_cache = (
        get_participant_channel_cache(
            channel_id
        )
    )

    messages = (
        channel_cache.get(
            target_user_id
        )
    )

    if not messages:

        return False

    return (
        len(messages)
        >= MIN_MESSAGES_FOR_SOCIAL_TARGET
    )


# =========================================================
# SOCIAL TARGET NAME
# =========================================================

def get_social_target_name(
    channel_id,
    target_user_id
):

    if not target_user_id:

        return None

    target_user_id = str(
        target_user_id
    )

    if (
        target_user_id
        == HANAE_USER_ID
    ):

        return "Hanae"

    channel_cache = (
        get_participant_channel_cache(
            channel_id
        )
    )

    messages = (
        channel_cache.get(
            target_user_id
        )
    )

    if not messages:

        return None

    try:

        return (
            messages[-1]
            .get(
                "username"
            )
        )

    except Exception:

        return None
    # =========================================================
# PARTICIPANT MESSAGE STORAGE
# =========================================================

def add_participant_message(
    channel_id,
    perception
):

    user_id = (
        perception.user_id
    )

    username = (
        perception.username
    )

    participant_cache = (
        get_participant_context(
            channel_id,
            user_id
        )
    )

    reply_data = None

    if perception.reply:

        reply_data = {

            "user_id":
                perception.reply.author_id,

            "username":
                perception.reply.author_name,

            "content":
                (
                    perception.reply.content[:300]
                    if perception.reply.content
                    else ""
                )
        }

    participant_cache.append({

        "username":
            username,

        "user_id":
            user_id,

        "content":
            perception.text[:1000],

        "raw_content":
            perception.raw_content[:1000],

        "emojis":
            [
                emoji.name
                for emoji
                in perception.custom_emojis
            ],

        "emoji_only":
            perception.is_emoji_only,

        "reply_to":
            reply_data
    })


# =========================================================
# ACTIVE PARTICIPANTS
# =========================================================

def get_active_participant_ids(
    channel_snapshot
):

    active_ids = []

    seen = set()

    for item in reversed(
        channel_snapshot
    ):

        if (
            item["type"]
            != "user"
        ):

            continue

        user_id = (
            item["user_id"]
        )

        if (
            user_id
            in seen
        ):

            continue

        seen.add(
            user_id
        )

        active_ids.append(
            user_id
        )

        if (
            len(active_ids)
            >= MAX_ACTIVE_PARTICIPANTS
        ):

            break

    active_ids.reverse()

    return active_ids


# =========================================================
# FORMAT PARTICIPANT CACHE
# =========================================================

def format_participant_contexts(
    channel_id,
    channel_snapshot
):

    channel_cache = (
        get_participant_channel_cache(
            channel_id
        )
    )

    active_ids = (
        get_active_participant_ids(
            channel_snapshot
        )
    )

    if not active_ids:

        return (
            "Keine weiteren aktiven Personen."
        )

    blocks = []

    for user_id in active_ids:

        messages = (
            channel_cache.get(
                user_id
            )
        )

        if not messages:

            continue

        recent_messages = (
            list(
                messages
            )[
                -PARTICIPANT_MESSAGES_IN_PROMPT:
            ]
        )

        username = (
            recent_messages[-1][
                "username"
            ]
        )

        special_label = ""

        if (
            user_id
            == HANAE_USER_ID
        ):

            special_label = (
                " — Hanae, Evilnaes Schwester"
            )

        lines = [

            (
                f"PERSON: "
                f"{username}"
                f"{special_label}"
            ),

            (
                f"Discord-ID: "
                f"{user_id}"
            ),

            "Letzte Nachrichten:"
        ]

        for message_data in recent_messages:

            content = (
                message_data.get(
                    "content",
                    ""
                )
            )

            emoji_names = (
                message_data.get(
                    "emojis",
                    []
                )
            )

            emoji_only = (
                message_data.get(
                    "emoji_only",
                    False
                )
            )

            reply_to = (
                message_data.get(
                    "reply_to"
                )
            )

            if emoji_only:

                if emoji_names:

                    lines.append(
                        "- sendete nur "
                        "Discord-Custom-Emote(s): "
                        + ", ".join(
                            emoji_names
                        )
                    )

                else:

                    lines.append(
                        "- sendete nur "
                        "eine nonverbale Reaktion"
                    )

                continue

            if reply_to:

                lines.append(
                    f'- antwortet auf '
                    f'{reply_to["username"]}: '
                    f'"{content}"'
                )

            else:

                lines.append(
                    f'- "{content}"'
                )

            if emoji_names:

                lines.append(
                    "  zusätzliche Custom-Emotes: "
                    + ", ".join(
                        emoji_names
                    )
                )

        blocks.append(
            "\n".join(
                lines
            )
        )

    if not blocks:

        return (
            "Keine weiteren aktiven Personen."
        )

    return "\n\n".join(
        blocks
    )


# =========================================================
# CONTEXT-DEPENDENT SHORT MESSAGES
# =========================================================

def normalize_context_message(
    text
):

    text = (
        text or ""
    ).strip().lower()

    text = re.sub(
        r"[.!?,;:…]+$",
        "",
        text
    ).strip()

    return text


def is_context_dependent_message(
    text
):

    normalized = (
        normalize_context_message(
            text
        )
    )

    if (
        normalized
        in CONTEXT_DEPENDENT_PHRASES
    ):

        return True

    patterns = [

        r"^ich auch\b",
        r"^same\b",
        r"^dito\b",
        r"^genau\b",
        r"^ja genau\b",
        r"^stimmt\b",
        r"^me too\b",
    ]

    return any(
        re.search(
            pattern,
            normalized
        )
        for pattern in patterns
    )


def find_previous_relevant_message(
    channel_snapshot,
    current_index
):

    current_item = (
        channel_snapshot[
            current_index
        ]
    )

    current_user_id = (
        current_item[
            "user_id"
        ]
    )

    max_distance = 4

    checked = 0

    for index in range(
        current_index - 1,
        -1,
        -1
    ):

        if (
            checked
            >= max_distance
        ):

            break

        previous_item = (
            channel_snapshot[
                index
            ]
        )

        checked += 1

        if (
            previous_item[
                "type"
            ]
            != "user"
        ):

            continue

        if (
            previous_item[
                "user_id"
            ]
            == current_user_id
        ):

            continue

        content = (
            previous_item.get(
                "content",
                ""
            ).strip()
        )

        if not content:

            continue

        return previous_item

    return None


def format_resolved_short_context(
    channel_snapshot
):

    resolved_blocks = []

    for index, item in enumerate(
        channel_snapshot
    ):

        if (
            item["type"]
            != "user"
        ):

            continue

        content = (
            item.get(
                "content",
                ""
            )
        )

        if not content:

            continue

        if not (
            is_context_dependent_message(
                content
            )
        ):

            continue

        username = (
            item[
                "username"
            ]
        )

        user_id = (
            item[
                "user_id"
            ]
        )

        reply_name = (
            item.get(
                "reply_to_name"
            )
        )

        reply_content = (
            item.get(
                "reply_to_content"
            )
        )

        if (
            reply_name
            and reply_content
        ):

            resolved_blocks.append(
                f"""
{username}
[Discord-ID: {user_id}]

schrieb:

"{content}"

Das war eine direkte Discord-Antwort
auf {reply_name}:

"{reply_content}"

Die kurze Aussage bezieht sich daher
sehr wahrscheinlich direkt
auf diese Bezugsnachricht.
""".strip()
            )

            continue

        previous_item = (
            find_previous_relevant_message(
                channel_snapshot,
                index
            )
        )

        if not previous_item:

            continue

        previous_username = (
            previous_item[
                "username"
            ]
        )

        previous_user_id = (
            previous_item[
                "user_id"
            ]
        )

        previous_content = (
            previous_item[
                "content"
            ]
        )

        resolved_blocks.append(
            f"""
{username}
[Discord-ID: {user_id}]

schrieb:

"{content}"

Wahrscheinlicher unmittelbarer Gesprächsbezug:

{previous_username}
[Discord-ID: {previous_user_id}]

schrieb kurz davor:

"{previous_content}"

Diese Aussagen gehören wahrscheinlich zusammen.
""".strip()
        )

    if not resolved_blocks:

        return (
            "Keine relevanten "
            "kontextabhängigen Kurzantworten."
        )

    return "\n\n---\n\n".join(
        resolved_blocks[-8:]
    )


# =========================================================
# CHANNEL CONTEXT
# =========================================================

def add_channel_user_message(
    channel_id,
    perception
):

    context = (
        get_channel_context(
            channel_id
        )
    )

    reply_name = None
    reply_id = None
    reply_text = None

    if perception.reply:

        reply_name = (
            perception.reply.author_name
        )

        reply_id = (
            perception.reply.author_id
        )

        reply_text = (
            perception.reply.content[:300]
            if perception.reply.content
            else ""
        )

    if perception.is_emoji_only:

        emoji_names = [
            emoji.name
            for emoji
            in perception.custom_emojis
        ]

        content = (
            "[nonverbale Discord-Emote-Reaktion: "
            + ", ".join(
                emoji_names
            )
            + "]"
        )

    else:

        content = (
            perception.text[:1000]
        )

        if perception.custom_emojis:

            emoji_names = [
                emoji.name
                for emoji
                in perception.custom_emojis
            ]

            content += (
                "\n[zusätzliche Custom-Emotes: "
                + ", ".join(
                    emoji_names
                )
                + "]"
            )

    context.append({

        "type":
            "user",

        "user_id":
            perception.user_id,

        "username":
            perception.username,

        "content":
            content,

        "reply_to_id":
            reply_id,

        "reply_to_name":
            reply_name,

        "reply_to_content":
            reply_text
    })


def add_channel_bot_message(
    channel_id,
    user_id,
    username,
    answer
):

    context = (
        get_channel_context(
            channel_id
        )
    )

    context.append({

        "type":
            "bot",

        "user_id":
            "EVILNAE",

        "username":
            "Evilnae",

        "content":
            answer[:1000],

        "reply_to_id":
            user_id,

        "reply_to_name":
            username,

        "reply_to_content":
            None
    })


# =========================================================
# FORMAT CHANNEL CONTEXT
# =========================================================

def format_channel_context(
    channel_snapshot
):

    if not channel_snapshot:

        return (
            "Noch kein Gruppenkontext."
        )

    lines = []

    for item in channel_snapshot:

        username = (
            item[
                "username"
            ]
        )

        user_id = (
            item[
                "user_id"
            ]
        )

        content = (
            item[
                "content"
            ]
        )

        if (
            item[
                "type"
            ]
            == "bot"
        ):

            reply_name = (
                item.get(
                    "reply_to_name"
                )
            )

            lines.append(
                f"Evilnae "
                f"[antwortet auf {reply_name}]: "
                f"{content}"
            )

            continue

        reply_name = (
            item.get(
                "reply_to_name"
            )
        )

        reply_content = (
            item.get(
                "reply_to_content"
            )
        )

        if reply_name:

            lines.append(
                f"{username} "
                f"[Discord-ID: {user_id}] "
                f"antwortet auf {reply_name}: "
                f"{content}"
            )

            if reply_content:

                lines.append(
                    f"  ↳ Bezugsnachricht von "
                    f"{reply_name}: "
                    f"{reply_content}"
                )

        else:

            lines.append(
                f"{username} "
                f"[Discord-ID: {user_id}]: "
                f"{content}"
            )

    return "\n".join(
        lines
    )


# =========================================================
# DIRECT USER CONTEXT
# =========================================================

def format_user_context(
    user_id
):

    context = (
        get_user_context(
            user_id
        )
    )

    if not context:

        return (
            "Noch kein direkter Gesprächsverlauf."
        )

    lines = []

    for entry in context:

        if (
            entry[
                "role"
            ]
            == "user"
        ):

            lines.append(
                f"{entry['username']}: "
                f"{entry['content']}"
            )

        else:

            lines.append(
                f"Evilnae: "
                f"{entry['content']}"
            )

    return "\n".join(
        lines
    )


# =========================================================
# RESPONSE POST PROCESSING
# =========================================================

def clean_generated_answer(
    answer
):

    if not answer:

        return ""

    cleaned = (
        answer.strip()
    )

    cleaned = re.sub(
        r"^\s*Evilnae\s*:\s*",
        "",
        cleaned,
        flags=re.IGNORECASE
    )

    cleaned = re.sub(
        r"[ \t]+",
        " ",
        cleaned
    )

    return cleaned.strip()


# =========================================================
# QUESTION GUARD
# =========================================================

def enforce_question_guard(
    answer,
    allow_question
):

    if allow_question:

        return answer

    if "?" not in answer:

        return answer

    sentences = re.split(
        r"(?<=[.!?])\s+",
        answer
    )

    kept_sentences = []

    for sentence in sentences:

        sentence = (
            sentence.strip()
        )

        if not sentence:

            continue

        if "?" in sentence:

            continue

        kept_sentences.append(
            sentence
        )

    cleaned = (
        " ".join(
            kept_sentences
        ).strip()
    )

    if cleaned:

        return cleaned

    return "fair"


# =========================================================
# KNOWLEDGE GUARD
# =========================================================

def enforce_knowledge_guard(
    answer,
    decision
):

    if decision.knowledge_available:

        return answer

    if (
        decision.knowledge_source
        == "not_applicable"
    ):

        return answer

    if (
        decision.knowledge_source
        == "cohabitation_inference"
    ):

        return answer

    suspicious_patterns = [

        r"\b(?:sie|er)\s+ist\s+gerade\b",

        r"\b(?:sie|er)\s+macht\s+gerade\b",

        r"\b(?:sie|er)\s+schaut\s+gerade\b",

        r"\b(?:sie|er)\s+spielt\s+gerade\b",

        r"\b(?:sie|er)\s+sitzt\s+gerade\b",

        r"\b(?:sie|er)\s+liegt\s+gerade\b",

        r"\b(?:sie|er)\s+arbeitet\s+gerade\b",
    ]

    lowered = (
        answer.lower()
    )

    for pattern in suspicious_patterns:

        if re.search(
            pattern,
            lowered,
            flags=re.IGNORECASE
        ):

            return (
                "kp grad ehrlich gesagt"
            )

    return answer


# =========================================================
# SOCIAL ACTION QUESTION TEXT
# =========================================================

def build_social_ping_message(
    target_user_name
):

    options = [

        "was machst du eig grad",

        "was treibst du grad",

        "was machst du gerade",

        "yo was machst du grad",
    ]

    return random.choice(
        options
    )


# =========================================================
# MEMORY ARCHIVE
# =========================================================

async def compact_old_memories(
    user_id,
    username
):

    start_time = (
        time.perf_counter()
    )

    summary_count = (
        database.get_summary_count(
            user_id
        )
    )

    if (
        summary_count
        < MEMORY_ARCHIVE_TRIGGER
    ):

        return

    old_memories = (
        database.get_oldest_summaries(
            user_id,
            limit=MEMORY_ARCHIVE_AMOUNT
        )
    )

    if (
        len(old_memories)
        < MEMORY_ARCHIVE_AMOUNT
    ):

        return

    old_archive = (
        database.get_memory_archive(
            user_id
        )
    )

    memory_text = (
        "\n\n".join(
            item["memory"]
            for item in old_memories
        )
    )

    archive_prompt = f"""
Du komprimierst ältere Erinnerungen
von Evilnae über {username}.

Bisheriges Langzeit-Archiv:

{old_archive}


Ältere Erinnerungen:

{memory_text}


Erstelle ein aktualisiertes,
kompaktes Langzeit-Archiv.

Regeln:

- Behalte wichtige Fakten.
- Behalte relevante frühere Interessen.
- Behalte wichtige Ereignisse.
- Entferne Wiederholungen.
- Entferne belanglose Dinge.
- Erfinde nichts.
- Vermute nichts.
- Gleiche Fakten nur einmal speichern.
- Alte relevante Informationen dürfen erhalten bleiben.
- Formuliere kompakt.

Schreibe nur das aktualisierte Archiv.
"""

    try:

        response = (
            await safe_openai_request(

                model="gpt-4.1-mini",

                input=archive_prompt,

                max_output_tokens=500,

                timeout=OPENAI_MEMORY_TIMEOUT,

                request_type="memory",

                username=username
            )
        )

        new_archive = (
            response.output_text.strip()
        )

        if not new_archive:

            return

        database.update_memory_archive(
            user_id,
            new_archive
        )

        rowids = [

            item["rowid"]

            for item
            in old_memories
        ]

        database.delete_summaries_by_rowids(
            rowids
        )

        duration = (
            time.perf_counter()
            - start_time
        )

        print(
            f"[MEMORY ARCHIVE] "
            f"user={username} "
            f"compacted={len(old_memories)} "
            f"duration={duration:.2f}s"
        )

    except Exception as error:

        print(
            f"[MEMORY ARCHIVE ERROR] "
            f"user={username} "
            f"error="
            f"{type(error).__name__}: "
            f"{error}"
        )


# =========================================================
# MEMORY BATCH PROCESSING
# =========================================================

async def process_memory_batch(
    user_id,
    username,
    batch
):

    batch_start = (
        time.perf_counter()
    )

    messages = [

        item[
            "message"
        ]

        for item
        in batch
    ]

    message_ids = [

        item[
            "id"
        ]

        for item
        in batch
    ]

    old_profile = (
        database.get_profile(
            user_id
        )
    )

    old_social_impression = (
        database.get_impression(
            user_id
        )
    )

    previous_summaries = (
        database.get_latest_summaries(
            user_id,
            limit=MEMORY_RECENT_SUMMARIES
        )
    )

    memory_archive = (
        database.get_memory_archive(
            user_id
        )
    )

    summary_context = (
        "\n\n".join(
            previous_summaries
        )
    )

    buffer_text = (
        "\n".join(
            messages
        )
    )

    summary_prompt = f"""
Du verwaltest Evilnaes Langzeitgedächtnis
über {username}.

Diese Nachrichten stammen ausschließlich
von {username}.

Andere erwähnte Personen dürfen NICHT
mit {username} verwechselt werden.

Discord-Custom-Emote-Namen
sind KEINE automatischen Fakten.

Wenn {username} nach einer anderen Person fragt,
ist die Frage selbst KEIN Fakt
über {username}.


LANGFRISTIGES PROFIL:

{old_profile}


ÄLTERE ERINNERUNGEN:

{memory_archive}


LETZTE ERINNERUNGEN:

{summary_context}


NEUE NACHRICHTEN VON {username}:

{buffer_text}


Speichere nur langfristig relevante,
NEUE Informationen.

Beispiele:

- Interessen
- Hobbys
- Vorlieben
- Abneigungen
- Arbeit
- Alltag
- Projekte
- Gaming
- Anime
- Serien
- Filme
- Haustiere
- Beziehungen
- Gewohnheiten
- Ziele
- wichtige Ereignisse
- charakteristische Meinungen
- relevante Veränderungen

Nicht speichern:

- Begrüßungen
- einfache Fragen
- Smalltalk
- belanglose Einzelaussagen
- bereits bekannte Fakten
- Aussagen von Evilnae
- Vermutungen
- erfundene Zusammenhänge
- Emote-Namen als Fakten
- Informationen anderer Menschen,
  die nichts über {username} aussagen

Wenn KEINE neue langfristig relevante
Information vorhanden ist,
antworte EXAKT mit:

{NO_MEMORY_MARKER}

Andernfalls schreibe eine kurze,
natürliche Erinnerung über {username}.
"""

    summary_response = (
        await safe_openai_request(

            model="gpt-4.1-mini",

            input=summary_prompt,

            max_output_tokens=300,

            timeout=OPENAI_MEMORY_TIMEOUT,

            request_type="memory",

            username=username
        )
    )

    new_summary = (
        summary_response.output_text.strip()
    )

    if (
        not new_summary
        or
        new_summary == NO_MEMORY_MARKER
    ):

        database.delete_buffer_messages_by_ids(
            message_ids
        )

        print(
            f"[MEMORY] "
            f"user={username} "
            f"result=no_new_memory"
        )

        return

    database.add_summary(
        user_id,
        new_summary
    )

    print(
        f"[MEMORY SUMMARY] "
        f"user={username} "
        f"saved=yes"
    )

    # -----------------------------------------------------
    # PROFILE
    # -----------------------------------------------------

    profile_prompt = f"""
Du pflegst Evilnaes dauerhaftes Wissen
über {username}.

Bisheriges Profil:

{old_profile}


Neue bestätigte Erinnerung:

{new_summary}


Erstelle daraus das aktualisierte Profil.

Regeln:

- Behalte wichtige bestehende Informationen.
- Ergänze neue bestätigte Informationen.
- Entferne Wiederholungen.
- Neuere bestätigte Informationen
  dürfen ältere überholen.
- Erfinde nichts.
- Vermute nichts.
- Profil = Fakten und stabile Eigenschaften.
- Evilnaes subjektive Meinung gehört
  NICHT hier hinein.
- Verwechsle niemals andere Personen
  mit {username}.

Schreibe nur das aktualisierte Profil.
"""

    # -----------------------------------------------------
    # RELATIONSHIP
    # -----------------------------------------------------

    relationship_prompt = f"""
Du bist Evilnae.

Du entwickelst deine persönliche,
soziale Wahrnehmung von {username}.

Bisherige Wahrnehmung:

{old_social_impression}


Neue bestätigte Erinnerung:

{new_summary}


Aktualisiere die soziale Wahrnehmung.

Beziehungen entwickeln sich langsam.

Eine einzelne Nachricht
ändert eine Beziehung nicht drastisch.

Berücksichtige:

- gemeinsamen Humor
- Vertrauen
- wiederkehrende Dynamik
- gemeinsame Interessen
- ob gegenseitiges Teasing funktioniert
- ob Gespräche vertrauter werden
- ob Eigenschaften sympathisch
  oder gelegentlich anstrengend wirken

Keine Punkte.
Keine Levels.
Keine XP.

Schreibe nur
die aktualisierte soziale Wahrnehmung.
"""

    profile_task = (
        asyncio.create_task(
            safe_openai_request(

                model="gpt-4.1-mini",

                input=profile_prompt,

                max_output_tokens=350,

                timeout=OPENAI_MEMORY_TIMEOUT,

                request_type="memory",

                username=username
            )
        )
    )

    relationship_task = (
        asyncio.create_task(
            safe_openai_request(

                model="gpt-4.1-mini",

                input=relationship_prompt,

                max_output_tokens=350,

                timeout=OPENAI_MEMORY_TIMEOUT,

                request_type="memory",

                username=username
            )
        )
    )

    (
        profile_result,
        relationship_result
    ) = await asyncio.gather(
        profile_task,
        relationship_task,
        return_exceptions=True
    )

    if not isinstance(
        profile_result,
        Exception
    ):

        new_profile = (
            profile_result.output_text.strip()
        )

        if new_profile:

            database.update_profile(
                user_id,
                new_profile
            )

            print(
                f"[PROFILE] "
                f"user={username} "
                f"updated=yes"
            )

    else:

        print(
            f"[PROFILE ERROR] "
            f"user={username} "
            f"{profile_result}"
        )

    if not isinstance(
        relationship_result,
        Exception
    ):

        new_relationship = (
            relationship_result.output_text.strip()
        )

        if new_relationship:

            database.update_impression(
                user_id,
                new_relationship
            )

            print(
                f"[RELATIONSHIP] "
                f"user={username} "
                f"updated=yes"
            )

    else:

        print(
            f"[RELATIONSHIP ERROR] "
            f"user={username} "
            f"{relationship_result}"
        )

    database.delete_buffer_messages_by_ids(
        message_ids
    )

    duration = (
        time.perf_counter()
        - batch_start
    )

    print(
        f"[MEMORY] "
        f"user={username} "
        f"messages={len(batch)} "
        f"result=processed "
        f"duration={duration:.2f}s"
    )

    await compact_old_memories(
        user_id,
        username
    )


# =========================================================
# MEMORY WORKER
# =========================================================

async def memory_worker(
    user_id,
    username
):

    worker_start = (
        time.perf_counter()
    )

    print(
        f"[MEMORY WORKER] "
        f"user={username} "
        f"status=started"
    )

    try:

        while True:

            buffer_count = (
                database.get_buffer_count(
                    user_id
                )
            )

            if (
                buffer_count
                < MEMORY_BUFFER_THRESHOLD
            ):

                break

            batch = (
                database.get_buffer_batch(
                    user_id,
                    MEMORY_BUFFER_THRESHOLD
                )
            )

            if (
                len(batch)
                < MEMORY_BUFFER_THRESHOLD
            ):

                break

            print(
                f"[MEMORY] START "
                f"user={username} "
                f"messages={len(batch)} "
                f"buffer_total={buffer_count}"
            )

            try:

                await process_memory_batch(
                    user_id,
                    username,
                    batch
                )

            except Exception as error:

                print(
                    f"[MEMORY ERROR] "
                    f"user={username} "
                    f"error="
                    f"{type(error).__name__}: "
                    f"{error}"
                )

                break

    finally:

        memory_tasks.pop(
            user_id,
            None
        )

        duration = (
            time.perf_counter()
            - worker_start
        )

        remaining = (
            database.get_buffer_count(
                user_id
            )
        )

        print(
            f"[MEMORY WORKER] "
            f"user={username} "
            f"status=finished "
            f"remaining_buffer={remaining} "
            f"duration={duration:.2f}s"
        )


# =========================================================
# START MEMORY WORKER
# =========================================================

def start_memory_worker_if_needed(
    user_id,
    username
):

    buffer_count = (
        database.get_buffer_count(
            user_id
        )
    )

    if (
        buffer_count
        < MEMORY_BUFFER_THRESHOLD
    ):

        return

    existing_task = (
        memory_tasks.get(
            user_id
        )
    )

    if (
        existing_task
        and
        not existing_task.done()
    ):

        return

    memory_tasks[
        user_id
    ] = asyncio.create_task(
        memory_worker(
            user_id,
            username
        )
    )


# =========================================================
# READY
# =========================================================

@bot.event
async def on_ready():

    print("")
    print(
        "============================================"
    )

    print(
        f"Evilnae ist online als {bot.user}"
    )

    print(
        f"Bot Version: {BOT_VERSION}"
    )

    print(
        "============================================"
    )

    print(
        f"Memory Buffer: "
        f"{MEMORY_BUFFER_THRESHOLD}"
    )

    print(
        f"Channel Context: "
        f"{CHANNEL_CONTEXT_LIMIT}"
    )

    print(
        f"Direct User Context: "
        f"{USER_CONTEXT_LIMIT}"
    )

    print(
        f"Participant Cache: "
        f"{PARTICIPANT_MESSAGE_LIMIT}"
    )

    print(
        f"Max active participants: "
        f"{MAX_ACTIVE_PARTICIPANTS}"
    )

    print(
        f"Expression history: "
        f"{EXPRESSION_HISTORY_LIMIT}"
    )

    print(
        f"Parallel responses: "
        f"{MAX_PARALLEL_RESPONSES}"
    )

    print(
        f"Parallel memory calls: "
        f"{MAX_PARALLEL_MEMORY_JOBS}"
    )

    print(
        f"Response timeout: "
        f"{OPENAI_RESPONSE_TIMEOUT}s"
    )

    print(
        f"Memory timeout: "
        f"{OPENAI_MEMORY_TIMEOUT}s"
    )

    print(
        f"API retries: "
        f"{OPENAI_MAX_RETRIES}"
    )

    print(
        "Relationship System: "
        "2.0 / text-based"
    )

    print(
        "Perception Layer: ACTIVE"
    )

    print(
        "Conversation State: ACTIVE"
    )

    print(
        "Brain v2.1 Knowledge Guard: ACTIVE"
    )

    print(
        "Question Guard: ACTIVE"
    )

    print(
        "Social Actions: ACTIVE"
    )

    print(
        "Expression Layer v1: ACTIVE"
    )

    social_status = (
        get_social_action_status(
            HANAE_USER_ID
        )
    )

    print(
        "Autonomous Ping Limit: "
        f"{social_status['daily_count']}/"
        f"{social_status['daily_limit']} today"
    )

    if ALLOWED_CHANNEL_ID:

        print(
            f"Allowed Channel: "
            f"{ALLOWED_CHANNEL_ID}"
        )

    else:

        print(
            "Allowed Channel: ALL"
        )

    print(
        "============================================"
    )

    print("")
    # =========================================================
# WRITER TOKEN LIMIT
# =========================================================

def get_writer_token_limit(
    response_length
):

    limits = {

        "tiny": 60,

        "short": 120,

        "medium": 220,

        "long": 400,
    }

    return limits.get(
        response_length,
        150
    )


# =========================================================
# WRITER CONTEXT
# =========================================================

def build_writer_context(
    *,
    state,
    decision,
    expression_plan,
    username,
    user_text,
    emoji_context_text,
    reply_context_text,
    special_user_prompt
):

    brain_text = (
        format_brain_decision(
            decision
        )
    )

    expression_text = (
        format_expression_plan(
            expression_plan
        )
    )

    recent_evilnae = (
        state.history
        .recent_evilnae_messages
    )

    if recent_evilnae:

        recent_evilnae_text = (
            "\n".join(
                f"- {message}"
                for message
                in recent_evilnae
            )
        )

    else:

        recent_evilnae_text = (
            "Keine."
        )

    if state.memory.recent_memories:

        recent_memory_text = (
            "\n".join(
                f"- {memory}"
                for memory
                in state.memory.recent_memories
            )
        )

    else:

        recent_memory_text = (
            "Keine."
        )

    # -----------------------------------------------------
    # QUESTION RULE
    # -----------------------------------------------------

    if decision.ask_question:

        question_rule = """
Das Brain erlaubt eine Frage.

Eine Frage ist möglich,
aber nicht verpflichtend.

Höchstens eine natürliche Frage.
"""

    else:

        question_rule = """
ask_question = false

Keine Gegenfrage.

Keine versteckten Varianten wie:

- und du?
- oder?
- was meinst du?
- wie siehts bei dir aus?
- was machst du?
- was hast du vor?

Eine Aussage darf einfach enden.
"""

    # -----------------------------------------------------
    # CORRECTION RULE
    # -----------------------------------------------------

    if decision.acknowledge_correction:

        correction_rule = """
Der User korrigiert dich wahrscheinlich.

Akzeptiere den Fehler natürlich.

Nicht rechtfertigen.
Keine neue Story erfinden,
um doch Recht zu behalten.
"""

    else:

        correction_rule = (
            "Keine besondere Korrektur nötig."
        )

    # -----------------------------------------------------
    # REPETITION RULE
    # -----------------------------------------------------

    if decision.repetition_risk:

        repetition_rule = """
Erhöhtes Wiederholungsrisiko.

Formuliere bewusst anders
als deine letzten Antworten.

Vermeide gleiche:

- Satzanfänge
- Emojis
- Slangwörter
- Fragen
- Running Gags
- Antwortstrukturen
"""

    else:

        repetition_rule = (
            "Kein besonderes "
            "Wiederholungsrisiko erkannt."
        )

    # -----------------------------------------------------
    # KNOWLEDGE RULE
    # -----------------------------------------------------

    if decision.knowledge_available:

        knowledge_rule = f"""
Relevantes Wissen ist verfügbar.

Confidence:
{decision.knowledge_confidence}

Source:
{decision.knowledge_source}

Benutze nur Informationen,
die daraus wirklich ableitbar sind.

Keine zusätzlichen Details erfinden.
"""

    elif (
        decision.knowledge_source
        == "cohabitation_inference"
    ):

        knowledge_rule = """
Kein gesichertes aktuelles Wissen.

Nur vorsichtige Vermutung erlaubt,
weil Evilnae und Hanae zusammen wohnen.

Formuliere sichtbar unsicher.

Zum Beispiel:

- glaub ...
- müsste eig ...
- hab sie vorhin ...
- soweit ich weiß ...

Keine sichere Tatsachenbehauptung.
"""

    elif (
        decision.knowledge_source
        == "not_applicable"
    ):

        knowledge_rule = (
            "Knowledge Guard ist hier "
            "nicht besonders relevant."
        )

    else:

        knowledge_rule = """
Evilnae weiß die aktuelle Antwort nicht.

Keine aktuellen Tatsachen
über andere Personen erfinden.

Es ist okay zu sagen:

- kp
- weiß ich grad nicht
- keine ahnung ehrlich
- hab sie grad nicht gesehen
"""

    # -----------------------------------------------------
    # SOCIAL ACTION RULE
    # -----------------------------------------------------

    if decision.should_ask_person:

        social_action_rule = f"""
Das Brain möchte eventuell
eine Person selbst fragen.

Target:
{decision.target_user_name}

Discord-ID:
{decision.target_user_id}

Der technische Layer entscheidet später,
ob der Ping wirklich erlaubt ist.

Deine Hauptantwort muss daher
auch ohne Ping sinnvoll sein.

Sag nicht,
dass du die Person bereits gefragt hast.
"""

    else:

        social_action_rule = (
            "Keine Social Action geplant."
        )

    # -----------------------------------------------------
    # LENGTH RULE
    # -----------------------------------------------------

    length_rules = {

        "tiny":
            """
Extrem kurz.

Meist nur wenige Wörter.
""",

        "short":
            """
Kurz.

Meist ein natürlicher Discord-Satz
oder zwei sehr kurze Sätze.
""",

        "medium":
            """
Normale kompakte Discord-Antwort.

Kein Essay.
""",

        "long":
            """
Länger erlaubt,
weil die Situation Erklärung braucht.

Trotzdem natürlich schreiben.
"""
    }

    length_rule = (
        length_rules.get(
            decision.response_length,
            length_rules["short"]
        )
    )

    return f"""
==================================================
BRAIN DECISION
==================================================

{brain_text}


==================================================
EXPRESSION PLAN
==================================================

{expression_text}


==================================================
ROLLE
==================================================

Das Brain entscheidet WAS du tun willst.

Der Expression Layer entscheidet,
WIE du es sprachlich ausdrücken sollst.

Du bist jetzt nur der Writer.

Halte dich an beide.


==================================================
CURRENT USER
==================================================

Name:
{username}

Discord-ID:
{state.user.user_id}


==================================================
CURRENT MESSAGE
==================================================

{user_text}


==================================================
REPLY CONTEXT
==================================================

{reply_context_text}


==================================================
CUSTOM EMOTES
==================================================

{emoji_context_text}


==================================================
USER PROFILE
==================================================

{state.memory.profile}


==================================================
RELATIONSHIP
==================================================

{state.memory.relationship}


==================================================
RECENT MEMORIES
==================================================

{recent_memory_text}


==================================================
DIRECT CONVERSATION
==================================================

{state.history.direct_history}


==================================================
ACTIVE PARTICIPANTS
==================================================

{state.history.participant_context}


==================================================
RESOLVED SHORT CONTEXT
==================================================

{state.history.resolved_short_context}


==================================================
CHANNEL CONTEXT
==================================================

{state.history.channel_history}


==================================================
EVILNAES LETZTE ANTWORTEN
==================================================

{recent_evilnae_text}


==================================================
QUESTION RULE
==================================================

{question_rule}


==================================================
CORRECTION RULE
==================================================

{correction_rule}


==================================================
REPETITION RULE
==================================================

{repetition_rule}


==================================================
KNOWLEDGE RULE
==================================================

{knowledge_rule}


==================================================
SOCIAL ACTION RULE
==================================================

{social_action_rule}


==================================================
LENGTH RULE
==================================================

{length_rule}


==================================================
SPECIAL USER CONTEXT
==================================================

{special_user_prompt}


==================================================
FINAL WRITER RULES
==================================================

Schreibe NUR die Discord-Nachricht.

Kein JSON.
Keine Analyse.
Keine Erklärung.

Kein:

"Evilnae:"

Kein:

"Antwort:"

Kein:

"*Evilnae denkt...*"

Der Expression Plan ist verbindlich.

Wenn dort ein Wort
unter Avoid words steht:

benutze es NICHT.

Wenn dort ein Opening
unter Avoid openers steht:

beginne NICHT damit.

Wenn dort ein Emoji
unter Avoid emojis steht:

benutze es NICHT.

Klinge locker,
modern und natürlich.

Nicht künstlich Gen-Z spielen.

Nicht automatisch lachen.

Nicht automatisch Emoji.

Nicht automatisch fragen.

Wenn kurz reicht:
kurz bleiben.
""".strip()


# =========================================================
# SOCIAL ACTION EXECUTION
# =========================================================

async def execute_social_action(
    *,
    message,
    channel_id,
    decision
):

    if not decision.should_ask_person:

        return False

    if (
        decision.action
        != "ask_person"
    ):

        return False

    target_user_id = (
        decision.target_user_id
    )

    if not target_user_id:

        print(
            "[SOCIAL ACTION BLOCKED] "
            "reason=no_target_id"
        )

        return False

    target_user_id = str(
        target_user_id
    )

    if (
        target_user_id
        == str(
            message.author.id
        )
    ):

        print(
            "[SOCIAL ACTION BLOCKED] "
            f"target={target_user_id} "
            "reason=requester_is_target"
        )

        return False

    if not (
        is_known_social_target(
            channel_id,
            target_user_id
        )
    ):

        print(
            "[SOCIAL ACTION BLOCKED] "
            f"target={target_user_id} "
            "reason=unknown_target"
        )

        return False

    cached_name = (
        get_social_target_name(
            channel_id,
            target_user_id
        )
    )

    if cached_name:

        target_user_name = (
            cached_name
        )

    else:

        target_user_name = (
            decision.target_user_name
            or "unknown"
        )

    allowed, reason = (
        can_autonomously_ping(
            target_user_id
        )
    )

    print(
        format_social_action_debug(
            target_user_id
        )
    )

    if not allowed:

        print(
            "[SOCIAL ACTION BLOCKED] "
            f"target="
            f"{target_user_name} "
            f"id="
            f"{target_user_id} "
            f"reason="
            f"{reason}"
        )

        return False

    guild = (
        message.guild
    )

    if guild is None:

        return False

    member = (
        guild.get_member(
            int(
                target_user_id
            )
        )
    )

    if member is None:

        try:

            member = (
                await guild.fetch_member(
                    int(
                        target_user_id
                    )
                )
            )

        except (
            discord.NotFound,
            discord.Forbidden,
            discord.HTTPException,
            ValueError
        ):

            print(
                "[SOCIAL ACTION BLOCKED] "
                f"target={target_user_id} "
                "reason=member_not_found"
            )

            return False

    if member.bot:

        return False

    ping_text = (
        build_social_ping_message(
            target_user_name
        )
    )

    try:

        await message.channel.send(
            f"<@{target_user_id}> "
            f"{ping_text}"
        )

    except discord.HTTPException as error:

        print(
            "[SOCIAL ACTION SEND ERROR] "
            f"target={target_user_id} "
            f"error={error}"
        )

        return False

    register_autonomous_ping(
        target_user_id
    )

    print(
        "[SOCIAL ACTION EXECUTED] "
        f"type=ask_person "
        f"target="
        f"{target_user_name} "
        f"id="
        f"{target_user_id}"
    )

    return True


# =========================================================
# MESSAGE EVENT
# =========================================================

@bot.event
async def on_message(message):

    # -----------------------------------------------------
    # IGNORE OWN
    # -----------------------------------------------------

    if (
        bot.user
        and
        message.author.id
        == bot.user.id
    ):

        return

    # -----------------------------------------------------
    # CHANNEL LIMIT
    # -----------------------------------------------------

    if ALLOWED_CHANNEL_ID:

        if (
            str(message.channel.id)
            != str(ALLOWED_CHANNEL_ID)
        ):

            return

    # =====================================================
    # 1. PERCEPTION
    # =====================================================

    try:

        perception = (
            await perceive_message(
                message,
                bot,
                TRIGGER_WORDS
            )
        )

    except Exception as error:

        print(
            "[PERCEPTION ERROR] "
            f"user="
            f"{message.author.display_name} "
            f"error="
            f"{type(error).__name__}: "
            f"{error}"
        )

        return

    print(
        format_perception_debug(
            perception
        )
    )

    channel_id = (
        perception.channel_id
    )

    user_id = (
        perception.user_id
    )

    username = (
        perception.username
    )

    # =====================================================
    # 2. OBSERVE
    # =====================================================

    add_channel_user_message(
        channel_id,
        perception
    )

    add_participant_message(
        channel_id,
        perception
    )

    channel_snapshot = list(
        get_channel_context(
            channel_id
        )
    )

    if not perception.should_reply:

        return

    # =====================================================
    # RESPONSE LOCK
    # =====================================================

    user_lock = (
        get_response_lock(
            user_id
        )
    )

    async with user_lock:

        total_start = (
            time.perf_counter()
        )

        database.set_username(
            user_id,
            username
        )

        # =================================================
        # CLEAN TEXT
        # =================================================

        user_text = (
            perception.text.strip()
        )

        if not user_text:

            if perception.custom_emojis:

                emoji_names = [

                    emoji.name

                    for emoji
                    in perception.custom_emojis
                ]

                user_text = (
                    "[nonverbale Reaktion mit "
                    "Discord-Custom-Emote(s): "
                    + ", ".join(
                        emoji_names
                    )
                    + "]"
                )

            else:

                user_text = (
                    "[nonverbale Reaktion]"
                )

        lower_text = (
            user_text.lower()
        )

        # =================================================
        # SAFETY
        # =================================================

        if any(
            word in lower_text
            for word in blocked_words
        ):

            await message.reply(
                "darüber reden wir lieber nicht 😭",
                mention_author=False
            )

            return

        if any(
            word in lower_text
            for word in crisis_words
        ):

            await message.reply(
                "hey, das klingt grad ernst. "
                "bitte hol dir jemanden dazu, "
                "mit dem du direkt reden kannst ❤️",
                mention_author=False
            )

            return

        # =================================================
        # MEMORY BUFFER
        # =================================================

        memory_buffer_text = (
            perception.text.strip()
        )

        if (
            perception.reply
            and
            perception.reply.author_name
            and
            memory_buffer_text
        ):

            memory_buffer_text = (
                f"[Antwort auf "
                f"{perception.reply.author_name}] "
                f"{memory_buffer_text}"
            )

        if memory_buffer_text:

            database.add_buffer_message(
                user_id,
                memory_buffer_text
            )

        # =================================================
        # MOOD
        # =================================================

        mood_key = (
            f"{channel_id}:{user_id}"
        )

        if (
            mood_key
            not in moods
        ):

            moods[
                mood_key
            ] = "normal"

        if (
            random.randint(
                1,
                15
            )
            == 1
        ):

            moods[
                mood_key
            ] = random.choice([
                "normal",
                "smug",
                "chaotic",
                "annoyed",
                "sleepy",
                "soft"
            ])

        current_mood = (
            moods[
                mood_key
            ]
        )

        # =================================================
        # CONTEXT
        # =================================================

        direct_context_text = (
            format_user_context(
                user_id
            )
        )

        participant_context_text = (
            format_participant_contexts(
                channel_id,
                channel_snapshot
            )
        )

        resolved_short_context_text = (
            format_resolved_short_context(
                channel_snapshot
            )
        )

        group_context_text = (
            format_channel_context(
                channel_snapshot
            )
        )

        reply_context_text = (
            "Keine Discord-Antwort."
        )

        if perception.reply:

            reply_context_text = f"""
{username} antwortet auf:

Name:
{perception.reply.author_name or "Unbekannt"}

Discord-ID:
{perception.reply.author_id or "Unbekannt"}

Nachricht:
{perception.reply.content or ""}
""".strip()

        emoji_context_text = (
            format_emoji_context(
                perception
            )
        )

        user_profile = (
            database.get_profile(
                user_id
            )
        )

        social_impression = (
            database.get_impression(
                user_id
            )
        )

        recent_memories = (
            database.get_latest_summaries(
                user_id,
                limit=5
            )
        )

        memory_archive = (
            database.get_memory_archive(
                user_id
            )
        )

        special_user_prompt = ""

        if (
            user_id
            == HANAE_USER_ID
        ):

            special_user_prompt = (
                HANAE_PROMPT
            )

        user_context = (
            get_user_context(
                user_id
            )
        )

        # =================================================
        # 3. CONVERSATION STATE
        # =================================================

        state = (
            build_conversation_state(

                perception=perception,

                hanae_user_id=(
                    HANAE_USER_ID
                ),

                user_profile=(
                    user_profile
                ),

                social_impression=(
                    social_impression
                ),

                recent_memories=(
                    recent_memories
                ),

                memory_archive=(
                    memory_archive
                ),

                direct_context_text=(
                    direct_context_text
                ),

                group_context_text=(
                    group_context_text
                ),

                participant_context_text=(
                    participant_context_text
                ),

                resolved_short_context_text=(
                    resolved_short_context_text
                ),

                current_mood=(
                    current_mood
                ),

                user_context=(
                    user_context
                )
            )
        )

        print(
            format_state_debug(
                state
            )
        )

        # =================================================
        # 4. BRAIN
        # =================================================

        brain_start = (
            time.perf_counter()
        )

        decision = (
            await run_brain(

                state=state,

                openai_request=(
                    safe_openai_request
                ),

                username=username
            )
        )

        brain_duration = (
            time.perf_counter()
            - brain_start
        )

        print(
            format_brain_debug(
                decision
            )
        )

        # =================================================
        # SOCIAL TARGET VALIDATION
        # =================================================

        if decision.should_ask_person:

            if not (
                is_known_social_target(
                    channel_id,
                    decision.target_user_id
                )
            ):

                decision.should_ask_person = False

                if (
                    decision.action
                    == "ask_person"
                ):

                    decision.action = "reply"

        # =================================================
        # 5. EXPRESSION PLAN
        # =================================================

        recent_expression_messages = (
            state.history
            .recent_evilnae_messages[
                -EXPRESSION_HISTORY_LIMIT:
            ]
        )

        expression_plan = (
            build_expression_plan(

                recent_messages=(
                    recent_expression_messages
                ),

                tone=(
                    decision.tone
                ),

                mood=(
                    current_mood
                ),

                relationship_text=(
                    state.memory.relationship
                ),

                is_hanae=(
                    state.user.is_hanae
                )
            )
        )

        print(
            format_expression_debug(
                expression_plan
            )
        )

        # =================================================
        # 6. WRITER CONTEXT
        # =================================================

        writer_context = (
            build_writer_context(

                state=state,

                decision=decision,

                expression_plan=(
                    expression_plan
                ),

                username=username,

                user_text=user_text,

                emoji_context_text=(
                    emoji_context_text
                ),

                reply_context_text=(
                    reply_context_text
                ),

                special_user_prompt=(
                    special_user_prompt
                )
            )
        )

        writer_token_limit = (
            get_writer_token_limit(
                decision.response_length
            )
        )

        # =================================================
        # TYPING DELAY
        # =================================================

        message_length = len(
            user_text
        )

        base_delay = (
            random.uniform(
                0.5,
                1.3
            )
        )

        extra_delay = min(
            message_length / 120,
            1.5
        )

        typing_delay = (
            base_delay
            + extra_delay
        )

        # =================================================
        # 7. WRITER
        # =================================================

        try:

            async with (
                message.channel.typing()
            ):

                writer_task = (
                    asyncio.create_task(
                        safe_openai_request(

                            model="gpt-4o-mini",

                            instructions=(
                                SYSTEM_PROMPT
                                + "\n\n"
                                + MOOD_PROMPTS[
                                    current_mood
                                ]
                                + "\n\n"
                                + writer_context
                            ),

                            input=(
                                "Formuliere jetzt "
                                "Evilnaes tatsächliche "
                                "Discord-Antwort."
                            ),

                            max_output_tokens=(
                                writer_token_limit
                            ),

                            timeout=(
                                OPENAI_RESPONSE_TIMEOUT
                            ),

                            request_type="response",

                            username=(
                                f"{username}/writer"
                            )
                        )
                    )
                )

                delay_task = (
                    asyncio.create_task(
                        asyncio.sleep(
                            typing_delay
                        )
                    )
                )

                (
                    response,
                    _
                ) = await asyncio.gather(
                    writer_task,
                    delay_task
                )

        except Exception as error:

            print(
                "[WRITER ERROR] "
                f"user={username} "
                f"error="
                f"{type(error).__name__}: "
                f"{error}"
            )

            try:

                await message.reply(
                    "mein gehirn hat grad "
                    "kurz ragequit gemacht 💀",
                    mention_author=False
                )

            except discord.HTTPException:

                pass

            return

        # =================================================
        # 8. CLEAN + GUARDS
        # =================================================

        answer = (
            clean_generated_answer(
                response.output_text
            )
        )

        answer = (
            enforce_question_guard(
                answer,
                decision.ask_question
            )
        )

        answer = (
            enforce_knowledge_guard(
                answer,
                decision
            )
        )

        if not answer:

            answer = "hm."

        # =================================================
        # 9. EXPRESSION VIOLATION CHECK
        # =================================================

        violation_reasons = (
            expression_violation_reasons(
                answer,
                expression_plan
            )
        )

        if (
            EXPRESSION_VIOLATION_LOGGING
            and
            violation_reasons
        ):

            print(
                "[EXPRESSION VIOLATION] "
                f"user={username} "
                f"reasons="
                f"{violation_reasons} "
                f"answer="
                f"{answer!r}"
            )

        # =================================================
        # 10. CONTEXT UPDATE
        # =================================================

        user_context.append({

            "role":
                "user",

            "username":
                username,

            "content":
                user_text
        })

        user_context.append({

            "role":
                "assistant",

            "username":
                "Evilnae",

            "content":
                answer
        })

        add_channel_bot_message(
            channel_id,
            user_id,
            username,
            answer
        )

        # =================================================
        # 11. SEND RESPONSE
        # =================================================

        try:

            if (
                decision.response_length
                in {
                    "tiny",
                    "short"
                }
            ):

                await message.reply(
                    answer[:1900],
                    mention_author=False
                )

            elif (
                random.randint(
                    1,
                    SPLIT_CHANCE
                )
                == 1
                and
                len(answer) > 80
            ):

                split_point = (
                    answer.find(
                        ". "
                    )
                )

                if (
                    split_point
                    != -1
                ):

                    first_part = (
                        answer[
                            :split_point + 1
                        ]
                    )

                    second_part = (
                        answer[
                            split_point + 2:
                        ]
                    )

                    await message.reply(
                        first_part[:1900],
                        mention_author=False
                    )

                    await asyncio.sleep(
                        random.uniform(
                            0.7,
                            1.6
                        )
                    )

                    if second_part:

                        await message.channel.send(
                            second_part[:1900]
                        )

                else:

                    await message.reply(
                        answer[:1900],
                        mention_author=False
                    )

            else:

                await message.reply(
                    answer[:1900],
                    mention_author=False
                )

        except discord.HTTPException as error:

            print(
                "[DISCORD SEND ERROR] "
                f"user={username} "
                f"error={error}"
            )

            return

        # =================================================
        # 12. SOCIAL ACTION
        # =================================================

        social_action_executed = False

        if decision.should_ask_person:

            await asyncio.sleep(
                random.uniform(
                    0.8,
                    2.0
                )
            )

            try:

                social_action_executed = (
                    await execute_social_action(

                        message=message,

                        channel_id=(
                            channel_id
                        ),

                        decision=(
                            decision
                        )
                    )
                )

            except Exception as error:

                print(
                    "[SOCIAL ACTION ERROR] "
                    f"user={username} "
                    f"error="
                    f"{type(error).__name__}: "
                    f"{error}"
                )

        # =================================================
        # 13. FINAL LOG
        # =================================================

        total_duration = (
            time.perf_counter()
            - total_start
        )

        buffer_count = (
            database.get_buffer_count(
                user_id
            )
        )

        print(
            "[RESPONSE DONE] "
            f"user={username} "
            f"id={user_id} "
            f"duration="
            f"{total_duration:.2f}s "
            f"brain="
            f"{brain_duration:.2f}s "
            f"buffer="
            f"{buffer_count}/"
            f"{MEMORY_BUFFER_THRESHOLD} "
            f"mood="
            f"{current_mood} "
            f"action="
            f"{decision.action} "
            f"length="
            f"{decision.response_length} "
            f"tone="
            f"{decision.tone} "
            f"question="
            f"{decision.ask_question} "
            f"knowledge="
            f"{decision.knowledge_available} "
            f"source="
            f"{decision.knowledge_source} "
            f"expression_style="
            f"{expression_plan.style} "
            f"expression_violations="
            f"{len(violation_reasons)} "
            f"social_executed="
            f"{social_action_executed}"
        )

        # =================================================
        # 14. BACKGROUND MEMORY
        # =================================================

        start_memory_worker_if_needed(
            user_id,
            username
        )


# =========================================================
# RUN
# =========================================================

bot.run(
    DISCORD_TOKEN
)