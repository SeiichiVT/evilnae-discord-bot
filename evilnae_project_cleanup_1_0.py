
from __future__ import annotations

from pathlib import Path
from datetime import datetime
import argparse
import ast
import fnmatch
import json
import shutil
import zipfile


SCRIPT_VERSION = "1.0"
PROJECT_ROOT = Path(__file__).resolve().parent
BOT_PATH = PROJECT_ROOT / "bot.py"

BACKUP_ROOT = PROJECT_ROOT / "live_fix_backups"
VSCODE_DIR = PROJECT_ROOT / ".vscode"
VSCODE_SETTINGS = VSCODE_DIR / "settings.json"

IGNORE_DIR_NAMES = {
    ".git", ".venv", "venv", "env", "__pycache__",
    "live_fix_backups", "logs", ".idea", ".pytest_cache",
    ".mypy_cache", ".ruff_cache", "node_modules",
}

SAFE_TOOL_PATTERNS = (
    "install_*.py",
    "repair_*.py",
)

SAFE_TEMP_FILE_PATTERNS = (
    "*.tmp", "*.temp", "*.pyc", "*.pyo", "*.bak",
    "*.old", "*.orig", "*~",
)

SAFE_TEMP_NAMES = {
    ".DS_Store", "Thumbs.db", "desktop.ini",
}

REVIEWISH_PATTERNS = (
    "test_*.py", "*_test.py", "debug_*.py", "*_debug.py",
    "tmp_*.py", "temp_*.py", "legacy_*.py", "*_legacy.py",
    "*_old.py", "old_*.py", "*_backup.py", "backup_*.py",
)

VSCODE_EXCLUDES = {
    "**/.venv": True,
    "**/venv": True,
    "**/__pycache__": True,
    "**/*.pyc": True,
    "**/logs": True,
    "**/live_fix_backups": True,
    "**/.git": True,
    "**/.pytest_cache": True,
    "**/.mypy_cache": True,
    "**/.ruff_cache": True,
}


def ok(text):
    print(f"[OK] {text}")


def warn(text):
    print(f"[WARN] {text}")


def fail(text):
    print()
    print(f"[CLEANUP ERROR] {text}")
    raise SystemExit(1)


def rel(path):
    path = Path(path)
    try:
        return str(path.relative_to(PROJECT_ROOT))
    except Exception:
        return str(path)


def iter_project_files():
    script_path = Path(__file__).resolve()

    for path in PROJECT_ROOT.rglob("*"):
        if path.resolve() == script_path:
            continue

        try:
            relative = path.relative_to(PROJECT_ROOT)
        except Exception:
            continue

        if any(part in IGNORE_DIR_NAMES for part in relative.parts):
            continue

        yield path


def python_module_name(path):
    path = Path(path)

    try:
        relative = path.relative_to(PROJECT_ROOT)
    except Exception:
        return None

    if path.suffix != ".py":
        return None

    parts = list(relative.parts)

    if parts[-1] == "__init__.py":
        parts = parts[:-1]
    else:
        parts[-1] = path.stem

    if not parts:
        return None

    return ".".join(parts)


def discover_local_python_modules():
    modules = {}

    for path in iter_project_files():
        if not path.is_file() or path.suffix != ".py":
            continue

        name = python_module_name(path)

        if name:
            modules[name] = path

    return modules


def parse_imports(path):
    found = set()

    try:
        text = Path(path).read_text(encoding="utf-8")
    except UnicodeDecodeError:
        text = Path(path).read_text(
            encoding="utf-8",
            errors="ignore",
        )
    except Exception:
        return found

    try:
        tree = ast.parse(text, filename=str(path))
    except Exception:
        return found

    current_module = python_module_name(path) or ""
    current_parts = current_module.split(".")

    if Path(path).name != "__init__.py" and current_parts:
        current_package = current_parts[:-1]
    else:
        current_package = current_parts

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name:
                    found.add(alias.name)

        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""

            if node.level:
                base = list(current_package)
                up = max(0, node.level - 1)

                if up:
                    base = base[:-up] if up <= len(base) else []

                full = ".".join(
                    base + module.split(".")
                ) if module else ".".join(base)
            else:
                full = module

            if full:
                found.add(full)

                for alias in node.names:
                    if alias.name != "*":
                        found.add(f"{full}.{alias.name}")

        elif isinstance(node, ast.Call):
            func_name = ""

            if isinstance(node.func, ast.Name):
                func_name = node.func.id

            elif isinstance(node.func, ast.Attribute):
                if isinstance(node.func.value, ast.Name):
                    func_name = (
                        f"{node.func.value.id}.{node.func.attr}"
                    )

            if func_name in {
                "__import__",
                "importlib.import_module",
            }:
                if node.args:
                    arg = node.args[0]

                    if (
                        isinstance(arg, ast.Constant)
                        and isinstance(arg.value, str)
                    ):
                        found.add(arg.value)

    return found


def resolve_local_import(import_name, local_modules):
    candidate = import_name

    while candidate:
        if candidate in local_modules:
            return candidate

        if "." not in candidate:
            break

        candidate = candidate.rsplit(".", 1)[0]

    return None


def build_reachable_graph():
    local_modules = discover_local_python_modules()

    bot_module = python_module_name(BOT_PATH)

    if not bot_module:
        fail("Could not resolve bot.py module name.")

    reachable = set()
    queue = [bot_module]

    while queue:
        module = queue.pop(0)

        if module in reachable:
            continue

        path = local_modules.get(module)

        if path is None:
            continue

        reachable.add(module)

        for imported in parse_imports(path):
            local = resolve_local_import(
                imported,
                local_modules,
            )

            if local and local not in reachable:
                queue.append(local)

    reachable_paths = {
        local_modules[module].resolve()
        for module in reachable
        if module in local_modules
    }

    return local_modules, reachable, reachable_paths


def matches_any(name, patterns):
    lower = name.lower()

    return any(
        fnmatch.fnmatch(lower, pattern.lower())
        for pattern in patterns
    )


def collect_candidates(reachable_paths):
    safe_files = set()
    cache_dirs = set()
    review_candidates = set()

    script_path = Path(__file__).resolve()

    for path in PROJECT_ROOT.glob("*.py"):
        resolved = path.resolve()

        if resolved in {
            script_path,
            BOT_PATH.resolve(),
        }:
            continue

        if matches_any(path.name, SAFE_TOOL_PATTERNS):
            safe_files.add(resolved)

    for path in PROJECT_ROOT.rglob("__pycache__"):
        try:
            relative = path.relative_to(PROJECT_ROOT)
        except Exception:
            continue

        if any(
            part in {".venv", "venv", "env", "live_fix_backups"}
            for part in relative.parts
        ):
            continue

        if path.is_dir():
            cache_dirs.add(path.resolve())

    for path in PROJECT_ROOT.rglob("*"):
        if not path.is_file():
            continue

        try:
            relative = path.relative_to(PROJECT_ROOT)
        except Exception:
            continue

        if any(
            part in {
                ".venv", "venv", "env", ".git",
                "live_fix_backups", "logs",
            }
            for part in relative.parts
        ):
            continue

        if path.resolve() == script_path:
            continue

        if (
            path.name in SAFE_TEMP_NAMES
            or matches_any(
                path.name,
                SAFE_TEMP_FILE_PATTERNS,
            )
        ):
            safe_files.add(path.resolve())

    for path in PROJECT_ROOT.glob("*.py"):
        resolved = path.resolve()

        if resolved in {
            script_path,
            BOT_PATH.resolve(),
        }:
            continue

        if resolved in reachable_paths:
            continue

        if resolved in safe_files:
            continue

        review_candidates.add(resolved)

    return (
        sorted(safe_files),
        sorted(cache_dirs),
        sorted(review_candidates),
    )


def load_json_file(path):
    if not path.exists():
        return {}

    try:
        text = path.read_text(
            encoding="utf-8"
        ).strip()

        if not text:
            return {}

        data = json.loads(text)

        if isinstance(data, dict):
            return data

    except Exception:
        pass

    return {}


def update_vscode_settings():
    VSCODE_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    settings = load_json_file(
        VSCODE_SETTINGS
    )

    files_exclude = settings.get(
        "files.exclude",
        {},
    )

    if not isinstance(files_exclude, dict):
        files_exclude = {}

    files_exclude.update(
        VSCODE_EXCLUDES
    )

    settings[
        "files.exclude"
    ] = files_exclude

    search_exclude = settings.get(
        "search.exclude",
        {},
    )

    if not isinstance(search_exclude, dict):
        search_exclude = {}

    search_exclude.update(
        VSCODE_EXCLUDES
    )

    settings[
        "search.exclude"
    ] = search_exclude

    watcher_exclude = settings.get(
        "files.watcherExclude",
        {},
    )

    if not isinstance(watcher_exclude, dict):
        watcher_exclude = {}

    watcher_exclude.update({
        "**/.venv/**": True,
        "**/venv/**": True,
        "**/logs/**": True,
        "**/live_fix_backups/**": True,
        "**/__pycache__/**": True,
    })

    settings[
        "files.watcherExclude"
    ] = watcher_exclude

    VSCODE_SETTINGS.write_text(
        json.dumps(
            settings,
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    return VSCODE_SETTINGS


def create_backup_zip(
    backup_dir,
    files,
    cache_dirs,
):
    zip_path = (
        Path(backup_dir)
        /
        "removed_files.zip"
    )

    with zipfile.ZipFile(
        zip_path,
        "w",
        compression=zipfile.ZIP_DEFLATED,
    ) as archive:

        added = set()

        for path in files:
            path = Path(path)

            if not path.exists():
                continue

            archive.write(
                path,
                arcname=rel(path),
            )

            added.add(
                path.resolve()
            )

        for directory in cache_dirs:
            directory = Path(directory)

            if not directory.exists():
                continue

            for path in directory.rglob("*"):
                if not path.is_file():
                    continue

                if path.resolve() in added:
                    continue

                archive.write(
                    path,
                    arcname=rel(path),
                )

                added.add(
                    path.resolve()
                )

    return zip_path


def write_report(
    backup_dir,
    reachable,
    reachable_paths,
    safe_files,
    cache_dirs,
    review_candidates,
):
    report = {
        "cleanup_version": SCRIPT_VERSION,
        "created_at": (
            datetime.now()
            .astimezone()
            .isoformat()
        ),
        "project_root": str(PROJECT_ROOT),
        "reachable_modules": sorted(reachable),
        "reachable_files": sorted(
            rel(path)
            for path in reachable_paths
        ),
        "safe_files_removed": [
            rel(path)
            for path in safe_files
        ],
        "cache_dirs_removed": [
            rel(path)
            for path in cache_dirs
        ],
        "review_candidates_not_removed": [
            rel(path)
            for path in review_candidates
        ],
    }

    report_path = (
        Path(backup_dir)
        /
        "cleanup_manifest.json"
    )

    report_path.write_text(
        json.dumps(
            report,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    return report_path


def delete_safe_items(
    files,
    cache_dirs,
):
    removed_files = 0
    removed_dirs = 0

    for path in files:
        path = Path(path)

        if not path.exists():
            continue

        try:
            path.unlink()
            removed_files += 1

        except Exception as error:
            warn(
                f"Could not remove {rel(path)}: {error}"
            )

    for directory in sorted(
        [Path(p) for p in cache_dirs],
        key=lambda p: len(p.parts),
        reverse=True,
    ):
        if not directory.exists():
            continue

        try:
            shutil.rmtree(directory)
            removed_dirs += 1

        except Exception as error:
            warn(
                f"Could not remove {rel(directory)}: {error}"
            )

    return removed_files, removed_dirs


def maybe_remove_review_candidates(
    review_candidates,
    backup_dir,
    enabled,
):
    if not enabled:
        return 0

    if not review_candidates:
        return 0

    archive_path = (
        Path(backup_dir)
        /
        "review_candidates.zip"
    )

    with zipfile.ZipFile(
        archive_path,
        "w",
        compression=zipfile.ZIP_DEFLATED,
    ) as archive:

        for path in review_candidates:
            path = Path(path)

            if path.exists():
                archive.write(
                    path,
                    arcname=rel(path),
                )

    removed = 0

    for path in review_candidates:
        path = Path(path)

        if not path.exists():
            continue

        try:
            path.unlink()
            removed += 1

        except Exception as error:
            warn(
                f"Could not remove review candidate "
                f"{rel(path)}: {error}"
            )

    return removed


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Safe Evilnae project cleanup."
        )
    )

    parser.add_argument(
        "--remove-unused-root-python",
        action="store_true",
        help=(
            "Also remove root-level Python files not "
            "statically reachable from bot.py. "
            "Backed up first."
        ),
    )

    args = parser.parse_args()

    print("=" * 78)
    print("EVILNAE PROJECT CLEANUP 1.0")
    print("=" * 78)
    print(f"Project: {PROJECT_ROOT}")
    print()
    print(
        "Bot darf für den Cleanup am besten AUS sein."
    )
    print()

    if not BOT_PATH.exists():
        fail(
            "bot.py not found next to this cleanup script."
        )

    try:
        ast.parse(
            BOT_PATH.read_text(
                encoding="utf-8"
            ),
            filename="bot.py",
        )
    except Exception as error:
        fail(
            f"bot.py could not be parsed safely: {error}"
        )

    ok(
        "bot.py syntax readable"
    )

    (
        local_modules,
        reachable,
        reachable_paths,
    ) = build_reachable_graph()

    ok(
        f"Import graph built: "
        f"{len(reachable_paths)} active local Python files"
    )

    (
        safe_files,
        cache_dirs,
        review_candidates,
    ) = collect_candidates(
        reachable_paths
    )

    print()
    print(
        f"[AUDIT] safe files to remove: "
        f"{len(safe_files)}"
    )
    print(
        f"[AUDIT] cache dirs to remove: "
        f"{len(cache_dirs)}"
    )
    print(
        f"[AUDIT] unused root Python review candidates: "
        f"{len(review_candidates)}"
    )

    if safe_files:
        print()
        print("Safe cleanup files:")

        for path in safe_files:
            print(
                f"  - {rel(path)}"
            )

    if review_candidates:
        print()
        print(
            "Review only — NOT deleted by default:"
        )

        for path in review_candidates:
            status = (
                "dev-looking"
                if matches_any(
                    Path(path).name,
                    REVIEWISH_PATTERNS,
                )
                else
                "unreachable"
            )

            print(
                f"  ? {rel(path)} [{status}]"
            )

    timestamp = (
        datetime.now()
        .astimezone()
        .strftime(
            "%Y%m%d-%H%M%S"
        )
    )

    backup_dir = (
        BACKUP_ROOT
        /
        f"{timestamp}_project_cleanup"
    )

    suffix = 1

    while backup_dir.exists():
        backup_dir = (
            BACKUP_ROOT
            /
            f"{timestamp}_project_cleanup_{suffix:02d}"
        )
        suffix += 1

    backup_dir.mkdir(
        parents=True,
        exist_ok=False,
    )

    ok(
        f"Backup directory: {rel(backup_dir)}"
    )

    backup_zip = create_backup_zip(
        backup_dir,
        safe_files,
        cache_dirs,
    )

    ok(
        f"Backup zip: {rel(backup_zip)}"
    )

    report_path = write_report(
        backup_dir,
        reachable,
        reachable_paths,
        safe_files,
        cache_dirs,
        review_candidates,
    )

    ok(
        f"Manifest: {rel(report_path)}"
    )

    if VSCODE_SETTINGS.exists():
        shutil.copy2(
            VSCODE_SETTINGS,
            backup_dir
            /
            "vscode_settings_before.json",
        )

        ok(
            "Backed up existing .vscode/settings.json"
        )

    removed_files, removed_dirs = (
        delete_safe_items(
            safe_files,
            cache_dirs,
        )
    )

    ok(
        f"Removed safe files: {removed_files}"
    )

    ok(
        f"Removed cache dirs: {removed_dirs}"
    )

    vscode_path = update_vscode_settings()

    ok(
        "VS Code Explorer/Search exclusions updated: "
        f"{rel(vscode_path)}"
    )

    removed_review = (
        maybe_remove_review_candidates(
            review_candidates,
            backup_dir,
            args.remove_unused_root_python,
        )
    )

    if args.remove_unused_root_python:
        ok(
            "Removed review candidates after backup: "
            f"{removed_review}"
        )

    else:
        print()
        print(
            "[SAFE MODE] Review candidates were intentionally NOT deleted."
        )

    print()
    print("=" * 78)
    print(
        "EVILNAE PROJECT CLEANUP COMPLETE"
    )
    print("=" * 78)
    print()
    print(
        f"Active local Python files detected: "
        f"{len(reachable_paths)}"
    )
    print(
        f"Old installer/repair/temp files removed: "
        f"{removed_files}"
    )
    print(
        f"Cache directories removed: "
        f"{removed_dirs}"
    )
    print(
        "Unreachable root Python files left for review: "
        f"{0 if args.remove_unused_root_python else len(review_candidates)}"
    )

    print()
    print("VS Code now hides:")
    print("  .venv / venv")
    print("  __pycache__ / *.pyc")
    print("  logs")
    print("  live_fix_backups")
    print("  .git")

    print()
    print("IMPORTANT:")
    print(
        "  [✓] Runtime state JSON/DB files were NOT deleted."
    )
    print(
        "  [✓] Character Learning / Episodes / Salience were NOT changed."
    )
    print(
        "  [✓] bot.py and active modules were NOT modified."
    )
    print(
        "  [✓] Every removed file was backed up first."
    )

    print()
    print(f"Backup: {backup_dir}")

    if (
        review_candidates
        and
        not args.remove_unused_root_python
    ):
        print()
        print("NEXT OPTIONAL STEP:")
        print(
            "  Paste the '?' review list to ChatGPT."
        )
        print(
            "  After review, the aggressive cleanup command is:"
        )
        print(
            f"  python {Path(__file__).name} "
            "--remove-unused-root-python"
        )

    print()
    print(
        "You can now reload the VS Code Explorer."
    )


if __name__ == "__main__":
    main()
