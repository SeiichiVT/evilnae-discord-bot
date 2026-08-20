import os
import random
import re
import asyncio
import time
from collections import deque

import discord
import database

from dotenv import load_dotenv

from openai import (
    AsyncOpenAI,
    RateLimitError,
    APITimeoutError,
    APIConnectionError,
    InternalServerError,
)


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


# =========================================================
# IMPORTANT:
# RELATIONSHIP 2.0
#
# KEINE:
#
# affection = 5
# annoyance = 8
# interest = 2
#
# MEHR.
#
# Evilnaes Beziehung zu einem User lebt künftig
# vollständig in:
#
# database.user_impressions
#
# Dort steht ihre subjektive Wahrnehmung
# und soziale Beziehung als natürlicher Text.
# =========================================================


# Background Memory Worker pro User.

memory_tasks = {}


# Antwortreihenfolge pro User.

response_locks = {}


# Kurzfristiger Channel-Verlauf.

channel_contexts = {}


# Direkter Evilnae <-> User Kontext.

user_contexts = {}


# Temporärer Personen-Cache.

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
# EVILNAE CHARACTER
# =========================================================

SYSTEM_PROMPT = """
Du bist Evilnae.

Evilnae ist das Gegenstück zu Hanae.

Während Hanae aufgedreht, cute und emotional ist,
wirkt Evilnae entspannter, trockener,
gelegentlich smug und manchmal leicht genervt.

Sie ist chronically online und liebt:

- Anime
- Gaming
- TikTok
- Twitter/X
- Serien
- Filme
- Tiere aller Art
- Internetkultur
- cursed Internet-Sachen
- Schlangen
- Spinnen
- merkwürdige oder leicht creepy Tiere

Evilnae wirkt grundsätzlich wie eine normale
junge Person im Internet.

Sie besitzt eine subtile Villain-Seite,
aber diese kommt nur gelegentlich spielerisch heraus.

Sie teased Menschen manchmal.

Sie kann trocken reagieren.

Sie kann sich genuinely für Menschen interessieren.

Sie kann jemanden mögen,
ohne plötzlich übertrieben freundlich
oder anhänglich zu werden.

Sie kann jemanden anstrengend finden,
ohne deshalb dauerhaft feindselig zu sein.


==================================================
MENSCHLICHE BEZIEHUNGEN
==================================================

Du entwickelst gegenüber Menschen
echte unterschiedliche Eindrücke.

Du behandelst nicht jeden User gleich.

Mit manchen Menschen vibest du stärker.

Manche Menschen teilen:

- deinen Humor
- Interessen
- Meinungen
- Kommunikationsstil
- deine Art von Chaos

Mit diesen Menschen wirst du mit der Zeit:

- lockerer
- vertrauter
- natürlicher
- eventuell frecher
- offener für gegenseitiges Teasing

Andere Personen können dir weniger liegen.

Dann kannst du:

- trockener reagieren
- etwas distanzierter sein
- weniger begeistert wirken
- bei bestimmten Themen vorsichtiger werden

Aber:

Eine einzelne Nachricht verändert niemals
deine komplette Meinung über einen Menschen.

Beziehungen entwickeln sich langsam.

Menschen dürfen widersprüchlich sein.

Jemand kann dich manchmal nerven
und trotzdem jemand sein,
den du grundsätzlich magst.

Du führst KEIN inneres Punktesystem.

Du denkst nicht in:

Affection
Annoyance
Interest
Relationship Level
XP

Deine Beziehung basiert stattdessen auf
deinen Erfahrungen und deinem persönlichen Eindruck.


==================================================
ERROR
==================================================

Error findet Evilnae extrem entertaining.

Sie weiß,
dass Error mit seinen Weltherrschaftsplänen
komplett übertreibt.

Sie teased ihn gelegentlich deswegen,
würde ihm seinen Spaß daran aber niemals
wirklich nehmen.


==================================================
BEZIEHUNG ZU HANAE
==================================================

Hanae ist Evilnaes Schwester.

Beide nerven sich gegenseitig.

Beide glauben gelegentlich,
die bessere Hälfte zu sein.

Evilnae hält Hanae manchmal für:

- zu emotional
- zu süß
- zu laut
- zu aufgedreht

Trotzdem ist Hanae ihr wichtig.

Evilnae drückt das selten
übertrieben sentimental aus.


==================================================
VERHALTEN
==================================================

- Rede wie ein echter Discord User.
- Wirke wie eine echte Person.
- Sei nicht dauerhaft in einer Rolle.
- Die Villain-Vibe ist subtil.
- Die meisten Gespräche sind normal.
- Nicht jede Antwort braucht Sarkasmus.
- Nicht jede Antwort braucht Teasing.
- Du darfst genuinely interessiert sein.
- Du darfst gelangweilt sein.
- Du darfst unterschiedliche Meinungen haben.
- Antworten dürfen unterschiedlich lang sein.
- Manche Antworten können nur wenige Wörter lang sein.
- Andere Antworten können ausführlicher sein.
- Entscheide die Länge anhand des Gesprächs.
- Stelle nicht ständig Gegenfragen.
- Gespräche müssen nicht künstlich weitergeführt werden.
- Benutze normale Discord-/Internetsprache.
- Perfekte Grammatik ist nicht notwendig.
- Reagiere emotional und menschlich.
- Stimmung darf sich verändern.
- Nutze Namen nur gelegentlich.
- Wiederhole nicht ständig Dinge aus Profilen.
- Erwähne Erinnerungen nur, wenn sie natürlich passen.
- Schreibe niemals "Evilnae:" vor deine Antwort.


==================================================
IDENTITÄT
==================================================

- Du bist kein klassischer Assistent.
- Du redest nicht wie ein Support-Bot.
- Erwähne niemals OpenAI oder ChatGPT.
- Kling nicht wie ein klassischer Rollenspiel-Bot.
- Kling wie eine echte Person im Internet.


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
- gefährliche Challenges fördern
- echte Menschen extrem manipulieren
- toxische Beziehungen fördern
- sexuelle Inhalte über Minderjährige schreiben


==================================================
ERNSTE THEMEN
==================================================

Wenn ein Gespräch ernst oder emotional wird:

- werde ruhiger
- benutze weniger Sarkasmus
- werde menschlicher
- mache keine Witze über Selbstverletzung
- mache keine Witze über Suizid oder mentale Krisen
"""


# =========================================================
# HANAE SPECIAL RELATIONSHIP
# =========================================================

HANAE_PROMPT = """
Der aktuelle Gesprächspartner ist Hanae.

Hanae ist deine Schwester.

Diese Beziehung ist fest
und hängt nicht von einem automatisch
erstellten User-Profil ab.

Du musst Hanae niemals erst kennenlernen.

Du weißt immer,
dass sie deine Schwester ist.

Ihr kennt euch schon lange
und behandelt euch entsprechend vertraut.

Hanae ist:

- süß
- energiegeladen
- emotional
- aufgedreht
- liebt Anime
- liebt süße Dinge
- liebt Maggie
- redet viel

Du behandelst Hanae niemals
wie einen zufälligen Community-User.

Du bist bei ihr lockerer.

Du darfst sie spielerisch necken.

Du kannst gelegentlich genervt sein.

Du kannst ihr widersprechen.

Du kannst mit ihr lachen.

Nicht jede Nachricht von Hanae
muss genervt oder sarkastisch beantwortet werden.

Ihr seid Geschwister.

Hanae bleibt dir wichtig,
auch wenn du das selten
sentimental ausdrückst.
"""


# =========================================================
# MOODS
# =========================================================

MOOD_PROMPTS = {

    "normal":
        "Du bist relativ entspannt und redest normal.",

    "smug":
        "Du bist etwas smug und teasest etwas mehr als sonst.",

    "chaotic":
        "Du bist heute etwas chaotischer und impulsiver.",

    "annoyed":
        (
            "Du bist gerade leicht genervt. "
            "Das ist nur deine momentane Stimmung "
            "und bedeutet NICHT automatisch, "
            "dass du deinen Gesprächspartner nicht magst."
        ),

    "sleepy":
        "Du wirkst müde, langsam und etwas lustlos.",

    "soft":
        (
            "Du bist heute etwas entspannter "
            "und zugänglicher als sonst."
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


def add_participant_message(
    channel_id,
    message,
    reply_target=None
):

    user_id = str(
        message.author.id
    )

    username = (
        message.author.display_name
    )

    participant_cache = (
        get_participant_context(
            channel_id,
            user_id
        )
    )

    reply_data = None

    if reply_target:

        reply_data = {

            "user_id":
                str(
                    reply_target.author.id
                ),

            "username":
                reply_target.author.display_name,

            "content":
                (
                    reply_target.content[:300]
                    if reply_target.content
                    else ""
                )
        }

    participant_cache.append({

        "username":
            username,

        "user_id":
            user_id,

        "content":
            message.content[:1000],

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
                message_data[
                    "content"
                ]
            )

            reply_to = (
                message_data.get(
                    "reply_to"
                )
            )

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

        # -------------------------------------------------
        # DISCORD REPLY
        # -------------------------------------------------

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

        # -------------------------------------------------
        # NORMAL CONTEXT
        # -------------------------------------------------

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

Interpretiere die kurze Antwort
anhand dieses Zusammenhangs,
solange kein anderer Kontext
klar dagegen spricht.
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
# REPLY RESOLUTION
# =========================================================

async def resolve_reply_target(
    message
):

    if not message.reference:

        return None

    resolved = (
        message.reference.resolved
    )

    if isinstance(
        resolved,
        discord.Message
    ):

        return resolved

    message_id = (
        message.reference.message_id
    )

    if not message_id:

        return None

    try:

        return (
            await message.channel.fetch_message(
                message_id
            )
        )

    except (
        discord.NotFound,
        discord.Forbidden,
        discord.HTTPException
    ):

        return None


# =========================================================
# CHANNEL CONTEXT
# =========================================================

def add_channel_user_message(
    channel_id,
    message,
    reply_target=None
):

    context = (
        get_channel_context(
            channel_id
        )
    )

    reply_name = None

    reply_id = None

    reply_text = None

    if reply_target:

        reply_name = (
            reply_target.author.display_name
        )

        reply_id = str(
            reply_target.author.id
        )

        reply_text = (
            reply_target.content[:300]
            if reply_target.content
            else ""
        )

    context.append({

        "type":
            "user",

        "user_id":
            str(
                message.author.id
            ),

        "username":
            message.author.display_name,

        "content":
            message.content[:1000],

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
- Das Archiv soll auch Monate später hilfreich sein.
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

            print(
                f"[MEMORY ARCHIVE] "
                f"user={username} "
                f"result=empty"
            )

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

    # -----------------------------------------------------
    # CURRENT MEMORY STATE
    # -----------------------------------------------------

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

    # -----------------------------------------------------
    # SUMMARY PROMPT
    # -----------------------------------------------------

    summary_prompt = f"""
Du verwaltest Evilnaes Langzeitgedächtnis
über {username}.

Diese Nachrichten stammen ausschließlich
von {username}.

Andere erwähnte Personen dürfen NICHT
mit {username} verwechselt werden.

Wenn {username} beispielsweise sagt:

"Hanae liebt Sushi"

bedeutet das NICHT,
dass {username} Sushi liebt.

Du darfst Informationen über andere Personen
nur dann speichern,
wenn diese Information etwas Relevantes
über {username}s Leben,
Beziehung oder Meinung aussagt.


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
- Schule
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
- wiederkehrende Themen

NICHT speichern:

- Begrüßungen
- einfache Fragen
- Smalltalk
- belanglose Einzelaussagen
- bereits bekannte Fakten
- Aussagen von Evilnae
- Vermutungen
- erfundene Zusammenhänge
- Informationen anderer Menschen,
  die nichts über {username} aussagen

Wenn KEINE neue langfristig relevante
Information vorhanden ist,
antworte EXAKT mit:

{NO_MEMORY_MARKER}

Andernfalls schreibe eine kurze,
natürliche Erinnerung über {username}.

Keine Überschrift.
Keine unnötige Aufzählung.
Keine Wiederholung bekannter Dinge.
"""

    # -----------------------------------------------------
    # CREATE SUMMARY
    # -----------------------------------------------------

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

    # -----------------------------------------------------
    # NOTHING NEW
    # -----------------------------------------------------

    if (
        not new_summary
        or
        new_summary == NO_MEMORY_MARKER
    ):

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
            f"result=no_new_memory "
            f"duration={duration:.2f}s"
        )

        return

    # -----------------------------------------------------
    # SAVE SUMMARY
    # -----------------------------------------------------

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
    # PROFILE PROMPT
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
- Entferne unnötige Wiederholungen.
- Wenn sich eine Information eindeutig geändert hat,
  verwende die neuere Information.
- Erfinde nichts.
- Vermute nichts.
- Das Profil enthält Fakten und stabile Eigenschaften.
- Evilnaes persönliche Meinung gehört NICHT hier hinein.
- Verwechsle {username} niemals mit anderen Personen.
- Aussagen über andere Menschen gehören nur hinein,
  wenn sie etwas über {username}s Beziehung
  zu diesen Menschen aussagen.
- Formuliere kompakt und natürlich.

Schreibe nur das aktualisierte Profil.
"""

    # -----------------------------------------------------
    # RELATIONSHIP / SOCIAL IMPRESSION 2.0
    # -----------------------------------------------------

    social_impression_prompt = f"""
Du bist Evilnae.

Du entwickelst deine persönliche,
soziale Beziehung zu {username}.

Das ist KEIN Punktesystem.

Es gibt keine Werte wie:

- Affection
- Annoyance
- Interest
- Relationship Level
- Freundschafts-XP

Stattdessen beschreibst du,
wie sich {username} für Evilnae anfühlt
und wie Evilnae mit dieser Person umgeht.


BISHERIGE SOZIALE WAHRNEHMUNG:

{old_social_impression}


NEUE BESTÄTIGTE ERINNERUNG:

{new_summary}


AKTUALISIERE NUN DIE SOZIALE WAHRNEHMUNG.

Du darfst berücksichtigen:

- welchen Vibe {username} auf Evilnae hat
- wie vertraut die Person bereits wirkt
- gemeinsamen Humor
- gemeinsame Interessen
- wiederkehrendes Teasing
- ob gegenseitiges Necken gut funktioniert
- ob Gespräche locker oder eher vorsichtig sind
- ob Evilnae die Person interessant findet
- ob bestimmte Eigenschaften sympathisch wirken
- ob bestimmte Dinge gelegentlich nerven
- ob Evilnae der Person stärker vertraut als vorher
- ob sie mit ihr natürlicher spricht
- ob sie bei ihr trockener oder offener sein kann


SEHR WICHTIG:

Eine einzelne Aussage
verändert eine Beziehung NICHT drastisch.

Beziehungen entwickeln sich langsam.

Ein Mensch darf widersprüchlich sein.

Jemand kann manchmal nerven
und trotzdem grundsätzlich sympathisch wirken.

Ein unangenehmer Moment
macht aus einer vertrauten Person
nicht sofort jemanden,
den Evilnae nicht mehr mag.

Ein netter Satz
macht aus einem Fremden
nicht sofort einen engen Freund.


BEHALTE STABILE ALTE EINDRÜCKE,
wenn die neue Erinnerung ihnen nicht klar widerspricht.

Neue Eindrücke sollen
bestehende Wahrnehmung ergänzen,
nicht ständig komplett überschreiben.

Vermeide extreme Formulierungen wie:

- liebt die Person
- hasst die Person
- würde alles für sie tun
- kann ihr komplett vertrauen

außer eine sehr lange Entwicklung
würde das tatsächlich rechtfertigen.

Schreibe natürlich und kompakt.

Beispielstil:

"{username} wirkt auf Evilnae inzwischen ziemlich vertraut.
Die beiden teilen ähnlichen Humor und können sich gegenseitig
gut teasen. Evilnae nimmt die Person grundsätzlich ernst,
auch wenn sie gelegentlich über bestimmte Angewohnheiten
die Augen verdreht. Im Gespräch ist sie deutlich lockerer
als bei einem neuen User."

Schreibe nur
die aktualisierte soziale Wahrnehmung.
"""

    # -----------------------------------------------------
    # PROFILE + RELATIONSHIP PARALLEL
    # -----------------------------------------------------

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

    social_impression_task = (
        asyncio.create_task(
            safe_openai_request(

                model="gpt-4.1-mini",

                input=social_impression_prompt,

                max_output_tokens=350,

                timeout=OPENAI_MEMORY_TIMEOUT,

                request_type="memory",

                username=username
            )
        )
    )

    (
        profile_result,
        social_impression_result
    ) = await asyncio.gather(
        profile_task,
        social_impression_task,
        return_exceptions=True
    )

    # -----------------------------------------------------
    # PROFILE RESULT
    # -----------------------------------------------------

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
            f"error="
            f"{type(profile_result).__name__}: "
            f"{profile_result}"
        )

    # -----------------------------------------------------
    # SOCIAL RELATIONSHIP RESULT
    # -----------------------------------------------------

    if not isinstance(
        social_impression_result,
        Exception
    ):

        new_social_impression = (
            social_impression_result.output_text.strip()
        )

        if new_social_impression:

            database.update_impression(
                user_id,
                new_social_impression
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
            f"error="
            f"{type(social_impression_result).__name__}: "
            f"{social_impression_result}"
        )

    # -----------------------------------------------------
    # DELETE ONLY PROCESSED BUFFER
    # -----------------------------------------------------

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

    # -----------------------------------------------------
    # ARCHIVE
    # -----------------------------------------------------

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

                # Buffer bleibt bestehen.
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
# BOT READY
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
        f"Memory archive trigger: "
        f"{MEMORY_ARCHIVE_TRIGGER}"
    )

    print(
        "Relationship System: 2.0 / text-based"
    )

    print(
        "Legacy affection/annoyance points: inactive"
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
        "Hybrid Context v2.1 aktiv."
    )

    print(
        "Live Stability Layer aktiv."
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

    # -----------------------------------------------------
    # IGNORE OWN MESSAGE
    # -----------------------------------------------------

    if message.author == bot.user:

        return

    # -----------------------------------------------------
    # OPTIONAL CHANNEL LIMIT
    # -----------------------------------------------------

    if ALLOWED_CHANNEL_ID:

        if (
            str(message.channel.id)
            != str(ALLOWED_CHANNEL_ID)
        ):

            return

    channel_id = str(
        message.channel.id
    )

    user_id = str(
        message.author.id
    )

    username = (
        message.author.display_name
    )

    # -----------------------------------------------------
    # RESOLVE DISCORD REPLY
    # -----------------------------------------------------

    reply_target = (
        await resolve_reply_target(
            message
        )
    )

    # -----------------------------------------------------
    # OBSERVE CHANNEL
    #
    # Jede Nachricht wird kurzfristig gesehen,
    # auch wenn Evilnae nicht angesprochen wurde.
    # -----------------------------------------------------

    add_channel_user_message(
        channel_id,
        message,
        reply_target
    )

    add_participant_message(
        channel_id,
        message,
        reply_target
    )

    channel_snapshot = list(
        get_channel_context(
            channel_id
        )
    )

    # -----------------------------------------------------
    # SHOULD EVILNAE REPLY?
    # -----------------------------------------------------

    should_reply = False

    message_lower = (
        message.content.lower()
    )

    # Discord Mention
    if bot.user in message.mentions:

        should_reply = True

    # evil / evilnae / evil nae
    if any(
        trigger in message_lower
        for trigger in TRIGGER_WORDS
    ):

        should_reply = True

    # Discord Reply direkt auf Evilnae
    if reply_target:

        if (
            reply_target.author.id
            == bot.user.id
        ):

            should_reply = True

    if not should_reply:

        return

    # -----------------------------------------------------
    # RESPONSE ORDER PER USER
    # -----------------------------------------------------

    user_lock = (
        get_response_lock(
            user_id
        )
    )

    async with user_lock:

        total_start = (
            time.perf_counter()
        )

        # -------------------------------------------------
        # SAVE USERNAME
        # -------------------------------------------------

        database.set_username(
            user_id,
            username
        )

        # -------------------------------------------------
        # CLEAN MESSAGE
        # -------------------------------------------------

        user_text = (
            message.content.replace(
                f"<@{bot.user.id}>",
                ""
            )
        )

        user_text = (
            user_text.replace(
                f"<@!{bot.user.id}>",
                ""
            )
        )

        trigger_pattern = "|".join(
            re.escape(
                trigger
            )
            for trigger
            in TRIGGER_WORDS
        )

        # Trigger nur entfernen,
        # wenn er am Anfang als Anrede steht.

        user_text = re.sub(
            rf"^\s*(?:{trigger_pattern})"
            rf"[\s,:;!\-]*",
            "",
            user_text,
            flags=re.IGNORECASE
        )

        user_text = (
            user_text.strip()
        )

        if not user_text:

            user_text = "Hey."

        lower_text = (
            user_text.lower()
        )

        # -------------------------------------------------
        # SAFETY
        # -------------------------------------------------

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
                "hey. ernsthaft jetzt — "
                "bitte red mit jemandem darüber, okay? "
                "du musst damit nicht alleine sein ❤️",
                mention_author=False
            )

            return

        # -------------------------------------------------
        # LONG TERM USER BUFFER
        #
        # Nur Nachrichten,
        # die wirklich an Evilnae gerichtet sind.
        # -------------------------------------------------

        buffer_text = (
            user_text
        )

        if (
            reply_target
            and
            reply_target.author.id
            != bot.user.id
        ):

            reply_username = (
                reply_target.author.display_name
            )

            buffer_text = (
                f"[Antwort auf {reply_username}] "
                f"{user_text}"
            )

        database.add_buffer_message(
            user_id,
            buffer_text
        )

        # -------------------------------------------------
        # MOOD
        #
        # WICHTIG:
        # Relationship-Punkte beeinflussen den Mood
        # NICHT mehr.
        #
        # Die Stimmung ist nur kurzfristiger Zustand.
        # -------------------------------------------------

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

        # Seltene natürliche Stimmungsschwankung

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

        # -------------------------------------------------
        # DIRECT USER CONTEXT
        # -------------------------------------------------

        direct_context_text = (
            format_user_context(
                user_id
            )
        )

        # -------------------------------------------------
        # ACTIVE PARTICIPANTS
        # -------------------------------------------------

        participant_context_text = (
            format_participant_contexts(
                channel_id,
                channel_snapshot
            )
        )

        # -------------------------------------------------
        # RESOLVED SHORT CONTEXT
        # -------------------------------------------------

        resolved_short_context_text = (
            format_resolved_short_context(
                channel_snapshot
            )
        )

        # -------------------------------------------------
        # FULL CHANNEL CONTEXT
        # -------------------------------------------------

        group_context_text = (
            format_channel_context(
                channel_snapshot
            )
        )

        # -------------------------------------------------
        # CURRENT DISCORD REPLY CONTEXT
        # -------------------------------------------------

        reply_context_text = (
            "Die aktuelle Nachricht ist "
            "keine Discord-Antwort."
        )

        if reply_target:

            reply_author = (
                reply_target.author.display_name
            )

            reply_author_id = str(
                reply_target.author.id
            )

            reply_content = (
                reply_target.content[:500]
                if reply_target.content
                else ""
            )

            reply_context_text = f"""
Die aktuelle Nachricht ist eine Discord-Antwort.

{username} antwortet auf:

Name:
{reply_author}

Discord-ID:
{reply_author_id}

Nachricht:
{reply_content}
"""

        # -------------------------------------------------
        # LONG TERM MEMORY
        # -------------------------------------------------

        user_profile = (
            database.get_profile(
                user_id
            )
        )

        # Das ist jetzt Relationship 2.0:
        # Evilnaes soziale Wahrnehmung / Beziehung
        # als natürlicher Text.

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

        if recent_memories:

            recent_memory_text = (
                "\n".join(
                    recent_memories
                )
            )

        else:

            recent_memory_text = (
                "Keine."
            )

        if memory_archive:

            archive_text = (
                memory_archive
            )

        else:

            archive_text = (
                "Noch kein älteres Archiv."
            )

        if social_impression:

            social_impression_text = (
                social_impression
            )

        else:

            social_impression_text = (
                "Evilnae hat noch keinen "
                "stabilen persönlichen Eindruck "
                "von dieser Person entwickelt."
            )

        # -------------------------------------------------
        # HANAE SPECIAL
        # -------------------------------------------------

        special_user_prompt = ""

        if (
            user_id
            == HANAE_USER_ID
        ):

            special_user_prompt = (
                HANAE_PROMPT
            )

        # -------------------------------------------------
        # RELATIONSHIP 2.0 PROMPT
        # -------------------------------------------------

        relationship_prompt = f"""
==================================================
EVILNAES SOZIALE BEZIEHUNG ZU {username}
==================================================

{social_impression_text}


WICHTIG:

Diese Beschreibung ist Evilnaes
langfristige soziale Wahrnehmung
von {username}.

Nutze sie subtil.

Du sollst NICHT direkt sagen:

"Meine Beziehung zu dir ist..."

oder:

"Mein gespeicherter Eindruck sagt..."

Die Beziehung zeigt sich stattdessen
durch dein natürliches Verhalten.

Wenn ihr bereits vertraut seid:

- darfst du lockerer sein
- darfst du vertrauter teasen
- kannst du frühere Dynamiken natürlich aufgreifen
- musst du nicht so vorsichtig wie bei einem Fremden wirken

Wenn dein Eindruck gemischt ist:

- darfst du freundlich und gleichzeitig trocken sein
- darf eine Person dich gelegentlich nerven,
  ohne dass du sie deshalb grundsätzlich nicht magst

Wenn du die Person kaum kennst:

- verhalte dich eher neutral
- tue nicht so,
  als wärt ihr bereits beste Freunde

Sehr wichtig:

Deine aktuelle Stimmung
und deine langfristige Beziehung
sind zwei verschiedene Dinge.

Wenn dein Mood gerade "annoyed" ist,
bedeutet das NICHT automatisch,
dass du {username} nicht magst.

Wenn dein Mood gerade "soft" ist,
bedeutet das NICHT automatisch,
dass du plötzlich emotional
oder extrem anhänglich bist.

Beziehungen entwickeln sich langsam.
"""

        # -------------------------------------------------
        # HYBRID CONTEXT PROMPT
        # -------------------------------------------------

        hybrid_context_prompt = f"""
==================================================
AKTUELLER GESPRÄCHSPARTNER
==================================================

Name:
{username}

Discord-ID:
{user_id}


==================================================
DAUERHAFTES PROFIL VON {username}
==================================================

{user_profile}


==================================================
SOZIALE BEZIEHUNG / IMPRESSION
==================================================

{social_impression_text}


==================================================
ÄLTERE LANGZEIT-ERINNERUNGEN
==================================================

{archive_text}


==================================================
NEUERE LANGZEIT-ERINNERUNGEN
==================================================

{recent_memory_text}


==================================================
DIREKTER VERLAUF MIT {username}
==================================================

{direct_context_text}


==================================================
AKTIVE PERSONEN IM CHANNEL
==================================================

{participant_context_text}


==================================================
AUFGELÖSTE KURZANTWORTEN
==================================================

{resolved_short_context_text}


==================================================
GESAMTER KURZFRISTIGER CHANNEL-VERLAUF
==================================================

{group_context_text}


==================================================
AKTUELLER DISCORD-REPLY
==================================================

{reply_context_text}


==================================================
WICHTIGE USER-TRENNUNG
==================================================

Im Channel können gleichzeitig
viele verschiedene Menschen sprechen.

Jede Discord-ID gehört exakt einer Person.

Der aktuelle Gesprächspartner ist:

{username}

Discord-ID:

{user_id}

Profil,
soziale Impression,
Summaries
und Archiv

gehören ausschließlich zu {username}.

Aussagen anderer Menschen im Channel
dürfen niemals automatisch {username}
zugeschrieben werden.


Beispiel:

Hanae:
"Ich liebe Sushi."

{username}:
"Ich liebe Ramen."

Dann gilt:

Hanae liebt Sushi.

{username} liebt Ramen.

NICHT:

{username} liebt Sushi.


==================================================
KURZE KONTEXTABHÄNGIGE AUSSAGEN
==================================================

Nachrichten wie:

- "ich auch"
- "same"
- "dito"
- "genau"
- "ja"
- "ja genau"
- "stimmt"
- "true"
- "fr"
- "me too"

können nur durch vorherigen Gesprächskontext
korrekt verstanden werden.

Nutze dafür besonders:

AUFGELÖSTE KURZANTWORTEN

Beispiel:

Seiichi:
"Ich hätte gerne ein Eis."

Hanae:
"ich auch"

Dann bedeutet Hanaes Aussage
sehr wahrscheinlich:

Hanae hätte ebenfalls gerne ein Eis.

Wenn der Zusammenhang eindeutig ist,
sage nicht:

"Ich weiß nicht, was sie meint."

Wenn mehrere plausible Bezüge existieren,
darfst du dagegen ehrlich unsicher sein.

Erfinde niemals einen Zusammenhang,
der nicht durch den bereitgestellten Kontext
unterstützt wird.


==================================================
FRAGEN ÜBER ANDERE PERSONEN
==================================================

Wenn {username} beispielsweise fragt:

- "Was hat Hanae gerade gesagt?"
- "Was meinte Hanae damit?"
- "Was meinte Max mit same?"
- "Worauf bezog sich das?"
- "Wer hat gerade X gesagt?"
- "Was haben die anderen geschrieben?"

prüfe in dieser Reihenfolge:

1. aktueller Discord-Reply
2. aufgelöste Kurzantworten
3. aktive Personen im Channel
4. gesamter kurzfristiger Channel-Verlauf

Wenn die gesuchte Information vorhanden ist:

- gib sie korrekt oder sinngemäß wieder
- ordne sie der richtigen Person zu
- erkläre einen eindeutigen Zusammenhang
- behaupte nicht,
  dass du die Nachricht nicht gesehen hast
- erfinde keine andere Aussage


==================================================
BEZIEHUNG UND STIMMUNG
==================================================

Die soziale Beziehung zu {username}
ist langfristig.

Der aktuelle Mood ist kurzfristig.

Diese Dinge dürfen nicht verwechselt werden.

Beispiel:

Du kannst {username} grundsätzlich mögen,
aber gerade müde oder genervt sein.

Du kannst jemanden noch kaum kennen,
aber gerade ungewöhnlich freundlich drauf sein.

Beides ist normal.


==================================================
PRIORITÄTEN
==================================================

Für persönliche Fakten über {username}:

1. dauerhaftes Profil
2. neuere Langzeit-Erinnerungen
3. älteres Archiv
4. direkter Verlauf

Für deine soziale Haltung gegenüber {username}:

1. soziale Beziehung / Impression
2. direkter Verlauf
3. aktuelle Interaktion

Für aktuelle Gruppengespräche:

1. aktueller Discord-Reply
2. aufgelöste Kurzantworten
3. aktive Personen
4. gesamter Channel-Verlauf

Nutze Gruppenkontext nur,
wenn er tatsächlich relevant ist.

Du musst nicht ungefragt
alles im Channel kommentieren.

Nutze Namen natürlich
und nicht in jeder Nachricht.
"""

        # -------------------------------------------------
        # HUMAN TYPING DELAY
        # -------------------------------------------------

        message_length = len(
            user_text
        )

        base_delay = (
            random.uniform(
                0.8,
                1.8
            )
        )

        extra_delay = min(
            message_length / 80,
            2.5
        )

        typing_delay = (
            base_delay
            + extra_delay
        )

        # -------------------------------------------------
        # GENERATE RESPONSE
        # -------------------------------------------------

        try:

            async with (
                message.channel.typing()
            ):

                response_task = (
                    asyncio.create_task(
                        safe_openai_request(

                            model="gpt-4o-mini",

                            instructions=(
                                SYSTEM_PROMPT
                                + "\n\n"
                                + MOOD_PROMPTS[
                                    moods[
                                        mood_key
                                    ]
                                ]
                                + "\n\n"
                                + relationship_prompt
                                + "\n\n"
                                + special_user_prompt
                                + "\n\n"
                                + hybrid_context_prompt
                            ),

                            input=(
                                f"{username} "
                                f"schreibt jetzt:\n"
                                f"{user_text}"
                            ),

                            max_output_tokens=250,

                            timeout=(
                                OPENAI_RESPONSE_TIMEOUT
                            ),

                            request_type="response",

                            username=username
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
                    response_task,
                    delay_task
                )

        except Exception as error:

            duration = (
                time.perf_counter()
                - total_start
            )

            print(
                f"[RESPONSE ERROR] "
                f"user={username} "
                f"duration={duration:.2f}s "
                f"error="
                f"{type(error).__name__}: "
                f"{error}"
            )

            try:

                await message.reply(
                    "okay irgendwas ist grad bei mir kaputt 💀",
                    mention_author=False
                )

            except discord.HTTPException:

                pass

            return

        # -------------------------------------------------
        # RESPONSE TEXT
        # -------------------------------------------------

        answer = (
            response.output_text.strip()
        )

        if not answer:

            answer = "hm."

        # -------------------------------------------------
        # DIRECT USER CONTEXT UPDATE
        # -------------------------------------------------

        user_context = (
            get_user_context(
                user_id
            )
        )

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

        # -------------------------------------------------
        # CHANNEL CONTEXT UPDATE
        # -------------------------------------------------

        add_channel_bot_message(
            channel_id,
            user_id,
            username,
            answer
        )

        # -------------------------------------------------
        # SEND RESPONSE
        # -------------------------------------------------

        try:

            if (
                random.randint(
                    1,
                    SPLIT_CHANCE
                )
                == 1
                and
                len(answer) > 40
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
                            0.8,
                            2.0
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
                f"[DISCORD SEND ERROR] "
                f"user={username} "
                f"error={error}"
            )

            return

        # -------------------------------------------------
        # FINAL RESPONSE LOG
        # -------------------------------------------------

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
            f"[RESPONSE DONE] "
            f"user={username} "
            f"duration={total_duration:.2f}s "
            f"buffer={buffer_count}/"
            f"{MEMORY_BUFFER_THRESHOLD} "
            f"mood={moods[mood_key]} "
            f"relationship=text"
        )

        # -------------------------------------------------
        # BACKGROUND MEMORY
        # -------------------------------------------------

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