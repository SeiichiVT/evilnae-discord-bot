import os
from datetime import datetime, timezone

import discord
from dotenv import load_dotenv


# =========================================================
# ENV
# =========================================================

load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

# HIER DIE CHANNEL-ID EINTRAGEN
CHANNEL_ID = 1540825121990778942


# =========================================================
# DISCORD
# =========================================================

intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(
    intents=intents
)


# =========================================================
# HELPERS
# =========================================================

def format_message(message):

    timestamp = (
        message.created_at
        .astimezone()
        .strftime("%Y-%m-%d %H:%M:%S")
    )

    username = (
        message.author.display_name
    )

    user_id = (
        message.author.id
    )

    content = (
        message.content
        if message.content
        else "[kein Text]"
    )

    lines = [
        f"[{timestamp}]",
        f"{username} [{user_id}]",
        content
    ]

    # -----------------------------------------
    # REPLY INFO
    # -----------------------------------------

    if message.reference:

        resolved = (
            message.reference.resolved
        )

        if isinstance(
            resolved,
            discord.Message
        ):

            reply_name = (
                resolved.author.display_name
            )

            reply_content = (
                resolved.content
                if resolved.content
                else "[kein Text]"
            )

            lines.append(
                f"↳ Antwort auf {reply_name}: "
                f"{reply_content}"
            )

    # -----------------------------------------
    # ATTACHMENTS
    # -----------------------------------------

    if message.attachments:

        for attachment in message.attachments:

            lines.append(
                f"[Anhang: {attachment.url}]"
            )

    # -----------------------------------------
    # STICKERS
    # -----------------------------------------

    if message.stickers:

        for sticker in message.stickers:

            lines.append(
                f"[Sticker: {sticker.name}]"
            )

    return "\n".join(lines)


# =========================================================
# READY
# =========================================================

@client.event
async def on_ready():

    print(
        f"Eingeloggt als {client.user}"
    )

    channel = client.get_channel(
        CHANNEL_ID
    )

    if channel is None:

        print(
            "Channel nicht gefunden."
        )

        await client.close()

        return

    print(
        f"Exportiere Channel: "
        f"{channel.name}"
    )

    # -----------------------------------------
    # HEUTE, LOKALE ZEIT
    # -----------------------------------------

    now_local = (
        datetime.now()
        .astimezone()
    )

    today_start_local = (
        now_local
        .replace(
            hour=0,
            minute=0,
            second=0,
            microsecond=0
        )
    )

    # Discord arbeitet mit UTC.
    today_start_utc = (
        today_start_local
        .astimezone(
            timezone.utc
        )
    )

    exported_messages = []

    print(
        "Lese Nachrichten..."
    )

    async for message in channel.history(
        limit=None,
        after=today_start_utc,
        oldest_first=True
    ):

        exported_messages.append(
            format_message(
                message
            )
        )

    # -----------------------------------------
    # FILE NAME
    # -----------------------------------------

    safe_channel_name = (
        channel.name
        .replace(" ", "_")
    )

    filename = (
        f"discord_export_"
        f"{safe_channel_name}_"
        f"{now_local.strftime('%Y-%m-%d')}.txt"
    )

    # -----------------------------------------
    # WRITE FILE
    # -----------------------------------------

    with open(
        filename,
        "w",
        encoding="utf-8"
    ) as file:

        file.write(
            f"Discord Chat Export\n"
            f"Channel: #{channel.name}\n"
            f"Datum: "
            f"{now_local.strftime('%Y-%m-%d')}\n"
            f"Nachrichten: "
            f"{len(exported_messages)}\n"
            f"\n"
            f"{'=' * 70}\n\n"
        )

        for message_text in exported_messages:

            file.write(
                message_text
            )

            file.write(
                "\n\n"
                + "-" * 70
                + "\n\n"
            )

    print("")
    print(
        "FERTIG!"
    )

    print(
        f"{len(exported_messages)} "
        f"Nachrichten exportiert."
    )

    print(
        f"Datei: {filename}"
    )

    await client.close()


# =========================================================
# RUN
# =========================================================

client.run(
    DISCORD_TOKEN
)