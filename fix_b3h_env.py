from pathlib import Path


ENV_PATH = Path(".env")


TARGET_VALUES = {
    "LOCAL_VOICE_QUEUE_TIMEOUT": "1.5",
    "LOCAL_VOICE_NUM_PREDICT": "200",
}


def fail(message):
    raise SystemExit(
        f"\n[ERROR] {message}\n"
    )


if not ENV_PATH.exists():
    fail(".env nicht gefunden.")


text = ENV_PATH.read_text(
    encoding="utf-8"
)


lines = text.splitlines()

updated = set()

new_lines = []


for line in lines:

    stripped = line.strip()

    replaced = False

    for key, value in TARGET_VALUES.items():

        if (
            stripped.startswith(
                key + "="
            )
            and
            not stripped.startswith("#")
        ):

            new_lines.append(
                f"{key}={value}"
            )

            updated.add(
                key
            )

            replaced = True

            print(
                f"[OK] {key} -> {value}"
            )

            break

    if not replaced:
        new_lines.append(
            line
        )


for key, value in TARGET_VALUES.items():

    if key not in updated:

        if (
            new_lines
            and
            new_lines[-1].strip()
        ):
            new_lines.append("")

        new_lines.append(
            f"{key}={value}"
        )

        print(
            f"[OK] {key} hinzugefügt -> {value}"
        )


ENV_PATH.write_text(
    "\n".join(
        new_lines
    )
    +
    "\n",
    encoding="utf-8"
)


print("")
print(
    "B3H ENV HOTFIX COMPLETE"
)
print("")
print(
    "Erwartete effektive Werte:"
)
print(
    "  queue=1.5s"
)
print(
    "  predict=200"
)