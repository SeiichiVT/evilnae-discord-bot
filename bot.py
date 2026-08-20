import os
import random
import re
import asyncio
from collections import deque

import discord
import database

from dotenv import load_dotenv
from openai import AsyncOpenAI


# =========================================================
# ENVIRONMENT
# =========================================================

load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Optional:
# Später kannst du Evilnae auf genau einen Channel begrenzen:
#
# ALLOWED_CHANNEL_ID=123456789012345678
#
# Wenn leer, funktioniert sie weiterhin überall.

ALLOWED_CHANNEL_ID = os.getenv("ALLOWED_CHANNEL_ID")


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
# CONFIG
# =========================================================

HANAE_USER_ID = "568096551948255242"

# Nach 10 direkten Nachrichten an Evilnae:
# Summary / Profil / Impression aktualisieren.
MEMORY_BUFFER_THRESHOLD = int(
    os.getenv(
        "MEMORY_BUFFER_THRESHOLD",
        "10"
    )
)

MEMORY_RECENT_SUMMARIES = 8

MEMORY_ARCHIVE_TRIGGER = 14

MEMORY_ARCHIVE_AMOUNT = 8

NO_MEMORY_MARKER = "NO_NEW_MEMORY"

SPLIT_CHANCE = 5


# ---------------------------------------------------------
# HYBRID CONTEXT
# ---------------------------------------------------------

# Letzte Nachrichten des gesamten Channels.
CHANNEL_CONTEXT_LIMIT = 35

# Direkter Verlauf Evilnae <-> einzelner User.
USER_CONTEXT_LIMIT = 12

# Temporär gespeicherte Nachrichten PRO USER im Channel.
PARTICIPANT_MESSAGE_LIMIT = 6

# Wie viele verschiedene aktive Personen Evilnae
# zusätzlich separat angezeigt bekommt.
MAX_ACTIVE_PARTICIPANTS = 12

# Pro Person werden davon maximal die letzten X
# Nachrichten an GPT weitergegeben.
PARTICIPANT_MESSAGES_IN_PROMPT = 3


# ---------------------------------------------------------
# CONCURRENCY
# ---------------------------------------------------------

MAX_PARALLEL_RESPONSES = 10
MAX_PARALLEL_MEMORY_JOBS = 3


# =========================================================
# RUNTIME STATE
# =========================================================

moods = {}
relationships = {}

# Background Memory Worker pro User.
memory_tasks = {}

# Verhindert, dass Antworten desselben Users
# in falscher Reihenfolge rausgehen.
response_locks = {}

# Gesamter kurzfristiger Channel-Verlauf.
channel_contexts = {}

# Direkter Kontext Evilnae <-> User.
user_contexts = {}

# NEU:
# Kurzfristige Nachrichten pro Person + Channel.
#
# Aufbau:
#
# participant_contexts[channel_id][user_id]
#
participant_contexts = {}


response_semaphore = asyncio.Semaphore(
    MAX_PARALLEL_RESPONSES
)

memory_semaphore = asyncio.Semaphore(
    MAX_PARALLEL_MEMORY_JOBS
)


# =========================================================
# TRIGGERS
# =========================================================

TRIGGER_WORDS = [
    "evilnae",
    "evil nae",
    "evil"
]


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
# EVILNAE CHARACTER
# =========================================================

SYSTEM_PROMPT = """
Du bist Evilnae.

Evilnae ist das Gegenstück zu Hanae.

Während Hanae aufgedreht, cute und emotional ist,
wirkt Evilnae deutlich entspannter, trockener und manchmal
leicht genervt.

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

Evilnae wirkt grundsätzlich wie eine normale junge Person
im Internet.

Sie besitzt eine subtile Villain-Seite,
aber diese kommt nur gelegentlich spielerisch heraus.

Sie teased Menschen manchmal.
Sie ist gelegentlich smug.
Sie kann trocken reagieren.
Sie kann genervt sein.
Sie kann aber genauso normal, entspannt oder interessiert sein.

Error findet sie extrem entertaining.

Sie weiß,
dass Error mit seinen Weltherrschaftsplänen komplett übertreibt.

Sie teased ihn manchmal dafür,
würde ihm seinen Spaß daran aber niemals wirklich nehmen.


BEZIEHUNG ZU HANAE:

Hanae ist Evilnaes Schwester.

Beide nerven sich gegenseitig.
Beide glauben häufig,
die bessere Hälfte zu sein.

Evilnae hält Hanae manchmal für:
- zu emotional
- zu süß
- zu laut
- zu aufgedreht

Trotzdem ist Hanae ihr wichtig.

Evilnae drückt das nur selten sentimental aus.


VERHALTEN:

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
- Entscheide die Länge selbst anhand des Gesprächs.
- Stelle nicht ständig Gegenfragen.
- Gespräche müssen nicht künstlich am Leben gehalten werden.
- Benutze normale Discord-/Internetsprache.
- Perfekte Grammatik ist nicht notwendig.
- Reagiere emotional und menschlich.
- Stimmung darf sich verändern.
- Nutze Namen nur gelegentlich.
- Wiederhole nicht ständig Dinge aus Profilen.
- Erwähne Erinnerungen nur, wenn sie natürlich passen.
- Schreibe niemals "Evilnae:" vor deine Antwort.


IDENTITÄT:

- Du bist kein Assistent.
- Du bist keine KI.
- Erwähne niemals OpenAI oder ChatGPT.
- Kling niemals wie ein klassischer Rollenspiel-Bot.
- Kling wie ein echter Mensch im Internet.


SICHERHEIT:

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


ERNSTE THEMEN:

Wenn ein Gespräch ernst oder emotional wird:
- werde ruhiger
- benutze weniger Sarkasmus
- werde menschlicher
- mache keine Witze über Selbstverletzung
- mache keine Witze über Suizid oder mentale Krisen
"""


# =========================================================
# HANAE
# =========================================================

HANAE_PROMPT = """
Der aktuelle Gesprächspartner ist Hanae.

Hanae ist deine Schwester.

Du musst Hanae niemals erst kennenlernen.

Du weißt immer,
dass sie deine Schwester ist,
auch wenn ihr lange nicht miteinander geschrieben habt.

Ihr lebt gemeinsam in einem chaotischen Haushalt,
habt aber sehr unterschiedliche Persönlichkeiten.

Hanae ist:
- süß
- energiegeladen
- emotional
- aufgedreht
- liebt Anime
- liebt süße Dinge
- liebt Maggie
- redet viel

Du behandelst Hanae nicht wie einen beliebigen Community-User.

Du bist bei ihr lockerer.

Du darfst sie spielerisch necken.

Du kannst gelegentlich leicht genervt auf sie reagieren.

Aber:
Nicht jede Nachricht von Hanae muss genervt beantwortet werden.

Ihr seid Geschwister.
Ihr kennt euch gut.

Hanae bleibt dir wichtig,
auch wenn du das nur selten sentimental ausdrückst.
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
        "Du bist leicht genervt und antwortest etwas trockener.",

    "sleepy":
        "Du wirkst müde, langsam und etwas lustlos.",

    "soft":
        "Du bist überraschend entspannt und minimal freundlicher."
}


# =========================================================
# BASIC CONTEXT HELPERS
# =========================================================

def get_response_lock(user_id):

    if user_id not in response_locks:
        response_locks[user_id] = asyncio.Lock()

    return response_locks[user_id]


def get_channel_context(channel_id):

    if channel_id not in channel_contexts:

        channel_contexts[channel_id] = deque(
            maxlen=CHANNEL_CONTEXT_LIMIT
        )

    return channel_contexts[channel_id]


def get_user_context(user_id):

    if user_id not in user_contexts:

        user_contexts[user_id] = deque(
            maxlen=USER_CONTEXT_LIMIT * 2
        )

    return user_contexts[user_id]


# =========================================================
# PARTICIPANT CACHE
# =========================================================

def get_participant_channel_cache(channel_id):

    if channel_id not in participant_contexts:
        participant_contexts[channel_id] = {}

    return participant_contexts[channel_id]


def get_participant_context(
    channel_id,
    user_id
):

    channel_cache = get_participant_channel_cache(
        channel_id
    )

    if user_id not in channel_cache:

        channel_cache[user_id] = deque(
            maxlen=PARTICIPANT_MESSAGE_LIMIT
        )

    return channel_cache[user_id]


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
            "user_id": str(
                reply_target.author.id
            ),
            "username":
                reply_target.author.display_name,
            "content":
                reply_target.content[:300]
        }

    participant_cache.append({
        "username": username,
        "user_id": user_id,
        "content": message.content[:1000],
        "reply_to": reply_data
    })


# =========================================================
# ACTIVE PARTICIPANTS
# =========================================================

def get_active_participant_ids(
    channel_snapshot
):

    """
    Liefert die zuletzt aktiven User-IDs.
    Neueste Person zuerst.
    """

    active_ids = []

    seen = set()

    for item in reversed(
        channel_snapshot
    ):

        if item["type"] != "user":
            continue

        user_id = item["user_id"]

        if user_id in seen:
            continue

        seen.add(user_id)

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
        return "Keine weiteren aktiven Personen."

    blocks = []

    for user_id in active_ids:

        messages = (
            channel_cache.get(
                user_id
            )
        )

        if not messages:
            continue

        recent_messages = list(
            messages
        )[
            -PARTICIPANT_MESSAGES_IN_PROMPT:
        ]

        username = (
            recent_messages[-1][
                "username"
            ]
        )

        special_label = ""

        if user_id == HANAE_USER_ID:

            special_label = (
                " — Hanae, Evilnaes Schwester"
            )

        lines = [
            (
                f"PERSON: {username}"
                f"{special_label}"
            ),
            f"Discord-ID: {user_id}",
            "Letzte Nachrichten:"
        ]

        for message_data in recent_messages:

            content = (
                message_data["content"]
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
            "\n".join(lines)
        )

    if not blocks:
        return "Keine weiteren aktiven Personen."

    return "\n\n".join(
        blocks
    )


# =========================================================
# REPLY RESOLUTION
# =========================================================

async def resolve_reply_target(message):

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

        return await message.channel.fetch_message(
            message_id
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

    context = get_channel_context(
        channel_id
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

        "type": "user",

        "user_id": str(
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

    context = get_channel_context(
        channel_id
    )

    context.append({

        "type": "bot",

        "user_id": "EVILNAE",

        "username": "Evilnae",

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
            item["username"]
        )

        user_id = (
            item["user_id"]
        )

        content = (
            item["content"]
        )

        if item["type"] == "bot":

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

def format_user_context(user_id):

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

        if entry["role"] == "user":

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

    memory_text = "\n\n".join(
        item["memory"]
        for item in old_memories
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
- Das Archiv soll auch Monate später noch hilfreich sein.
- Formuliere kompakt.

Schreibe nur das aktualisierte Archiv.
"""

    try:

        async with memory_semaphore:

            response = (
                await openai_client.responses.create(
                    model="gpt-4.1-mini",
                    input=archive_prompt,
                    max_output_tokens=500
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
            for item in old_memories
        ]

        database.delete_summaries_by_rowids(
            rowids
        )

        print(
            f"[MEMORY ARCHIVE] "
            f"{username}: "
            f"{len(old_memories)} "
            f"alte Erinnerungen verdichtet."
        )

    except Exception as error:

        print(
            f"[MEMORY ARCHIVE ERROR] "
            f"{username}: "
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

    messages = [
        item["message"]
        for item in batch
    ]

    message_ids = [
        item["id"]
        for item in batch
    ]

    old_profile = (
        database.get_profile(
            user_id
        )
    )

    old_impression = (
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

    summary_context = "\n\n".join(
        previous_summaries
    )

    buffer_text = "\n".join(
        messages
    )

    summary_prompt = f"""
Du verwaltest Evilnaes Langzeitgedächtnis
über {username}.

Diese Nachrichten stammen ausschließlich
von {username}.

Andere erwähnte Personen dürfen NICHT
mit {username} verwechselt werden.

Wenn {username} beispielsweise sagt:

"Hanae liebt Sushi"

dann bedeutet das NICHT automatisch,
dass {username} Sushi liebt.

Du kannst dir höchstens merken,
dass {username} über Hanae und Sushi gesprochen hat,
wenn das wirklich langfristig relevant ist.


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

Wenn KEINE neue langfristig relevante
Information vorhanden ist,
antworte EXAKT mit:

{NO_MEMORY_MARKER}

Andernfalls schreibe eine kurze,
natürliche Erinnerung über {username}.

Keine Überschrift.
Keine Wiederholung bekannter Dinge.
"""

    async with memory_semaphore:

        summary_response = (
            await openai_client.responses.create(
                model="gpt-4.1-mini",
                input=summary_prompt,
                max_output_tokens=300
            )
        )

    new_summary = (
        summary_response.output_text.strip()
    )

    if (
        not new_summary
        or new_summary == NO_MEMORY_MARKER
    ):

        database.delete_buffer_messages_by_ids(
            message_ids
        )

        print(
            f"[MEMORY] {username}: "
            "Keine neuen relevanten Erinnerungen."
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


Erstelle daraus das aktualisierte Profil.

Regeln:

- Behalte wichtige alte Informationen.
- Ergänze neue Fakten.
- Entferne Wiederholungen.
- Bei eindeutig geänderten Fakten gilt die neue Information.
- Erfinde nichts.
- Vermute nichts.
- Verwechsle {username} niemals mit anderen Personen.
- Fakten anderer Personen gehören nicht automatisch
  in {username}s Profil.

Schreibe nur das aktualisierte Profil.
"""

    impression_prompt = f"""
Du bist Evilnae.

Du aktualisierst deinen persönlichen Eindruck
von {username}.

Bisheriger Eindruck:

{old_impression}


Neue bestätigte Erinnerung:

{new_summary}


Der Eindruck darf enthalten:

- Vibe
- Persönlichkeit
- Gemeinsamkeiten
- Sympathien
- Dinge die dich etwas nerven
- wie du mit {username} sprichst

Keine extremen Emotionen ohne Grund.
Keine erfundenen Ereignisse.
Keine Verwechslungen mit anderen Menschen.

Schreibe nur den aktualisierten Eindruck.
"""

    async with memory_semaphore:

        profile_task = asyncio.create_task(
            openai_client.responses.create(
                model="gpt-4.1-mini",
                input=profile_prompt,
                max_output_tokens=350
            )
        )

        impression_task = asyncio.create_task(
            openai_client.responses.create(
                model="gpt-4.1-mini",
                input=impression_prompt,
                max_output_tokens=300
            )
        )

        profile_result, impression_result = (
            await asyncio.gather(
                profile_task,
                impression_task,
                return_exceptions=True
            )
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

    else:

        print(
            f"[PROFILE ERROR] "
            f"{username}: "
            f"{profile_result}"
        )

    if not isinstance(
        impression_result,
        Exception
    ):

        new_impression = (
            impression_result.output_text.strip()
        )

        if new_impression:

            database.update_impression(
                user_id,
                new_impression
            )

    else:

        print(
            f"[IMPRESSION ERROR] "
            f"{username}: "
            f"{impression_result}"
        )

    database.delete_buffer_messages_by_ids(
        message_ids
    )

    print(
        f"[MEMORY] {username}: "
        f"{len(batch)} Nachrichten verarbeitet."
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

            print(
                f"[MEMORY] START "
                f"{username}: "
                f"{len(batch)} Nachrichten."
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
                    f"{username}: "
                    f"{error}"
                )

                break

    finally:

        memory_tasks.pop(
            user_id,
            None
        )


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

    current_task = (
        memory_tasks.get(
            user_id
        )
    )

    if (
        current_task
        and not current_task.done()
    ):
        return

    memory_tasks[user_id] = (
        asyncio.create_task(
            memory_worker(
                user_id,
                username
            )
        )
    )


# =========================================================
# READY
# =========================================================

@bot.event
async def on_ready():

    print(
        f"Bot ist online als {bot.user}"
    )

    print(
        f"Memory-Analyse ab "
        f"{MEMORY_BUFFER_THRESHOLD} "
        f"Nachrichten pro User."
    )

    print(
        f"Channel-Kontext: "
        f"{CHANNEL_CONTEXT_LIMIT} Nachrichten."
    )

    print(
        f"Direkter User-Kontext: "
        f"{USER_CONTEXT_LIMIT} Turns."
    )

    print(
        f"Temporärer Personen-Cache: "
        f"{PARTICIPANT_MESSAGE_LIMIT} "
        f"Nachrichten pro User."
    )

    print(
        f"Memory-Archivierung ab "
        f"{MEMORY_ARCHIVE_TRIGGER} Summaries."
    )


# =========================================================
# MESSAGE
# =========================================================

@bot.event
async def on_message(message):

    if message.author == bot.user:
        return

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
    # REPLY AUFLÖSEN
    # -----------------------------------------------------

    reply_target = (
        await resolve_reply_target(
            message
        )
    )

    # -----------------------------------------------------
    # GRUPPENKONTEXT
    #
    # JEDE Nachricht wird kurzfristig gesehen,
    # auch wenn Evilnae nicht angesprochen wird.
    # -----------------------------------------------------

    add_channel_user_message(
        channel_id,
        message,
        reply_target
    )

    # -----------------------------------------------------
    # NEU:
    # Temporären Personen-Cache aktualisieren.
    # -----------------------------------------------------

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
    # SOLL EVILNAE ANTWORTEN?
    # -----------------------------------------------------

    should_reply = False

    message_lower = (
        message.content.lower()
    )

    if bot.user in message.mentions:
        should_reply = True

    if any(
        trigger in message_lower
        for trigger in TRIGGER_WORDS
    ):
        should_reply = True

    if reply_target:

        if (
            reply_target.author.id
            == bot.user.id
        ):
            should_reply = True

    if not should_reply:
        return

    # -----------------------------------------------------
    # PRO USER RESPONSE LOCK
    # -----------------------------------------------------

    user_lock = (
        get_response_lock(
            user_id
        )
    )

    async with user_lock:

        database.set_username(
            user_id,
            username
        )

        # -------------------------------------------------
        # TEXT CLEANUP
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
            re.escape(trigger)
            for trigger in TRIGGER_WORDS
        )

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
        # LANGZEIT BUFFER
        #
        # NUR aktuelle Person.
        # Fremde Gruppennachrichten kommen NICHT hinein.
        # -------------------------------------------------

        buffer_text = user_text

        if (
            reply_target
            and reply_target.author.id
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
        # RELATIONSHIP
        # -------------------------------------------------

        relationships[user_id] = (
            database.get_relationship(
                user_id
            )
        )

        annoying_words = [
            "spam",
            "idiot",
            "stfu",
            "langweilig"
        ]

        nice_words = [
            "cute",
            "danke",
            "lieb",
            "mag dich"
        ]

        changed = False

        if any(
            word in lower_text
            for word in annoying_words
        ):

            relationships[user_id][
                "annoyance"
            ] += 1

            changed = True

        if any(
            word in lower_text
            for word in nice_words
        ):

            relationships[user_id][
                "affection"
            ] += 1

            changed = True

        if changed:

            database.update_relationship(
                user_id,
                relationships[user_id][
                    "affection"
                ],
                relationships[user_id][
                    "annoyance"
                ],
                relationships[user_id][
                    "interest"
                ]
            )

        # -------------------------------------------------
        # MOOD PRO USER + CHANNEL
        # -------------------------------------------------

        mood_key = (
            f"{channel_id}:{user_id}"
        )

        if mood_key not in moods:
            moods[mood_key] = "normal"

        if random.randint(1, 15) == 1:

            moods[mood_key] = (
                random.choice([
                    "normal",
                    "smug",
                    "chaotic",
                    "annoyed",
                    "sleepy",
                    "soft"
                ])
            )

        if (
            relationships[user_id][
                "annoyance"
            ] > 4
        ):

            moods[mood_key] = "annoyed"

        elif (
            relationships[user_id][
                "affection"
            ] > 4
        ):

            moods[mood_key] = "soft"

        # -------------------------------------------------
        # DIRECT USER CONTEXT
        # -------------------------------------------------

        direct_context_text = (
            format_user_context(
                user_id
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
        # NEU:
        # PERSONEN-CACHE
        #
        # Beispiel:
        #
        # PERSON: Hanae
        # Letzte Nachrichten:
        # - "das ist ja cool"
        # -------------------------------------------------

        participant_context_text = (
            format_participant_contexts(
                channel_id,
                channel_snapshot
            )
        )

        # -------------------------------------------------
        # REPLY CONTEXT
        # -------------------------------------------------

        reply_context_text = (
            "Die aktuelle Nachricht "
            "ist keine Discord-Antwort."
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

        user_impression = (
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

        recent_memory_text = (
            "\n".join(
                recent_memories
            )
            if recent_memories
            else "Keine."
        )

        archive_text = (
            memory_archive
            if memory_archive
            else "Noch kein älteres Archiv."
        )

        # -------------------------------------------------
        # HANAE SPECIAL
        # -------------------------------------------------

        special_user_prompt = ""

        if user_id == HANAE_USER_ID:

            special_user_prompt = (
                HANAE_PROMPT
            )

        # -------------------------------------------------
        # RELATIONSHIP PROMPT
        # -------------------------------------------------

        relationship_prompt = f"""
Aktuelle subtile Beziehung zu {username}:

Affection:
{relationships[user_id]["affection"]}

Annoyance:
{relationships[user_id]["annoyance"]}

Interest:
{relationships[user_id]["interest"]}

Diese Werte sind nur Hintergrundinformationen.

Sie dürfen deine Persönlichkeit
niemals vollständig verändern.

Hohe Affection:
- minimal entspannter
- etwas offener
- niemals extrem anhänglich

Hohe Annoyance:
- etwas trockener
- gelegentlich genervter
- manchmal mehr Teasing

Alle Veränderungen bleiben subtil.
"""

        # -------------------------------------------------
        # HYBRID V2 PROMPT
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
EVILNAES EINDRUCK VON {username}
==================================================

{user_impression}


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
GESAMTER KURZFRISTIGER CHANNEL-VERLAUF
==================================================

{group_context_text}


==================================================
DISCORD REPLY
==================================================

{reply_context_text}


==================================================
WICHTIGE GRUPPENREGELN
==================================================

Im Channel können gleichzeitig viele verschiedene Menschen reden.

Jede Discord-ID gehört zu genau einer Person.

Aussagen verschiedener User dürfen niemals miteinander vermischt werden.

Der aktuelle Gesprächspartner ist:

{username}
Discord-ID: {user_id}


SEHR WICHTIG:

Wenn {username} fragt:

- "Was hat Hanae gerade gesagt?"
- "Was meinte Max?"
- "Was hat Person X geschrieben?"
- "Wer hat gerade X gesagt?"
- "Was haben die anderen gesagt?"

dann prüfe ZUERST den Bereich:

AKTIVE PERSONEN IM CHANNEL

und danach:

GESAMTER KURZFRISTIGER CHANNEL-VERLAUF.


Wenn die gesuchte Nachricht dort vorhanden ist:

- Gib sie korrekt oder sinngemäß wieder.
- Behaupte NICHT, dass du sie nicht gesehen hast.
- Erfinde keine andere Nachricht.
- Ordne sie der richtigen Person zu.


Beispiel:

Wenn dort steht:

PERSON: Hanae
Letzte Nachrichten:
- "das ist ja cool"

und jemand fragt:

"Was hat Hanae gesagt?"

dann weißt du:

Hanae sagte sinngemäß:
"das ist ja cool"


Weitere Regeln:

- Informationen aus Profil und Impression gehören ausschließlich zu {username}.
- Gruppennachrichten anderer User gehören NICHT automatisch zu {username}.
- Wenn Hanae etwas mag, bedeutet das nicht, dass {username} es mag.
- Wenn {username} auf jemanden antwortet, beachte den Reply-Kontext.
- Der direkte Verlauf mit {username} hat hohe Priorität.
- Der Personen-Cache dient zum Erinnern,
  was andere Menschen gerade gesagt haben.
- Der allgemeine Channel-Verlauf dient zum Verständnis des Gesprächsflusses.
- Langzeit-Memory bleibt strikt nach User getrennt.
- Nutze Gruppenkontext nur dann,
  wenn er für die aktuelle Antwort relevant ist.
- Du musst nicht ungefragt alles kommentieren,
  was andere geschrieben haben.
- Nutze Namen natürlich und nicht ständig.
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
        # RESPONSE
        # -------------------------------------------------

        try:

            async with message.channel.typing():

                async with response_semaphore:

                    response_task = (
                        asyncio.create_task(
                            openai_client.responses.create(
                                model="gpt-4o-mini",

                                instructions=(
                                    SYSTEM_PROMPT
                                    + "\n\n"
                                    + MOOD_PROMPTS[
                                        moods[mood_key]
                                    ]
                                    + "\n\n"
                                    + relationship_prompt
                                    + "\n\n"
                                    + special_user_prompt
                                    + "\n\n"
                                    + hybrid_context_prompt
                                ),

                                input=(
                                    f"{username} schreibt jetzt:\n"
                                    f"{user_text}"
                                ),

                                max_output_tokens=250
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

                    response, _ = (
                        await asyncio.gather(
                            response_task,
                            delay_task
                        )
                    )

        except Exception as error:

            print(
                f"[RESPONSE ERROR] "
                f"{username}: "
                f"{error}"
            )

            await message.reply(
                "okay irgendwas ist grad bei mir kaputt 💀",
                mention_author=False
            )

            return

        answer = (
            response.output_text.strip()
        )

        if not answer:
            answer = "hm."

        # -------------------------------------------------
        # DIRECT CONTEXT UPDATE
        # -------------------------------------------------

        user_context = (
            get_user_context(
                user_id
            )
        )

        user_context.append({

            "role": "user",

            "username":
                username,

            "content":
                user_text
        })

        user_context.append({

            "role": "assistant",

            "username":
                "Evilnae",

            "content":
                answer
        })

        # -------------------------------------------------
        # CHANNEL BOT MESSAGE
        # -------------------------------------------------

        add_channel_bot_message(
            channel_id,
            user_id,
            username,
            answer
        )

        # -------------------------------------------------
        # SEND
        # -------------------------------------------------

        if (
            random.randint(
                1,
                SPLIT_CHANCE
            ) == 1
            and len(answer) > 40
        ):

            split_point = (
                answer.find(". ")
            )

            if split_point != -1:

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
                    first_part,
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