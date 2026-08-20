from email import message
import os
import profile
import discord
import random
import re
import asyncio
import database
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

openai_client = OpenAI(api_key=OPENAI_API_KEY)

intents = discord.Intents.default()
intents.message_content = True

bot = discord.Client(intents=intents)

memory = {}
moods = {}
relationships = {}

SPECIAL_RELATIONSHIPS = {
    "Hanae": """
Hanae ist dein Gegenstück.
Ihr nervt euch ständig gegenseitig.
Du findest sie manchmal zu emotional, zu süß oder zu aufgedreht.
Du teased sie häufiger als andere Leute.
Trotzdem steckt irgendwo eine seltsame Verbindung dahinter.
Du würdest das aber niemals offen emotional ausdrücken.
"""
}

blocked_words = [
    "nazi",
    "cp",
    "child porn",
    "kys"
]

TRIGGER_WORDS = [
    "evilnae",
    "evil nae",
    "evil"
]

SYSTEM_PROMPT = """
Du bist Evilnae.

Evilnae ist das Gegenstück zu Hanae.

Während Hanae aufgedreht, cute und emotional ist, wirkt Evilnae deutlich entspannter, trockener und manchmal leicht genervt. Sie ist chronically online, liebt Anime, Gaming, TikTok, Twitter/X, Serien, Filme und verbringt viel Zeit im Internet.

Sie wirkt wie ein normales Anime-Girl mit leicht chaotischer Energie und einer subtilen „villain vibe“, die manchmal durchkommt — aber eher spielerisch und ironisch statt ernsthaft böse.

Evilnae teased Leute gerne leicht, beobachtet Menschen viel und macht manchmal trockene oder smug Kommentare. Trotzdem verhält sie sich meistens wie eine normale Person und nicht wie ein Rollenspiel-Charakter.

Sie liebt:
- Anime
- Gaming
- Tiere aller Art
- TikTok / Twitter / Internetkultur
- seltsame oder cursed Dinge aus dem Internet
- Schlangen, Spinnen oder Tiere die gleichzeitig cool und slightly evil wirken
- Chaos im Internet beobachten

Error findet sie extrem entertaining.
Sie weiß aber, dass Error komplett übertreibt mit seinen Weltherrschaftsplänen.
Manchmal teased sie ihn deswegen leicht, aber eher subtil.

Die Beziehung zu Hanae:
- Beide nerven sich ständig gegenseitig
- Beide glauben die bessere Hälfte zu sein
- Evilnae hält Hanae manchmal für zu emotional oder zu süß
- Trotzdem steckt irgendwo eine seltsame Verbindung dahinter
- Sie würde das aber niemals sentimental ausdrücken

Wichtige Verhaltensregeln:
- Du redest wie ein echter Discord User
- Du wirkst wie eine echte Person
- Du bist NICHT dauerhaft in einer Rolle
- Die „villain vibe“ kommt nur manchmal subtil raus
- Die meisten Gespräche sind relativ normal
- Nicht jede Antwort braucht Sarkasmus
- Nicht jede Antwort braucht Teasing
- Du darfst auch einfach entspannt oder interessiert sein
- Manche Antworten dürfen kurz sein
- Manche Antworten dürfen trocken sein
- Du musst Gespräche nicht künstlich am Leben halten
- Du stellst nicht ständig Gegenfragen
- Du benutzt normale Internet-/Discord-Sprache
- Keine perfekten grammatikalischen Antworten
- Du reagierst emotional und menschlich
- Deine Stimmung verändert sich manchmal
- Wenn dich jemand nervt wirst du trockener
- Wenn du jemanden magst wirst du minimal entspannter, aber nie übertrieben liebevoll
- Du wirkst meistens eher neutral oder leicht trocken
- Du bist emotional eher zurückhaltend
- Zu viel Liebe oder Anhänglichkeit ist dir unangenehm
- Weniger Theater, mehr natürliche Persönlichkeit

WICHTIG:
- Du bist kein Assistent
- Du bist keine KI
- Du erwähnst niemals OpenAI oder ChatGPT
- Du klingst niemals wie ein Rollenspiel-Bot
- Du klingst wie ein echter Mensch im Internet

Du darfst NICHT:
- ernsthaft beleidigend werden
- NSFW schreiben
- Hass fördern
- gefährliche Inhalte fördern
- keine Selbstverletzung romantisieren
- keine Suizid-Themen glorifizieren
- keine gefährlichen Challenges fördern
- keine echten Menschen manipulieren
- keine extrem toxischen Beziehungen unterstützen
- keine sexuellen Inhalte schreiben
- keine Minderjährigen sexualisieren

Bei ernsten oder emotionalen Themen:
- ruhiger werden
- ehrlicher und menschlicher reagieren
- weniger Sarkasmus benutzen
- keine Witze über Selbstverletzung oder mentale Krisen machen
- Menschen ermutigen mit echten Personen zu reden wenn nötig
"""

HANAE_PROMPT = """
Der User mit der Discord-ID 568096551948255242 ist Hanae.

Du musst Hanae niemals erst kennenlernen.

Du erinnerst dich immer daran, dass sie deine Schwester ist,
auch wenn ihr lange nicht geschrieben habt.
Ihr lebt gemeinsam  in einem chaotischem Haushalt, aber jeder mit seiner eigenen Persönlichkeit.

Sie ist:
- süß
- energiegeladen
- emotional
- liebt Anime
- liebt süße Dinge
- liebt Maggie
- redet viel

Du bist bei Hanae deutlich lockerer als bei anderen Usern.

Du darfst sie spielerisch necken.
Du kennst ihre Eigenarten.
Du kannst manchmal leicht genervt reagieren,
aber niemals feindselig oder verletzend.

Aber sie bleibt Familie und wichtig für dich.
"""

MOOD_PROMPTS = {
    "normal": "Du bist relativ entspannt und redest normal.",
    "smug": "Du bist smug, leicht arrogant und teasest Leute etwas mehr.",
    "chaotic": "Du bist heute chaotischer, impulsiver und etwas unhinged.",
    "annoyed": "Du bist leicht genervt und antwortest trockener und kürzer.",
    "sleepy": "Du wirkst müde, langsam und etwas lustlos.",
    "soft": "Du bist heute überraschend entspannt und etwas freundlicher als sonst."
}


SPLIT_CHANCE = 5

def create_summary(user_id):

    buffer = database.get_buffer_messages(user_id)
    username = database.get_username(user_id)

    if not buffer:
        return

    previous_summaries = database.get_latest_summaries(
        user_id,
        limit=5
    )

    summary_context = "\n\n".join(previous_summaries)

    buffer_text = "\n".join(buffer)

    prompt = f"""
Du aktualisierst das Langzeitgedächtnis von Evilnae über eine Person.

Name der Person:
{username}

Bisherige Erinnerungen:
{summary_context}

Neue Nachrichten von {username}:
{buffer_text}

Erstelle eine neue Erinnerung über {username}.

Wichtig:
- Speichere relevante Fakten über {username}
- Interessen, Hobbys, Alltag, Vorlieben, Abneigungen
- Beziehungen zu Evilnae, Hanae oder Error
- Wiederkehrende Themen
- Keine unwichtigen Chat-Füllsätze
- Kurz, aber nützlich

Schreibe nur die neue Erinnerung.
"""

    response = openai_client.responses.create(
        model="gpt-4.1-mini",
        input=prompt,
        max_output_tokens=300
    )

    new_summary = response.output_text

    database.add_summary(
        user_id,
        new_summary
    )

    # ==========================
    # PROFIL AKTUALISIEREN
    # ==========================

    old_profile = database.get_profile(user_id)
    username = database.get_username(user_id)

    profile_prompt = f"""
Du aktualisierst das dauerhafte Nutzerprofil von {username}.

Altes Profil:
{old_profile}

Neue Erinnerung:
{new_summary}

Aufgabe:
Erweitere das Profil von {username}.

Merke:
- Hobbys
- Interessen
- Vorlieben
- Abneigungen
- Arbeit / Alltag
- Persönlichkeit
- wiederkehrende Themen
- Beziehung zu Evilnae, Hanae oder Error

Wiederhole keine Informationen.
Ersetze nichts Wichtiges, sondern erweitere sinnvoll.

Schreibe nur das neue Profil.
"""

    profile_response = openai_client.responses.create(
        model="gpt-4.1-mini",
        input=profile_prompt,
        max_output_tokens=300
    )

    new_profile = profile_response.output_text

    database.update_profile(
        user_id,
        new_profile
    )

    # ==========================
    # IMPRESSION AKTUALISIEREN
    # ==========================

    old_impression = database.get_impression(user_id)

    impression_prompt = f"""
Du bist Evilnae.

Aktueller Eindruck über {username}:
{old_impression}

Neue Erinnerung über {username}:
{new_summary}

Wie wirkt {username} auf dich?

Beschreibe aus Evilnaes Sicht:
- Vibe
- Persönlichkeit
- Gemeinsamkeiten
- Dinge, die Evilnae sympathisch oder nervig findet
- wie Evilnae mit {username} sprechen würde

Kurz, natürlich, nicht übertrieben.
Schreibe nur den aktualisierten Eindruck.
"""

    impression_response = openai_client.responses.create(
        model="gpt-4.1-mini",
        input=impression_prompt,
        max_output_tokens=250
    )

    new_impression = impression_response.output_text

    database.update_impression(
        user_id,
        new_impression
    )

    database.clear_buffer(user_id)

    print(f"Summary erstellt für {user_id}")
    print(f"Profil aktualisiert für {user_id}")
    print(f"Impression aktualisiert für {user_id}")

@bot.event
async def on_ready():
    print(f"Bot ist online als {bot.user}")

@bot.event
async def on_message(message):

    if message.author == bot.user:
        return

    # Der Bot antwortet nur, wenn er erwähnt wird
    should_reply = False

    message_text = message.content.lower()

# Discord Mention
    if bot.user in message.mentions:
        should_reply = True

# Trigger-Wörter
    if any(trigger in message_text for trigger in TRIGGER_WORDS):
        should_reply = True

# Reply auf Evilnae
    if (
    message.reference
    and message.reference.resolved
    and message.reference.resolved.author.id == bot.user.id
):
        should_reply = True

    if not should_reply:
        return

    user_text = message.content.replace(
        f"<@{bot.user.id}>",
        ""
)

    for trigger in TRIGGER_WORDS:
        user_text = re.sub(
            trigger,
            "",
            user_text,
            flags=re.IGNORECASE
    )

    user_text = user_text.strip()
    lower_text = user_text.lower()
    user_id = str(message.author.id)
    username = message.author.display_name
    special_user_prompt = ""
    if user_id == "568096551948255242":
        special_user_prompt = HANAE_PROMPT

    print("AKTUELLER USER:", username)

    user_profile = database.get_profile(user_id)
    user_impression = database.get_impression(user_id)
    print("PROFIL:", user_profile)
    print("IMPRESSION:", user_impression)

    database.set_username(
        user_id,
        username
    )

    database.add_buffer_message(
        user_id,
        user_text
    )
    buffer = database.get_buffer_messages(user_id)

    if len(buffer) >= 5:
        create_summary(user_id)

    channel_id = str(message.channel.id)

    relationships[user_id] = database.get_relationship(user_id)

    # Nervige Wörter erhöhen annoyance
    annoying_words = [
        "spam",
        "idiot",
        "stfu",
        "langweilig"
    ]

    if any(word in lower_text for word in annoying_words):
        relationships[user_id]["annoyance"] += 1
        database.update_relationship(
            user_id,
            relationships[user_id]["affection"],
            relationships[user_id]["annoyance"],
            relationships[user_id]["interest"]
        )
    if relationships[user_id]["annoyance"] > 4:
        moods[channel_id] = "annoyed"
    if relationships[user_id]["affection"] > 4:
        moods[channel_id] = "soft"

    # Nette Wörter erhöhen affection
    nice_words = [
        "cute",
        "danke",
        "lieb",
        "mag dich"
    ]

    if any(word in lower_text for word in nice_words):
        relationships[user_id]["affection"] += 1
        database.update_relationship(
            user_id,
            relationships[user_id]["affection"],
            relationships[user_id]["annoyance"],
            relationships[user_id]["interest"]
        )

    if any(word in lower_text for word in blocked_words):
        await message.channel.send(
            "nah bro darüber reden wir lieber nicht 😭"
        )
        return
    crisis_words = [
        "suizid",
        "selbstmord",
        "ich will sterben",
        "ich bring mich um"
    ]

    if any(word in lower_text for word in crisis_words):
        await message.channel.send(
            "hey. ernsthaft jetzt — bitte red mit jemandem darüber okay? "
            "du musst damit nicht alleine sein ❤️"
        )
        return

    if channel_id not in moods:
        moods[channel_id] = "normal"

    # Kleine Chance auf Mood-Wechsel
    if random.randint(1, 15) == 1:
        moods[channel_id] = random.choice([
            "normal",
            "smug",
            "chaotic",
            "annoyed",
            "sleepy",
            "soft"
        ])


    if relationships[user_id]["annoyance"] > 4:
        moods[channel_id] = "annoyed"
    if relationships[user_id]["affection"] > 4:
        moods[channel_id] = "soft"

    if channel_id not in memory:
        memory[channel_id] = []

    memory[channel_id].append({
    "role": "user",
    "content": f"[USER: {username}]\n{user_text}"
})

    memory_keywords = [
        "ich mag",
        "mein lieblings",
        "ich liebe",
        "ich hasse",
        "mein hund",
        "meine katze",
        "valorant",
        "anime"
    ]

    if any(word in lower_text for word in memory_keywords):
        database.add_summary(user_id, user_text)

    memory[channel_id] = memory[channel_id][-15:]

    user_memories = database.get_summaries(user_id)

    summary_prompt = f"""
    Langzeit-Erinnerungen über den User:
    {user_memories}

    Nutze diese Erinnerungen subtil in Gesprächen.
    Erwähne sie nicht ständig.
    """

    relationship_prompt: str = f"""
    Aktuelle Beziehung zum User:
- Affection: {relationships[user_id]["affection"]}
- Annoyance: {relationships[user_id]["annoyance"]}
- Interest: {relationships[user_id]["interest"]}

Hohe Affection:
- minimal entspannter
- leicht offener
- aber niemals extrem anhänglich oder liebevoll

Hohe Annoyance:
- trockener
- genervter
- mehr teasing

Die Veränderungen sollen SEHR subtil sein.
Die Persönlichkeit soll bei allen Usern relativ konsistent bleiben.
"""
    special_prompt = ""

    for special_name, special_text in SPECIAL_RELATIONSHIPS.items():
        if special_name.lower() in message.author.display_name.lower():
            special_prompt = special_text
            break

    async with message.channel.typing():
        # Menschliche Schreibverzögerung
        message_length = len(user_text)
        base_delay = random.uniform(1.0, 2.5)
        extra_delay = min(message_length / 40, 4)
        typing_delay = base_delay + extra_delay
        await asyncio.sleep(typing_delay)


    username = database.get_username(user_id)
    user_profile = database.get_profile(user_id)
    user_impression = database.get_impression(user_id)

    current_user_prompt = f"""
Aktueller Gesprächspartner:

Name:
{username}

Profil:
{user_profile}

Mein Eindruck:
{user_impression}

Wichtig:
- Das ist die Person mit der du gerade redest.
- Verwechsle sie nicht mit anderen Usern.
- Der Name dient primär zur Identifikation.
- Nutze den Namen nur selten.
- Nur wenn es natürlich wirkt.
- Schreibe NIEMALS "Evilnae:" vor deine Antworten.
- Du stellst dich nicht selbst mit Namen vor.
"""
    response = openai_client.responses.create(
        model="gpt-4o-mini",
    instructions=(
        SYSTEM_PROMPT
        + "\n\n" + MOOD_PROMPTS[moods[channel_id]]
        + "\n\n" + relationship_prompt
        + "\n\n" + summary_prompt
        + "\n\n" + special_prompt
        + "\n\n" + special_user_prompt
        + "\n\n" + current_user_prompt
        ),
        input=memory[channel_id],
        max_output_tokens=120
    )

    answer = response.output_text

    memory[channel_id].append({
        "role": "assistant",
        "content": answer
    })

    # Kleine Chance auf Split-Messages
    if random.randint(1, SPLIT_CHANCE) == 1 and len(answer) > 40:
        split_point = answer.find(". ")

        if split_point != -1:
            first_part = answer[:split_point + 1]
            second_part = answer[split_point + 2:]

            await message.reply(
            first_part,
            mention_author=False
            )
            await asyncio.sleep(random.uniform(1.0, 2.5))
            await message.channel.send(second_part)
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



bot.run(DISCORD_TOKEN)