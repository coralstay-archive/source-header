#!/usr/bin/env python3
# ---
# title: source-header
# description: 소스 파일 머리 주석의 YAML 헤더를 검사·유지하는 도구
# authors: [coralstay]
# license: AGPL-3.0-only
# status: draft
# task: TASK-1
# created_date: '2026-10-31'
# updated_date: '2026-10-31'
# ---
# [설계 메모]
# 프로젝트 상태와 간단한 소스 관리의 SSOT는 소스 파일 자체와 그 머리 주석이다.
# 이 도구는 그 머리 주석 안의 YAML 헤더(위 블록이 그 형식이다)를 읽고, 검사하고,
# git에서 유도할 수 있는 값(created_date, authors, license, updated_date)을 채운다.
#
# - 표준 라이브러리만 쓴다: 워크스페이스에 PyYAML이 없고, pre-commit·CI·다른 에이전트
#   어디서든 python3와 git만 있으면 같은 결과가 나와야 하기 때문이다.
# - 파서는 agile-hooks scripts/work_order.py의 parse_frontmatter 사본이다. 주석 접두사를
#   벗기면 Backlog.md 카드와 같은 텍스트가 되므로, 새 YAML 파서를 만들지 않고 훅과 같은
#   동작을 공유한다. 사본이 원본과 같은지는 테스트가 확인한다.
# - --staged는 작업 트리가 아니라 인덱스(git show :path)를 읽는다. 커밋되는 것은 인덱스
#   내용이므로, 작업 트리를 보면 고친 척만 하고 틀린 내용이 커밋될 수 있다.
# - fix는 일부만 staged된 파일을 고치지 않는다. 작업 트리 파일을 고쳐 다시 git add하면
#   아직 stage하지 않은 변경까지 커밋에 섞여 들어가기 때문이다.
# - 규칙은 (fields, ctx) -> [Finding] 함수 목록(RULES)이라 단계마다 덧붙이기 쉽다.
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path, PurePath

# --- 헤더 스키마 ---

# 확장자 → 주석 접두사. .md는 접두사 없이 1번 줄의 일반 프론트 매터를 쓴다.
COMMENT_PREFIX = {
    **dict.fromkeys((".py", ".sh", ".bash", ".yaml", ".yml", ".toml", ".rb"), "#"),
    **dict.fromkeys(
        (".js", ".ts", ".tsx", ".jsx", ".go", ".rs", ".java", ".c", ".h", ".cpp", ".hpp",
         ".kt", ".swift"),
        "//",
    ),
    **dict.fromkeys((".sql", ".lua"), "--"),
    ".md": "",
}

REQUIRED = ("title", "description", "authors", "license", "status", "created_date",
            "updated_date")
OPTIONAL = ("task", "reviewers", "reviewed_date", "published_date", "deprecated_date",
            "superseded_by", "labels", "version", "upstream")
# render가 쓰는 고정 순서. 사람이 쓰는 필드 → 상태 → git 유도 날짜 → 수명 주기 날짜.
FIELD_ORDER = ("title", "description", "authors", "reviewers", "license", "status", "task",
               "labels", "version", "upstream", "superseded_by", "created_date",
               "updated_date", "reviewed_date", "published_date", "deprecated_date")
LIST_FIELDS = ("authors", "reviewers", "labels")
DATE_FIELDS = ("created_date", "updated_date", "reviewed_date", "published_date",
               "deprecated_date")
STATUSES = ("draft", "review", "published", "deprecated", "archived")

# shebang 다음에 올 수 있는 PEP 263 encoding 줄
ENCODING_RE = re.compile(r"^[ \t\f]*#.*?coding[:=]")


# --- agile-hooks와 공유하는 파서 (scripts/work_order.py 사본, 수정 금지) ---

KEY_RE = re.compile(r"^([A-Za-z_][\w-]*):\s*(.*)$")


def parse_frontmatter(text):
    """The top-level keys of a `---` frontmatter block. Values are strings,
    or lists for block (`- x`) and inline (`[x, y]`) lists. Only what
    backlog.md writes is understood - this is not a YAML parser."""

    def unquote(value):
        if len(value) >= 2 and value[0] == value[-1] == "'":
            return value[1:-1].replace("''", "'")
        if len(value) >= 2 and value[0] == value[-1] == '"':
            return value[1:-1]
        return value

    lines = text.split("\n")
    if lines[0].strip() != "---":
        return {}
    fields = {}
    key = None
    for line in lines[1:]:
        if line.strip() == "---":
            break
        m = KEY_RE.match(line)
        if m:
            key, value = m.group(1), m.group(2).strip()
            if value.startswith("[") and value.endswith("]"):
                inner = value[1:-1].strip()
                fields[key] = [unquote(v.strip()) for v in inner.split(",")] if inner else []
            elif value in (">-", ">", "|", "|-"):
                fields[key] = ""
            else:
                fields[key] = unquote(value)
            continue
        item = line.strip()
        if key is None or not item:
            continue
        if item == "-" or item.startswith("- "):
            if not isinstance(fields[key], list):
                fields[key] = []
            fields[key].append(unquote(item[2:].strip()))
        elif isinstance(fields[key], str):
            fields[key] = (fields[key] + " " + item).strip()
    return fields


# --- 추출 · 렌더 ---


@dataclass
class Header:
    """파일 안 헤더 하나. start/end는 여는·닫는 `---` 줄 번호(1부터), lines는 필드별 줄 번호."""

    fields: dict
    start: int
    end: int
    prefix: str
    lines: dict = field(default_factory=dict)


def prefix_for(path) -> str | None:
    """확장자의 주석 접두사. 모르는 형식(JSON 등 주석을 못 다는 파일)은 None."""
    return COMMENT_PREFIX.get(PurePath(str(path)).suffix.lower())


def strip_yaml_comment(line: str) -> str:
    """따옴표 밖의 YAML 주석(` #...`, 줄 머리 `#`)을 떼어 낸다.

    템플릿은 필드마다 설명 주석을 단다. parse_frontmatter는 주석을 모르므로 넘기기 전에
    여기서 지운다. 주석이 없는 줄은 그대로라 원본 파서와의 동일성이 깨지지 않는다."""
    if line.lstrip().startswith("#"):
        return ""
    quote = None
    i = 0
    while i < len(line):
        ch = line[i]
        if quote:
            if ch == quote == "'" and line[i + 1:i + 2] == "'":
                i += 1  # 작은따옴표 안의 '' 는 이스케이프된 '
            elif ch == quote:
                quote = None
        elif ch in "'\"" and (i == 0 or line[i - 1] in " \t[,:-"):
            quote = ch
        elif ch == "#" and i > 0 and line[i - 1] in " \t":
            return line[:i].rstrip()
        i += 1
    return line


def header_start(lines: list[str], prefix: str) -> int:
    """헤더가 시작할 수 있는 줄 위치(0부터). shebang과 encoding 줄을 건너뛴다."""
    i = 0
    if prefix and i < len(lines) and lines[i].startswith("#!"):
        i += 1
    while prefix == "#" and i < len(lines) and i < 2 and ENCODING_RE.match(lines[i]):
        i += 1
    return i


def _unprefix(line: str, prefix: str) -> str | None:
    """`<prefix> text`에서 text를 꺼낸다. 접두사가 아니면 None(헤더 밖)."""
    if not prefix:
        return line
    stripped = line.rstrip("\r")
    if stripped == prefix:
        return ""
    if stripped.startswith(prefix + " "):
        return stripped[len(prefix) + 1:]
    return None


def extract_header(text: str, path) -> Header | None:
    """파일 텍스트에서 헤더를 찾아 필드와 줄 위치를 돌려준다. 없거나 닫히지 않으면 None.

    접두사를 벗기고 YAML 주석을 지운 `---` 블록을 parse_frontmatter에 넘기므로,
    필드 해석은 Backlog.md 카드를 읽는 agile-hooks와 똑같다."""
    prefix = prefix_for(path)
    if prefix is None:
        return None
    lines = text.split("\n")
    i = header_start(lines, prefix)
    if i >= len(lines) or (_unprefix(lines[i], prefix) or "").strip() != "---":
        return None
    body: list[tuple[int, str]] = []
    for j in range(i + 1, len(lines)):
        inner = _unprefix(lines[j], prefix)
        if inner is None:
            return None
        if inner.strip() == "---":
            block = "\n".join(["---", *(t for _, t in body), "---"])
            key_lines = {}
            for lineno, t in body:
                m = KEY_RE.match(t)
                if m and m.group(1) not in key_lines:
                    key_lines[m.group(1)] = lineno
            return Header(parse_frontmatter(block), i + 1, j + 1, prefix, key_lines)
        body.append((j + 1, strip_yaml_comment(inner)))
    return None


def _needs_quote(value: str) -> bool:
    if value == "" or value != value.strip():
        return True
    if value in (">-", ">", "|", "|-") or value[0] in "'\"[{&*!%@`|>":
        return True
    if value.startswith("- ") or value == "-" or " #" in value or value.startswith("#"):
        return True
    return bool(DATE_RE.match(value))


def render_value(value) -> str:
    """값 하나를 YAML 스칼라/인라인 리스트로. 날짜는 Backlog.md처럼 작은따옴표로 감싼다."""
    if isinstance(value, list):
        return "[" + ", ".join(render_scalar(v) for v in value) + "]"
    return render_scalar(value)


def render_scalar(value: str) -> str:
    if _needs_quote(value):
        return "'" + value.replace("'", "''") + "'"
    return value


DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}( \d{2}:\d{2})?$")


def render_header(fields: dict, prefix: str) -> str:
    """필드를 헤더 블록 텍스트로 만든다. FIELD_ORDER 순서 고정, 모르는 필드는 그 뒤에 원래 순서로.

    순서를 고정해야 사람·도구가 고친 헤더의 diff가 작고 예측 가능하다."""
    keys = [k for k in FIELD_ORDER if k in fields] + [k for k in fields if k not in FIELD_ORDER]
    lines = ["---"]
    for key in keys:
        value = fields[key]
        if isinstance(value, list) and any("," in v for v in value):
            # 인라인 리스트는 쉼표로 나뉘므로 쉼표가 든 항목은 블록 리스트로 쓴다.
            lines.append(f"{key}:")
            lines.extend(f"  - {render_scalar(v)}" for v in value)
        else:
            lines.append(f"{key}: {render_value(value)}")
    lines.append("---")
    if not prefix:
        return "\n".join(lines) + "\n"
    return "".join(f"{prefix} {line}\n" for line in lines)


# --- lint 규칙 ---


@dataclass
class Finding:
    """규칙 위반 하나. code는 문서·억제에 쓰는 안정된 식별자다(README 규칙 표 참고)."""

    path: str
    line: int
    level: str  # "error" | "warning"
    code: str
    message: str

    def format(self) -> str:
        # 편집기·CI가 바로 점프할 수 있는 컴파일러식 형식
        return f"{self.path}:{self.line}: {self.level}: {self.message} ({self.code})"


@dataclass
class LintContext:
    """규칙이 필드 밖에서 알아야 하는 것: 파일 위치, 저장소 루트, 옵션, 저장소 기본값."""

    path: str
    root: Path
    strict: bool = False
    default_license: str | None = None
    header: Header | None = None


def parse_date(value):
    """헤더 날짜를 datetime으로. 형식이 틀리거나 실존하지 않는 날짜면 None."""
    if not isinstance(value, str) or not DATE_RE.match(value):
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d %H:%M" if " " in value else "%Y-%m-%d")
    except ValueError:
        return None


def _line(ctx: LintContext, key: str | None = None) -> int:
    """필드가 적힌 줄. 필드가 없으면(누락 등) 헤더 시작 줄."""
    header = ctx.header
    if header is None:
        return 1
    return header.lines.get(key, header.start) if key else header.start


def _finding(ctx, key, level, code, message) -> Finding:
    return Finding(ctx.path, _line(ctx, key), level, code, message)


def rule_required(fields, ctx):
    """F001 필수 필드 누락, F005 빈 필수 값(description만 경고: init이 일부러 비워 둔다)."""
    out = []
    for key in REQUIRED:
        if key not in fields:
            out.append(_finding(ctx, None, "error", "F001", f"required field '{key}' is missing"))
        elif fields[key] in ("", []):
            level = "warning" if key == "description" else "error"
            out.append(_finding(ctx, key, level, "F005", f"field '{key}' is empty"))
    return out


def rule_unknown(fields, ctx):
    """F002 모르는 필드. 오타를 잡으려는 것이라 기본은 경고, --strict면 오류."""
    level = "error" if ctx.strict else "warning"
    return [
        _finding(ctx, key, level, "F002", f"unknown field '{key}'")
        for key in fields
        if key not in REQUIRED and key not in OPTIONAL
    ]


def rule_types(fields, ctx):
    """F003 리스트여야 하는 필드가 스칼라, F004 스칼라여야 하는 필드가 리스트."""
    out = []
    for key, value in fields.items():
        if key in LIST_FIELDS and not isinstance(value, list) and value != "":
            out.append(_finding(ctx, key, "error", "F003", f"field '{key}' must be a list"))
        elif key not in LIST_FIELDS and (key in REQUIRED or key in OPTIONAL) and isinstance(value, list):
            out.append(_finding(ctx, key, "error", "F004", f"field '{key}' must be a scalar"))
    return out


def rule_status(fields, ctx):
    """S001 status 값이 정해진 다섯 가지가 아님."""
    status = fields.get("status")
    if status in (None, "") or status in STATUSES:
        return []
    return [_finding(ctx, "status", "error", "S001",
                     f"status '{status}' is not one of {', '.join(STATUSES)}")]


def rule_dates(fields, ctx):
    """D001 날짜 형식(YYYY-MM-DD 또는 YYYY-MM-DD HH:MM)·실존 날짜."""
    out = []
    for key in DATE_FIELDS:
        value = fields.get(key)
        if value in (None, "") or isinstance(value, list):
            continue
        if parse_date(value) is None:
            out.append(_finding(ctx, key, "error", "D001",
                                f"'{key}' must be a real date as YYYY-MM-DD or YYYY-MM-DD HH:MM"))
    return out


RULES = [rule_required, rule_unknown, rule_types, rule_status, rule_dates]


def lint_text(text: str, path: str, ctx: LintContext) -> list[Finding]:
    """파일 텍스트 하나에 RULES를 모두 적용한다. 헤더가 없으면 H001/H002 하나만 보고한다."""
    header = extract_header(text, path)
    if header is None:
        prefix = prefix_for(path) or ""
        lines = text.split("\n")
        i = header_start(lines, prefix)
        opened = i < len(lines) and (_unprefix(lines[i], prefix) or "").strip() == "---"
        if opened:
            return [Finding(path, i + 1, "error", "H002", "header block is not closed")]
        return [Finding(path, 1, "error", "H001", "source header is missing")]
    ctx.header = header
    out = []
    for rule in RULES:
        out.extend(rule(header.fields, ctx))
    return out


# --- CLI ---


def repo_root(cwd: Path) -> Path:
    """cwd가 속한 git 저장소의 최상위. git 저장소가 아니면 cwd 자체."""
    out = git(["rev-parse", "--show-toplevel"], cwd)
    return Path(out.strip()) if out else cwd


def git(args: list[str], cwd: Path) -> str | None:
    """git 명령 출력. 실패(저장소 아님, 파일 없음 등)하면 None."""
    try:
        res = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=False)
    except FileNotFoundError:
        return None
    return res.stdout if res.returncode == 0 else None


def iter_files(paths: list[str]):
    """경로 인자를 파일 목록으로. 디렉터리는 재귀로 펼친다."""
    for raw in paths:
        p = Path(raw)
        if p.is_dir():
            yield from sorted(q for q in p.rglob("*") if q.is_file())
        elif p.is_file():
            yield p


def cmd_lint(args) -> int:
    cwd = Path.cwd()
    root = repo_root(cwd)
    findings: list[Finding] = []
    for path in iter_files(args.paths or ["."]):
        if prefix_for(path) is None:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        ctx = LintContext(path=str(path), root=root, strict=args.strict)
        findings.extend(lint_text(text, str(path), ctx))
    for f in findings:
        print(f.format())
    return 1 if any(f.level == "error" for f in findings) else 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="source-header", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("lint", help="헤더 규칙 검사")
    p.add_argument("paths", nargs="*")
    p.add_argument("--strict", action="store_true", help="모르는 필드도 오류로")
    p.set_defaults(func=cmd_lint)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
