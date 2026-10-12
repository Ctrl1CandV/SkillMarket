# /// script
# requires-python = ">=3.12"
# ///
"""Initialize and validate grad-radar configuration. Manage only radar fields; preserve settings for other skills."""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path

TEMPLATE = {
# The query is determined by user input and the current session; do not prefill or save research preferences.
# Keep legacy fields for compatibility. An empty array means no search scope was specified, not a search across all fields.
    "keywords": [],
    "categories": [],
# Low-effort starting point (implementation plan §1.1): prioritize 1 (focus) and 2 (overview);
# counts are configurable and need not be filled. Preserve custom values such as 5/15 from older configs.
    "daily_caps": {"must_read": 1, "skim": 2},
    "days": 3,
    "reading_profile": {
        "direction": None,
        "learning_goal": None,
        "known_background": [],
        "available_minutes": None,
    },
}

PROFILE_KEYS = ("direction", "learning_goal", "known_background", "available_minutes")

if sys.stdout and sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")


def result(ok: bool, **payload) -> dict:
    return {"ok": ok, **payload}


def validate_reading_profile(profile: object) -> list[str]:
    """Validate reading_profile permissively (R14: treat new fields as optional for older configs)."""
    errors: list[str] = []
    if profile is None:
        return errors
    if not isinstance(profile, dict):
        return ["reading_profile must be an object"]
    for field in ("direction", "learning_goal"):
        value = profile.get(field)
        if value is not None and (not isinstance(value, str) or not value.strip()):
            errors.append(f"reading_profile.{field} must be a non-empty string or null")
    known = profile.get("known_background")
    if known is not None:
        if not isinstance(known, list) or any(not isinstance(x, str) or not x.strip() for x in known):
            errors.append("reading_profile.known_background must be an array of non-empty strings")
    minutes = profile.get("available_minutes")
    if minutes is not None and (isinstance(minutes, bool) or not isinstance(minutes, int) or minutes < 1):
        errors.append("reading_profile.available_minutes must be an integer >= 1 or null (leave unset; do not invent a value)")
    return errors


def validate_config(data: object) -> list[str]:
    errors: list[str] = []
    if not isinstance(data, dict):
        return ["The configuration root must be a JSON object"]

    keywords = data.get("keywords")
    if not isinstance(keywords, list):
        errors.append("keywords must be a nested array (it may be empty to indicate no specified scope)")
    else:
        for index, group in enumerate(keywords):
            if not isinstance(group, list) or not group:
                errors.append(f"keywords[{index}] must be a non-empty array")
                continue
            for word_index, word in enumerate(group):
                if not isinstance(word, str) or not word.strip():
                    errors.append(f"keywords[{index}][{word_index}] must be a non-empty string")

    categories = data.get("categories")
    if not isinstance(categories, list):
        errors.append("categories must be an array of strings (it may be empty to indicate no specified scope)")
    else:
        for index, category in enumerate(categories):
            if not isinstance(category, str) or not category.strip():
                errors.append(f"categories[{index}] must be a non-empty string")

    caps = data.get("daily_caps")
    if not isinstance(caps, dict):
        errors.append("daily_caps must be an object")
    else:
        for name in ("must_read", "skim"):
            value = caps.get(name)
            # 0 means this category is not scheduled (zero output is allowed); reject bools, negatives, and non-integers.
            if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= 1000:
                errors.append(f"daily_caps.{name} must be an integer from 0 to 1000 (0 means this category is not scheduled)")

    days = data.get("days")
    if days is not None and (isinstance(days, bool) or not isinstance(days, int) or days < 1):
        errors.append("days must be an integer >= 1 (arXiv indexing can lag; use a window of at least 1 day)")

    errors.extend(validate_reading_profile(data.get("reading_profile")))
    return errors


def _atomic_write_json(path: Path, data: dict) -> None:
    """Write via a same-directory temporary file and atomic replacement, following the same rule as init."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, raw_temp = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    temp_path = Path(raw_temp)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
            json.dump(data, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp_path, path)
    finally:
        temp_path.unlink(missing_ok=True)


def init_config(path: Path) -> dict:
    temp_path: Path | None = None
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        return result(False, error="WRITE_FAILED", detail=f"Could not create configuration directory: {exc}")
    try:
        fd, raw_temp = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
        temp_path = Path(raw_temp)
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
            json.dump(TEMPLATE, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        try:
            os.link(temp_path, path)
        except FileExistsError:
            return result(False, error="CONFLICT", detail=f"Configuration already exists and will not be overwritten: {path}")
    except OSError as exc:
        return result(False, error="WRITE_FAILED", detail=f"Could not create configuration: {exc}")
    finally:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)
    return result(True, data={"config": str(path), "created": True, "config_data": TEMPLATE})


def load_and_validate(path: Path) -> dict:
    if not path.is_file():
        return result(False, error="NOT_FOUND", detail=f"Configuration not found: {path}; run init first")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return result(False, error="BAD_CONFIG", detail=f"Could not parse configuration: {exc}")
    errors = validate_config(data)
    if errors:
        return result(False, error="INVALID_CONFIG", detail="Radar configuration validation failed", errors=errors)
    profile = data.get("reading_profile")
    return result(True, data={"config": str(path), "valid": True, "radar": {
        "keywords": data["keywords"],
        "categories": data["categories"],
        "daily_caps": data["daily_caps"],
        "days": data.get("days"),
        # For legacy configs without reading_profile, use an empty default (unset does not mean guess).
        "reading_profile": {key: (profile or {}).get(key,
                              [] if key == "known_background" else None)
                            for key in PROFILE_KEYS},
    }})


def update_profile(path: Path, fields: dict) -> dict:
    """Update reading_profile fields only when the user explicitly asks to save profile settings.

    Modify only named keys within reading_profile. Preserve unknown fields and settings such as
    venues_watch/thesis_rules for other skills unchanged (R14). The caller supplies the final list
    for known_background append/remove operations; this function replaces only the selected keys.
    """
    if not path.is_file():
        return result(False, error="NOT_FOUND", detail=f"Configuration not found: {path}; run init first")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return result(False, error="BAD_CONFIG", detail=f"Could not parse configuration: {exc}")
    if not isinstance(data, dict):
        return result(False, error="BAD_CONFIG", detail="The configuration root must be a JSON object")
    profile = data.get("reading_profile")
    if profile is not None and not isinstance(profile, dict):
        return result(False, error="BAD_CONFIG", detail="reading_profile is not an object; refusing to overwrite it")
    profile = dict(profile or {})
    for key, value in fields.items():
        if key not in PROFILE_KEYS:
            return result(False, error="BAD_ARGS",
                          detail=f"Unknown profile field {key!r}; update a supported field instead")
        profile[key] = value
    data["reading_profile"] = profile
    errors = validate_config(data)
    if errors:
        return result(False, error="INVALID_CONFIG", detail="Validation failed after update; nothing was written", errors=errors)
    try:
        _atomic_write_json(path, data)
    except OSError as exc:
        return result(False, error="WRITE_FAILED", detail=f"Could not write configuration: {exc}")
    return result(True, data={"config": str(path), "reading_profile": profile,
                              "preserved_fields": [k for k in data if k != "reading_profile"]})


def main() -> None:
    parser = argparse.ArgumentParser(description="Initialize, validate, or update grad-radar configuration")
    sub = parser.add_subparsers(dest="action", required=True)
    for action in ("init", "validate"):
        command = sub.add_parser(action)
        command.add_argument("--config", default=".grad/config.json")
        command.add_argument("--json", action="store_true")
    ap_profile = sub.add_parser("profile", help="Update reading_profile fields (persist only when explicitly requested)")
    ap_profile.add_argument("--config", default=".grad/config.json")
    ap_profile.add_argument("--direction", default=None, help="Research direction; an empty string sets null")
    ap_profile.add_argument("--learning-goal", default=None, help="Current learning goal")
    ap_profile.add_argument("--known-background", default=None,
                            help="Known background, comma-separated; replaces the existing list")
    ap_profile.add_argument("--available-minutes", default=None, help="Available reading time in minutes per session")
    ap_profile.add_argument("--json", action="store_true")
    args = parser.parse_args()

    if args.action == "init":
        output = init_config(Path(args.config))
    elif args.action == "validate":
        output = load_and_validate(Path(args.config))
    else:
        fields: dict = {}
        if args.direction is not None:
            fields["direction"] = args.direction.strip() or None
        if args.learning_goal is not None:
            fields["learning_goal"] = args.learning_goal.strip() or None
        if args.known_background is not None:
            fields["known_background"] = [w.strip() for w in args.known_background.split(",") if w.strip()]
        if args.available_minutes is not None:
            text = args.available_minutes.strip()
            try:
                fields["available_minutes"] = int(text) if text else None
            except ValueError:
                fields["available_minutes"] = text  # Let validate report invalid values accurately.
        if fields:
            output = update_profile(Path(args.config), fields)
        else:
            output = result(False, error="BAD_ARGS",
                            detail="profile requires at least one field (--direction/--learning-goal/--known-background/--available-minutes)")
    if args.json:
        print(json.dumps(output, ensure_ascii=False))
    elif output["ok"]:
        if args.action == "profile":
            print(f"reading_profile updated: {output['data']['reading_profile']}")
        else:
            print(f"Configuration {'created' if args.action == 'init' else 'valid'}: {args.config}")
    else:
        print(f"{output['error']}: {output['detail']}", file=sys.stderr)
        for error in output.get("errors", []):
            print(f"- {error}", file=sys.stderr)
    if not output["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
