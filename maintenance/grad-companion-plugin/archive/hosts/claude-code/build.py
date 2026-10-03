"""Claude Code 宿主适配层构建脚本：读 plugin/（宿主中立主干），生成 dist/claude-code/。

用法：
    python hosts/claude-code/build.py

与 hosts/zcode/build.py 平级、各自独立（不跨宿主 import 是既定纪律）。本文件属于适配层，
允许出现宿主专有词；plugin/ 不允许——构建前扫描，命中宿主专有词立即中止（不变量 #8）。

与 ZCode 布局的差异（namespace 是抽象概念，落地由各宿主 build 决定）：
- 清单位置：.claude-plugin/plugin.json；无 description_i18n（该键是 ZCode 格式）
- 命令扁平放置：commands/<name>.md——命名空间由插件名提供（宿主自己的规则），不用 grad/ 子目录
- frontmatter 转换：`skill:` 键整个移除（该宿主经 Skill 工具自动发现 skill），正文注入引导语与 $ARGUMENTS

诚实边界：产物结构与清单按公开的 Claude Code 插件规范静态生成并自检；
真实宿主的加载行为未在本机实测（见同目录 README.md 的「验证边界」）。
"""

from __future__ import annotations

import json
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PLUGIN = ROOT.parents[2] / "plugins" / "grad-companion-plugin" / "plugin"
DIST = ROOT / "dist" / "claude-code"
STAGING = DIST.with_name(f".{DIST.name}.staging")
BACKUP = DIST.with_name(f".{DIST.name}.backup")

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
            continue
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
    return [], text


def lint_source(manifest: dict) -> None:
    """构建前最小校验；失败时保留上一份产物。详细规范校验归契约测试。

    结构性校验与 zcode 侧 lint 同强度（skill 存在、命令 skill: 键与 manifest 一致且指向
    存在的 skill）；各宿主独有的格式规则（frontmatter 细节、布局）仍归各自实现。
    """
    errors: list[str] = []
    skills = manifest.get("skills", [])
    for name in skills:
        path = PLUGIN / "skills" / str(name) / "SKILL.md"
        if not path.is_file():
            errors.append(f"skill 缺失：{path}")
            continue
        fm, _ = split_frontmatter(path.read_text(encoding="utf-8"))
        joined = "\n".join(fm)
        if not fm:
            errors.append(f"{name}: frontmatter 缺失或未闭合")
            continue
        m_name = re.search(r"^name:\s*(\S+)", joined, re.M)
        if not m_name or m_name.group(1) != name:
            errors.append(f"{name}: frontmatter name 与目录名不一致")
        m_desc = re.search(r"^description:\s*(.+)$", joined, re.M)
        if not m_desc:
            errors.append(f"{name}: description 缺失")
        elif len(m_desc.group(1)) > 1024:
            errors.append(f"{name}: description 超 1024 字符")
    for command in manifest.get("commands", []):
        name = str(command.get("name"))
        path = PLUGIN / "commands" / f"{name}.md"
        if not path.is_file():
            errors.append(f"命令缺失：{path}")
            continue
        expected_skill = command.get("skill")
        fm, _ = split_frontmatter(path.read_text(encoding="utf-8"))
        declared = None
        for line in fm:
            if line.startswith("skill:"):
                declared = line.split(":", 1)[1].strip()
        if declared != expected_skill:
            errors.append(f"{path.name}: skill={declared!r} 与 manifest 的 {expected_skill!r} 不一致")
        if expected_skill not in skills or not (PLUGIN / "skills" / str(expected_skill)).is_dir():
            errors.append(f"{path.name}: manifest skill 不存在：{expected_skill!r}")
    if errors:
        raise SystemExit("源码 lint 失败，保留现有 dist：\n  " + "\n  ".join(errors))


def transform_command(text: str, skill: str) -> str:
    """中立命令 → Claude Code 命令：移除 skill 键（先核对一致）、注入引导语与 $ARGUMENTS。"""
    fm, body = split_frontmatter(text)
    out = ["---"]
    for line in fm:
        if line.startswith("skill:"):
            declared = line.split(":", 1)[1].strip()
            if declared and declared != skill:
                print(f"警告：命令 frontmatter 的 skill={declared} 与 manifest 的 {skill} 不一致，以 manifest 为准")
            continue  # 该宿主无此键：skills 由插件目录自动发现
        out.append(line)
    out += ["---", "", f"使用 `{skill}` 技能处理这个请求：", "", "$ARGUMENTS", "", body.rstrip()]
    return "\n".join(out) + "\n"


def build_into(target: Path, manifest: dict) -> tuple[int, int]:
    target.mkdir(parents=True, exist_ok=False)

    write_json(target / ".claude-plugin" / "plugin.json", {
        "name": manifest["name"],
        "version": manifest["version"],
        "description": manifest["description"]["zh-CN"],
        "author": {"name": manifest["author"]},
        "license": manifest["license"],
        "keywords": manifest.get("keywords", []),
        "commands": "./commands",
        "skills": "./skills",
    })
    write_json(target / ".claude-plugin" / "marketplace.json", {
        "name": f'{manifest["name"]}-marketplace',
        "owner": {"name": manifest["author"]},
        "plugins": [{
            "name": manifest["name"],
            "source": "./",
            "version": manifest["version"],
            "description": manifest["description"]["zh-CN"],
        }],
    })

    n_skills = n_commands = 0
    for name in manifest["skills"]:
        shutil.copytree(
            PLUGIN / "skills" / str(name),
            target / "skills" / str(name),
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo"),
        )
        n_skills += 1

    for command in manifest["commands"]:
        source = PLUGIN / "commands" / f"{command['name']}.md"
        write_text(
            target / "commands" / f"{command['name']}.md",
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
