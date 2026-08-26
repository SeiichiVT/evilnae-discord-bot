from pathlib import Path
import re


PATH = Path(
    "install_performance_b3h.py"
)


if not PATH.exists():

    raise SystemExit(
        "[ERROR] install_performance_b3h.py nicht gefunden."
    )


text = PATH.read_text(
    encoding="utf-8"
)


# =========================================================
# FIND BROKEN RESPONSE PERFORMANCE STATE PATCH
# =========================================================

pattern = re.compile(
    r'''bot = insert_after\(\s*
\s*bot,\s*
\s*''' + "'''" + r'''\s+username = \(\s*
\s+perception\.username\s*
\s+\)\s*
\s*''' + "'''" + r''',\s*
\s*''' + "'''" + r'\s+# =====================================================\s*'
    r'# B3H RESPONSE PERFORMANCE STATE.*?'
    + "'''" +
    r''',\s*
\s*"Response performance state"\s*
\)''',
    re.DOTALL,
)


matches = list(
    pattern.finditer(
        text
    )
)


print(
    f"[B3H INSTALLER FIX] "
    f"problem blocks found: {len(matches)}"
)


if len(
    matches
) != 1:

    raise SystemExit(
        "[ERROR] Erwartet wurde genau 1 "
        "Response-performance Patch."
    )


# =========================================================
# REPLACE WITH UNIQUE ON_MESSAGE ANCHOR
# =========================================================

replacement = r'''bot = replace_once(

    bot,

    """    channel_id = (
        perception.channel_id
    )

    user_id = (
        perception.user_id
    )

    username = (
        perception.username
    )

    # =====================================================
    # CONTEXT REVISION
""",

    """    channel_id = (
        perception.channel_id
    )

    user_id = (
        perception.user_id
    )

    username = (
        perception.username
    )

    # =====================================================
    # B3H RESPONSE PERFORMANCE STATE
    # =====================================================

    reset_response_repair_budget()

    response_pipeline_started_at = (
        start_response_timer()
    )

    # =====================================================
    # CONTEXT REVISION
""",

    "Response performance state"
)'''


text = pattern.sub(
    replacement,
    text,
    count=1,
)


PATH.write_text(
    text,
    encoding="utf-8"
)


# =========================================================
# VERIFY
# =========================================================

verify = PATH.read_text(
    encoding="utf-8"
)


if (
    'reset_response_repair_budget()'
    not in verify
):

    raise SystemExit(
        "[ERROR] Neue Performance-State "
        "Integration fehlt."
    )


if (
    '"Response performance state"'
    not in verify
):

    raise SystemExit(
        "[ERROR] Patch-Label fehlt."
    )


print(
    "[OK] Response performance anchor repaired"
)

print(
    "[OK] Installer gespeichert"
)

print("")
print(
    "NEXT:"
)
print(
    "python install_performance_b3h.py"
)