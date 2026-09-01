from pathlib import Path
from datetime import datetime
import ast
import re
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
BOT = ROOT / "bot.py"
LIVE = ROOT / "live_stability.py"
SURFACE = ROOT / "surface_writer.py"
VOICE = ROOT / "local_voice.py"
CURIOSITY = ROOT / "curiosity.py"
ROUTING = ROOT / "routing_hardening.py"
TURN = ROOT / "turn_runtime.py"
BEHAVIOR = ROOT / "live_behavior.py"
BACKUPS = ROOT / "live_fix_backups"

LIVE_BEHAVIOR_SOURCE = 'from __future__ import annotations\n\nimport hashlib\nimport re\nfrom difflib import SequenceMatcher\nfrom typing import Any\n\n\nLIVE_BEHAVIOR_VERSION = "1.0"\n\n\n_SECOND_PERSON = re.compile(\n    r"\\b(?:du|dir|dich|dein|deine|deiner|deinem|deinen|"\n    r"ihr|euch|euer|eure|eurem|euren)\\b",\n    re.IGNORECASE,\n)\n\n_QUESTION_LEAD = re.compile(\n    r"^\\s*(?:warum|wieso|weshalb|was|wer|wie|wann|wo|"\n    r"welche|welcher|welches|kann|können|koennen|"\n    r"ist|sind|hat|haben|macht|machen)\\b",\n    re.IGNORECASE,\n)\n\n_CURRENT_ACTIVITY = re.compile(\n    r"\\b(?:was\\s+machst\\s+du|was\\s+treibst\\s+du|"\n    r"was\\s+zockst\\s+du|was\\s+spielst\\s+du|"\n    r"was\\s+schaust\\s+du|was\\s+guckst\\s+du|"\n    r"was\\s+hörst\\s+du|was\\s+hoerst\\s+du)\\b",\n    re.IGNORECASE,\n)\n\n_GREETING = re.compile(\n    r"^\\s*(?:guten\\s+morgen|morgen|moin|hallo|hey|hi|yo)\\b",\n    re.IGNORECASE,\n)\n\n_BOTLIKE_RECENT = re.compile(\n    r"\\b(?:"\n    r"(?:das\\s+)?klingt\\s+(?:ja\\s+|echt\\s+|wirklich\\s+)?"\n    r"(?:nach|wie|spannend|interessant|gut|cool|frustrierend|nervig)|"\n    r"das\\s+freut\\s+mich|"\n    r"schön\\s+zu\\s+hören|schoen\\s+zu\\s+hoeren|"\n    r"gut\\s+zu\\s+hören|gut\\s+zu\\s+hoeren|"\n    r"hoffentlich|danke\\s+(?:für|fuer)\\s+die\\s+frage"\n    r")\\b",\n    re.IGNORECASE,\n)\n\n\nBOTLIKE_QUALITY_ISSUES = {\n    "sounds_like_wrapper",\n    "overpolite_smalltalk",\n    "assistant_empathy",\n    "imagined_empathy",\n    "support_closure",\n    "service_success",\n    "generic_excited",\n    "generic_validation",\n    "motivational_coach",\n    "bot_happy_mirror",\n    "automatic_plan_agreement",\n    "assistant_deserved_validation",\n    "cozy_service_phrase",\n    "soft_fail_wrapper",\n}\n\n\ndef _clean(value: Any) -> str:\n    return re.sub(\n        r"\\s+",\n        " ",\n        str(value or ""),\n    ).strip()\n\n\ndef _normalize(value: Any) -> str:\n    text = _clean(value).lower()\n    text = re.sub(\n        r"<a?:[A-Za-z0-9_]+:\\d+>",\n        " ",\n        text,\n    )\n    text = re.sub(\n        r"[^a-z0-9äöüß]+",\n        " ",\n        text,\n    )\n    return re.sub(\n        r"\\s+",\n        " ",\n        text,\n    ).strip()\n\n\ndef _words(value: Any) -> list[str]:\n    return re.findall(\n        r"[A-Za-zÄÖÜäöüß0-9]+",\n        str(value or ""),\n    )\n\n\ndef is_nonconversational_self_answered_question(\n    text: str,\n) -> bool:\n    value = _clean(text)\n\n    if value.count("?") != 1:\n        return False\n\n    before, after = value.split(\n        "?",\n        1,\n    )\n\n    before = before.strip()\n    after = after.strip()\n\n    if (\n        not before\n        or not after\n        or len(_words(after)) < 2\n    ):\n        return False\n\n    if not _QUESTION_LEAD.search(\n        before\n    ):\n        return False\n\n    if _SECOND_PERSON.search(\n        before\n    ):\n        return False\n\n    return "?" not in after\n\n\ndef has_forbidden_conversational_question(\n    text: str,\n    *,\n    allow_question: bool,\n) -> bool:\n    value = _clean(text)\n    marks = value.count("?")\n\n    if marks <= 0:\n        return False\n\n    if allow_question:\n        return marks > 1\n\n    if (\n        marks == 1\n        and\n        is_nonconversational_self_answered_question(\n            value\n        )\n    ):\n        return False\n\n    return True\n\n\ndef _pick_variant(\n    variants,\n    *,\n    user_text,\n    recent_evilnae_messages=None,\n) -> str:\n    recent = [\n        _normalize(item)\n        for item\n        in (\n            recent_evilnae_messages\n            or []\n        )[-10:]\n        if _normalize(item)\n    ]\n\n    digest = hashlib.sha1(\n        _normalize(user_text).encode(\n            "utf-8",\n            errors="ignore",\n        )\n    ).hexdigest()\n\n    offset = (\n        int(\n            digest[:8],\n            16,\n        )\n        %\n        max(\n            1,\n            len(variants),\n        )\n    )\n\n    ordered = (\n        variants[offset:]\n        +\n        variants[:offset]\n    )\n\n    for candidate in ordered:\n        norm = _normalize(\n            candidate\n        )\n\n        if all(\n            SequenceMatcher(\n                None,\n                norm,\n                old,\n            ).ratio()\n            <\n            0.78\n            for old in recent\n        ):\n            return candidate\n\n    return ordered[0]\n\n\ndef build_grounded_epistemic_fallback(\n    user_text: str,\n    *,\n    is_hanae=False,\n    recent_evilnae_messages=None,\n) -> str:\n    user = str(\n        user_text\n        or ""\n    )\n\n    if _CURRENT_ACTIVITY.search(\n        user\n    ):\n        variants = [\n            "gerade? ich häng hier im Discord rum.",\n            "aktuell nichts Spektakuläres, ich bin einfach hier.",\n            "im Moment? eher hier rumhängen als irgendwas Großes.",\n            "gerade bin ich einfach hier bei euch, mehr Drama gibt\'s nicht.",\n            "nichts, was ich gerade groß ankündigen müsste. ich bin hier.",\n        ]\n\n        if is_hanae:\n            variants.extend(\n                [\n                    "gerade? offensichtlich mit dir hier rumhängen, sis.",\n                    "im Moment bin ich einfach hier, sis. sehr exklusiv.",\n                ]\n            )\n\n        return _pick_variant(\n            variants,\n            user_text=user,\n            recent_evilnae_messages=(\n                recent_evilnae_messages\n            ),\n        )\n\n    if _GREETING.search(\n        user\n    ):\n        variants = [\n            "moin.",\n            "morgen.",\n            "yo, morgen.",\n            "bin da. morgen.",\n            "guten morgen, ich existiere schon.",\n        ]\n\n        if is_hanae:\n            variants.append(\n                "morgen, sis."\n            )\n\n        return _pick_variant(\n            variants,\n            user_text=user,\n            recent_evilnae_messages=(\n                recent_evilnae_messages\n            ),\n        )\n\n    return ""\n\n\ndef surface_failure_directive(\n    reason: str,\n    rejected_candidate: str = "",\n) -> str:\n    reason = str(\n        reason\n        or ""\n    ).strip()\n\n    rejected = _clean(\n        rejected_candidate\n    )\n\n    lines = [\n        "[SURFACE FALLBACK RECOVERY]",\n        (\n            "Der lokale Surface-Entwurf wurde verworfen. "\n            "Der OpenAI-Fallback darf NICHT einfach denselben Gedanken "\n            "mit Synonymen nachbauen."\n        ),\n    ]\n\n    if (\n        "repeat" in reason\n        or "recent_copy" in reason\n    ):\n        lines.append(\n            (\n                "REPETITION ESCAPE: Wechsle den sozialen/reagierenden "\n                "Winkel. Nicht dieselbe Pointe, Stimmung oder Kernaussage "\n                "nur neu formulieren."\n            )\n        )\n\n    if any(\n        marker in reason.lower()\n        for marker in (\n            "assistant",\n            "generic",\n            "wrapper",\n            "bot",\n        )\n    ):\n        lines.append(\n            (\n                "ANTI-BOT: Keine Service-Bestätigung, kein \'klingt nach\', "\n                "kein Motivations-/Support-Abschluss. Eigene Haltung zuerst."\n            )\n        )\n\n    if rejected:\n        lines.append(\n            "NICHT NACHFORMULIEREN:\\n"\n            +\n            rejected[:500]\n        )\n\n    return "\\n\\n".join(\n        lines\n    )\n\n\ndef quality_requires_personality_repair(\n    analysis,\n) -> bool:\n    issues = set(\n        str(item)\n        for item\n        in (\n            getattr(\n                analysis,\n                "issues",\n                [],\n            )\n            or []\n        )\n    )\n\n    if (\n        issues\n        &\n        BOTLIKE_QUALITY_ISSUES\n    ):\n        return True\n\n    return bool(\n        int(\n            getattr(\n                analysis,\n                "generic_score",\n                0,\n            )\n            or 0\n        )\n        >= 3\n        or\n        int(\n            getattr(\n                analysis,\n                "repetition_score",\n                0,\n            )\n            or 0\n        )\n        >= 2\n        or\n        int(\n            getattr(\n                analysis,\n                "grammar_score",\n                0,\n            )\n            or 0\n        )\n        >= 3\n        or\n        int(\n            getattr(\n                analysis,\n                "total_penalty",\n                0,\n            )\n            or 0\n        )\n        >= 5\n    )\n\n\ndef apply_surface_variety_to_plan(\n    plan,\n    *,\n    recent_evilnae_messages,\n    user_text: str,\n):\n    recent = [\n        _clean(item)\n        for item\n        in (\n            recent_evilnae_messages\n            or []\n        )[-8:]\n        if _clean(item)\n    ]\n\n    if not recent:\n        return plan\n\n    must_avoid = list(\n        getattr(\n            plan,\n            "must_avoid",\n            [],\n        )\n        or []\n    )\n\n    opener_counts = {}\n\n    for item in recent[-5:]:\n        match = re.match(\n            r"^\\s*(ich|bin|das|ja|mhm|morgen|okay|ok|also)\\b",\n            item,\n            re.IGNORECASE,\n        )\n\n        if match:\n            opener = (\n                match.group(1)\n                .lower()\n            )\n\n            opener_counts[\n                opener\n            ] = opener_counts.get(\n                opener,\n                0,\n            ) + 1\n\n    for opener, count in opener_counts.items():\n        if count >= 2:\n            must_avoid.append(\n                (\n                    "Rhythmus wechseln: nicht schon wieder "\n                    f"mit \'{opener}\' eröffnen"\n                )\n            )\n\n    if any(\n        _BOTLIKE_RECENT.search(\n            item\n        )\n        for item in recent[-6:]\n    ):\n        must_avoid.append(\n            (\n                "keine \'klingt nach\'/Support-/Service-Verpackung; "\n                "eigene Reaktion oder Haltung statt Bestätigung"\n            )\n        )\n\n    short_declaratives = sum(\n        1\n        for item in recent[-4:]\n        if (\n            len(_words(item)) <= 10\n            and\n            "?" not in item\n        )\n    )\n\n    if short_declaratives >= 3:\n        must_avoid.append(\n            (\n                "nicht wieder denselben kurzen Aussagesatz-Rhythmus; "\n                "Satzbau/Opener natürlich variieren, ohne Stimmung zu erfinden"\n            )\n        )\n\n    unique = []\n\n    for item in must_avoid:\n        item = str(\n            item\n            or ""\n        ).strip()\n\n        if (\n            item\n            and\n            item not in unique\n        ):\n            unique.append(\n                item\n            )\n\n    try:\n        plan.must_avoid = unique[:18]\n    except Exception:\n        pass\n\n    return plan\n\n\ndef _self_test() -> int:\n    from types import SimpleNamespace\n\n    tests = []\n\n    joke = (\n        "Warum können Skelette keine Lügen erzählen? "\n        "Weil ihnen das Rückgrat fehlt."\n    )\n\n    tests.append(\n        (\n            "self-answered joke allowed",\n            is_nonconversational_self_answered_question(\n                joke\n            )\n            and\n            not has_forbidden_conversational_question(\n                joke,\n                allow_question=False,\n            ),\n        )\n    )\n\n    tests.append(\n        (\n            "real counterquestion blocked",\n            has_forbidden_conversational_question(\n                "Und wie geht es dir?",\n                allow_question=False,\n            ),\n        )\n    )\n\n    tests.append(\n        (\n            "second-person question not rhetorical escape",\n            not is_nonconversational_self_answered_question(\n                "Was machst du? Ich chille."\n            ),\n        )\n    )\n\n    activity = build_grounded_epistemic_fallback(\n        "Was machst du gerade?",\n    )\n\n    tests.append(\n        (\n            "grounded activity fallback",\n            bool(activity)\n            and\n            not re.search(\n                r"\\b(?:elden|valorant|warzone|chainsaw|minecraft)\\b",\n                activity,\n                re.IGNORECASE,\n            ),\n        )\n    )\n\n    tests.append(\n        (\n            "unrelated knowledge has no canned fallback",\n            build_grounded_epistemic_fallback(\n                "Kennst du Person X?"\n            )\n            ==\n            "",\n        )\n    )\n\n    directive = surface_failure_directive(\n        "surface_near_recent_copy",\n        "Morgen, läuft.",\n    )\n\n    tests.append(\n        (\n            "repetition fallback changes angle",\n            "Wechsle den sozialen/reagierenden Winkel"\n            in directive\n            and\n            "NICHT NACHFORMULIEREN"\n            in directive,\n        )\n    )\n\n    analysis = SimpleNamespace(\n        issues=[\n            "sounds_like_wrapper",\n        ],\n        generic_score=2,\n        repetition_score=0,\n        grammar_score=0,\n        total_penalty=2,\n    )\n\n    tests.append(\n        (\n            "botlike low penalty still repairs",\n            quality_requires_personality_repair(\n                analysis\n            ),\n        )\n    )\n\n    plan = SimpleNamespace(\n        must_avoid=[],\n    )\n\n    apply_surface_variety_to_plan(\n        plan,\n        recent_evilnae_messages=[\n            "Ich bin da.",\n            "Ich bin wach.",\n            "Ich bin halt hier.",\n        ],\n        user_text="yo",\n    )\n\n    tests.append(\n        (\n            "repeated opener creates variety pressure",\n            any(\n                "nicht schon wieder"\n                in item\n                for item in plan.must_avoid\n            ),\n        )\n    )\n\n    passed = sum(\n        1\n        for _, success in tests\n        if success\n    )\n\n    print()\n    print("=" * 68)\n    print(\n        f"LIVE BEHAVIOR v"\n        f"{LIVE_BEHAVIOR_VERSION} TEST"\n    )\n    print("=" * 68)\n\n    for name, success in tests:\n        print(\n            f"[{\'PASS\' if success else \'FAIL\'}] "\n            f"{name}"\n        )\n\n    print(\n        f"RESULT: {passed}/{len(tests)} PASS"\n    )\n\n    return (\n        0\n        if passed == len(tests)\n        else 1\n    )\n\n\nif __name__ == "__main__":\n    raise SystemExit(\n        _self_test()\n    )\n'
TURN_RUNTIME_SOURCE = 'from __future__ import annotations\n\nimport asyncio\nimport contextvars\nimport re\nimport time\nfrom typing import Any\n\n\nTURN_RUNTIME_VERSION = "2.0-trace-ordering"\n\n\n_CHANNEL_LOCKS = {}\n\n_QUEUE_WAIT = contextvars.ContextVar(\n    "evilnae_turn_queue_wait",\n    default=0.0,\n)\n\n_TRACE = contextvars.ContextVar(\n    "evilnae_turn_trace",\n    default=None,\n)\n\n\ndef _short(\n    value: Any,\n    limit=190,\n) -> str:\n    text = re.sub(\n        r"\\s+",\n        " ",\n        str(value or ""),\n    ).strip()\n\n    if len(text) <= limit:\n        return text\n\n    return (\n        text[: max(0, limit - 3)]\n        +\n        "..."\n    )\n\n\ndef _norm(\n    value: Any,\n) -> str:\n    return re.sub(\n        r"\\s+",\n        " ",\n        str(value or ""),\n    ).strip()\n\n\nclass _ChannelTurnLease:\n    def __init__(\n        self,\n        channel_id,\n    ):\n        self.channel_id = str(\n            channel_id\n            or ""\n        )\n\n        lock = _CHANNEL_LOCKS.get(\n            self.channel_id\n        )\n\n        if lock is None:\n            lock = asyncio.Lock()\n            _CHANNEL_LOCKS[\n                self.channel_id\n            ] = lock\n\n        self.lock = lock\n        self.started = 0.0\n\n    async def __aenter__(\n        self,\n    ):\n        self.started = (\n            time.perf_counter()\n        )\n\n        await self.lock.acquire()\n\n        _QUEUE_WAIT.set(\n            max(\n                0.0,\n                time.perf_counter()\n                -\n                self.started,\n            )\n        )\n\n        return self\n\n    async def __aexit__(\n        self,\n        exc_type,\n        exc,\n        tb,\n    ):\n        if self.lock.locked():\n            self.lock.release()\n\n        return False\n\n\ndef get_channel_turn_lease(\n    channel_id,\n):\n    return _ChannelTurnLease(\n        channel_id\n    )\n\n\ndef get_turn_queue_wait() -> float:\n    try:\n        return max(\n            0.0,\n            float(\n                _QUEUE_WAIT.get()\n                or 0.0\n            ),\n        )\n    except Exception:\n        return 0.0\n\n\ndef start_turn_trace(\n    *,\n    username,\n    user_id,\n    mode,\n    user_text,\n):\n    _TRACE.set(\n        {\n            "username": str(\n                username\n                or "unknown"\n            ),\n            "user_id": str(\n                user_id\n                or ""\n            ),\n            "mode": str(\n                mode\n                or "unknown"\n            ),\n            "user_text": _short(\n                user_text,\n                260,\n            ),\n            "events": [],\n            "last_candidate": "",\n            "last_stage": "",\n        }\n    )\n\n\ndef _trace() -> dict:\n    value = _TRACE.get()\n\n    if not isinstance(\n        value,\n        dict,\n    ):\n        value = {\n            "username": "unknown",\n            "user_id": "",\n            "mode": "unknown",\n            "user_text": "",\n            "events": [],\n            "last_candidate": "",\n            "last_stage": "",\n        }\n\n        _TRACE.set(\n            value\n        )\n\n    return value\n\n\ndef trace_candidate(\n    stage,\n    text,\n    *,\n    source="",\n    reason="",\n    accepted=True,\n):\n    text = _norm(\n        text\n    )\n\n    trace = _trace()\n\n    event = {\n        "kind": "candidate",\n        "stage": str(\n            stage\n            or "unknown"\n        ),\n        "text": text,\n        "source": str(\n            source\n            or ""\n        ),\n        "reason": str(\n            reason\n            or ""\n        ),\n        "accepted": bool(\n            accepted\n        ),\n    }\n\n    trace[\n        "events"\n    ].append(\n        event\n    )\n\n    if text:\n        trace[\n            "last_candidate"\n        ] = text\n\n    trace[\n        "last_stage"\n    ] = event[\n        "stage"\n    ]\n\n\ndef trace_change(\n    stage,\n    before,\n    after,\n    *,\n    reason="",\n):\n    before = _norm(\n        before\n    )\n    after = _norm(\n        after\n    )\n\n    if (\n        not before\n        and\n        not after\n    ):\n        return\n\n    if before == after:\n        return\n\n    trace = _trace()\n\n    event = {\n        "kind": "change",\n        "stage": str(\n            stage\n            or "unknown"\n        ),\n        "before": before,\n        "after": after,\n        "reason": str(\n            reason\n            or ""\n        ),\n    }\n\n    trace[\n        "events"\n    ].append(\n        event\n    )\n\n    if after:\n        trace[\n            "last_candidate"\n        ] = after\n    elif before:\n        trace[\n            "last_candidate"\n        ] = before\n\n    trace[\n        "last_stage"\n    ] = event[\n        "stage"\n    ]\n\n\ndef enrich_silent_final_line(\n    line: str,\n) -> str:\n    value = str(\n        line\n        or ""\n    ).strip()\n\n    trace = _TRACE.get()\n\n    base = value.replace(\n        "[SILENT FINAL]",\n        "[TURN FINAL] SILENT",\n        1,\n    )\n\n    if not isinstance(\n        trace,\n        dict,\n    ):\n        return base\n\n    candidate = _short(\n        trace.get(\n            "last_candidate",\n            "",\n        ),\n        180,\n    )\n\n    stage = str(\n        trace.get(\n            "last_stage",\n            "",\n        )\n        or ""\n    )\n\n    if not candidate:\n        return base\n\n    return (\n        base\n        +\n        "\\n"\n        +\n        "[TURN BLOCK] "\n        +\n        (\n            f"last_stage={stage} | "\n            if stage\n            else ""\n        )\n        +\n        f"lost_candidate={candidate!r}"\n    )\n\n\ndef _num(\n    obj,\n    name,\n    default=0.0,\n):\n    try:\n        return float(\n            getattr(\n                obj,\n                name,\n                default,\n            )\n            or default\n        )\n    except Exception:\n        return float(default)\n\n\ndef _dict_num(\n    data,\n    name,\n    default=0.0,\n):\n    try:\n        return float(\n            (\n                data\n                if isinstance(\n                    data,\n                    dict,\n                )\n                else {}\n            ).get(\n                name,\n                default,\n            )\n            or default\n        )\n    except Exception:\n        return float(default)\n\n\ndef _social(\n    user_id,\n):\n    if not user_id:\n        return {}\n\n    try:\n        from social_emotional_state import (\n            get_social_state,\n        )\n\n        return (\n            get_social_state(\n                str(user_id),\n                persist_decay=False,\n            )\n            or {}\n        )\n    except Exception:\n        return {}\n\n\ndef _interesting(\n    events,\n):\n    result = []\n\n    for event in (\n        events\n        or []\n    ):\n        if not isinstance(\n            event,\n            dict,\n        ):\n            continue\n\n        if (\n            event.get(\n                "kind"\n            )\n            ==\n            "change"\n        ):\n            result.append(\n                event\n            )\n\n        elif (\n            event.get(\n                "kind"\n            )\n            ==\n            "candidate"\n            and\n            not event.get(\n                "accepted",\n                True,\n            )\n        ):\n            result.append(\n                event\n            )\n\n    return result[-5:]\n\n\ndef format_turn_summary(\n    *,\n    username,\n    user_id,\n    mode,\n    delivery_seconds,\n    brain_seconds,\n    writer_seconds,\n    post_seconds,\n    dominant_feeling,\n    inner_state,\n    response_plan,\n    surface_writer_used,\n    surface_writer_result,\n    raw_surface_answer,\n    final_answer,\n    repair_count,\n    emote_result=None,\n    learning_result=None,\n    salience_result=None,\n):\n    social = _social(\n        user_id\n    )\n\n    trace = _trace()\n\n    qwen_seconds = _num(\n        surface_writer_result,\n        "duration",\n        0.0,\n    )\n\n    surface_reason = str(\n        getattr(\n            surface_writer_result,\n            "reason",\n            "",\n        )\n        or "n/a"\n    )\n\n    source = (\n        "qwen-surface"\n        if surface_writer_used\n        else "openai/fallback"\n    )\n\n    move = str(\n        getattr(\n            response_plan,\n            "social_move",\n            "",\n        )\n        or ""\n    )\n\n    stance = str(\n        getattr(\n            response_plan,\n            "stance",\n            "",\n        )\n        or ""\n    )\n\n    shape = str(\n        getattr(\n            response_plan,\n            "reply_shape",\n            "",\n        )\n        or ""\n    )\n\n    lines = [\n        (\n            "[TURN] "\n            f"{username} | mode={mode} | "\n            f"delivery={float(delivery_seconds or 0.0):.2f}s | "\n            f"queue={get_turn_queue_wait():.2f}s | "\n            f"brain={float(brain_seconds or 0.0):.2f}s | "\n            f"writer={float(writer_seconds or 0.0):.2f}s | "\n            f"post={float(post_seconds or 0.0):.2f}s"\n        ),\n        (\n            "[TURN STATE] "\n            f"feel={dominant_feeling} | "\n            f"val={_num(inner_state, \'valence\', 0.0):+.2f} "\n            f"energy={_num(inner_state, \'energy\', 0.0):.2f} "\n            f"irrit={_num(inner_state, \'irritation\', 0.0):.2f} "\n            f"social={_num(inner_state, \'social_energy\', 0.0):.2f} "\n            f"curious={_num(inner_state, \'curiosity\', 0.0):.2f} "\n            f"amused={_num(inner_state, \'amusement\', 0.0):.2f} "\n            f"warm={_num(inner_state, \'warmth\', 0.0):.2f} "\n            f"chaos={_num(inner_state, \'chaos_drive\', 0.0):.2f}"\n        ),\n        (\n            "[TURN PLAN] "\n            f"{move}/{stance}/{shape} | "\n            f"banter={_num(response_plan, \'banter_intensity\', 0.0):.2f} "\n            f"warmth={_num(response_plan, \'warmth_intensity\', 0.0):.2f} | "\n            "toward-user="\n            f"warm={_dict_num(social, \'warmth\', 0.0):.2f} "\n            f"trust={_dict_num(social, \'trust\', 0.0):.2f} "\n            f"close={_dict_num(social, \'closeness\', 0.0):.2f} "\n            f"rivalry={_dict_num(social, \'rivalry\', 0.0):.2f} "\n            f"irrit={_dict_num(social, \'irritation\', 0.0):.2f}"\n        ),\n        (\n            "[TURN WRITER] "\n            f"source={source} | qwen={qwen_seconds:.2f}s | "\n            f"repairs={int(repair_count or 0)} | "\n            f"surface={surface_reason} | "\n            f"raw={_short(raw_surface_answer)!r}"\n        ),\n    ]\n\n    for event in _interesting(\n        trace.get(\n            "events",\n            [],\n        )\n    ):\n        if (\n            event.get(\n                "kind"\n            )\n            ==\n            "change"\n        ):\n            lines.append(\n                (\n                    "[TURN CHANGE] "\n                    f"{event.get(\'stage\')}: "\n                    f"{_short(event.get(\'before\'))!r} -> "\n                    f"{_short(event.get(\'after\'))!r}"\n                    +\n                    (\n                        f" | reason={_short(event.get(\'reason\'), 90)}"\n                        if event.get(\n                            "reason"\n                        )\n                        else ""\n                    )\n                )\n            )\n        else:\n            lines.append(\n                (\n                    "[TURN CHANGE] "\n                    f"{event.get(\'stage\')}: REJECT "\n                    f"{_short(event.get(\'text\'))!r} | "\n                    f"reason={_short(event.get(\'reason\'), 100)}"\n                )\n            )\n\n    emote = "none"\n\n    if (\n        emote_result is not None\n        and\n        bool(\n            getattr(\n                emote_result,\n                "added",\n                False,\n            )\n        )\n    ):\n        emote = str(\n            getattr(\n                emote_result,\n                "emoji_name",\n                "",\n            )\n            or\n            getattr(\n                emote_result,\n                "semantic",\n                "",\n            )\n            or "added"\n        )\n\n    learning = "none"\n\n    if isinstance(\n        learning_result,\n        dict,\n    ):\n        learning = str(\n            learning_result.get(\n                "status",\n                "",\n            )\n            or\n            learning_result.get(\n                "reason",\n                "",\n            )\n            or\n            "none"\n        )\n\n    salience = str(\n        getattr(\n            salience_result,\n            "event_level",\n            "",\n        )\n        or "n/a"\n    )\n\n    lines.append(\n        (\n            "[TURN FINAL] SEND "\n            f"{_short(final_answer)!r} | "\n            f"emote={emote} | "\n            f"learning={_short(learning, 60)} | "\n            f"salience={salience}"\n        )\n    )\n\n    return "\\n".join(\n        lines\n    )\n\n\ndef _self_test() -> int:\n    from types import SimpleNamespace\n\n    tests = []\n\n    async def fifo():\n        order = []\n        release = asyncio.Event()\n\n        async def first():\n            async with get_channel_turn_lease(\n                "c"\n            ):\n                order.append(\n                    "first"\n                )\n                await release.wait()\n\n        async def second():\n            await asyncio.sleep(\n                0.01\n            )\n\n            async with get_channel_turn_lease(\n                "c"\n            ):\n                order.append(\n                    "second"\n                )\n\n        a = asyncio.create_task(\n            first()\n        )\n        b = asyncio.create_task(\n            second()\n        )\n\n        await asyncio.sleep(\n            0.04\n        )\n\n        blocked = (\n            order\n            ==\n            ["first"]\n        )\n\n        release.set()\n\n        await asyncio.gather(\n            a,\n            b,\n        )\n\n        return (\n            blocked\n            and\n            order\n            ==\n            [\n                "first",\n                "second",\n            ]\n        )\n\n    tests.append(\n        (\n            "per-channel FIFO",\n            asyncio.run(\n                fifo()\n            ),\n        )\n    )\n\n    start_turn_trace(\n        username="Tester",\n        user_id="",\n        mode="direct",\n        user_text="yo",\n    )\n\n    trace_candidate(\n        "qwen_surface",\n        "Das klingt gut.",\n        source="qwen",\n        reason="surface_near_recent_copy",\n        accepted=False,\n    )\n\n    trace_change(\n        "quality",\n        "Das klingt gut.",\n        "jo. immerhin.",\n        reason="anti-bot",\n    )\n\n    state = SimpleNamespace(\n        valence=0.2,\n        energy=0.55,\n        irritation=0.08,\n        social_energy=0.65,\n        curiosity=0.55,\n        amusement=0.3,\n        warmth=0.45,\n        chaos_drive=0.35,\n    )\n\n    plan = SimpleNamespace(\n        social_move="react",\n        stance="dry",\n        reply_shape="short",\n        banter_intensity=0.3,\n        warmth_intensity=0.2,\n    )\n\n    surface = SimpleNamespace(\n        duration=4.2,\n        reason="surface_near_recent_copy",\n    )\n\n    summary = format_turn_summary(\n        username="Tester",\n        user_id="",\n        mode="direct",\n        delivery_seconds=8.0,\n        brain_seconds=2.0,\n        writer_seconds=4.5,\n        post_seconds=1.5,\n        dominant_feeling="neutral",\n        inner_state=state,\n        response_plan=plan,\n        surface_writer_used=False,\n        surface_writer_result=surface,\n        raw_surface_answer="Das klingt gut.",\n        final_answer="jo. immerhin.",\n        repair_count=1,\n    )\n\n    tests.append(\n        (\n            "trace shows transformations",\n            "[TURN CHANGE]"\n            in summary\n            and\n            "[TURN FINAL] SEND"\n            in summary,\n        )\n    )\n\n    silent = enrich_silent_final_line(\n        "[SILENT FINAL] user=Tester stage=self_knowledge reason=no_safe_fallback"\n    )\n\n    tests.append(\n        (\n            "silence includes lost candidate",\n            "[TURN FINAL] SILENT"\n            in silent\n            and\n            "[TURN BLOCK]"\n            in silent,\n        )\n    )\n\n    passed = sum(\n        1\n        for _, success in tests\n        if success\n    )\n\n    print()\n    print("=" * 68)\n    print(\n        f"TURN RUNTIME v"\n        f"{TURN_RUNTIME_VERSION} TEST"\n    )\n    print("=" * 68)\n\n    for name, success in tests:\n        print(\n            f"[{\'PASS\' if success else \'FAIL\'}] "\n            f"{name}"\n        )\n\n    print(\n        f"RESULT: {passed}/{len(tests)} PASS"\n    )\n\n    return (\n        0\n        if passed == len(tests)\n        else 1\n    )\n\n\nif __name__ == "__main__":\n    raise SystemExit(\n        _self_test()\n    )\n'
HTTP_REPLACEMENT = '# =========================================================\n# HTTP\n# =========================================================\n\ndef _ollama_chat_sync(\n    payload,\n    timeout=None,\n):\n    request_timeout = max(\n        0.5,\n        float(\n            timeout\n            if timeout is not None\n            else LOCAL_VOICE_TIMEOUT\n        ),\n    )\n\n    url = (\n        LOCAL_VOICE_URL\n        +\n        "/api/chat"\n    )\n\n    encoded = (\n        json.dumps(\n            payload,\n            ensure_ascii=False\n        )\n        .encode(\n            "utf-8"\n        )\n    )\n\n    request = urllib.request.Request(\n        url,\n        data=encoded,\n        method="POST",\n        headers={\n            "Content-Type":\n                "application/json"\n        }\n    )\n\n    with urllib.request.urlopen(\n        request,\n        timeout=request_timeout\n    ) as response:\n        raw = (\n            response\n            .read()\n            .decode(\n                "utf-8"\n            )\n        )\n\n    return json.loads(\n        raw\n    )\n\n\nasync def ollama_chat(\n    payload,\n    timeout=None,\n):\n    request_timeout = max(\n        0.5,\n        float(\n            timeout\n            if timeout is not None\n            else LOCAL_VOICE_TIMEOUT\n        ),\n    )\n\n    return await asyncio.wait_for(\n        asyncio.to_thread(\n            _ollama_chat_sync,\n            payload,\n            request_timeout,\n        ),\n        timeout=(\n            request_timeout\n            +\n            0.75\n        )\n    )\n\n\nasync def run_local_model(\n    *,\n    system_prompt,\n    user_prompt,\n    temperature,\n    num_predict,\n    timeout=None,\n):\n    payload = {\n        "model":\n            LOCAL_VOICE_MODEL,\n\n        "stream":\n            False,\n\n        "format":\n            "json",\n\n        "keep_alive":\n            LOCAL_VOICE_KEEP_ALIVE,\n\n        "messages": [\n            {\n                "role":\n                    "system",\n\n                "content":\n                    system_prompt\n            },\n            {\n                "role":\n                    "user",\n\n                "content":\n                    user_prompt\n            }\n        ],\n\n        "options": {\n            "temperature":\n                temperature,\n\n            "num_ctx":\n                LOCAL_VOICE_NUM_CTX,\n\n            "num_predict":\n                num_predict\n        }\n    }\n\n    response = await ollama_chat(\n        payload,\n        timeout=timeout,\n    )\n\n    try:\n        return (\n            response[\n                "message"\n            ][\n                "content"\n            ]\n        )\n\n    except (\n        KeyError,\n        TypeError\n    ):\n        return None\n\n\n'
ROUTING_INSERT = '    # v1.4: first-person clause + trailing Evil/Evilnae\n    # is usually a social vocative:\n    # "Ich bereite mich auf den Stream vor, Evil."\n    # Object statements such as "Ich mag Evil" stay third-person.\n    if is_end:\n        first_person_clause = text[\n            :match.start()\n        ]\n\n        has_first_person = bool(\n            re.search(\n                r"\\b(?:ich|wir)\\b",\n                first_person_clause,\n                flags=re.IGNORECASE,\n            )\n        )\n\n        object_verb_tail = bool(\n            re.search(\n                r"\\b(?:mag|liebe|hasse|kenne|sehe|vermisse|"\n                r"finde|meine|bin|heiße|heisse)\\s*$",\n                first_person_clause.strip(),\n                flags=re.IGNORECASE,\n            )\n        )\n\n        if (\n            has_first_person\n            and\n            not object_verb_tail\n        ):\n            return True\n\n'
ORDER_WRAPPER = '# =========================================================\n# 4.1 STRICT PER-CHANNEL TURN ORDER\n# =========================================================\n\n@bot.event\nasync def on_message(\n    message\n):\n    channel = getattr(\n        message,\n        "channel",\n        None,\n    )\n\n    channel_id = str(\n        getattr(\n            channel,\n            "id",\n            "",\n        )\n        or ""\n    )\n\n    if not channel_id:\n        return await _evilnae_on_message_inner(\n            message\n        )\n\n    async with get_channel_turn_lease(\n        channel_id\n    ):\n        # Reset the per-task trace before ANY routing/participation\n        # decision can end in silence. The real conversation mode\n        # replaces this trace again immediately before Brain.\n        author = getattr(\n            message,\n            "author",\n            None,\n        )\n\n        start_turn_trace(\n            username=str(\n                getattr(\n                    author,\n                    "display_name",\n                    None,\n                )\n                or\n                getattr(\n                    author,\n                    "name",\n                    "unknown",\n                )\n                or\n                "unknown"\n            ),\n            user_id=str(\n                getattr(\n                    author,\n                    "id",\n                    "",\n                )\n                or ""\n            ),\n            mode="routing",\n            user_text=str(\n                getattr(\n                    message,\n                    "content",\n                    "",\n                )\n                or ""\n            ),\n        )\n\n        return await _evilnae_on_message_inner(\n            message\n        )\n\n\n'


EXPECTED = {
    "bot": 'BOT_VERSION = "4.0.1-turn-console-latency"',
    "live": 'LIVE_STABILITY_VERSION = "1.5-turn-console-latency"',
    "console": 'CONSOLE_OUTPUT_VERSION = "1.1-turn-summary"',
    "surface": 'SURFACE_WRITER_VERSION = "1.1-context-safe"',
    "voice": 'LOCAL_VOICE_VERSION = "1.3.0"',
    "curiosity": 'CURIOSITY_VERSION = "1.1"',
    "routing": 'ROUTING_HARDENING_VERSION = "1.3-trailing-vocative"',
    "turn": 'TURN_RUNTIME_VERSION = "1.0"',
}

TARGET = {
    "bot": 'BOT_VERSION = "4.1.0-live-behavior-polish"',
    "live": 'LIVE_STABILITY_VERSION = "1.6-behavior-trace"',
    "console": 'CONSOLE_OUTPUT_VERSION = "1.2-turn-trace"',
    "surface": 'SURFACE_WRITER_VERSION = "1.2-fast-rhetorical"',
    "voice": 'LOCAL_VOICE_VERSION = "1.3.1-timeout-control"',
    "curiosity": 'CURIOSITY_VERSION = "1.2-rhetorical-safe"',
    "routing": 'ROUTING_HARDENING_VERSION = "1.4-trailing-vocative-plus"',
}


def ok(text):
    print(f"[OK] {text}")


def fail(text):
    print()
    print(f"[INSTALL ERROR] {text}")
    print("Nothing was overwritten by this installer.")
    raise SystemExit(1)


def replace_once(text, old, new, label):
    count = text.count(old)

    if count != 1:
        fail(
            f"{label}: expected exactly 1 match, "
            f"found {count}"
        )

    ok(label)
    return text.replace(old, new, 1)


def insert_before_once(text, marker, block, label):
    count = text.count(marker)

    if count != 1:
        fail(
            f"{label}: expected exactly 1 marker, "
            f"found {count}"
        )

    ok(label)
    return text.replace(
        marker,
        block + marker,
        1,
    )


def insert_after_once(text, marker, block, label):
    count = text.count(marker)

    if count != 1:
        fail(
            f"{label}: expected exactly 1 marker, "
            f"found {count}"
        )

    ok(label)
    return text.replace(
        marker,
        marker + block,
        1,
    )


def syntax_check(text, filename):
    try:
        ast.parse(
            text,
            filename=filename,
        )
    except SyntaxError as error:
        fail(
            f"{filename}: syntax error after patch "
            f"line {error.lineno}: {error.msg}"
        )

    ok(f"{filename} syntax check")


print("=" * 78)
print("EVILNAE 4.1.0 — LIVE BEHAVIOR / LATENCY / TRACE POLISH")
print("=" * 78)
print(f"Project: {ROOT}")
print()
print("WICHTIG: bot.py muss vollständig AUS sein.")
print()


for path in (
    BOT,
    LIVE,
    SURFACE,
    VOICE,
    CURIOSITY,
    ROUTING,
    TURN,
):
    if not path.exists():
        fail(f"Missing required file: {path.name}")


bot = BOT.read_text(encoding="utf-8")
live = LIVE.read_text(encoding="utf-8")
surface = SURFACE.read_text(encoding="utf-8")
voice = VOICE.read_text(encoding="utf-8")
curiosity = CURIOSITY.read_text(encoding="utf-8")
routing = ROUTING.read_text(encoding="utf-8")
turn = TURN.read_text(encoding="utf-8")


if TARGET["bot"] in bot and BEHAVIOR.exists():
    print("4.1.0 is already installed.")
    raise SystemExit(0)


for marker, text, label in (
    (EXPECTED["bot"], bot, "Bot 4.0.1"),
    (EXPECTED["live"], live, "Live Stability 1.5"),
    (EXPECTED["console"], live, "Compact Console 1.1"),
    (EXPECTED["surface"], surface, "Surface Writer 1.1"),
    (EXPECTED["voice"], voice, "Local Voice 1.3.0"),
    (EXPECTED["curiosity"], curiosity, "Curiosity 1.1"),
    (EXPECTED["routing"], routing, "Routing 1.3"),
    (EXPECTED["turn"], turn, "Turn Runtime 1.0"),
):
    if marker not in text:
        fail(f"Expected {label}")


if BEHAVIOR.exists():
    fail("live_behavior.py already exists unexpectedly.")


ok("Current pushed 4.0.1 base detected")


# =========================================================
# LOCAL VOICE — true per-call timeout
# =========================================================

voice = replace_once(
    voice,
    EXPECTED["voice"],
    TARGET["voice"],
    "Local Voice -> 1.3.1-timeout-control",
)

http_pattern = (
    r"# =========================================================\n"
    r"# HTTP\n"
    r"# =========================================================\n"
    r".*?"
    r"(?=# =========================================================\n"
    r"# AVAILABILITY\n"
    r"# =========================================================)"
)

matches = list(
    re.finditer(
        http_pattern,
        voice,
        flags=re.DOTALL,
    )
)

if len(matches) != 1:
    fail(
        "Local Voice HTTP block: expected 1 match, "
        f"found {len(matches)}"
    )

voice = re.sub(
    http_pattern,
    lambda _: HTTP_REPLACEMENT,
    voice,
    count=1,
    flags=re.DOTALL,
)

ok("Local Voice HTTP gets real per-call timeout")


# =========================================================
# SURFACE WRITER
# =========================================================

surface = replace_once(
    surface,
    EXPECTED["surface"],
    TARGET["surface"],
    "Surface Writer -> 1.2-fast-rhetorical",
)

surface = insert_before_once(
    surface,
    "# =========================================================\n# VERSION\n# =========================================================\n",
    "from live_behavior import (\n"
    "    has_forbidden_conversational_question,\n"
    ")\n\n\n",
    "Surface Writer imports rhetorical guard",
)

surface_temp_marker = (
    'SURFACE_WRITER_TEMPERATURE = float(\n'
    '    os.getenv(\n'
    '        "SURFACE_WRITER_TEMPERATURE",\n'
    '        "0.72"\n'
    '    )\n'
    ')\n'
)

surface = insert_after_once(
    surface,
    surface_temp_marker,
    '\n\nSURFACE_WRITER_TIMEOUT = float(\n'
    '    os.getenv(\n'
    '        "SURFACE_WRITER_TIMEOUT",\n'
    '        "12"\n'
    '    )\n'
    ')\n',
    "Surface Writer timeout default -> 12s",
)

surface_question_old = (
    '    if (\n'
    '        not allow_question\n'
    '        and\n'
    '        count_genuine_questions(\n'
    '            candidate\n'
    '        )\n'
    '        > 0\n'
    '    ):\n\n'
    '        return (\n'
    '            False,\n'
    '            "surface_question_not_allowed"\n'
    '        )\n'
)

surface_question_new = (
    '    if has_forbidden_conversational_question(\n'
    '        candidate,\n'
    '        allow_question=bool(\n'
    '            allow_question\n'
    '        ),\n'
    '    ):\n'
    '        return (\n'
    '            False,\n'
    '            "surface_question_not_allowed"\n'
    '        )\n'
)

surface = replace_once(
    surface,
    surface_question_old,
    surface_question_new,
    "Surface Writer permits self-answered joke/rhetorical setup",
)

surface_call_old = (
    '                    num_predict=(\n'
    '                        SURFACE_WRITER_NUM_PREDICT\n'
    '                    )\n'
    '                )\n'
)

surface_call_new = (
    '                    num_predict=(\n'
    '                        SURFACE_WRITER_NUM_PREDICT\n'
    '                    ),\n\n'
    '                    timeout=(\n'
    '                        SURFACE_WRITER_TIMEOUT\n'
    '                    ),\n'
    '                )\n'
)

surface = replace_once(
    surface,
    surface_call_old,
    surface_call_new,
    "Surface Writer passes 12s timeout into real Ollama request",
)

invalid_pattern = re.compile(
    r'return SurfaceWriterResult\(\s*'
    r'output_text="",\s*'
    r'success=False,\s*'
    r'used=True,\s*'
    r'reason=validation_reason,\s*'
    r'duration=duration,\s*'
    r'plan_preserved=plan_preserved,\s*'
    r'new_facts=new_facts,\s*'
    r'\)'
)

if not invalid_pattern.search(surface):
    fail("Surface rejected-result marker not found")

surface = invalid_pattern.sub(
    'return SurfaceWriterResult(\n'
    '                output_text=candidate,\n'
    '                success=False,\n'
    '                used=True,\n'
    '                reason=validation_reason,\n'
    '                duration=duration,\n'
    '                plan_preserved=plan_preserved,\n'
    '                new_facts=new_facts,\n'
    '            )',
    surface,
    count=1,
)

ok("Rejected Surface candidate retained for fallback/trace")

surface = replace_once(
    surface,
    '        f"predict={SURFACE_WRITER_NUM_PREDICT} "\n'
    '        f"temperature={SURFACE_WRITER_TEMPERATURE:.2f}"\n',
    '        f"predict={SURFACE_WRITER_NUM_PREDICT} "\n'
    '        f"temperature={SURFACE_WRITER_TEMPERATURE:.2f} "\n'
    '        f"timeout={SURFACE_WRITER_TIMEOUT:.1f}s"\n',
    "Surface debug shows timeout",
)


# =========================================================
# CURIOSITY / QUESTION POLICY
# =========================================================

curiosity = replace_once(
    curiosity,
    EXPECTED["curiosity"],
    TARGET["curiosity"],
    "Curiosity -> 1.2-rhetorical-safe",
)

curiosity = insert_after_once(
    curiosity,
    "from dataclasses import dataclass\n\n",
    "from live_behavior import (\n"
    "    is_nonconversational_self_answered_question,\n"
    ")\n\n\n",
    "Curiosity imports rhetorical guard",
)

curiosity_marks_old = (
    '    question_marks = (\n'
    '        answer.count(\n'
    '            "?"\n'
    '        )\n'
    '    )\n\n'
    '    reasons = []\n'
)

curiosity_marks_new = (
    '    question_marks = (\n'
    '        answer.count(\n'
    '            "?"\n'
    '        )\n'
    '    )\n\n'
    '    rhetorical_marks = (\n'
    '        1\n'
    '        if\n'
    '        is_nonconversational_self_answered_question(\n'
    '            answer\n'
    '        )\n'
    '        else\n'
    '        0\n'
    '    )\n\n'
    '    conversational_question_marks = max(\n'
    '        0,\n'
    '        question_marks - rhetorical_marks,\n'
    '    )\n\n'
    '    reasons = []\n'
)

curiosity = replace_once(
    curiosity,
    curiosity_marks_old,
    curiosity_marks_new,
    "Curiosity separates rhetorical from conversational questions",
)

curiosity = replace_once(
    curiosity,
    '        question_marks\n        >\n        0\n',
    '        conversational_question_marks\n        >\n        0\n',
    "No-question policy ignores self-answered rhetorical mark",
)

curiosity = replace_once(
    curiosity,
    '        question_marks\n        >\n        1\n',
    '        conversational_question_marks\n        >\n        1\n',
    "Multi-question policy counts conversational marks",
)

curiosity = replace_once(
    curiosity,
    "WICHTIG:\n\n0 Fragezeichen.\n",
    "WICHTIG:\n\n"
    "Keine Gesprächs-Gegenfrage an den User.\n\n"
    "Eine selbst beantwortete rhetorische Frage oder ein Joke-Setup "
    "in derselben Nachricht ist erlaubt, wenn es der eigentliche Inhalt ist.\n",
    "Curiosity prompt no longer kills joke setups",
)


# =========================================================
# ROUTING
# =========================================================

routing = replace_once(
    routing,
    EXPECTED["routing"],
    TARGET["routing"],
    "Routing -> 1.4-trailing-vocative-plus",
)

routing = insert_before_once(
    routing,
    '    words = re.findall(\n'
    '        r"[A-Za-zÄÖÜäöüß]+",\n'
    '        text,\n'
    '    )\n',
    ROUTING_INSERT,
    "Trailing first-person Evil vocatives become direct",
)


# =========================================================
# LIVE STABILITY / COMPACT CONSOLE
# =========================================================

live = replace_once(
    live,
    EXPECTED["live"],
    TARGET["live"],
    "Live Stability -> 1.6-behavior-trace",
)

live = replace_once(
    live,
    EXPECTED["console"],
    TARGET["console"],
    "Compact Console -> 1.2-turn-trace",
)

live = insert_after_once(
    live,
    "from typing import Any\n\n",
    "from live_behavior import (\n"
    "    apply_surface_variety_to_plan,\n"
    ")\n\n"
    "from turn_runtime import (\n"
    "    enrich_silent_final_line,\n"
    "    trace_candidate,\n"
    ")\n\n",
    "Live Stability imports Behavior + Turn Trace",
)

live = replace_once(
    live,
    '                "[LIVE IN]",\n'
    '                "[TURN]",\n'
    '                "[SILENT FINAL]",\n'
    '                "[AGENCY APPLICATION REACTION]",\n',
    '                "[LIVE IN]",\n'
    '                "[TURN]",\n'
    '                "[TURN STATE]",\n'
    '                "[TURN PLAN]",\n'
    '                "[TURN WRITER]",\n'
    '                "[TURN CHANGE]",\n'
    '                "[TURN FINAL]",\n'
    '                "[TURN BLOCK]",\n'
    '                "[AGENCY APPLICATION REACTION]",\n',
    "Compact console shows one coherent Turn Trace",
)

filter_old = (
    '            if self._show_line(line):\n'
    '                output.append(\n'
    '                    line + "\\n"\n'
    '                )\n'
)

filter_new = (
    '            stripped_line = line.strip()\n\n'
    '            if (\n'
    '                get_console_mode()\n'
    '                ==\n'
    '                "compact"\n'
    '                and\n'
    '                stripped_line.startswith(\n'
    '                    "[SILENT FINAL]"\n'
    '                )\n'
    '            ):\n'
    '                output.append(\n'
    '                    enrich_silent_final_line(\n'
    '                        stripped_line\n'
    '                    )\n'
    '                    +\n'
    '                    "\\n"\n'
    '                )\n'
    '                continue\n\n'
    '            if self._show_line(line):\n'
    '                output.append(\n'
    '                    line + "\\n"\n'
    '                )\n'
)

live = replace_once(
    live,
    filter_old,
    filter_new,
    "SILENT FINAL is enriched once with lost candidate",
)

planner_marker = (
    '        social_state = (\n'
    '            apply_social_state_to_plan(\n'
)

planner_variety = (
    '        plan = (\n'
    '            apply_surface_variety_to_plan(\n'
    '                plan,\n'
    '                recent_evilnae_messages=(\n'
    '                    recent\n'
    '                ),\n'
    '                user_text=user_text,\n'
    '            )\n'
    '        )\n\n'
)

live = insert_before_once(
    live,
    planner_marker,
    planner_variety,
    "Planner gets rhythm/opener variety without fake moods",
)

surface_trace_marker = (
    '        reason = (\n'
    '            semantic_violation_reason(\n'
)

surface_trace = (
    '        trace_candidate(\n'
    '            "qwen_surface",\n'
    '            candidate,\n'
    '            source="qwen",\n'
    '            reason=str(\n'
    '                getattr(\n'
    '                    result,\n'
    '                    "reason",\n'
    '                    "",\n'
    '                )\n'
    '                or ""\n'
    '            ),\n'
    '            accepted=bool(\n'
    '                getattr(\n'
    '                    result,\n'
    '                    "success",\n'
    '                    False,\n'
    '                )\n'
    '            ),\n'
    '        )\n\n'
)

live = insert_before_once(
    live,
    surface_trace_marker,
    surface_trace,
    "Qwen Surface candidate enters Turn Trace",
)


# =========================================================
# BOT
# =========================================================

bot = replace_once(
    bot,
    EXPECTED["bot"],
    TARGET["bot"],
    "Bot -> 4.1.0-live-behavior-polish",
)

turn_import_old = (
    'from turn_runtime import (\n'
    '    TURN_RUNTIME_VERSION,\n'
    '    format_turn_summary,\n'
    ')\n'
)

turn_import_new = (
    'from turn_runtime import (\n'
    '    TURN_RUNTIME_VERSION,\n'
    '    get_channel_turn_lease,\n'
    '    start_turn_trace,\n'
    '    trace_candidate,\n'
    '    trace_change,\n'
    '    format_turn_summary,\n'
    ')\n'
)

bot = replace_once(
    bot,
    turn_import_old,
    turn_import_new,
    "Bot imports Turn Runtime v2",
)

bot = insert_after_once(
    bot,
    turn_import_new + "\n",
    "from live_behavior import (\n"
    "    has_forbidden_conversational_question,\n"
    "    build_grounded_epistemic_fallback,\n"
    "    surface_failure_directive,\n"
    "    quality_requires_personality_repair,\n"
    ")\n\n",
    "Bot imports Live Behavior helpers",
)

writer_question_old = (
    '    if (\n'
    '        not decision.ask_question\n'
    '        and\n'
    '        count_genuine_questions(\n'
    '            answer\n'
    '        )\n'
    '        > 0\n'
    '    ):\n\n'
    '        reasons.append(\n'
    '            "question_not_allowed"\n'
    '        )\n'
)

writer_question_new = (
    '    if has_forbidden_conversational_question(\n'
    '        answer,\n'
    '        allow_question=bool(\n'
    '            decision.ask_question\n'
    '        ),\n'
    '    ):\n'
    '        reasons.append(\n'
    '            "question_not_allowed"\n'
    '        )\n'
)

bot = replace_once(
    bot,
    writer_question_old,
    writer_question_new,
    "Writer guard allows rhetorical/joke setup",
)

bot = replace_once(
    bot,
    '- keine erfundenen aktuellen Fakten\n\n{participation_rule}\n',
    '- keine erfundenen aktuellen Fakten\n'
    '- bei Wiederholung den Reaktionswinkel wechseln, NICHT nur Synonyme\n'
    '- bei Bot-/Generic-Problemen keine "klingt nach"/Support-/Service-Verpackung\n'
    '- Evilnaes eigene Haltung ist wichtiger als höfliches Validieren\n\n'
    '{participation_rule}\n',
    "Writer repair gets semantic repetition escape + anti-bot instruction",
)

router_old = (
    '            print(\n'
    '                "[WRITER ROUTER] "\n'
    '                f"user={username} "\n'
    '                "primary=qwen_surface_failed "\n'
    '                "fallback=openai_writer "\n'
    '                f"reason={fallback_reason}"\n'
    '            )\n\n'
    '            return await safe_openai_request(\n'
    '                **openai_writer_kwargs\n'
    '            )\n'
)

router_new = (
    '            rejected_surface_candidate = str(\n'
    '                getattr(\n'
    '                    surface_writer_result,\n'
    '                    "output_text",\n'
    '                    "",\n'
    '                )\n'
    '                or ""\n'
    '            ).strip()\n\n'
    '            recovery_directive = (\n'
    '                surface_failure_directive(\n'
    '                    fallback_reason,\n'
    '                    rejected_surface_candidate,\n'
    '                )\n'
    '            )\n\n'
    '            if recovery_directive:\n'
    '                openai_writer_kwargs = dict(\n'
    '                    openai_writer_kwargs\n'
    '                )\n'
    '                openai_writer_kwargs["input"] = (\n'
    '                    str(\n'
    '                        openai_writer_kwargs.get(\n'
    '                            "input",\n'
    '                            "",\n'
    '                        )\n'
    '                        or ""\n'
    '                    )\n'
    '                    + "\\n\\n"\n'
    '                    + recovery_directive\n'
    '                )\n\n'
    '            print(\n'
    '                "[WRITER ROUTER] "\n'
    '                f"user={username} "\n'
    '                "primary=qwen_surface_failed "\n'
    '                "fallback=openai_writer "\n'
    '                f"reason={fallback_reason}"\n'
    '            )\n\n'
    '            return await safe_openai_request(\n'
    '                **openai_writer_kwargs\n'
    '            )\n'
)

bot = replace_once(
    bot,
    router_old,
    router_new,
    "OpenAI fallback must escape rejected Qwen idea",
)

voice_skip_old = (
    '            if surface_writer_used:\n\n'
    '                print(\n'
    '                    "[LOCAL VOICE SECOND PASS SKIP] "\n'
    '                    f"user={username} "\n'
    '                    "reason=qwen_already_primary"\n'
    '                )\n\n'
    '                return SimpleNamespace(\n'
    '                    output_text=(\n'
    '                        voice_kwargs.get(\n'
    '                            "draft",\n'
    '                            ""\n'
    '                        )\n'
    '                    ),\n'
    '                    meaning_preserved=1.0,\n'
    '                    used=False,\n'
    '                    rewritten=False,\n'
    '                    reason=(\n'
    '                        "qwen_already_primary"\n'
    '                    ),\n'
    '                )\n\n'
    '            return await humanize_evilnae_response(\n'
    '                **voice_kwargs\n'
    '            )\n'
)

voice_skip_new = (
    '            surface_attempted = (\n'
    '                surface_writer_result\n'
    '                is not None\n'
    '            )\n\n'
    '            if (\n'
    '                surface_writer_used\n'
    '                or\n'
    '                surface_attempted\n'
    '            ):\n'
    '                skip_reason = (\n'
    '                    "qwen_already_primary"\n'
    '                    if surface_writer_used\n'
    '                    else "surface_attempt_failed_no_second_local"\n'
    '                )\n\n'
    '                print(\n'
    '                    "[LOCAL VOICE SECOND PASS SKIP] "\n'
    '                    f"user={username} "\n'
    '                    f"reason={skip_reason}"\n'
    '                )\n\n'
    '                return SimpleNamespace(\n'
    '                    output_text=(\n'
    '                        voice_kwargs.get(\n'
    '                            "draft",\n'
    '                            ""\n'
    '                        )\n'
    '                    ),\n'
    '                    meaning_preserved=1.0,\n'
    '                    used=False,\n'
    '                    rewritten=False,\n'
    '                    reason=skip_reason,\n'
    '                )\n\n'
    '            return await humanize_evilnae_response(\n'
    '                **voice_kwargs\n'
    '            )\n'
)

bot = replace_once(
    bot,
    voice_skip_old,
    voice_skip_new,
    "Failed Surface attempt cannot trigger another slow local Qwen",
)

raw_marker = (
    '        raw_surface_answer = str(\n'
    '            getattr(\n'
    '                response,\n'
    '                "output_text",\n'
    '                "",\n'
    '            )\n'
    '            or ""\n'
    '        ).strip()\n'
)

bot = insert_after_once(
    bot,
    raw_marker,
    '\n'
    '        trace_candidate(\n'
    '            "primary_writer",\n'
    '            raw_surface_answer,\n'
    '            source=(\n'
    '                "qwen_surface"\n'
    '                if surface_writer_used\n'
    '                else "openai_fallback"\n'
    '            ),\n'
    '            reason=str(\n'
    '                getattr(\n'
    '                    surface_writer_result,\n'
    '                    "reason",\n'
    '                    "",\n'
    '                )\n'
    '                or ""\n'
    '            ),\n'
    '            accepted=True,\n'
    '        )\n',
    "Primary Writer result enters Turn Trace",
)

bot = insert_before_once(
    bot,
    '        if not answer:\n\n'
    '            recovery_candidates = [\n',
    '        trace_change(\n'
    '            "writer_validation",\n'
    '            raw_surface_answer,\n'
    '            answer,\n'
    '            reason="writer validation / repair",\n'
    '        )\n\n',
    "Writer validation change enters Turn Trace",
)

# Replace epistemic fallback tuples only inside response pipeline.
epi_pattern = re.compile(
    r'\(\s*"epistemic_unknown",\s*"weiß ich grad nicht sicher\."\s*\)'
)

epi_matches = list(
    epi_pattern.finditer(
        bot
    )
)

if not epi_matches:
    fail("No epistemic_unknown fallback tuple found")

epi_replacement = (
    '(\n'
    '                        "epistemic_unknown",\n'
    '                        (\n'
    '                            build_grounded_epistemic_fallback(\n'
    '                                user_text,\n'
    '                                is_hanae=is_hanae,\n'
    '                                recent_evilnae_messages=(\n'
    '                                    channel_evilnae_messages\n'
    '                                ),\n'
    '                            )\n'
    '                            or\n'
    '                            "weiß ich grad nicht sicher."\n'
    '                        )\n'
    '                    )'
)

bot = epi_pattern.sub(
    epi_replacement,
    bot,
)

ok(
    f"Grounded fallback wired into {len(epi_matches)} epistemic path(s)"
)

quality_old = (
    '        quality_repair_needed = (\n'
    '            pre_final_quality_analysis\n'
    '            .grammar_score\n'
    '            >= 3\n\n'
    '            or\n\n'
    '            pre_final_quality_analysis\n'
    '            .repetition_score\n'
    '            >= 2\n\n'
    '            or\n\n'
    '            pre_final_quality_analysis\n'
    '            .generic_score\n'
    '            >= 3\n\n'
    '            or\n\n'
    '            pre_final_quality_analysis\n'
    '            .total_penalty\n'
    '            >= 5\n'
    '        )\n'
)

quality_new = (
    '        quality_repair_needed = (\n'
    '            quality_requires_personality_repair(\n'
    '                pre_final_quality_analysis\n'
    '            )\n'
    '        )\n'
)

bot = replace_once(
    bot,
    quality_old,
    quality_new,
    "Already-detected botlike output now forces repair",
)

bot = insert_before_once(
    bot,
    '        brain_start = (\n'
    '            time.perf_counter()\n'
    '        )\n',
    '        start_turn_trace(\n'
    '            username=username,\n'
    '            user_id=user_id,\n'
    '            mode=brain_conversation_mode,\n'
    '            user_text=user_text,\n'
    '        )\n\n',
    "Turn Trace starts before Brain",
)

bot = insert_before_once(
    bot,
    '            answer = (\n'
    '                self_repair\n'
    '            )\n',
    '            trace_change(\n'
    '                "self_knowledge",\n'
    '                answer,\n'
    '                self_repair,\n'
    '                reason="self knowledge authority",\n'
    '            )\n\n',
    "Self Knowledge transformation enters trace",
)

bot = insert_before_once(
    bot,
    '            answer = (\n'
    '                knowledge_repair\n'
    '            )\n',
    '            trace_change(\n'
    '                "knowledge",\n'
    '                answer,\n'
    '                knowledge_repair,\n'
    '                reason="knowledge/source authority",\n'
    '            )\n\n',
    "Knowledge transformation enters trace",
)

bot = insert_before_once(
    bot,
    '        # =====================================================\n'
    '        # B3I CONSOLIDATED POST-VOICE GATE\n',
    '        trace_change(\n'
    '            "local_voice",\n'
    '            original_writer_answer,\n'
    '            answer,\n'
    '            reason="local voice candidate",\n'
    '        )\n\n',
    "Local Voice transformation enters trace",
)

bot = insert_before_once(
    bot,
    '        expression_guard = (\n'
    '            apply_expression_final_guard(\n',
    '        pre_expression_answer = answer\n\n',
    "Expression snapshot",
)

bot = insert_before_once(
    bot,
    '        # =================================================\n'
    '        # B3I CONSOLIDATED PRE-QUALITY CRITICAL GATE\n',
    '        trace_change(\n'
    '            "expression",\n'
    '            pre_expression_answer,\n'
    '            answer,\n'
    '            reason="expression final guard",\n'
    '        )\n\n',
    "Expression transformation enters trace",
)

bot = insert_before_once(
    bot,
    '        answer = (\n'
    '            trim_safe_generic_tail(\n'
    '                answer\n'
    '            )\n'
    '        )\n',
    '        pre_quality_snapshot = answer\n\n',
    "Quality snapshot",
)

bot = insert_before_once(
    bot,
    '        # =================================================\n'
    '        # B3I FINAL SEND CANDIDATE GATE\n',
    '        trace_change(\n'
    '            "quality",\n'
    '            pre_quality_snapshot,\n'
    '            answer,\n'
    '            reason="output quality / repetition / anti-bot",\n'
    '        )\n\n',
    "Quality transformation enters trace",
)

bot = insert_before_once(
    bot,
    '        # =================================================\n'
    '        # 3.1 CHARACTER IDENTITY FINAL GATE\n',
    '        pre_social_identity_snapshot = answer\n\n',
    "Identity/social snapshot",
)

bot = insert_before_once(
    bot,
    '        # =================================================\n'
    '        # 11.9 EVILNAE APPLICATION EMOTE LAYER\n',
    '        trace_change(\n'
    '            "identity_social",\n'
    '            pre_social_identity_snapshot,\n'
    '            answer,\n'
    '            reason="identity / social stance final guard",\n'
    '        )\n\n',
    "Identity/social transformation enters trace",
)

bot = insert_before_once(
    bot,
    '        (\n'
    '            answer,\n'
    '            evilnae_emote_result\n'
    '        ) = apply_evilnae_emote_layer(\n',
    '        pre_emote_snapshot = answer\n\n',
    "Emote snapshot",
)

bot = insert_after_once(
    bot,
    '        print(\n'
    '            format_evilnae_emote_debug(\n'
    '                evilnae_emote_result\n'
    '            )\n'
    '        )\n',
    '\n'
    '        trace_change(\n'
    '            "emote",\n'
    '            pre_emote_snapshot,\n'
    '            answer,\n'
    '            reason="application emote layer / cooldown",\n'
    '        )\n',
    "Emote transformation enters trace",
)


# =========================================================
# Strict per-channel ordering around COMPLETE on_message
# =========================================================

event_marker = (
    "@bot.event\n"
    "async def on_message(\n"
    "    message\n"
    "):\n"
)

if bot.count(event_marker) != 1:
    fail(
        "Expected exactly one current on_message event; "
        f"found {bot.count(event_marker)}"
    )

bot = bot.replace(
    event_marker,
    "async def _evilnae_on_message_inner(\n"
    "    message\n"
    "):\n",
    1,
)

ok("Current on_message converted to ordered inner handler")

bot = insert_before_once(
    bot,
    "# =========================================================\n"
    "# RUN\n"
    "# =========================================================\n\n",
    ORDER_WRAPPER,
    "Strict per-channel FIFO wrapper installed",
)

bot = replace_once(
    bot,
    '"(feelings + text changes + stage timing)"',
    '"(trace v2 + FIFO + text-stage changes + silence reasons)"',
    "Startup Turn Runtime description updated",
)


# =========================================================
# Syntax + behavior preflight
# =========================================================

for source, filename in (
    (LIVE_BEHAVIOR_SOURCE, "live_behavior.py"),
    (TURN_RUNTIME_SOURCE, "turn_runtime.py"),
    (voice, "local_voice.py"),
    (surface, "surface_writer.py"),
    (curiosity, "curiosity.py"),
    (routing, "routing_hardening.py"),
    (live, "live_stability.py"),
    (bot, "bot.py"),
):
    syntax_check(
        source,
        filename,
    )


# Embedded behavior self-tests.
for source, filename, label in (
    (
        LIVE_BEHAVIOR_SOURCE,
        "live_behavior.py",
        "Live Behavior",
    ),
    (
        TURN_RUNTIME_SOURCE,
        "turn_runtime.py",
        "Turn Runtime",
    ),
):
    namespace = {
        "__name__":
            f"_evilnae_410_preflight_{label}_",
    }

    exec(
        compile(
            source,
            filename,
            "exec",
        ),
        namespace,
    )

    if namespace["_self_test"]() != 0:
        fail(
            f"{label} behavior self-test failed"
        )

    ok(
        f"{label} behavior self-test: PASS"
    )


# Routing probe.
routing_ns = {
    "__name__":
        "_evilnae_410_routing_probe_",
}

exec(
    compile(
        routing,
        "routing_hardening.py",
        "exec",
    ),
    routing_ns,
)

name_pattern = routing_ns[
    "EVIL_VARIANT_PATTERN"
]

vocative = routing_ns[
    "_looks_like_direct_vocative"
]


def routing_case(text):
    match = next(
        iter(
            name_pattern.finditer(
                text
            )
        ),
        None,
    )

    return bool(
        match
        and
        vocative(
            text,
            match,
        )
    )


for name, text, expected in (
    (
        "first-person trailing vocative",
        "Ich bereite mich mal auf den Stream vor Evil",
        True,
    ),
    (
        "object statement",
        "Ich mag Evil",
        False,
    ),
    (
        "third person",
        "Evil ist heute müde",
        False,
    ),
):
    actual = routing_case(
        text
    )

    if actual != expected:
        fail(
            f"Routing test failed: {name} "
            f"actual={actual} expected={expected}"
        )

ok("Routing behavior probe: 3/3 PASS")


contracts = {
    "surface timeout 12s":
        (
            "SURFACE_WRITER_TIMEOUT"
            in surface
            and
            '"12"'
            in surface
        ),

    "timeout reaches urllib":
        (
            "request_timeout"
            in voice
            and
            "timeout=request_timeout"
            in voice
        ),

    "rhetorical guard all layers":
        (
            "has_forbidden_conversational_question"
            in bot
            and
            "has_forbidden_conversational_question"
            in surface
            and
            "is_nonconversational_self_answered_question"
            in curiosity
        ),

    "semantic repetition escape":
        (
            "surface_failure_directive"
            in bot
        ),

    "botlike quality enforced":
        (
            "quality_requires_personality_repair"
            in bot
        ),

    "no second slow local pass":
        (
            "surface_attempt_failed_no_second_local"
            in bot
        ),

    "grounded fallback":
        (
            "build_grounded_epistemic_fallback"
            in bot
        ),

    "turn trace":
        (
            "trace_change"
            in bot
            and
            "enrich_silent_final_line"
            in live
        ),

    "FIFO":
        (
            "_evilnae_on_message_inner"
            in bot
            and
            "get_channel_turn_lease"
            in bot
        ),

    "single event handler":
        (
            bot.count(
                "@bot.event\nasync def on_message("
            )
            ==
            1
        ),

    "no memory reset code":
        (
            "unlink("
            not in LIVE_BEHAVIOR_SOURCE
            and
            "evilnae_social_emotional_state.json"
            not in LIVE_BEHAVIOR_SOURCE
        ),
}

failed = [
    name
    for name, value in contracts.items()
    if not value
]

if failed:
    fail(
        "Contract self-test failed: "
        +
        ", ".join(
            failed
        )
    )

ok(
    f"Contract self-test: "
    f"{len(contracts)}/"
    f"{len(contracts)} PASS"
)


# =========================================================
# Backup
# =========================================================

stamp = (
    datetime.now()
    .astimezone()
    .strftime(
        "%Y%m%d-%H%M%S"
    )
)

backup_dir = (
    BACKUPS
    /
    stamp
)

suffix = 1

while backup_dir.exists():
    backup_dir = (
        BACKUPS
        /
        f"{stamp}_{suffix:02d}"
    )
    suffix += 1

backup_dir.mkdir(
    parents=True,
    exist_ok=False,
)

for path in (
    BOT,
    LIVE,
    SURFACE,
    VOICE,
    CURIOSITY,
    ROUTING,
    TURN,
):
    shutil.copy2(
        path,
        backup_dir
        /
        path.name,
    )

    ok(
        f"Backup: {path.name}"
    )


# =========================================================
# Atomic write
# =========================================================

def atomic_write(path, text):
    temp = Path(
        str(path)
        +
        ".tmp"
    )

    temp.write_text(
        text,
        encoding="utf-8",
    )

    temp.replace(
        path
    )


atomic_write(
    BEHAVIOR,
    LIVE_BEHAVIOR_SOURCE,
)
ok("Created: live_behavior.py")

atomic_write(
    TURN,
    TURN_RUNTIME_SOURCE,
)
ok("Updated: turn_runtime.py")

atomic_write(
    VOICE,
    voice,
)
ok("Updated: local_voice.py")

atomic_write(
    SURFACE,
    surface,
)
ok("Updated: surface_writer.py")

atomic_write(
    CURIOSITY,
    curiosity,
)
ok("Updated: curiosity.py")

atomic_write(
    ROUTING,
    routing,
)
ok("Updated: routing_hardening.py")

atomic_write(
    LIVE,
    live,
)
ok("Updated: live_stability.py")

atomic_write(
    BOT,
    bot,
)
ok("Updated: bot.py")


# =========================================================
# Compile + real selftests
# =========================================================

compile_targets = [
    BEHAVIOR,
    TURN,
    VOICE,
    SURFACE,
    CURIOSITY,
    ROUTING,
    LIVE,
    BOT,
]

result = subprocess.run(
    [
        sys.executable,
        "-m",
        "py_compile",
        *[
            str(path)
            for path in compile_targets
        ],
    ],
    cwd=str(ROOT),
    check=False,
)

if result.returncode != 0:
    print()
    print(
        "[POST-INSTALL WARNING] py_compile failed."
    )
    print(f"Backup: {backup_dir}")
    raise SystemExit(
        result.returncode
    )

ok("Post-install py_compile: 8/8")


for path, label in (
    (
        BEHAVIOR,
        "Live Behavior",
    ),
    (
        TURN,
        "Turn Runtime",
    ),
    (
        SURFACE,
        "Surface Writer",
    ),
    (
        ROUTING,
        "Routing Hardening",
    ),
):
    result = subprocess.run(
        [
            sys.executable,
            str(path),
        ],
        cwd=str(ROOT),
        check=False,
    )

    if result.returncode != 0:
        print()
        print(
            "[POST-INSTALL WARNING] "
            f"{label} self-test failed."
        )
        print(f"Backup: {backup_dir}")
        raise SystemExit(
            result.returncode
        )

    ok(
        f"Post-install {label} self-test: PASS"
    )


print()
print("=" * 78)
print("EVILNAE 4.1.0 LIVE BEHAVIOR / LATENCY / TRACE POLISH INSTALLED")
print("=" * 78)

print()
print("Behavior:")
print("  [✓] joke/rhetorical setup questions survive the question guard")
print("  [✓] repetition fallback changes angle instead of synonym-paraphrasing")
print("  [✓] already-detected botlike output now forces a personality repair")
print("  [✓] repeated opener/rhythm gets variety pressure without fake moods")
print("  [✓] harmless current-activity unknown can answer grounded instead of silence")
print("  [✓] trailing first-person '... Evil' vocatives route as direct")

print()
print("Latency:")
print("  [✓] Qwen Surface request default cap = 12s")
print("  [✓] cap reaches the real urllib/Ollama socket request")
print("  [✓] failed/rejected Surface attempt cannot trigger a second slow Qwen pass")
print("  [✓] OpenAI fallback remains available")

print()
print("Ordering:")
print("  [✓] complete FIFO processing per Discord channel")
print("  [✓] later messages cannot overtake an older reply")
print("  [✓] different channels remain independent")

print()
print("Terminal Trace v2:")
print("  [✓] state / per-user social state once")
print("  [✓] response plan once")
print("  [✓] writer source + timing once")
print("  [✓] only real text transformations appear as TURN CHANGE")
print("  [✓] silence becomes TURN FINAL SILENT with lost candidate when available")
print("  [✓] full file log remains verbose/unfiltered")

print()
print("Versions:")
print("  Bot: 4.1.0-live-behavior-polish")
print("  Live Stability: 1.6-behavior-trace")
print("  Compact Console: 1.2-turn-trace")
print("  Turn Runtime: 2.0-trace-ordering")
print("  Surface Writer: 1.2-fast-rhetorical")
print("  Local Voice: 1.3.1-timeout-control")
print("  Curiosity: 1.2-rhetorical-safe")
print("  Routing: 1.4-trailing-vocative-plus")
print("  Live Behavior: 1.0")

print()
print("Unchanged:")
print("  [✓] Foundation / Canon")
print("  [✓] Character Learning / Experience Learning")
print("  [✓] Social Emotional State")
print("  [✓] Self Development / Arcs")
print("  [✓] Episodes / Salience / Inner State")
print("  [✓] runtime JSON / DB state")
print("  [✓] Emote Layer stays separate for now")

print()
print(f"Backup: {backup_dir}")
print()
print("NO MEMORY RESET REQUIRED.")
print()
print("NEXT:")
print("  python bot.py")
print("  Then test naturally and paste compact TURN blocks only when something looks wrong.")
