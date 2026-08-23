import asyncio
import json
import os
import re
import time
import urllib.error
import urllib.request
from dataclasses import dataclass

from dotenv import load_dotenv

from voice_memory import (
    get_relevant_voice_examples,
    format_voice_examples,
)


# =========================================================
# VERSION
# =========================================================

LOCAL_VOICE_VERSION = "1.0"


# =========================================================
# ENV
# =========================================================

load_dotenv()


def env_bool(
    name,
    default=False
):

    value = os.getenv(
        name
    )

    if value is None:

        return default

    return (
        value.strip().lower()
        in {
            "1",
            "true",
            "yes",
            "on",
        }
    )


LOCAL_VOICE_ENABLED = (
    env_bool(
        "LOCAL_VOICE_ENABLED",
        True
    )
)

LOCAL_VOICE_URL = (
    os.getenv(
        "LOCAL_VOICE_URL",
        "http://127.0.0.1:11434"
    )
    .rstrip("/")
)

LOCAL_VOICE_MODEL = (
    os.getenv(
        "LOCAL_VOICE_MODEL",
        "qwen3:4b-instruct"
    )
)

LOCAL_VOICE_TIMEOUT = float(
    os.getenv(
        "LOCAL_VOICE_TIMEOUT",
        "12"
    )
)

LOCAL_VOICE_KEEP_ALIVE = (
    os.getenv(
        "LOCAL_VOICE_KEEP_ALIVE",
        "5m"
    )
)

LOCAL_VOICE_NUM_CTX = int(
    os.getenv(
        "LOCAL_VOICE_NUM_CTX",
        "4096"
    )
)

LOCAL_VOICE_NUM_PREDICT = int(
    os.getenv(
        "LOCAL_VOICE_NUM_PREDICT",
        "220"
    )
)

LOCAL_VOICE_TEMPERATURE = float(
    os.getenv(
        "LOCAL_VOICE_TEMPERATURE",
        "0.65"
    )
)

LOCAL_VOICE_BOT_THRESHOLD = float(
    os.getenv(
        "LOCAL_VOICE_BOT_THRESHOLD",
        "0.38"
    )
)

LOCAL_VOICE_REPETITION_THRESHOLD = float(
    os.getenv(
        "LOCAL_VOICE_REPETITION_THRESHOLD",
        "0.42"
    )
)

LOCAL_VOICE_MATCH_THRESHOLD = float(
    os.getenv(
        "LOCAL_VOICE_MATCH_THRESHOLD",
        "0.58"
    )
)


# =========================================================
# RESULT
# =========================================================

@dataclass
class LocalVoiceResult:

    output_text: str

    used: bool

    rewritten: bool

    bot_likeness: float

    repetition: float

    evilnae_match: float

    reason: str

    duration: float = 0.0


# =========================================================
# HELPERS
# =========================================================

def clamp01(
    value,
    default=0.0
):

    try:

        value = float(
            value
        )

    except (
        TypeError,
        ValueError
    ):

        return default

    return max(
        0.0,
        min(
            1.0,
            value
        )
    )


def clean_response_text(
    text
):

    text = (
        text
        or ""
    ).strip()

    if not text:

        return ""

    text = re.sub(
        r"^\s*Evilnae\s*:\s*",
        "",
        text,
        flags=re.IGNORECASE
    )

    quote_pairs = [
        ('"', '"'),
        ("„", "“"),
        ("“", "”"),
        ("'", "'"),
    ]

    for (
        opening,
        closing
    ) in quote_pairs:

        if (
            text.startswith(
                opening
            )
            and
            text.endswith(
                closing
            )
            and
            len(text) > 2
        ):

            candidate = (
                text[
                    len(opening):
                    len(text)
                    - len(closing)
                ]
                .strip()
            )

            if candidate:

                text = candidate

                break

    return (
        text.strip()
    )


# =========================================================
# HTTP
# =========================================================

def _ollama_chat_sync(
    payload
):

    url = (
        LOCAL_VOICE_URL
        + "/api/chat"
    )

    encoded = json.dumps(
        payload,
        ensure_ascii=False
    ).encode(
        "utf-8"
    )

    request = urllib.request.Request(
        url,
        data=encoded,
        method="POST",
        headers={
            "Content-Type":
                "application/json"
        }
    )

    with urllib.request.urlopen(
        request,
        timeout=LOCAL_VOICE_TIMEOUT
    ) as response:

        raw = (
            response
            .read()
            .decode(
                "utf-8"
            )
        )

    return json.loads(
        raw
    )


async def ollama_chat(
    payload
):

    return await asyncio.wait_for(

        asyncio.to_thread(
            _ollama_chat_sync,
            payload
        ),

        timeout=(
            LOCAL_VOICE_TIMEOUT
            + 1.0
        )
    )


# =========================================================
# AVAILABILITY
# =========================================================

def _ollama_version_sync():

    url = (
        LOCAL_VOICE_URL
        + "/api/version"
    )

    request = urllib.request.Request(
        url,
        method="GET"
    )

    with urllib.request.urlopen(
        request,
        timeout=2.5
    ) as response:

        raw = (
            response
            .read()
            .decode(
                "utf-8"
            )
        )

    return json.loads(
        raw
    )


async def is_local_voice_available():

    if not LOCAL_VOICE_ENABLED:

        return False

    try:

        await asyncio.wait_for(

            asyncio.to_thread(
                _ollama_version_sync
            ),

            timeout=3.0
        )

        return True

    except Exception:

        return False


# =========================================================
# VOICE SYSTEM PROMPT
# =========================================================

VOICE_SYSTEM_PROMPT = """
Du bist NICHT Evilnaes Brain.

Du bist ihr interner Voice Editor.

Deine einzige Aufgabe:

Prüfe einen bereits fertigen,
inhaltlich entschiedenen Discord-Entwurf
und entscheide,
ob er zu botartig klingt.

Falls nötig,
formulierst du denselben Gedanken
menschlicher und Evilnae-typischer.

Du darfst NICHT:

- neue Fakten erfinden
- bestehende Fakten verändern
- Namen oder Beziehungen erfinden
- neue aktuelle Ereignisse erfinden
- die Absicht der Antwort verändern
- Sicherheitsgrenzen verändern
- neue Versprechen machen
- zusätzliche Aktionen ankündigen

Du optimierst nur:

- Natürlichkeit
- Discord-Rhythmus
- Evilnae-Voice
- weniger Bot-Sprache
- weniger Wiederholung


==================================================
WAS OFT BOTARTIG WIRKT
==================================================

Typische schlechte Muster:

- "Das klingt spannend!"
- "Das klingt super!"
- "Ich hoffe, dass..."
- "Viel Erfolg!"
- "Alles klar!"
- "Das freut mich zu hören!"
- User-Aussage nochmal zusammenfassen
- erst bestätigen, dann paraphrasieren,
  dann freundlich abschließen
- jede Antwort perfekt rund machen
- jede Nachricht maximal hilfreich machen
- immer vollständige saubere Sätze
- künstlich optimistische Abschlussfloskeln
- ständig Gegenfragen
- denselben Gedanken wie
  Evilnaes letzte Nachricht nochmal sagen


==================================================
WAS MENSCHLICHER WIRKT
==================================================

Menschen im Discord:

- reagieren oft nur auf einen Teil
- haben eigene kleine Gedanken
- schreiben manchmal Fragmente
- lassen Aussagen einfach stehen
- müssen nicht alles bestätigen
- variieren Satzlänge
- wiederholen den User nicht ständig
- dürfen trocken sein
- dürfen locker sein
- müssen nicht permanent hilfreich sein

Evilnae ist:

- locker
- internet-affin
- etwas frech
- manchmal trocken
- gelegentlich chaotisch
- nicht künstlich edgy
- nicht grundsätzlich abweisend
- nicht Kundenservice


==================================================
WICHTIG
==================================================

Eine bereits gute,
natürliche Antwort
musst du NICHT umschreiben.

Nicht jede Antwort muss
maximal quirky sein.

Natürlichkeit ist wichtiger
als erzwungene Persönlichkeit.

Antworte ausschließlich
mit gültigem JSON.
"""


# =========================================================
# BUILD PROMPT
# =========================================================

def build_voice_prompt(
    *,
    user_message,
    draft,
    conversation_mode,
    response_goal,
    allow_question,
    inner_state_guidance,
    recent_evilnae_messages,
    good_examples,
    bad_examples
):

    recent_text = (
        "\n".join(
            f"- {message}"
            for message
            in recent_evilnae_messages[
                -6:
            ]
        )
        if recent_evilnae_messages
        else "Keine."
    )

    good_text = (
        format_voice_examples(
            good_examples
        )
    )

    bad_text = (
        format_voice_examples(
            bad_examples
        )
    )

    question_rule = (
        "Eine Frage ist erlaubt."
        if allow_question
        else
        (
            "Keine neue Frage hinzufügen. "
            "Der finale Text darf "
            "keine Gegenfrage enthalten."
        )
    )

    return f"""
AKTUELLE USER-NACHRICHT:

{user_message}


==================================================
CONVERSATION MODE
==================================================

{conversation_mode}


==================================================
BRAIN RESPONSE GOAL
==================================================

{response_goal}


==================================================
INNER STATE
==================================================

{inner_state_guidance}


==================================================
ORIGINAL ENTWURF
==================================================

{draft}


==================================================
FRAGE-REGEL
==================================================

{question_rule}


==================================================
LETZTE EVILNAE-NACHRICHTEN
==================================================

{recent_text}


==================================================
GELERNTE GUTE BEISPIELE
==================================================

{good_text}


==================================================
GELERNTE SCHLECHTE BEISPIELE
==================================================

{bad_text}


==================================================
BEWERTUNG
==================================================

Bewerte:

bot_likeness:
0.0 = wirkt klar wie Mensch im Discord
1.0 = wirkt extrem wie Chatbot/Kundensupport

repetition:
0.0 = kein problematisches Wiederholen
1.0 = wiederholt stark vorherige Aussagen/Muster

evilnae_match:
0.0 = passt gar nicht zu Evilnae
1.0 = passt sehr gut zu Evilnae


==================================================
ENTSCHEIDUNG
==================================================

Wenn der Entwurf bereits natürlich ist:

rewrite = false

response = Originalentwurf


Wenn er botartig,
unnötig glatt,
wiederholend
oder untypisch ist:

rewrite = true

response = natürlichere Version


==================================================
JSON SCHEMA
==================================================

{{
  "bot_likeness": 0.0,
  "repetition": 0.0,
  "evilnae_match": 0.0,
  "rewrite": false,
  "reason": "kurzer interner Grund",
  "response": "finale Discord-Nachricht"
}}
""".strip()


# =========================================================
# PARSE RESULT
# =========================================================

def parse_voice_result(
    raw_text,
    original_draft
):

    raw_text = (
        raw_text
        or ""
    ).strip()

    raw_text = re.sub(
        r"^```(?:json)?\s*",
        "",
        raw_text,
        flags=re.IGNORECASE
    )

    raw_text = re.sub(
        r"\s*```$",
        "",
        raw_text
    )

    try:

        data = json.loads(
            raw_text
        )

    except json.JSONDecodeError:

        start = (
            raw_text.find(
                "{"
            )
        )

        end = (
            raw_text.rfind(
                "}"
            )
        )

        if (
            start == -1
            or
            end == -1
            or
            end <= start
        ):

            return None

        try:

            data = json.loads(
                raw_text[
                    start:end + 1
                ]
            )

        except json.JSONDecodeError:

            return None

    if not isinstance(
        data,
        dict
    ):

        return None

    bot_likeness = (
        clamp01(
            data.get(
                "bot_likeness"
            ),
            0.5
        )
    )

    repetition = (
        clamp01(
            data.get(
                "repetition"
            ),
            0.0
        )
    )

    evilnae_match = (
        clamp01(
            data.get(
                "evilnae_match"
            ),
            0.5
        )
    )

    model_rewrite = bool(
        data.get(
            "rewrite",
            False
        )
    )

    response_text = (
        clean_response_text(
            data.get(
                "response",
                ""
            )
        )
    )

    if not response_text:

        response_text = (
            original_draft
        )

    should_rewrite = (
        model_rewrite
        or
        bot_likeness
        >= LOCAL_VOICE_BOT_THRESHOLD
        or
        repetition
        >= LOCAL_VOICE_REPETITION_THRESHOLD
        or
        evilnae_match
        < LOCAL_VOICE_MATCH_THRESHOLD
    )

    return {

        "bot_likeness":
            bot_likeness,

        "repetition":
            repetition,

        "evilnae_match":
            evilnae_match,

        "should_rewrite":
            should_rewrite,

        "response":
            response_text,

        "reason":
            str(
                data.get(
                    "reason",
                    ""
                )
            )[:300]
    }


# =========================================================
# MAIN VOICE FUNCTION
# =========================================================

async def humanize_evilnae_response(
    *,
    user_message,
    draft,
    conversation_mode,
    response_goal,
    allow_question,
    inner_state_guidance,
    recent_evilnae_messages
):

    draft = (
        draft
        or ""
    ).strip()

    if not draft:

        return LocalVoiceResult(
            output_text="",
            used=False,
            rewritten=False,
            bot_likeness=0.0,
            repetition=0.0,
            evilnae_match=0.0,
            reason="empty_draft"
        )

    if not LOCAL_VOICE_ENABLED:

        return LocalVoiceResult(
            output_text=draft,
            used=False,
            rewritten=False,
            bot_likeness=0.0,
            repetition=0.0,
            evilnae_match=1.0,
            reason="disabled"
        )

    (
        good_examples,
        bad_examples
    ) = (
        get_relevant_voice_examples(
            user_message
        )
    )

    prompt = (
        build_voice_prompt(

            user_message=(
                user_message
            ),

            draft=draft,

            conversation_mode=(
                conversation_mode
            ),

            response_goal=(
                response_goal
            ),

            allow_question=(
                allow_question
            ),

            inner_state_guidance=(
                inner_state_guidance
            ),

            recent_evilnae_messages=(
                recent_evilnae_messages
            ),

            good_examples=(
                good_examples
            ),

            bad_examples=(
                bad_examples
            )
        )
    )

    payload = {

        "model":
            LOCAL_VOICE_MODEL,

        "stream":
            False,

        "format":
            "json",

        "keep_alive":
            LOCAL_VOICE_KEEP_ALIVE,

        "messages": [

            {
                "role":
                    "system",

                "content":
                    VOICE_SYSTEM_PROMPT
            },

            {
                "role":
                    "user",

                "content":
                    prompt
            }
        ],

        "options": {

            "temperature":
                LOCAL_VOICE_TEMPERATURE,

            "num_ctx":
                LOCAL_VOICE_NUM_CTX,

            "num_predict":
                LOCAL_VOICE_NUM_PREDICT
        }
    }

    start = (
        time.perf_counter()
    )

    try:

        response = (
            await ollama_chat(
                payload
            )
        )

    except (
        asyncio.TimeoutError,
        TimeoutError,
        urllib.error.URLError,
        urllib.error.HTTPError,
        ConnectionError,
        OSError
    ) as error:

        duration = (
            time.perf_counter()
            - start
        )

        print(
            "[LOCAL VOICE FALLBACK] "
            f"model={LOCAL_VOICE_MODEL} "
            f"duration={duration:.2f}s "
            f"reason="
            f"{type(error).__name__}"
        )

        return LocalVoiceResult(
            output_text=draft,
            used=False,
            rewritten=False,
            bot_likeness=0.0,
            repetition=0.0,
            evilnae_match=1.0,
            reason=(
                "local_model_unavailable"
            ),
            duration=duration
        )

    except Exception as error:

        duration = (
            time.perf_counter()
            - start
        )

        print(
            "[LOCAL VOICE ERROR] "
            f"{type(error).__name__}: "
            f"{error}"
        )

        return LocalVoiceResult(
            output_text=draft,
            used=False,
            rewritten=False,
            bot_likeness=0.0,
            repetition=0.0,
            evilnae_match=1.0,
            reason="unexpected_error",
            duration=duration
        )

    duration = (
        time.perf_counter()
        - start
    )

    try:

        raw_content = (
            response[
                "message"
            ][
                "content"
            ]
        )

    except (
        KeyError,
        TypeError
    ):

        return LocalVoiceResult(
            output_text=draft,
            used=False,
            rewritten=False,
            bot_likeness=0.0,
            repetition=0.0,
            evilnae_match=1.0,
            reason="invalid_ollama_response",
            duration=duration
        )

    parsed = (
        parse_voice_result(
            raw_content,
            draft
        )
    )

    if parsed is None:

        print(
            "[LOCAL VOICE PARSE ERROR] "
            f"raw={raw_content[:500]!r}"
        )

        return LocalVoiceResult(
            output_text=draft,
            used=False,
            rewritten=False,
            bot_likeness=0.0,
            repetition=0.0,
            evilnae_match=1.0,
            reason="json_parse_error",
            duration=duration
        )

    final_text = (
        parsed[
            "response"
        ]
        if parsed[
            "should_rewrite"
        ]
        else draft
    )

    final_text = (
        clean_response_text(
            final_text
        )
    )

    # -----------------------------------------------------
    # HARD SAFETY FOR VOICE LAYER
    #
    # Das lokale Modell darf nicht plötzlich
    # eine Gegenfrage erzeugen,
    # wenn das Brain sie verboten hat.
    # -----------------------------------------------------

    if (
        not allow_question
        and
        "?" in final_text
    ):

        final_text = (
            draft
        )

        rewritten = False

        reason = (
            "local_rewrite_added_question"
        )

    elif re.search(
        r"\bfair(?:\s+enough)?\b",
        final_text,
        flags=re.IGNORECASE
    ):

        final_text = (
            draft
        )

        rewritten = False

        reason = (
            "local_rewrite_used_banned_word"
        )

    else:

        rewritten = (
            parsed[
                "should_rewrite"
            ]
            and
            final_text.strip()
            != draft.strip()
        )

        reason = (
            parsed[
                "reason"
            ]
        )

    print(
        "[LOCAL VOICE] "
        f"v={LOCAL_VOICE_VERSION} "
        f"model={LOCAL_VOICE_MODEL} "
        f"duration={duration:.2f}s "
        f"rewrite={rewritten} "
        f"bot={parsed['bot_likeness']:.2f} "
        f"repeat={parsed['repetition']:.2f} "
        f"match={parsed['evilnae_match']:.2f} "
        f"reason={reason!r}"
    )

    return LocalVoiceResult(

        output_text=(
            final_text
        ),

        used=True,

        rewritten=(
            rewritten
        ),

        bot_likeness=(
            parsed[
                "bot_likeness"
            ]
        ),

        repetition=(
            parsed[
                "repetition"
            ]
        ),

        evilnae_match=(
            parsed[
                "evilnae_match"
            ]
        ),

        reason=(
            reason
        ),

        duration=(
            duration
        )
    )


# =========================================================
# DEBUG
# =========================================================

def format_local_voice_debug():

    return (
        "[LOCAL VOICE CONFIG] "
        f"v={LOCAL_VOICE_VERSION} "
        f"enabled={LOCAL_VOICE_ENABLED} "
        f"model={LOCAL_VOICE_MODEL} "
        f"url={LOCAL_VOICE_URL} "
        f"timeout={LOCAL_VOICE_TIMEOUT}s "
        f"ctx={LOCAL_VOICE_NUM_CTX}"
    )


# =========================================================
# STANDALONE TEST
# =========================================================

async def _test():

    print(
        format_local_voice_debug()
    )

    available = (
        await is_local_voice_available()
    )

    print(
        "[LOCAL VOICE TEST] "
        f"available={available}"
    )

    if not available:

        print(
            "Ollama ist nicht erreichbar."
        )

        return

    result = (
        await humanize_evilnae_response(

            user_message=(
                "wir testen dich später "
                "noch ein bisschen"
            ),

            draft=(
                "Cool, das klingt spannend! "
                "Ich bin gespannt, was ihr "
                "alles testen werdet. Viel Erfolg! 😈"
            ),

            conversation_mode="direct",

            response_goal=(
                "locker auf die Aussage reagieren"
            ),

            allow_question=False,

            inner_state_guidance=(
                "neutral, sozial zugänglich"
            ),

            recent_evilnae_messages=[]
        )
    )

    print("")
    print(
        "ORIGINAL:"
    )

    print(
        "Cool, das klingt spannend! "
        "Ich bin gespannt, was ihr "
        "alles testen werdet. Viel Erfolg! 😈"
    )

    print("")
    print(
        "VOICE:"
    )

    print(
        result.output_text
    )

    print("")

    print(
        result
    )


if __name__ == "__main__":

    asyncio.run(
        _test()
    )