from pathlib import Path
from datetime import datetime
import ast
import shutil
import sys


# =========================================================
# CONFIG
# =========================================================

INSTALLER_PATH = Path(
    "install_understanding_b1.py"
)


# =========================================================
# OUTPUT
# =========================================================

def fail(
    message
):

    print("")
    print(
        f"[FIX ERROR] {message}"
    )
    print("")

    sys.exit(
        1
    )


def ok(
    message
):

    print(
        f"[OK] {message}"
    )


# =========================================================
# REPLACE EXACTLY ONCE
# =========================================================

def replace_once(
    text,
    old,
    new,
    label
):

    count = (
        text.count(
            old
        )
    )

    if count != 1:

        fail(
            f"{label}: expected 1 match, "
            f"found {count}"
        )

    text = text.replace(
        old,
        new,
        1
    )

    ok(
        label
    )

    return text


# =========================================================
# LOAD
# =========================================================

if not INSTALLER_PATH.exists():

    fail(
        "install_understanding_b1.py "
        "not found."
    )


text = INSTALLER_PATH.read_text(
    encoding="utf-8"
)


# =========================================================
# ALREADY FIXED?
# =========================================================

if (
    'call_name="is_active_conversation_continuation"'
    in text
):

    print("")
    print(
        "============================================"
    )
    print(
        "B1 INSTALLER IS ALREADY FIXED"
    )
    print(
        "============================================"
    )
    print("")

    print(
        "Run:"
    )

    print(
        "python install_understanding_b1.py"
    )

    sys.exit(
        0
    )


# =========================================================
# BACKUP
# =========================================================

stamp = (
    datetime.now()
    .strftime(
        "%Y%m%d-%H%M%S"
    )
)

backup_path = Path(
    f"install_understanding_b1.py."
    f"before-assignment-fix-"
    f"{stamp}.bak"
)

shutil.copy2(
    INSTALLER_PATH,
    backup_path
)

print(
    f"[BACKUP] {backup_path}"
)


# =========================================================
# FIX 1
#
# find_assignment() bekommt einen optionalen
# call_name Filter.
#
# Damit können wir sagen:
#
# Suche NICHT irgendein
# conversation_continuation Assignment,
#
# sondern genau das Assignment dessen RHS:
#
# is_active_conversation_continuation(...)
#
# ist.
# =========================================================

old_find_signature = '''def find_assignment(
    tree,
    function_name,
    variable_name
):
'''


new_find_signature = '''def find_assignment(
    tree,
    function_name,
    variable_name,
    call_name=None
):
'''


text = replace_once(
    text,
    old_find_signature,
    new_find_signature,
    "find_assignment supports call_name"
)


# =========================================================
# FIX 2
#
# Nach dem Sammeln aller Assignments
# filtern wir optional nach dem Funktionsaufruf
# auf der rechten Seite.
# =========================================================

old_match_check = '''    if len(matches) != 1:

        fail(
            f"{variable_name} assignment in "
            f"{function_name}: expected 1, "
            f"found {len(matches)}"
        )

    return matches[0]
'''


new_match_check = '''    # -----------------------------------------------------
    # OPTIONAL RHS CALL FILTER
    #
    # Beispiel:
    #
    # conversation_continuation = False
    #
    # und später:
    #
    # conversation_continuation = (
    #     is_active_conversation_continuation(...)
    # )
    #
    # Ohne Filter wären das zwei Treffer.
    # -----------------------------------------------------

    if call_name is not None:

        filtered_matches = []

        for node in matches:

            value = getattr(
                node,
                "value",
                None
            )

            if not isinstance(
                value,
                ast.Call
            ):

                continue

            function_node = (
                value.func
            )

            detected_call_name = None

            if isinstance(
                function_node,
                ast.Name
            ):

                detected_call_name = (
                    function_node.id
                )

            elif isinstance(
                function_node,
                ast.Attribute
            ):

                detected_call_name = (
                    function_node.attr
                )

            if (
                detected_call_name
                ==
                call_name
            ):

                filtered_matches.append(
                    node
                )

        matches = (
            filtered_matches
        )

    if len(matches) != 1:

        call_info = (

            f" with call_name={call_name!r}"

            if call_name is not None

            else
            ""
        )

        fail(
            f"{variable_name} assignment in "
            f"{function_name}{call_info}: "
            f"expected 1, "
            f"found {len(matches)}"
        )

    return matches[0]
'''


text = replace_once(
    text,
    old_match_check,
    new_match_check,
    "assignment call filter"
)


# =========================================================
# FIX 3
#
# insert_after_assignment()
# ebenfalls um call_name erweitern.
# =========================================================

old_insert_signature = '''def insert_after_assignment(
    text,
    function_name,
    variable_name,
    insertion,
    unique_marker,
    label
):
'''


new_insert_signature = '''def insert_after_assignment(
    text,
    function_name,
    variable_name,
    insertion,
    unique_marker,
    label,
    call_name=None
):
'''


text = replace_once(
    text,
    old_insert_signature,
    new_insert_signature,
    "insert_after_assignment supports call_name"
)


# =========================================================
# FIX 4
#
# call_name an find_assignment weitergeben.
# =========================================================

old_find_call = '''    node = find_assignment(
        tree,
        function_name,
        variable_name
    )
'''


new_find_call = '''    node = find_assignment(
        tree,
        function_name,
        variable_name,
        call_name=call_name
    )
'''


text = replace_once(
    text,
    old_find_call,
    new_find_call,
    "forward call_name"
)


# =========================================================
# FIX 5
#
# Nur beim Conversation Target Guard
# den speziellen RHS Call verlangen.
#
# writer_context bleibt unverändert.
# =========================================================

old_target_install = '''bot = insert_after_assignment(
    bot,
    "on_message",
    "conversation_continuation",
    target_guard_code,
    "[ACTIVE CONVERSATION BLOCKED]",
    "Target Guard / Active Conversation v2"
)
'''


new_target_install = '''bot = insert_after_assignment(
    bot,
    "on_message",
    "conversation_continuation",
    target_guard_code,
    "[ACTIVE CONVERSATION BLOCKED]",
    "Target Guard / Active Conversation v2",
    call_name="is_active_conversation_continuation"
)
'''


text = replace_once(
    text,
    old_target_install,
    new_target_install,
    "Target Guard selects real continuation call"
)


# =========================================================
# SYNTAX CHECK
# =========================================================

try:

    ast.parse(
        text,
        filename=str(
            INSTALLER_PATH
        )
    )

except SyntaxError as error:

    print("")
    print(
        "============================================"
    )
    print(
        "FIXED INSTALLER HAS SYNTAX ERROR"
    )
    print(
        "============================================"
    )

    print(
        f"Line: {error.lineno}"
    )

    print(
        f"Offset: {error.offset}"
    )

    print(
        f"Error: {error.msg}"
    )

    print("")

    print(
        "Installer was NOT overwritten."
    )

    print(
        f"Backup: {backup_path}"
    )

    sys.exit(
        1
    )


ok(
    "installer syntax check"
)


# =========================================================
# WRITE
# =========================================================

temp_path = Path(
    "install_understanding_b1.py.tmp"
)

temp_path.write_text(
    text,
    encoding="utf-8"
)

temp_path.replace(
    INSTALLER_PATH
)

ok(
    "install_understanding_b1.py updated"
)


# =========================================================
# VERIFY
# =========================================================

installed = (
    INSTALLER_PATH.read_text(
        encoding="utf-8"
    )
)

required = [

    "call_name=None",

    "filtered_matches = []",

    "call_name=call_name",

    (
        'call_name='
        '"is_active_conversation_continuation"'
    ),
]


missing = [

    marker

    for marker
    in required

    if marker not in installed
]


if missing:

    fail(
        "Post-fix verification failed: "
        +
        ", ".join(
            missing
        )
    )


# =========================================================
# SUCCESS
# =========================================================

print("")
print(
    "============================================"
)
print(
    "B1 INSTALLER ASSIGNMENT FIX COMPLETE"
)
print(
    "============================================"
)

print(
    f"Backup: {backup_path}"
)

print("")
print(
    "Problem fixed:"
)

print(
    "  [✓] initialization assignment ignored"
)

print(
    "  [✓] actual continuation call selected"
)

print(
    "  [✓] writer_context behavior unchanged"
)

print("")
print(
    "NEXT:"
)

print(
    "python install_understanding_b1.py"
)

print(
    "============================================"
)