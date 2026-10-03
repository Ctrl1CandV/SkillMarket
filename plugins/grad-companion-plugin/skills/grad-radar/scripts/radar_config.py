# /// script
# requires-python = ">=3.12"
# ///
"""初始化并校验 grad-radar 配置。只管理 radar 字段，不覆盖其他 skill 的配置。"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path

TEMPLATE = {
    "keywords": [["llm", "agent"], ["tool", "use"], ["multi-agent"]],
    "categories": ["cs.AI", "cs.CL"],
    # 低负担起点（实施方案 §1.1）：重点关注 1、速览 2；数量可配置、不要求填满。
    # 旧配置的 5/15 等自定义值继续有效，不静默覆盖。
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
    """reading_profile 宽容校验（R14：新增字段按缺省处理，旧配置缺它不报错）。"""
    errors: list[str] = []
    if profile is None:
        return errors
    if not isinstance(profile, dict):
        return ["reading_profile 必须是对象"]
    for field in ("direction", "learning_goal"):
        value = profile.get(field)
        if value is not None and (not isinstance(value, str) or not value.strip()):
            errors.append(f"reading_profile.{field} 必须是非空字符串或 null")
    known = profile.get("known_background")
    if known is not None:
        if not isinstance(known, list) or any(not isinstance(x, str) or not x.strip() for x in known):
            errors.append("reading_profile.known_background 必须是非空字符串数组")
    minutes = profile.get("available_minutes")
    if minutes is not None and (isinstance(minutes, bool) or not isinstance(minutes, int) or minutes < 1):
        errors.append("reading_profile.available_minutes 必须是 >=1 的整数或 null（未设置不填假值）")
    return errors


def validate_config(data: object) -> list[str]:
    errors: list[str] = []
    if not isinstance(data, dict):
        return ["配置根节点必须是 JSON 对象"]

    keywords = data.get("keywords")
    if not isinstance(keywords, list) or not keywords:
        errors.append("keywords 必须是非空嵌套数组")
    else:
        for index, group in enumerate(keywords):
            if not isinstance(group, list) or not group:
                errors.append(f"keywords[{index}] 必须是非空数组")
                continue
            for word_index, word in enumerate(group):
                if not isinstance(word, str) or not word.strip():
                    errors.append(f"keywords[{index}][{word_index}] 必须是非空字符串")

    categories = data.get("categories")
    if not isinstance(categories, list) or not categories:
        errors.append("categories 必须是非空字符串数组")
    else:
        for index, category in enumerate(categories):
            if not isinstance(category, str) or not category.strip():
                errors.append(f"categories[{index}] 必须是非空字符串")

    caps = data.get("daily_caps")
    if not isinstance(caps, dict):
        errors.append("daily_caps 必须是对象")
    else:
        for name in ("must_read", "skim"):
            value = caps.get(name)
            # 0 = 本次不安排该类（允许零输出）；拒绝 bool、负数和非整数。旧自定义值继续有效。
            if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= 1000:
                errors.append(f"daily_caps.{name} 必须是 0..1000 的整数（0 表示该类不安排）")

    days = data.get("days")
    if days is not None and (isinstance(days, bool) or not isinstance(days, int) or days < 1):
        errors.append("days 必须是 >=1 的整数（arXiv 索引滞后，窗口不宜小于 1）")

    errors.extend(validate_reading_profile(data.get("reading_profile")))
    return errors


def _atomic_write_json(path: Path, data: dict) -> None:
    """同目录临时文件 + 原子替换；与 init 相同的落盘纪律。"""
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
        return result(False, error="WRITE_FAILED", detail=f"配置目录创建失败：{exc}")
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
            return result(False, error="CONFLICT", detail=f"配置已存在，不会覆盖：{path}")
    except OSError as exc:
        return result(False, error="WRITE_FAILED", detail=f"配置创建失败：{exc}")
    finally:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)
    return result(True, data={"config": str(path), "created": True, "config_data": TEMPLATE})


def load_and_validate(path: Path) -> dict:
    if not path.is_file():
        return result(False, error="NOT_FOUND", detail=f"配置不存在：{path}；先运行 init")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return result(False, error="BAD_CONFIG", detail=f"配置无法解析：{exc}")
    errors = validate_config(data)
    if errors:
        return result(False, error="INVALID_CONFIG", detail="radar 配置校验失败", errors=errors)
    profile = data.get("reading_profile")
    return result(True, data={"config": str(path), "valid": True, "radar": {
        "keywords": data["keywords"],
        "categories": data["categories"],
        "daily_caps": data["daily_caps"],
        "days": data.get("days"),
        # 旧配置缺 reading_profile 时按全空默认返回（未设置≠猜值）
        "reading_profile": {key: (profile or {}).get(key,
                              [] if key == "known_background" else None)
                            for key in PROFILE_KEYS},
    }})


def update_profile(path: Path, fields: dict) -> dict:
    """按字段更新 reading_profile（用户明确要求记住背景配置时才持久化）。

    只动 reading_profile 内被点名的键；未知字段与 venues_watch/thesis_rules 等其他
    skill 的配置原样保留（R14）。known_background 支持 append/remove 语义由调用方
    传入最终列表——本函数只整体替换被点的键。
    """
    if not path.is_file():
        return result(False, error="NOT_FOUND", detail=f"配置不存在：{path}；先运行 init")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return result(False, error="BAD_CONFIG", detail=f"配置无法解析：{exc}")
    if not isinstance(data, dict):
        return result(False, error="BAD_CONFIG", detail="配置根节点必须是 JSON 对象")
    profile = data.get("reading_profile")
    if profile is not None and not isinstance(profile, dict):
        return result(False, error="BAD_CONFIG", detail="reading_profile 已是非对象字段，拒绝覆盖")
    profile = dict(profile or {})
    for key, value in fields.items():
        if key not in PROFILE_KEYS:
            return result(False, error="BAD_ARGS",
                          detail=f"未知 profile 字段 {key!r}；可更新：{'、'.join(PROFILE_KEYS)}")
        profile[key] = value
    data["reading_profile"] = profile
    errors = validate_config(data)
    if errors:
        return result(False, error="INVALID_CONFIG", detail="更新后校验失败，未写入", errors=errors)
    try:
        _atomic_write_json(path, data)
    except OSError as exc:
        return result(False, error="WRITE_FAILED", detail=f"配置写入失败：{exc}")
    return result(True, data={"config": str(path), "reading_profile": profile,
                              "preserved_fields": [k for k in data if k != "reading_profile"]})


def main() -> None:
    parser = argparse.ArgumentParser(description="初始化、校验或更新 grad-radar 配置")
    sub = parser.add_subparsers(dest="action", required=True)
    for action in ("init", "validate"):
        command = sub.add_parser(action)
        command.add_argument("--config", default=".grad/config.json")
        command.add_argument("--json", action="store_true")
    ap_profile = sub.add_parser("profile", help="按字段更新 reading_profile（用户明确要求记住时才持久化）")
    ap_profile.add_argument("--config", default=".grad/config.json")
    ap_profile.add_argument("--direction", default=None, help="研究方向；传空串置 null")
    ap_profile.add_argument("--learning-goal", default=None, help="近期学习目标")
    ap_profile.add_argument("--known-background", default=None,
                            help="已掌握基础，逗号分隔；整体替换现有列表")
    ap_profile.add_argument("--available-minutes", default=None, help="可支配阅读时间（分钟/次）")
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
                fields["available_minutes"] = text  # 非法值交给 validate 如实报错
        if fields:
            output = update_profile(Path(args.config), fields)
        else:
            output = result(False, error="BAD_ARGS",
                            detail="profile 至少要给出一个字段（--direction/--learning-goal/--known-background/--available-minutes）")
    if args.json:
        print(json.dumps(output, ensure_ascii=False))
    elif output["ok"]:
        if args.action == "profile":
            print(f"reading_profile 已更新：{output['data']['reading_profile']}")
        else:
            print(f"配置{'已创建' if args.action == 'init' else '有效'}：{args.config}")
    else:
        print(f"{output['error']}: {output['detail']}", file=sys.stderr)
        for error in output.get("errors", []):
            print(f"- {error}", file=sys.stderr)
    if not output["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
