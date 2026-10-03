"""宿主适配层构建脚本：读 plugin/（宿主中立主干），生成 dist/zcode/。

用法：
    python hosts/zcode/build.py
    （或 uv run --no-project hosts/zcode/build.py）

本文件属于适配层，允许出现宿主专有词；plugin/ 不允许——
构建前先扫描 plugin/，命中宿主专有词立即中止（不变量 #8 的机械门禁）。
"""

from __future__ import annotations

import json
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PLUGIN = ROOT.parents[2] / "plugins" / "grad-companion-plugin" / "plugin"
HOST_DIR = Path(__file__).resolve().parent
DIST = ROOT / "dist" / "zcode"
STAGING = DIST.with_name(f".{DIST.name}.staging")
BACKUP = DIST.with_name(f".{DIST.name}.backup")

# 主干里出现任何一个宿主名或宿主目录名即为架构破坏
HOST_WORDS = re.compile(r"zcode|qoder|claude|trae|cursor|windsurf|marketplace", re.IGNORECASE)
IGNORED_PARTS = {"__pycache__"}
IGNORED_SUFFIXES = {".pyc", ".pyo"}


def check_neutral() -> None:
    hits: list[str] = []
    for p in sorted(PLUGIN.rglob("*")):
        if not p.is_file() or any(part in IGNORED_PARTS for part in p.parts) or p.suffix in IGNORED_SUFFIXES:
            continue
        try:
            text = p.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue  # 二进制文件不检查
        for i, line in enumerate(text.splitlines(), 1):
            if HOST_WORDS.search(line):
                hits.append(f"  plugin/{p.relative_to(PLUGIN)}:{i}: {line.strip()}")
    if hits:
        sys.exit("plugin/ 含宿主专有词，构建中止：\n" + "\n".join(hits))


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as f:
        f.write(text)


def write_json(path: Path, obj: dict) -> None:
    write_text(path, json.dumps(obj, ensure_ascii=False, indent=2) + "\n")


def split_frontmatter(text: str) -> tuple[list[str], str]:
    lines = text.split("\n")
    if not lines or lines[0].strip() != "---":
        return [], text
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            return lines[1:i], "\n".join(lines[i + 1:]).lstrip("\n")
    return [], text  # frontmatter 未闭合，按无 frontmatter 处理


def transform_command(text: str, skill: str) -> str:
    """中立命令 → 宿主命令：skill 键改名、注入 $ARGUMENTS 与技能引导语。"""
    fm, body = split_frontmatter(text)
    out = ["---"]
    for line in fm:
        if line.startswith("skill:"):
            file_skill = line.split(":", 1)[1].strip()
            if file_skill and file_skill != skill:
                print(f"警告：命令 frontmatter 的 skill={file_skill} 与 manifest 的 {skill} 不一致，以 manifest 为准")
            out.append(f"skills: {skill}")
        else:
            out.append(line)
    out += ["---", "", f"使用 `{skill}` 技能处理这个请求：", "", "$ARGUMENTS", "", body.rstrip()]
    return "\n".join(out) + "\n"


def parse_skill_fields(lines: list[str], source: str, errors: list[str]) -> dict[str, str]:
    fields: dict[str, str] = {}
    index = 0
    while index < len(lines):
        line = lines[index]
        if line.startswith((" ", "\t")) or ":" not in line:
            errors.append(f"{source}: 非法 frontmatter 行：{line!r}")
            index += 1
            continue
        key, raw_value = line.split(":", 1)
        key, value = key.strip(), raw_value.strip()
        if key in fields:
            errors.append(f"{source}: frontmatter 键重复：{key}")
        if value in (">", "|"):
            continuation: list[str] = []
            index += 1
            while index < len(lines) and lines[index].startswith((" ", "\t")):
                continuation.append(lines[index].strip())
                index += 1
            value = (" " if value == ">" else "\n").join(continuation)
            fields[key] = value
            continue
        fields[key] = value
        index += 1
    return fields


def lint_source(manifest: dict) -> None:
    """在触碰 dist 前验证所有主干组件；失败时保留上一份产物。"""
    errors: list[str] = []
    skill_names = manifest.get("skills", [])
    if not isinstance(skill_names, list) or not all(isinstance(name, str) for name in skill_names):
        raise SystemExit("源码 lint 失败，保留现有 dist：\n  manifest.skills 必须是字符串数组")
    for name in skill_names:
        skill_dir = PLUGIN / "skills" / name
        skill_file = skill_dir / "SKILL.md"
        if not skill_dir.is_dir() or not skill_file.is_file():
            errors.append(f"skill 缺失：plugin/skills/{name}/SKILL.md")
            continue
        text = skill_file.read_text(encoding="utf-8")
        fm, body = split_frontmatter(text)
        if not fm or not text.startswith("---\n"):
            errors.append(f"{name}: frontmatter 缺失或未闭合")
            continue
        fields = parse_skill_fields(fm, name, errors)
        if fields.get("name") != name:
            errors.append(f"{name}: name={fields.get('name')!r} 与目录名不一致")
        description = fields.get("description", "")
        if not description:
            errors.append(f"{name}: description 缺失")
        elif len(description) > 1024:
            errors.append(f"{name}: description 超过 1024 字符（{len(description)}）")
        if len(body.splitlines()) > 500:
            errors.append(f"{name}: 正文超过 500 行（{len(body.splitlines())}）")

    allowed_command_fields = {"description", "argument-hint", "skill"}
    for command in manifest.get("commands", []):
        name = command.get("name", "")
        if not re.fullmatch(r"[a-z0-9][a-z0-9_:-]{0,63}", name):
            errors.append(f"命令名非法：{name!r}")
            continue
        path = PLUGIN / "commands" / f"{name}.md"
        if not path.is_file():
            errors.append(f"命令缺失：plugin/commands/{name}.md")
            continue
        text = path.read_text(encoding="utf-8")
        fm, body = split_frontmatter(text)
        if not fm or not text.startswith("---\n"):
            errors.append(f"{path.name}: frontmatter 缺失或未闭合")
            continue
        fields: dict[str, str] = {}
        for line in fm:
            if not line.strip():
                continue
            if line.startswith((" ", "\t")) or ":" not in line:
                errors.append(f"{path.name}: frontmatter 必须是单行顶层键：{line!r}")
                continue
            key, value = (part.strip() for part in line.split(":", 1))
            if key in fields:
                errors.append(f"{path.name}: frontmatter 键重复：{key}")
            if key not in allowed_command_fields:
                errors.append(f"{path.name}: 未知 frontmatter 键：{key}")
            fields[key] = value
        expected_skill = command.get("skill")
        if not fields.get("skill"):
            errors.append(f"{path.name}: skill 缺失")
        elif fields["skill"] != expected_skill:
            errors.append(f"{path.name}: skill={fields['skill']!r} 与 manifest 的 {expected_skill!r} 不一致")
        if expected_skill not in skill_names or not (PLUGIN / "skills" / str(expected_skill)).is_dir():
            errors.append(f"{path.name}: manifest skill 不存在：{expected_skill!r}")
        if not fields.get("description") and not body.strip():
            errors.append(f"{path.name}: description 与正文不能同时为空")

    if errors:
        raise SystemExit("源码 lint 失败，保留现有 dist：\n  " + "\n  ".join(errors))


def build_into(target: Path, manifest: dict) -> tuple[int, int]:
    target.mkdir(parents=True, exist_ok=False)
    write_json(target / ".zcode-plugin" / "plugin.json", {
        "name": manifest["name"],
        "version": manifest["version"],
        "description": manifest["description"]["zh-CN"],
        "description_i18n": manifest["description"],
        "author": {"name": manifest["author"]},
        "license": manifest["license"],
        "skills": "skills",
        "commands": "commands",
    })

    template = (HOST_DIR / "marketplace.json").read_text(encoding="utf-8")
    write_text(target / "marketplace.json", template.replace("@VERSION@", manifest["version"]))

    n_skills = n_commands = 0
    for name in manifest["skills"]:
        source = PLUGIN / "skills" / name
        shutil.copytree(
            source,
            target / "skills" / name,
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo"),
        )
        n_skills += 1

    for command in manifest["commands"]:
        source = PLUGIN / "commands" / f"{command['name']}.md"
        write_text(
            target / "commands" / command["namespace"] / f"{command['name']}.md",
            transform_command(source.read_text(encoding="utf-8"), command["skill"]),
        )
        n_commands += 1
    return n_skills, n_commands


def publish_staging() -> None:
    if BACKUP.exists():
        if DIST.exists():
            shutil.rmtree(BACKUP)
        else:
            BACKUP.rename(DIST)
    if DIST.exists():
        DIST.rename(BACKUP)
    try:
        STAGING.rename(DIST)
    except Exception:
        if BACKUP.exists() and not DIST.exists():
            BACKUP.rename(DIST)
        raise
    else:
        if BACKUP.exists():
            try:
                shutil.rmtree(BACKUP)
            except OSError as exc:
                print(f"警告：新产物已发布，但旧备份清理失败：{BACKUP}（{exc}）", file=sys.stderr)


def main() -> None:
    check_neutral()
    manifest = json.loads((PLUGIN / "manifest.json").read_text(encoding="utf-8"))
    lint_source(manifest)

    if STAGING.exists():
        shutil.rmtree(STAGING)
    try:
        n_skills, n_commands = build_into(STAGING, manifest)
        publish_staging()
    except Exception:
        if STAGING.exists():
            shutil.rmtree(STAGING)
        raise

    print(f"构建完成 → {DIST}")
    print(f"  skills 复制 {n_skills}/{len(manifest['skills'])}，commands 生成 {n_commands}/{len(manifest['commands'])}")


if __name__ == "__main__":
    main()
