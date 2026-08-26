from pathlib import Path


INSTALLER_PATH = Path(
    "install_context_b3c.py"
)


if not INSTALLER_PATH.exists():

    raise SystemExit(
        "[ERROR] install_context_b3c.py nicht gefunden."
    )


text = INSTALLER_PATH.read_text(
    encoding="utf-8"
)


# =========================================================
# BUG
#
# Im Installer stehen innerhalb der Patch-Strings:
#
# "\n\n"
#
# Beim Ausführen des Installers werden diese Escapes
# von Python bereits ausgewertet und erzeugen im
# gepatchten bot.py:
#
# "
#
#
# "
#
# Dadurch entsteht ein unterminated string literal.
#
# Wir müssen im INSTALLER deshalb aus:
#
# "\n\n"
#
# folgendes machen:
#
# "\\n\\n"
#
# =========================================================

old = '"\\n\\n"'

new = '"\\\\n\\\\n"'


count = text.count(
    old
)


print(
    f"[B3C INSTALLER FIX] gefunden: {count}"
)


if count == 0:

    print(
        "[INFO] Keine ungefixten \\n\\n-Stellen gefunden."
    )

    print(
        "Der Installer ist entweder bereits repariert "
        "oder der Fehler sitzt an einer anderen Stelle."
    )

    raise SystemExit(
        0
    )


text = text.replace(
    old,
    new
)


INSTALLER_PATH.write_text(
    text,
    encoding="utf-8"
)


verify_text = INSTALLER_PATH.read_text(
    encoding="utf-8"
)


remaining_bad = verify_text.count(
    old
)


escaped_good = verify_text.count(
    new
)


print(
    f"[OK] repariert: {count}"
)

print(
    f"[VERIFY] ungefixt übrig: {remaining_bad}"
)

print(
    f"[VERIFY] escaped vorhanden: {escaped_good}"
)


if remaining_bad != 0:

    raise SystemExit(
        "[ERROR] Es sind noch ungefixte Stellen vorhanden."
    )


print("")
print(
    "============================================"
)

print(
    "B3C INSTALLER FIX COMPLETE"
)

print(
    "============================================"
)

print("")
print(
    "Jetzt ausführen:"
)

print(
    "python install_context_b3c.py"
)