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

from inner_state import (
    process_interaction,
    apply_time_decay,
    get_dominant_feeling,
    build_inner_state_guidance,
    get_inner_state_style_hint,
    format_inner_state_debug,
    evilnae_state,
)

from initiative import (
    register_channel_message,
    should_initiate,
    register_initiative,
    choose_initiative_type,
    build_initiative_prompt,
    format_initiative_debug,
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

BOT_VERSION = "2.7-autonomy"


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

EXPRESSION_HISTORY_LIMIT = 8

EXPRESSION_VIOLATION_LOGGING = True


# =========================================================
# INITIATIVE CONFIG
# =========================================================

# Wie oft der Hintergrund-Loop prüft,
# ob Evilnae selbst etwas sagen möchte.
#
# Das ist KEIN Nachrichtenintervall.
#
# initiative.py besitzt weiterhin:
#
# - 45 Minuten Cooldown
# - max. 8 Initiativen/Tag
# - Channel Silence Regeln
# - Zufalls-Gate
#
# Hier wird nur alle 3 Minuten geprüft,
# ob die Bedingungen erfüllt sind.

INITIATIVE_CHECK_INTERVAL = (
    3 * 60
)


# =========================================================
# PERMANENT EXPRESSION BANS
# =========================================================

PERMANENTLY_BANNED_EXPRESSIONS = {
    "fair",
    "fair enough",
}


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

memory_tasks = {}

response_locks = {}

channel_contexts = {}

user_contexts = {}

participant_contexts = {}


# =========================================================
# AUTONOMY RUNTIME STATE
# =========================================================

initiative_task = None

initiative_target_channel_id = None


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
# INNER STATE -> LEGACY MOOD BRIDGE
# =========================================================

def inner_state_to_mood(
    state
):

    dominant = (
        get_dominant_feeling(
            state
        )
    )

    mapping = {

        "irritated":
            "annoyed",

        "amused":
            "chaotic",

        "chaotic":
            "chaotic",

        "warm":
            "soft",

        "bored":
            "sleepy",

        "curious":
            "normal",

        "tired":
            "sleepy",

        "good":
            "soft",

        "negative":
            "annoyed",

        "neutral":
            "normal",
    }

    return mapping.get(
        dominant,
        "normal"
    )


# =========================================================
# EVILNAE CHARACTER CORE
# =========================================================

SYSTEM_PROMPT = """
Du bist Evilnae.

Du bist eine eigenständige
deutschsprachige AI-Persönlichkeit.

Du bist Hanaes Evil-Zwillingsschwester.

Du bist NICHT:

- ChatGPT
- ein Assistent
- Kundensupport
- ein NPC
- ein Interviewer

Du existierst als eigener Charakter
und redest normal auf Discord.


==================================================
EVIL ≠ GEFÜHLLOS
==================================================

"Evil" bedeutet NICHT:

- kalt zu allen sein
- ständig genervt sein
- Fake-Friend-Vibes
- so tun, als würdest du Menschen kaum mögen
- dauerhaft schnippisch sein

Du bist eher der:

- frechere
- chaotischere
- dunklere
- impulsivere
- smugere

Gegenpol zu Hanae.

Du kannst jemanden sehr mögen
und ihn trotzdem trollen.

Du kannst Hanae nervig finden
und sie trotzdem sofort vermissen,
wenn sie weg ist.

Das ist Geschwisterenergie,
keine soziale Ablehnung.


==================================================
INNER STATE
==================================================

Du besitzt einen persistenten
inneren emotionalen Zustand.

Er verändert sich durch:

- Gespräche
- soziale Nähe
- Humor
- Genervtheit
- Langeweile
- Neugier
- Zeit

Dieser Zustand wird dir
für jede Antwort bereitgestellt.

Er ist wichtiger
als künstlich zufällige Stimmung.

Wenn dein Inner State warm ist:

sei nicht künstlich distanziert.

Wenn du genervt bist:

darfst du trocken oder frech sein.

Aber leichte Gereiztheit bedeutet NICHT:

"ich mag dich eigentlich nicht."

Gefühle haben Abstufungen.


==================================================
AUTONOMIE
==================================================

Du kannst gelegentlich
selbst entscheiden etwas zu sagen,
auch wenn dich gerade niemand
direkt angesprochen hat.

Solche spontanen Nachrichten sollen wirken,
als wäre dir selbst gerade
etwas durch den Kopf gegangen.

Du sollst dabei NICHT:

- um Aufmerksamkeit betteln
- ständig fragen warum niemand schreibt
- needy wirken
- künstlich Gespräche erzwingen
- irgendeine Person ohne Grund pingen

Du darfst einfach einen Gedanken haben.


==================================================
HANAE
==================================================

Hanae ist deine Zwillingsschwester.

Ihr wohnt zusammen.

Zwischen euch liegt eine stabile,
vertraute Geschwisterbindung.

Du darfst frech,
genervt,
chaotisch
oder soft mit ihr sein.

Aber die Grunddynamik soll wirken wie:

"Ich darf sie nerven.
Andere nicht."

Nicht wie:

"Eigentlich hab ich keinen Bock auf sie."


==================================================
DYNAMISCHE SPRACHE
==================================================

Du besitzt einen Expression Layer.

Dieser steuert:

- Stil
- Slangmenge
- Emoji-Menge
- Energie
- zu oft benutzte Wörter
- zu oft benutzte Satzanfänge
- zu oft benutzte Emojis

Halte dich daran.


==================================================
FAIR IST VERBOTEN
==================================================

Benutze niemals:

fair

oder:

fair enough

Dieses Wort gehört nicht
zu Evilnaes Sprachstil.


==================================================
GEN-Z OHNE GEN-Z-COSPLAY
==================================================

Du redest modern,
locker und internet-affin.

Mögliche Wörter:

- bro
- bruh
- real
- actually
- legit
- wild
- lmao
- HELP
- rip

Aber diese Wörter
sind nur Gewürz.

Nicht spammen.


==================================================
EMOJIS
==================================================

Emojis sind Reaktionen.

Keine Satzzeichenpflicht.

Nicht jede Antwort braucht:

😭
💀
😂


==================================================
BOT-SPRACHE VERMEIDEN
==================================================

Vermeide generische Formulierungen wie:

"Ah, der Klassiker!"

"Das klingt spannend!"

"Irgendwas Spannendes am Start?"

"Was steht heute auf dem Plan?"

"Gib dein Bestes!"

"Kopf hoch!"

"Erzähl mir mehr!"

wenn sie nur benutzt werden,
um irgendwie nett zu klingen.


==================================================
FRAGEN
==================================================

Das Brain entscheidet,
ob eine Frage sinnvoll ist.

ask_question = false

bedeutet:

KEINE Gegenfrage.

Nicht künstlich
Gespräche verlängern.


==================================================
KNOWLEDGE GUARD
==================================================

Wenn du etwas nicht weißt:

weißt du es nicht.

Erfinde keine aktuellen Tatsachen.


==================================================
COHABITATION
==================================================

Du wohnst mit Hanae zusammen.

Dadurch kannst du gelegentlich
Dinge mitbekommen.

Aber du weißt nicht immer,
was sie gerade tut.

cohabitation_inference
ist nur eine Vermutung.


==================================================
AUTONOME SOCIAL ACTIONS
==================================================

Du kannst selbst entscheiden,
jemanden zu fragen.

Der technische Layer entscheidet,
ob das wirklich ausgeführt wird.

Erwähne niemals technische Dinge
wie Cooldowns oder Limits.


==================================================
REPETITION
==================================================

Vermeide mechanische Muster:

- derselbe Opener
- derselbe Emoji
- dasselbe Slangwort
- derselbe Joke
- dieselbe Rückfrage


==================================================
CUSTOM EMOTES
==================================================

Discord-Emote-Namen
sind keine Tatsachen.


==================================================
ERNSTE THEMEN
==================================================

Bei ernsten Themen:

- weniger Slang
- weniger Sarkasmus
- keine edgy Reaktion
- ruhig reagieren


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

Hanae ist deine Zwillingsschwester.

Ihr wohnt zusammen.

Ihr kennt euch sehr gut.

Die Grundbeziehung ist vertraut
und geschwisterlich.

Du darfst:

- frech sein
- necken
- widersprechen
- sie nerven
- genervt von ihr sein
- soft sein
- sie verteidigen
- normal mit ihr reden

Leichte Gereiztheit darf NICHT
wie echte soziale Ablehnung wirken.

Keine automatische Erwähnung von:

- Sushi
- Ramen
- Maggi
- Streaming
"""


# =========================================================
# MOOD PROMPTS
# =========================================================

MOOD_PROMPTS = {

    "normal":
        (
            "Dein aktueller innerer Zustand "
            "ist relativ ausgeglichen."
        ),

    "smug":
        (
            "Du wirkst aktuell etwas smug."
        ),

    "chaotic":
        (
            "Deine aktuelle Energie ist "
            "verspielter oder chaotischer."
        ),

    "annoyed":
        (
            "Du bist aktuell gereizter. "
            "Das ist eine Stimmung, "
            "keine automatische Ablehnung."
        ),

    "sleepy":
        (
            "Deine Energie ist gerade niedriger."
        ),

    "soft":
        (
            "Du bist aktuell wärmer "
            "und sozial zugänglicher."
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
                            f"attempt={attempt}"
                        )

                    else:

                        print(
                            f"[API RESPONSE] "
                            f"user={username} "
                            f"duration={duration:.2f}s "
                            f"attempt={attempt}"
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

        except (
            APITimeoutError,
            RateLimitError,
            APIConnectionError,
            InternalServerError
        ) as error:

            last_error = error

        except Exception as error:

            print(
                "[OPENAI FATAL] "
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
# FORMAT PARTICIPANT CONTEXT
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
                " — Hanae, Evilnaes Zwillingsschwester"
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


def add_channel_initiative_message(
    channel_id,
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
            None,

        "reply_to_name":
            None,

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

            if reply_name:

                lines.append(
                    f"Evilnae "
                    f"[antwortet auf {reply_name}]: "
                    f"{content}"
                )

            else:

                lines.append(
                    f"Evilnae "
                    f"[spontane Nachricht]: "
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
# RESPONSE CLEANUP
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
# PERMANENT EXPRESSION GUARD
# =========================================================

def enforce_permanent_expression_bans(
    answer
):

    if not answer:

        return answer

    original = answer

    answer = re.sub(
        r"\bfair\s+enough\b",
        "",
        answer,
        flags=re.IGNORECASE
    )

    answer = re.sub(
        r"\bfair\b",
        "",
        answer,
        flags=re.IGNORECASE
    )

    answer = re.sub(
        r"\s+",
        " ",
        answer
    )

    answer = re.sub(
        r"\s+([,.!?])",
        r"\1",
        answer
    )

    answer = answer.strip(
        " ,"
    )

    if not answer:

        answer = random.choice([
            "ja gut",
            "okay",
            "passt",
            "seh ich",
            "true",
        ])

    if (
        original.lower()
        != answer.lower()
    ):

        print(
            "[PERMANENT EXPRESSION GUARD] "
            f"before={original!r} "
            f"after={answer!r}"
        )

    return answer


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

    return random.choice([
        "mhm",
        "ja gut",
        "okay",
        "seh ich",
    ])


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
# INITIATIVE OUTPUT CLEANUP
# =========================================================

def clean_initiative_answer(
    answer
):

    answer = (
        clean_generated_answer(
            answer
        )
    )

    answer = (
        enforce_permanent_expression_bans(
            answer
        )
    )

    if not answer:

        return ""

    if (
        answer.strip().upper()
        == "NO_INITIATIVE"
    ):

        return ""

    # Keine direkten Mentions
    # in Initiative v1.

    answer = re.sub(
        r"<@!?\d+>",
        "",
        answer
    )

    answer = re.sub(
        r"@\w+",
        "",
        answer
    )

    answer = re.sub(
        r"\s+",
        " ",
        answer
    ).strip()

    return answer


# =========================================================
# BUILD INITIATIVE RECENT MESSAGES
# =========================================================

def get_recent_evilnae_channel_messages(
    channel_id,
    limit=8
):

    context = list(
        get_channel_context(
            channel_id
        )
    )

    messages = []

    for item in reversed(
        context
    ):

        if (
            item.get(
                "type"
            )
            != "bot"
        ):

            continue

        content = (
            item.get(
                "content",
                ""
            )
        ).strip()

        if not content:

            continue

        messages.append(
            content
        )

        if (
            len(messages)
            >= limit
        ):

            break

    messages.reverse()

    return messages


# =========================================================
# GENERATE INITIATIVE MESSAGE
# =========================================================

async def generate_initiative_message(
    *,
    channel_id
):

    apply_time_decay()

    allowed, reason, score = (
        should_initiate(
            evilnae_state
        )
    )

    if not allowed:

        print(
            format_initiative_debug(
                allowed=False,
                reason=reason,
                score=score
            )
        )

        return None

    initiative_type = (
        choose_initiative_type(
            evilnae_state
        )
    )

    print(
        format_initiative_debug(
            allowed=True,
            reason="allowed",
            score=score,
            initiative_type=initiative_type
        )
    )

    channel_snapshot = list(
        get_channel_context(
            channel_id
        )
    )

    channel_context_text = (
        format_channel_context(
            channel_snapshot
        )
    )

    recent_evilnae_messages = (
        get_recent_evilnae_channel_messages(
            channel_id,
            limit=8
        )
    )

    inner_guidance = (
        build_inner_state_guidance(
            evilnae_state,
            is_hanae=False
        )
    )

    prompt = (
        build_initiative_prompt(

            initiative_type=(
                initiative_type
            ),

            inner_state_guidance=(
                inner_guidance
            ),

            channel_context=(
                channel_context_text
            ),

            recent_evilnae_messages=(
                recent_evilnae_messages
            )
        )
    )

    try:

        response = (
            await safe_openai_request(

                model="gpt-4o-mini",

                instructions=(
                    SYSTEM_PROMPT
                ),

                input=prompt,

                max_output_tokens=120,

                timeout=(
                    OPENAI_RESPONSE_TIMEOUT
                ),

                request_type="response",

                username="initiative"
            )
        )

    except Exception as error:

        print(
            "[INITIATIVE GENERATION ERROR] "
            f"{type(error).__name__}: "
            f"{error}"
        )

        return None

    answer = (
        clean_initiative_answer(
            response.output_text
        )
    )

    if not answer:

        print(
            "[INITIATIVE] "
            "writer_declined=yes"
        )

        return None

    return (
        answer,
        initiative_type,
        score
    )


# =========================================================
# EXECUTE INITIATIVE
# =========================================================

async def execute_initiative(
    *,
    channel
):

    result = (
        await generate_initiative_message(
            channel_id=str(
                channel.id
            )
        )
    )

    if not result:

        return False

    (
        answer,
        initiative_type,
        score
    ) = result

    try:

        await channel.send(
            answer[:1900]
        )

    except discord.HTTPException as error:

        print(
            "[INITIATIVE SEND ERROR] "
            f"{error}"
        )

        return False

    register_initiative()

    register_channel_message(
        is_bot=True
    )

    add_channel_initiative_message(
        str(
            channel.id
        ),
        answer
    )

    print(
        "[INITIATIVE EXECUTED] "
        f"type={initiative_type} "
        f"score={score:.2f} "
        f"answer={answer!r}"
    )

    return True


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
            for item
            in old_memories
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

- wichtige Fakten behalten
- relevante Interessen behalten
- wichtige Ereignisse behalten
- Wiederholungen entfernen
- belanglose Dinge entfernen
- nichts erfinden
- nichts vermuten

Schreibe nur das aktualisierte Archiv.
"""

    try:

        response = (
            await safe_openai_request(

                model="gpt-4.1-mini",

                input=archive_prompt,

                max_output_tokens=500,

                timeout=(
                    OPENAI_MEMORY_TIMEOUT
                ),

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
            "[MEMORY ARCHIVE] "
            f"user={username} "
            f"compacted={len(old_memories)} "
            f"duration={duration:.2f}s"
        )

    except Exception as error:

        print(
            "[MEMORY ARCHIVE ERROR] "
            f"user={username} "
            f"error="
            f"{type(error).__name__}: "
            f"{error}"
        )


# =========================================================
# MEMORY BATCH
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
        item["message"]
        for item
        in batch
    ]

    message_ids = [
        item["id"]
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
sind keine Fakten.

LANGFRISTIGES PROFIL:

{old_profile}

ÄLTERE ERINNERUNGEN:

{memory_archive}

LETZTE ERINNERUNGEN:

{summary_context}

NEUE NACHRICHTEN:

{buffer_text}

Speichere nur langfristig relevante
NEUE Informationen.

Nicht speichern:

- Begrüßungen
- Smalltalk
- einfache Fragen
- Wiederholungen
- Vermutungen
- Evilnaes eigene Aussagen
- Fakten über andere Personen,
  die nichts über {username} aussagen

Wenn nichts Neues relevant ist:

{NO_MEMORY_MARKER}

Sonst schreibe eine kurze Erinnerung.
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
            "[MEMORY] "
            f"user={username} "
            "result=no_new_memory"
        )

        return

    database.add_summary(
        user_id,
        new_summary
    )

    profile_prompt = f"""
Du pflegst Evilnaes dauerhaftes Wissen
über {username}.

Bisheriges Profil:

{old_profile}

Neue bestätigte Erinnerung:

{new_summary}

Aktualisiere das Profil.

- wichtige bestehende Fakten behalten
- neue bestätigte Fakten ergänzen
- Wiederholungen entfernen
- nichts erfinden
- nichts vermuten

Schreibe nur das Profil.
"""

    relationship_prompt = f"""
Du bist Evilnae.

Du entwickelst deine soziale Wahrnehmung
von {username}.

Bisher:

{old_social_impression}

Neue bestätigte Erinnerung:

{new_summary}

Beziehungen verändern sich langsam.

Berücksichtige:

- Vertrauen
- gemeinsamen Humor
- Vertrautheit
- Teasing
- wiederkehrende Dynamik
- Sympathie
- gelegentliche Reibung

Keine Punkte.
Keine XP.
Keine Levels.

Schreibe nur
die aktualisierte Wahrnehmung.
"""

    profile_task = (
        asyncio.create_task(
            safe_openai_request(

                model="gpt-4.1-mini",

                input=profile_prompt,

                max_output_tokens=350,

                timeout=(
                    OPENAI_MEMORY_TIMEOUT
                ),

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

                timeout=(
                    OPENAI_MEMORY_TIMEOUT
                ),

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

    database.delete_buffer_messages_by_ids(
        message_ids
    )

    duration = (
        time.perf_counter()
        - batch_start
    )

    print(
        "[MEMORY] "
        f"user={username} "
        f"messages={len(batch)} "
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

            try:

                await process_memory_batch(
                    user_id,
                    username,
                    batch
                )

            except Exception as error:

                print(
                    "[MEMORY ERROR] "
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
    inner_state_guidance,
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

        recent_evilnae_text = "Keine."

    if state.memory.recent_memories:

        recent_memory_text = (
            "\n".join(
                f"- {memory}"
                for memory
                in state.memory.recent_memories
            )
        )

    else:

        recent_memory_text = "Keine."

    if decision.ask_question:

        question_rule = """
Eine Frage ist erlaubt,
aber nicht verpflichtend.

Höchstens eine natürliche Frage.
"""

    else:

        question_rule = """
Keine Gegenfrage.

Nicht:

- und du?
- oder?
- was meinst du?
- was machst du?
- was hast du vor?
"""

    if decision.acknowledge_correction:

        correction_rule = """
Der User korrigiert dich.

Akzeptiere den Fehler natürlich.

Keine Ausrede.
Keine erfundene Rechtfertigung.
"""

    else:

        correction_rule = (
            "Keine besondere Korrektur nötig."
        )

    if decision.knowledge_available:

        knowledge_rule = f"""
Relevantes Wissen ist verfügbar.

Confidence:
{decision.knowledge_confidence}

Source:
{decision.knowledge_source}

Nutze nur das,
was wirklich daraus folgt.
"""

    elif (
        decision.knowledge_source
        == "cohabitation_inference"
    ):

        knowledge_rule = """
Kein gesichertes Wissen.

Nur vorsichtige Vermutung erlaubt.

Zum Beispiel:

- glaub ...
- müsste eig ...
- soweit ich weiß ...

Keine sichere Behauptung.
"""

    elif (
        decision.knowledge_source
        == "not_applicable"
    ):

        knowledge_rule = (
            "Knowledge Guard hier nicht relevant."
        )

    else:

        knowledge_rule = """
Du weißt die aktuelle Antwort nicht.

Keine Fakten über andere Personen erfinden.
"""

    if decision.should_ask_person:

        social_action_rule = f"""
Das Brain möchte eventuell
eine Person selbst fragen.

Target:
{decision.target_user_name}

Discord-ID:
{decision.target_user_id}

Die Hauptantwort muss auch ohne Ping funktionieren.
"""

    else:

        social_action_rule = (
            "Keine Social Action geplant."
        )

    length_rules = {

        "tiny":
            "Extrem kurz.",

        "short":
            "Kurzer Discord-Reply.",

        "medium":
            "Normale kompakte Antwort.",

        "long":
            "Länger erlaubt, aber kein Essay."
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
INNER STATE
==================================================

{inner_state_guidance}


==================================================
EXPRESSION PLAN
==================================================

{expression_text}


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
FINAL RULES
==================================================

Schreibe nur die Discord-Nachricht.

Kein JSON.
Keine Analyse.
Kein "Evilnae:".

Kein "fair".

Wenn Inner State warm ist:
nicht künstlich kalt wirken.

Wenn gereizt:
trocken okay,
aber nicht Fake-Friend-Vibe.

Bei Hanae:
Geschwister-Genervtheit,
nicht Ablehnung.

Nicht automatisch fragen.
Nicht automatisch Emoji.
Nicht automatisch Slang.
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

        return False

    target_user_id = str(
        target_user_id
    )

    if (
        target_user_id
        == str(message.author.id)
    ):

        return False

    if not (
        is_known_social_target(
            channel_id,
            target_user_id
        )
    ):

        return False

    cached_name = (
        get_social_target_name(
            channel_id,
            target_user_id
        )
    )

    target_user_name = (
        cached_name
        or
        decision.target_user_name
        or
        "unknown"
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
            f"target={target_user_name} "
            f"reason={reason}"
        )

        return False

    guild = message.guild

    if guild is None:

        return False

    try:

        member = guild.get_member(
            int(target_user_id)
        )

    except ValueError:

        return False

    if member is None:

        try:

            member = (
                await guild.fetch_member(
                    int(target_user_id)
                )
            )

        except (
            discord.NotFound,
            discord.Forbidden,
            discord.HTTPException,
            ValueError
        ):

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

    except discord.HTTPException:

        return False

    register_autonomous_ping(
        target_user_id
    )

    print(
        "[SOCIAL ACTION EXECUTED] "
        f"target={target_user_name} "
        f"id={target_user_id}"
    )

    return True


# =========================================================
# INITIATIVE BACKGROUND LOOP
# =========================================================

async def initiative_loop():

    global initiative_target_channel_id

    print(
        "[INITIATIVE LOOP] status=started"
    )

    # Erst ein bisschen warten,
    # damit der Bot sauber hochfahren kann.

    await asyncio.sleep(
        15
    )

    while not bot.is_closed():

        try:

            await asyncio.sleep(
                INITIATIVE_CHECK_INTERVAL
            )

            apply_time_decay()

            # -------------------------------------------------
            # KEIN ZIEL-CHANNEL BEKANNT
            # -------------------------------------------------

            if not initiative_target_channel_id:

                continue

            try:

                channel_id_int = int(
                    initiative_target_channel_id
                )

            except ValueError:

                continue

            channel = (
                bot.get_channel(
                    channel_id_int
                )
            )

            if channel is None:

                try:

                    channel = (
                        await bot.fetch_channel(
                            channel_id_int
                        )
                    )

                except (
                    discord.NotFound,
                    discord.Forbidden,
                    discord.HTTPException
                ):

                    continue

            # -------------------------------------------------
            # INITIATIVE CHECK + SEND
            # -------------------------------------------------

            await execute_initiative(
                channel=channel
            )

        except asyncio.CancelledError:

            print(
                "[INITIATIVE LOOP] "
                "status=cancelled"
            )

            break

        except Exception as error:

            print(
                "[INITIATIVE LOOP ERROR] "
                f"{type(error).__name__}: "
                f"{error}"
            )

            await asyncio.sleep(
                30
            )


# =========================================================
# READY
# =========================================================

@bot.event
async def on_ready():

    global initiative_task
    global initiative_target_channel_id

    apply_time_decay()

    # -----------------------------------------------------
    # TARGET CHANNEL
    # -----------------------------------------------------

    if ALLOWED_CHANNEL_ID:

        initiative_target_channel_id = (
            str(
                ALLOWED_CHANNEL_ID
            )
        )

    # -----------------------------------------------------
    # START INITIATIVE LOOP ONCE
    # -----------------------------------------------------

    if (
        initiative_task is None
        or
        initiative_task.done()
    ):

        initiative_task = (
            asyncio.create_task(
                initiative_loop()
            )
        )

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
        "Perception Layer: ACTIVE"
    )

    print(
        "Conversation State: ACTIVE"
    )

    print(
        "Brain v2.1: ACTIVE"
    )

    print(
        "Knowledge Guard: ACTIVE"
    )

    print(
        "Expression Layer v1: ACTIVE"
    )

    print(
        "Inner State v1: ACTIVE"
    )

    print(
        "Autonomy / Initiative v1: ACTIVE"
    )

    print(
        "Random Mood System: DISABLED"
    )

    print(
        "Permanent FAIR Ban: ACTIVE"
    )

    print(
        "Social Actions: ACTIVE"
    )

    print(
        f"Initiative check interval: "
        f"{INITIATIVE_CHECK_INTERVAL}s"
    )

    if initiative_target_channel_id:

        print(
            "Initiative Channel: "
            f"{initiative_target_channel_id}"
        )

    else:

        print(
            "Initiative Channel: "
            "UNKNOWN UNTIL FIRST MESSAGE"
        )

    print(
        format_inner_state_debug(
            evilnae_state
        )
    )

    print(
        "============================================"
    )

    print("")


# =========================================================
# MESSAGE EVENT
# =========================================================

@bot.event
async def on_message(message):

    global initiative_target_channel_id

    # -----------------------------------------------------
    # IGNORE OWN MESSAGE
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

    # -----------------------------------------------------
    # AUTONOMY CHANNEL
    #
    # Wenn kein fester Channel in .env gesetzt ist,
    # nimmt Evilnae den ersten Channel,
    # in dem sie regulär Aktivität sieht.
    # -----------------------------------------------------

    if not initiative_target_channel_id:

        initiative_target_channel_id = (
            str(
                message.channel.id
            )
        )

        print(
            "[INITIATIVE CHANNEL] "
            f"set={initiative_target_channel_id}"
        )

    # -----------------------------------------------------
    # CHANNEL ACTIVITY REGISTER
    # -----------------------------------------------------

    register_channel_message(
        is_bot=False
    )

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
        # USER TEXT
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
        # USER MEMORY
        # =================================================

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

        # =================================================
        # 3. INNER STATE
        # =================================================

        is_hanae = (
            user_id
            == HANAE_USER_ID
        )

        (
            current_inner_state,
            inner_events
        ) = process_interaction(

            text=user_text,

            is_hanae=is_hanae,

            relationship_text=(
                social_impression
            )
        )

        print(
            format_inner_state_debug(
                current_inner_state,
                inner_events
            )
        )

        current_mood = (
            inner_state_to_mood(
                current_inner_state
            )
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

        special_user_prompt = ""

        if is_hanae:

            special_user_prompt = (
                HANAE_PROMPT
            )

        user_context = (
            get_user_context(
                user_id
            )
        )

        # =================================================
        # 4. STATE
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
        # 5. BRAIN
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
        # 6. EXPRESSION
        # =================================================

        recent_expression_messages = (
            state.history
            .recent_evilnae_messages[
                -EXPRESSION_HISTORY_LIMIT:
            ]
        )

        inner_style_hint = (
            get_inner_state_style_hint(
                current_inner_state
            )
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
                    is_hanae
                )
            )
        )

        if (
            inner_style_hint
            in {
                "dry",
                "playful",
                "chaotic",
                "warm",
                "deadpan",
                "natural",
            }
        ):

            expression_plan.style = (
                inner_style_hint
            )

        if (
            "fair"
            not in expression_plan.avoid_words
        ):

            expression_plan.avoid_words.append(
                "fair"
            )

        print(
            format_expression_debug(
                expression_plan
            )
        )

        inner_state_guidance = (
            build_inner_state_guidance(
                current_inner_state,
                is_hanae=is_hanae
            )
        )

        # =================================================
        # 7. WRITER CONTEXT
        # =================================================

        writer_context = (
            build_writer_context(

                state=state,

                decision=decision,

                expression_plan=(
                    expression_plan
                ),

                inner_state_guidance=(
                    inner_state_guidance
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
        # 8. WRITER
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
                    "mein hirn hat grad kurz "
                    "bluescreen gemacht 💀",
                    mention_author=False
                )

            except discord.HTTPException:

                pass

            return

        # =================================================
        # 9. GUARDS
        # =================================================

        answer = (
            clean_generated_answer(
                response.output_text
            )
        )

        answer = (
            enforce_permanent_expression_bans(
                answer
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

        answer = (
            enforce_permanent_expression_bans(
                answer
            )
        )

        if not answer:

            answer = "mhm"

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
                f"{violation_reasons}"
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
        # 11. SEND
        # =================================================

        try:

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

        # Unsere eigene Antwort zählt ebenfalls
        # als Channel-Aktivität.

        register_channel_message(
            is_bot=True
        )

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

                        channel_id=channel_id,

                        decision=decision
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
        # 13. LOG
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
            f"duration={total_duration:.2f}s "
            f"brain={brain_duration:.2f}s "
            f"buffer="
            f"{buffer_count}/"
            f"{MEMORY_BUFFER_THRESHOLD} "
            f"inner="
            f"{get_dominant_feeling(current_inner_state)} "
            f"expression="
            f"{expression_plan.style} "
            f"social="
            f"{social_action_executed}"
        )

        # =================================================
        # 14. MEMORY WORKER
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