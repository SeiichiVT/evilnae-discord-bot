from pathlib import Path

PATH = Path(
    "install_routing_b3f.py"
)

if not PATH.exists():

    raise SystemExit(
        "[ERROR] install_routing_b3f.py nicht gefunden."
    )


text = PATH.read_text(
    encoding="utf-8"
)


old = (
    '"Output Quality v2.0: ACTIVE",'
)

new = (
    '"Output Quality v{OUTPUT_QUALITY_VERSION}: ACTIVE",'
)


count = text.count(
    old
)


print(
    f"[B3F INSTALLER FIX] gefunden: {count}"
)


if count != 1:

    raise SystemExit(
        "[ERROR] Erwartet wurde genau 1 Stelle."
    )


text = text.replace(
    old,
    new,
    1
)


PATH.write_text(
    text,
    encoding="utf-8"
)


verify = PATH.read_text(
    encoding="utf-8"
)


if old in verify:

    raise SystemExit(
        "[ERROR] Alte Verification noch vorhanden."
    )


if new not in verify:

    raise SystemExit(
        "[ERROR] Neue Verification fehlt."
    )


print(
    "[OK] B3F Verification repariert"
)

print("")
print(
    "Jetzt:"
)
print(
    "python install_routing_b3f.py"
)