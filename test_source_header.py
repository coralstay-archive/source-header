# ---
# title: test_source_header
# description: source-header.py 단위·통합 테스트
# authors: [coralstay]
# license: AGPL-3.0-only
# status: draft
# task: TASK-1
# created_date: '2026-10-31'
# updated_date: '2026-10-31'
# ---
# TASK-1: source-header 1단계 - 헤더 스키마·파서·lint·init·fix·status·new
#
# 하이픈이 든 source-header.py는 import 문으로 못 불러오므로 importlib로 로드한다.
# git이 필요한 테스트는 임시 디렉터리에 저장소를 새로 만들어 CLI를 subprocess로 돌린다.
from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
MODULE_PATH = HERE / "source-header.py"
spec = importlib.util.spec_from_file_location("source_header", MODULE_PATH)
assert spec is not None and spec.loader is not None
sh = importlib.util.module_from_spec(spec)
sys.modules["source_header"] = sh
spec.loader.exec_module(sh)

WORK_ORDER = Path(
    "/Users/flynn_macpro/githubs/coralstay-software-factory/components/"
    "claude-code-agile-hooks/scripts/work_order.py"
)

CANONICAL_FIELDS = {
    "title": "demo",
    "description": "데모 파일",
    "authors": ["coralstay"],
    "license": "AGPL-3.0-only",
    "status": "draft",
    "task": "TASK-1",
    "created_date": "2026-10-01",
    "updated_date": "2026-10-31 09:30",
}


def commented(block: str, prefix: str) -> str:
    """`---` 블록 텍스트의 각 줄에 주석 접두사를 붙인다."""
    return "".join(f"{prefix} {line}".rstrip() + "\n" for line in block.splitlines())


def py_file(fields: dict, body: str = "print(1)\n") -> str:
    return sh.render_header(fields, "#") + body


def fields_with(**changes) -> dict:
    """CANONICAL_FIELDS에서 값을 바꾸거나(None이면 지운다) 더한 사본."""
    out = dict(CANONICAL_FIELDS)
    for key, value in changes.items():
        if value is None:
            out.pop(key, None)
        else:
            out[key] = value
    return out


def run_cli(args: list[str], cwd) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(MODULE_PATH), *args],
        cwd=cwd, capture_output=True, text=True, check=False,
    )


def codes(findings) -> list[str]:
    return [f.code for f in findings]


class TempDirCase(unittest.TestCase):
    """임시 디렉터리 하나를 쓰는 테스트 기반 클래스."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def write(self, rel: str, text: str) -> Path:
        path = self.tmp / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path

    def lint(self, fields: dict, strict: bool = False, **ctx) -> list:
        context = sh.LintContext(path="a.py", root=self.tmp, strict=strict, **ctx)
        return sh.lint_text(py_file(fields), "a.py", context)


def load_work_order():
    ws = importlib.util.spec_from_file_location("work_order_ref", WORK_ORDER)
    assert ws is not None and ws.loader is not None
    mod = importlib.util.module_from_spec(ws)
    ws.loader.exec_module(mod)
    return mod


PARSER_SAMPLES = [
    "---\ntitle: a\nauthors: [x, y]\n---\n",
    "---\nid: TASK-1\nlabels:\n  - tool\n  - ssot\ncreated_date: '2026-10-30 18:57'\n---\nbody\n",
    "---\ndescription: >-\n  여러 줄\n  설명\nstatus: \"In Progress\"\nempty: []\n---\n",
    "---\nk: 'it''s'\nlist:\n  -\n  - b\n---\n",
    "no frontmatter\n",
]


# == AC/DoD ==


class TestExtractRender(unittest.TestCase):
    """TASK-1#1 헤더 추출·렌더"""

    def test_prefix_table(self) -> None:
        """TASK-1#1 확장자별 주석 접두사(# // --, .md는 접두사 없음)"""
        cases = {
            "a.py": "#", "a.sh": "#", "a.yaml": "#", "a.toml": "#", "a.rb": "#",
            "a.ts": "//", "a.go": "//", "a.rs": "//", "a.java": "//", "a.cpp": "//",
            "a.sql": "--", "a.lua": "--", "a.md": "",
        }
        for name, prefix in cases.items():
            with self.subTest(name=name):
                self.assertEqual(sh.prefix_for(name), prefix)
        self.assertIsNone(sh.prefix_for("a.json"))

    def test_extract_each_prefix(self) -> None:
        """TASK-1#1 # // -- 접두사 헤더를 같은 필드로 읽는다"""
        block = sh.render_header(CANONICAL_FIELDS, "")
        for name, prefix in (("a.py", "#"), ("a.ts", "//"), ("a.sql", "--")):
            with self.subTest(name=name):
                text = commented(block, prefix) + "body\n"
                header = sh.extract_header(text, name)
                self.assertIsNotNone(header)
                self.assertEqual(header.fields, CANONICAL_FIELDS)
                self.assertEqual((header.start, header.end), (1, 10))
                self.assertEqual(header.lines["status"], 6)

    def test_markdown_plain_block(self) -> None:
        """TASK-1#1 .md는 1번 줄의 일반 --- 블록이다"""
        text = sh.render_header(CANONICAL_FIELDS, "") + "# 제목\n"
        header = sh.extract_header(text, "README.md")
        self.assertEqual(header.fields, CANONICAL_FIELDS)
        self.assertEqual(header.prefix, "")

    def test_skips_shebang_and_encoding(self) -> None:
        """TASK-1#1 shebang·encoding 줄 다음의 헤더를 찾는다"""
        text = (
            "#!/usr/bin/env python3\n# -*- coding: utf-8 -*-\n"
            + commented(sh.render_header(CANONICAL_FIELDS, ""), "#")
            + "print(1)\n"
        )
        header = sh.extract_header(text, "x.py")
        self.assertEqual(header.fields, CANONICAL_FIELDS)
        self.assertEqual(header.start, 3)

    def test_no_header(self) -> None:
        """TASK-1#1 헤더가 없거나 닫히지 않으면 None"""
        self.assertIsNone(sh.extract_header("print(1)\n", "x.py"))
        self.assertIsNone(sh.extract_header("# ---\n# title: a\nprint(1)\n", "x.py"))
        self.assertIsNone(sh.extract_header("x", "x.json"))

    @unittest.skipUnless(WORK_ORDER.exists(), "agile-hooks work_order.py 없음")
    def test_parser_matches_agile_hooks(self) -> None:
        """TASK-1#1 접두사 제거 후 파싱 결과가 agile-hooks parse_frontmatter와 같다"""
        ref = load_work_order()
        self.assertEqual(sh.KEY_RE.pattern, ref.KEY_RE.pattern)
        for sample in PARSER_SAMPLES:
            with self.subTest(sample=sample):
                self.assertEqual(sh.parse_frontmatter(sample), ref.parse_frontmatter(sample))
                if sample.startswith("---"):
                    block = sample.split("---\n", 2)
                    header_text = "---\n" + block[1] + "---\n"
                    for name, prefix in (("a.py", "#"), ("a.go", "//")):
                        header = sh.extract_header(commented(header_text, prefix), name)
                        self.assertEqual(header.fields, ref.parse_frontmatter(sample))

    def test_render_field_order_and_unknown(self) -> None:
        """TASK-1#1 render는 FIELD_ORDER를 고정하고 모르는 필드는 뒤에 보존한다"""
        fields = {"zeta": "1", "updated_date": "2026-10-31", "title": "t", "alpha": ["a"]}
        out = sh.render_header(fields, "#").splitlines()
        self.assertEqual(
            out,
            [
                "# ---",
                "# title: t",
                "# updated_date: '2026-10-31'",
                "# zeta: 1",
                "# alpha: [a]",
                "# ---",
            ],
        )

    def test_round_trip_lossless(self) -> None:
        """TASK-1#1 extract→render 왕복이 무손실이다"""
        tricky = dict(
            CANONICAL_FIELDS,
            description="콜론: 과 # 해시, 'quote'",
            labels=[],
            reviewers=["a", "b"],
            upstream="https://example.com/x#frag",
            extra="[not a list]",
            blank="",
        )
        for name, prefix in (("a.py", "#"), ("a.ts", "//"), ("a.sql", "--"), ("a.md", "")):
            with self.subTest(name=name):
                block = sh.render_header(tricky, prefix)
                text = ("#!/bin/x\n" if prefix == "#" else "") + block + "rest\n"
                header = sh.extract_header(text, name)
                self.assertEqual(header.fields, tricky)
                self.assertEqual(sh.render_header(header.fields, prefix), block)

    def test_yaml_comments_are_ignored(self) -> None:
        """TASK-1#1 헤더 안 YAML 주석(템플릿의 필드 설명)은 값에 섞이지 않는다"""
        text = textwrap.dedent(
            """\
            # ---
            # title: demo  # 필수 · str · 파일 이름
            # # reviewers: []  # 선택
            # upstream: 'a #b'  # 따옴표 안의 #은 값
            # ---
            """
        )
        header = sh.extract_header(text, "a.py")
        self.assertEqual(header.fields, {"title": "demo", "upstream": "a #b"})


class TestLintFormat(TempDirCase):
    """TASK-1#2 lint 형식 규칙과 출력 형식"""

    def test_valid_header_has_no_findings(self) -> None:
        """TASK-1#2 올바른 헤더는 아무것도 보고하지 않는다"""
        self.assertEqual(self.lint(CANONICAL_FIELDS), [])

    def test_missing_required_field(self) -> None:
        """TASK-1#2 필수 필드 누락은 오류(F001)이고 헤더 시작 줄을 가리킨다"""
        for key in sh.REQUIRED:
            with self.subTest(key=key):
                found = self.lint(fields_with(**{key: None}))
                self.assertIn("F001", codes(found))
                miss = [f for f in found if f.code == "F001"][0]
                self.assertEqual((miss.level, miss.line), ("error", 1))
                self.assertIn(key, miss.message)

    def test_no_header(self) -> None:
        """TASK-1#2 헤더가 없으면 H001, 닫히지 않았으면 H002"""
        ctx = sh.LintContext(path="a.py", root=self.tmp)
        self.assertEqual(codes(sh.lint_text("print(1)\n", "a.py", ctx)), ["H001"])
        self.assertEqual(codes(sh.lint_text("# ---\n# title: a\nx = 1\n", "a.py", ctx)), ["H002"])

    def test_status_enum(self) -> None:
        """TASK-1#2 status는 draft·review·published·deprecated·archived 중 하나(S001)"""
        found = self.lint(fields_with(status="done"))
        self.assertEqual(codes(found), ["S001"])
        self.assertEqual(found[0].line, 6)
        self.assertEqual(found[0].level, "error")

    def test_date_format_and_real_date(self) -> None:
        """TASK-1#2 날짜는 YYYY-MM-DD 또는 YYYY-MM-DD HH:MM이고 실존해야 한다(D001)"""
        for bad in ("2026/10/31", "2026-02-30", "2026-10-31 25:00", "31-10-2026", "2026-10-31T09:00"):
            with self.subTest(bad=bad):
                self.assertIn("D001", codes(self.lint(fields_with(updated_date=bad))))
        for good in ("2026-10-31", "2026-10-31 09:30", "2024-02-29"):
            with self.subTest(good=good):
                self.assertEqual(self.lint(fields_with(created_date=good, updated_date=good)), [])

    def test_list_field_types(self) -> None:
        """TASK-1#2 authors·reviewers·labels는 리스트(F003), 나머지는 스칼라(F004)"""
        self.assertEqual(codes(self.lint(fields_with(authors="coralstay"))), ["F003"])
        self.assertEqual(codes(self.lint(fields_with(labels="tool"))), ["F003"])
        self.assertEqual(codes(self.lint(fields_with(title=["a"]))), ["F004"])

    def test_empty_values(self) -> None:
        """TASK-1#2 빈 필수 값은 오류(F005), 단 description은 init이 비워 두므로 경고"""
        self.assertEqual(codes(self.lint(fields_with(title=""))), ["F005"])
        self.assertEqual(codes(self.lint(fields_with(authors=[]))), ["F005"])
        found = self.lint(fields_with(description=""))
        self.assertEqual([(f.code, f.level) for f in found], [("F005", "warning")])

    def test_unknown_field_warning_or_strict_error(self) -> None:
        """TASK-1#2 모르는 필드는 경고, --strict면 오류(F002)"""
        found = self.lint(fields_with(owner="x"))
        self.assertEqual([(f.code, f.level) for f in found], [("F002", "warning")])
        found = self.lint(fields_with(owner="x"), strict=True)
        self.assertEqual([(f.code, f.level) for f in found], [("F002", "error")])

    def test_finding_format(self) -> None:
        """TASK-1#2 출력은 path:line: level: message (code)"""
        f = sh.Finding("a.py", 6, "error", "S001", "bad status")
        self.assertEqual(f.format(), "a.py:6: error: bad status (S001)")

    def test_cli_exit_codes(self) -> None:
        """TASK-1#2 CLI: 오류가 있으면 exit 1, 경고만 있으면 exit 0, --strict면 모르는 필드도 exit 1"""
        self.write("ok.py", py_file(CANONICAL_FIELDS))
        self.write("warn.py", py_file(fields_with(owner="x")))
        res = run_cli(["lint", "ok.py", "warn.py"], self.tmp)
        self.assertEqual(res.returncode, 0, res.stdout + res.stderr)
        self.assertRegex(res.stdout, r"^warn\.py:\d+: warning: .* \(F002\)$")
        self.assertEqual(run_cli(["lint", "--strict", "warn.py"], self.tmp).returncode, 1)
        self.write("bad.py", py_file(fields_with(status="nope")))
        res = run_cli(["lint", "bad.py"], self.tmp)
        self.assertEqual(res.returncode, 1)
        self.assertIn("bad.py:6: error:", res.stdout)


PUBLISHED = fields_with(
    status="published",
    reviewers=["human"],
    reviewed_date="2026-10-10",
    published_date="2026-10-11",
    updated_date="2026-10-31",
)


class TestLintLifecycle(TempDirCase):
    """TASK-1#3 상태 조건·날짜 순서 규칙"""

    def test_reviewers_required_from_review(self) -> None:
        """TASK-1#3 TASK-1#B1 review·published·deprecated·archived면 reviewers가 있어야 한다"""
        self.assertEqual(codes(self.lint(fields_with(status="review", reviewers=["h"]))), [])
        self.assertEqual(codes(self.lint(fields_with(status="review"))), ["B1"])
        self.assertEqual(codes(self.lint(fields_with(status="review", reviewers=[]))), ["B1"])
        self.assertEqual(codes(self.lint(fields_with(reviewers=None))), [])  # draft는 무관
        no_reviewers = {k: v for k, v in PUBLISHED.items() if k != "reviewers"}
        self.assertIn("B1", codes(self.lint(no_reviewers)))

    def test_published_needs_review_and_publish_dates(self) -> None:
        """TASK-1#3 TASK-1#B2 published면 reviewed_date와 published_date가 있어야 한다"""
        self.assertEqual(self.lint(PUBLISHED), [])
        for key in ("reviewed_date", "published_date"):
            with self.subTest(key=key):
                found = self.lint(dict(PUBLISHED, **{key: ""}))
                self.assertEqual(codes(found), ["B2"])
                self.assertIn(key, found[0].message)

    def test_deprecated_needs_date_and_successor(self) -> None:
        """TASK-1#3 TASK-1#B3 deprecated·archived면 deprecated_date와 superseded_by가 있어야 한다"""
        for status in ("deprecated", "archived"):
            ok = fields_with(status=status, reviewers=["h"], deprecated_date="2026-10-31",
                             superseded_by="new.py")
            with self.subTest(status=status):
                self.assertEqual(self.lint(ok), [])
                self.assertEqual(codes(self.lint(dict(ok, superseded_by=""))), ["B3"])
                self.assertEqual(codes(self.lint(dict(ok, deprecated_date=""))), ["B3"])

    def test_date_order(self) -> None:
        """TASK-1#3 TASK-1#B4 created ≤ reviewed ≤ published ≤ deprecated, created ≤ updated"""
        self.assertEqual(codes(self.lint(fields_with(updated_date="2026-09-30"))), ["B4"])
        self.assertEqual(codes(self.lint(dict(PUBLISHED, reviewed_date="2026-10-12"))), ["B4"])
        self.assertEqual(codes(self.lint(dict(PUBLISHED, reviewed_date="2026-09-01"))), ["B4"])
        dep = dict(PUBLISHED, status="deprecated", superseded_by="x.py",
                   deprecated_date="2026-10-05")
        self.assertEqual(codes(self.lint(dep)), ["B4"])
        # 같은 날의 시각 차이는 순서 위반으로 보지 않는다(날짜 단위 비교)
        same_day = fields_with(created_date="2026-10-31 10:00", updated_date="2026-10-31")
        self.assertEqual(self.lint(same_day), [])
        # 형식이 틀린 날짜는 D001만 보고하고 순서 비교에서는 뺀다
        self.assertEqual(codes(self.lint(fields_with(updated_date="2026-13-01"))), ["D001"])


LICENSE_TEXTS = {
    "AGPL-3.0-only": "                    GNU AFFERO GENERAL PUBLIC LICENSE\n"
                     "                       Version 3, 19 November 2007\n",
    "GPL-3.0-only": "                    GNU GENERAL PUBLIC LICENSE\n"
                    "                       Version 3, 29 June 2007\n",
    "MIT": "MIT License\n\nCopyright (c) 2026 coralstay\n\n"
           "Permission is hereby granted, free of charge, to any person obtaining a copy\n",
    "Apache-2.0": "\n                                 Apache License\n"
                  "                           Version 2.0, January 2004\n",
    "BSD-3-Clause": "Copyright (c) 2026\n\nRedistribution and use in source and binary forms, "
                    "with or without\nmodification, are permitted provided that ...\n"
                    "3. Neither the name of the copyright holder nor the names of its\n",
}


class TestLintLicense(TempDirCase):
    """TASK-1#4 라이선스 규칙"""

    def test_spdx_expression(self) -> None:
        """TASK-1#4 TASK-1#B5 license는 SPDX 식별자 또는 AND/OR/WITH 식이어야 한다"""
        for good in ("MIT", "AGPL-3.0-only", "(MIT OR Apache-2.0)", "Apache-2.0 AND MIT",
                     "GPL-2.0-or-later WITH Classpath-exception-2.0", "LicenseRef-Proprietary",
                     "mit", "MIT AND (BSD-3-Clause OR Apache-2.0)", "GPL-2.0+"):
            with self.subTest(good=good):
                self.assertTrue(sh.valid_spdx(good))
                self.assertEqual(self.lint(fields_with(license=good)), [])
        for bad in ("MIT License", "GPL", "MIT OR", "MIT WITH Apache-2.0", "(MIT",
                    "Foo-1.0", "MIT Apache-2.0", "AND MIT"):
            with self.subTest(bad=bad):
                self.assertFalse(sh.valid_spdx(bad))
                self.assertEqual(codes(self.lint(fields_with(license=bad))), ["B5"])

    def test_spdx_identifier_line(self) -> None:
        """TASK-1#4 SPDX-License-Identifier 줄(헤더 필드 또는 머리 주석)은 license와 같아야 한다"""
        ctx = sh.LintContext(path="a.py", root=self.tmp)
        same = py_file(fields_with(), "# SPDX-License-Identifier: AGPL-3.0-only\nx = 1\n")
        self.assertEqual(sh.lint_text(same, "a.py", ctx), [])
        other = py_file(fields_with(), "# SPDX-License-Identifier: MIT\nx = 1\n")
        found = sh.lint_text(other, "a.py", sh.LintContext(path="a.py", root=self.tmp))
        self.assertEqual([(f.code, f.level, f.line) for f in found], [("L1", "error", 11)])
        as_field = fields_with(**{"SPDX-License-Identifier": "MIT"})
        self.assertEqual(codes(self.lint(as_field)), ["L1"])
        as_field_ok = fields_with(**{"SPDX-License-Identifier": "AGPL-3.0-only"})
        self.assertEqual(self.lint(as_field_ok), [])  # 알려진 키라 F002도 아니다

    def test_repo_license_detection(self) -> None:
        """TASK-1#4 저장소 LICENSE 첫머리에서 SPDX 식별자를 감지한다"""
        self.assertIsNone(sh.repo_license(self.tmp))
        for spdx, text in LICENSE_TEXTS.items():
            with self.subTest(spdx=spdx):
                self.write("LICENSE", text)
                self.assertEqual(sh.repo_license(self.tmp), spdx)

    def test_differs_from_repo_license_warns(self) -> None:
        """TASK-1#4 저장소 기본 라이선스와 다르면 경고(L2), 같은 계열(-only/-or-later)이나 식에 들어 있으면 통과"""
        found = self.lint(fields_with(license="MIT"), default_license="AGPL-3.0-only")
        self.assertEqual([(f.code, f.level) for f in found], [("L2", "warning")])
        for ok in ("AGPL-3.0-only", "AGPL-3.0-or-later", "MIT OR AGPL-3.0-only"):
            with self.subTest(ok=ok):
                self.assertEqual(self.lint(fields_with(license=ok), default_license="AGPL-3.0-only"), [])
        self.write("LICENSE", LICENSE_TEXTS["MIT"])
        self.write("a.py", py_file(CANONICAL_FIELDS))
        res = run_cli(["lint", "a.py"], self.tmp)
        self.assertEqual(res.returncode, 0)
        self.assertIn("(L2)", res.stdout)

    def test_upstream_needs_third_party_notice(self) -> None:
        """TASK-1#4 TASK-1#B6 upstream이 있는 파일은 THIRD_PARTY_NOTICES.md에 그 출처가 있어야 한다"""
        url = "https://github.com/karanb192/claude-code-hooks"
        found = self.lint(fields_with(upstream=url))
        self.assertEqual(codes(found), ["B6"])
        self.write("THIRD_PARTY_NOTICES.md", "# Notices\n\n- other (MIT)\n")
        self.assertEqual(codes(self.lint(fields_with(upstream=url))), ["B6"])
        self.write("THIRD_PARTY_NOTICES.md", f"# Notices\n\n- {url} (MIT)\n")
        self.assertEqual(self.lint(fields_with(upstream=url)), [])


class GitCase(TempDirCase):
    """임시 git 저장소 하나를 쓰는 테스트 기반 클래스."""

    def setUp(self) -> None:
        super().setUp()
        self.git("init", "-q", "-b", "main")
        self.git("config", "user.name", "tester")
        self.git("config", "user.email", "tester@example.com")
        self.git("config", "commit.gpgsign", "false")

    def git(self, *args: str, env: dict | None = None) -> str:
        res = subprocess.run(
            ["git", *args], cwd=self.tmp, capture_output=True, text=True, check=True,
            env={**os.environ, **(env or {})},
        )
        return res.stdout

    def commit(self, message: str, date: str | None = None, author: str | None = None) -> None:
        env = {}
        if date:
            env.update(GIT_AUTHOR_DATE=f"{date}T12:00:00", GIT_COMMITTER_DATE=f"{date}T12:00:00")
        args = ["commit", "-q", "-m", message]
        if author:
            args += ["--author", author]
        self.git(*args, env=env)

    def cli(self, *args: str) -> subprocess.CompletedProcess:
        return run_cli(list(args), self.tmp)


BAD = py_file(fields_with(status="bogus"))
GOOD = py_file(CANONICAL_FIELDS)


class TestLintTargets(GitCase):
    """TASK-1#5 lint 대상 선택"""

    def test_directory_recursion_and_default_excludes(self) -> None:
        """TASK-1#5 디렉터리는 재귀로 펼치고 기본 제외 경로와 모르는 확장자는 건너뛴다"""
        self.write("src/deep/a.py", BAD)
        self.write("src/b.ts", sh.render_header(fields_with(status="bogus"), "//"))
        for skipped in ("node_modules/x.py", ".venv/x.py", "backlog/tasks/x.md",
                        "opensource/x.py", "sub/node_modules/y.js", "data.json"):
            self.write(skipped, "no header\n")
        res = self.cli("lint", ".")
        self.assertEqual(res.returncode, 1)
        reported = sorted({line.split(":")[0] for line in res.stdout.splitlines()})
        self.assertEqual(reported, ["src/b.ts", "src/deep/a.py"])
        self.assertEqual(self.cli("lint").stdout, res.stdout)  # 인자가 없으면 "."

    def test_config_include_exclude(self) -> None:
        """TASK-1#5 .source-header.json의 include/exclude 글롭을 따른다"""
        self.write(".source-header.json", '{"include": ["src/**"], "exclude": ["src/gen/**"]}')
        self.write("src/a.py", BAD)
        self.write("src/gen/b.py", BAD)
        self.write("tools/c.py", BAD)
        res = self.cli("lint", ".")
        self.assertEqual([line.split(":")[0] for line in res.stdout.splitlines()], ["src/a.py"])

    def test_staged_reads_index_not_worktree(self) -> None:
        """TASK-1#5 --staged는 git show :path로 커밋될 내용을 검사한다"""
        self.write("a.py", BAD)
        self.git("add", "a.py")
        self.write("a.py", GOOD)  # 작업 트리만 고친다
        self.write("untracked.py", BAD)  # stage 안 된 파일은 대상이 아니다
        res = self.cli("lint", "--staged")
        self.assertEqual(res.returncode, 1)
        self.assertEqual({line.split(":")[0] for line in res.stdout.splitlines()}, {"a.py"})
        self.git("add", "a.py")
        self.write("a.py", BAD)  # 이번엔 index가 맞고 작업 트리가 틀렸다
        res = self.cli("lint", "--staged")
        self.assertEqual((res.returncode, res.stdout), (0, ""))

    def test_since_ref(self) -> None:
        """TASK-1#5 --since <ref>는 그 이후 바뀐 파일만 검사한다"""
        self.write("old.py", BAD)
        self.git("add", ".")
        self.commit("base")
        self.git("tag", "base")
        self.write("new.py", BAD)
        self.git("add", "new.py")
        self.commit("next")
        self.write("old_untouched.py", BAD)  # 추적되지 않은 파일은 diff에 없다
        res = self.cli("lint", "--since", "base")
        self.assertEqual(res.returncode, 1)
        self.assertEqual({line.split(":")[0] for line in res.stdout.splitlines()}, {"new.py"})
        bad_ref = self.cli("lint", "--since", "no-such-ref")
        self.assertEqual(bad_ref.returncode, 2)
        self.assertIn("no-such-ref", bad_ref.stderr)

    def test_paths_reported_relative_to_cwd(self) -> None:
        """TASK-1#5 하위 디렉터리에서 실행해도 --staged 경로는 cwd 기준으로 보인다"""
        self.write("pkg/a.py", BAD)
        self.git("add", ".")
        res = run_cli(["lint", "--staged"], self.tmp / "pkg")
        self.assertTrue(res.stdout.startswith("a.py:"), res.stdout)


TODAY = sh.today()


class TestInit(GitCase):
    """TASK-1#6 init"""

    def make_history(self) -> None:
        """alice가 1월에 추가하고, 2월에 이름을 바꾸고, bob이 3월에 고친 파일."""
        self.write("LICENSE", LICENSE_TEXTS["MIT"])
        self.write("tool_old.py", "#!/usr/bin/env python3\nprint(1)\n")
        self.git("add", ".")
        self.commit("add", "2026-01-05", "alice <a@example.com>")
        self.git("mv", "tool_old.py", "tool.py")
        self.commit("rename", "2026-02-01", "alice <a@example.com>")
        self.write("tool.py", "#!/usr/bin/env python3\nprint(2)\n")
        self.git("add", ".")
        self.commit("edit", "2026-03-01", "bob <b@example.com>")

    def test_git_derived_facts(self) -> None:
        """TASK-1#6 TASK-1#B7 created_date는 처음 추가된 커밋 날짜, authors는 git 작성자, license는 LICENSE"""
        self.make_history()
        self.assertEqual(sh.git_created_date(self.tmp, "tool.py"), "2026-01-05")
        self.assertEqual(sh.git_authors(self.tmp, "tool.py"), ["alice", "bob"])
        self.assertEqual(sh.repo_license(self.tmp), "MIT")
        self.assertIsNone(sh.git_created_date(self.tmp, "nope.py"))

    def test_init_inserts_derived_header(self) -> None:
        """TASK-1#6 TASK-1#B7 init은 git 유도 헤더 + status: draft + 빈 description을 shebang 뒤에 넣는다"""
        self.make_history()
        res = self.cli("init", "tool.py")
        self.assertEqual(res.returncode, 0, res.stdout + res.stderr)
        text = (self.tmp / "tool.py").read_text()
        self.assertTrue(text.startswith("#!/usr/bin/env python3\n# ---\n"))
        self.assertTrue(text.endswith("# ---\nprint(2)\n"))
        header = sh.extract_header(text, "tool.py")
        self.assertEqual(header.fields, {
            "title": "tool",
            "description": "",
            "authors": ["alice", "bob"],
            "license": "MIT",
            "status": "draft",
            "created_date": "2026-01-05",
            "updated_date": "2026-03-01",
        })
        lint = self.cli("lint", "tool.py")
        self.assertEqual(lint.returncode, 0)  # 빈 description 경고만 남는다
        self.assertIn("(F005)", lint.stdout)

    def test_init_is_idempotent(self) -> None:
        """TASK-1#6 여러 번 실행해도 결과가 같다"""
        self.make_history()
        self.write("docs/guide.md", "# Guide\n")
        self.cli("init", ".")
        first = {p: (self.tmp / p).read_text() for p in ("tool.py", "docs/guide.md")}
        res = self.cli("init", ".")
        self.assertEqual(res.returncode, 0)
        second = {p: (self.tmp / p).read_text() for p in ("tool.py", "docs/guide.md")}
        self.assertEqual(first, second)
        self.assertTrue(first["docs/guide.md"].startswith("---\ntitle: guide\n"))

    def test_init_untracked_file_and_license_fallback(self) -> None:
        """TASK-1#6 TASK-1#B7 추적 안 된 파일은 오늘 날짜·git 사용자, LICENSE가 없으면 --license 또는 NOASSERTION"""
        self.write("new.ts", "export const x = 1;\n")
        self.cli("init", "new.ts")
        fields = sh.extract_header((self.tmp / "new.ts").read_text(), "new.ts").fields
        self.assertEqual(fields["created_date"], TODAY)
        self.assertEqual(fields["updated_date"], TODAY)
        self.assertEqual(fields["authors"], ["tester"])
        self.assertEqual(fields["license"], "NOASSERTION")
        self.write("other.sql", "select 1;\n")
        self.cli("init", "--license", "AGPL-3.0-only", "other.sql")
        text = (self.tmp / "other.sql").read_text()
        self.assertTrue(text.startswith("-- ---\n"))
        self.assertEqual(sh.extract_header(text, "other.sql").fields["license"], "AGPL-3.0-only")


OLD = fields_with(created_date="2026-10-01", updated_date="2026-10-02")


class TestFixStaged(GitCase):
    """TASK-1#7 fix --staged"""

    def setUp(self) -> None:
        super().setUp()
        self.write("a.py", py_file(OLD, "x = 1\n"))
        self.git("add", ".")
        self.commit("base")

    def updated(self, where: str = "worktree") -> str:
        text = self.git("show", ":a.py") if where == "index" else (self.tmp / "a.py").read_text()
        return sh.extract_header(text, "a.py").fields["updated_date"]

    def test_body_change_sets_today_and_restages(self) -> None:
        """TASK-1#7 TASK-1#B8 본문이 HEAD와 달라진 staged 파일의 updated_date는 오늘이고 다시 stage된다"""
        self.write("a.py", py_file(OLD, "x = 2\n"))
        self.git("add", "a.py")
        res = self.cli("fix", "--staged")
        self.assertEqual(res.returncode, 0, res.stdout + res.stderr)
        self.assertEqual(self.updated(), TODAY)
        self.assertEqual(self.updated("index"), TODAY)
        self.assertEqual(self.git("diff", "--name-only"), "")  # 작업 트리 = 인덱스
        self.assertIn("a.py", res.stdout)
        # 고친 결과는 lint --staged를 통과한다
        self.assertEqual(self.cli("lint", "--staged").returncode, 0)

    def test_header_only_change_keeps_date(self) -> None:
        """TASK-1#7 TASK-1#B8 헤더만 바뀌고 본문이 HEAD와 같으면 updated_date를 건드리지 않는다"""
        self.write("a.py", py_file(dict(OLD, description="새 설명"), "x = 1\n"))
        self.git("add", "a.py")
        res = self.cli("fix", "--staged")
        self.assertEqual((res.returncode, res.stdout), (0, ""))
        self.assertEqual(self.updated("index"), "2026-10-02")

    def test_new_file_gets_today(self) -> None:
        """TASK-1#7 TASK-1#B8 HEAD에 없던 새 파일도 본문이 달라진 것으로 본다"""
        self.write("b.py", py_file(OLD, "y = 1\n"))
        self.git("add", "b.py")
        self.assertEqual(self.cli("fix", "--staged").returncode, 0)
        text = self.git("show", ":b.py")
        self.assertEqual(sh.extract_header(text, "b.py").fields["updated_date"], TODAY)

    def test_partially_staged_is_refused(self) -> None:
        """TASK-1#7 TASK-1#B9 일부만 staged된 파일은 수정하지 않고 오류로 멈춘다(exit 1)"""
        self.write("a.py", py_file(OLD, "x = 2\n"))
        self.git("add", "a.py")
        self.write("a.py", py_file(OLD, "x = 3\n"))  # stage 안 한 변경
        before_index = self.git("show", ":a.py")
        before_tree = (self.tmp / "a.py").read_text()
        res = self.cli("fix", "--staged")
        self.assertEqual(res.returncode, 1)
        self.assertIn("a.py", res.stdout + res.stderr)
        self.assertIn("B9", res.stdout + res.stderr)
        self.assertEqual(self.git("show", ":a.py"), before_index)
        self.assertEqual((self.tmp / "a.py").read_text(), before_tree)

    def test_preserves_comment_and_time_format(self) -> None:
        """TASK-1#7 TASK-1#B8 updated_date 줄만 바꾸고 그 줄의 설명 주석과 HH:MM 형식은 유지한다"""
        text = py_file(OLD, "x = 9\n").replace(
            "# updated_date: '2026-10-02'", "# updated_date: '2026-10-02 08:00'  # 커밋 때 자동"
        )
        self.write("a.py", text)
        self.git("add", "a.py")
        self.assertEqual(self.cli("fix", "--staged").returncode, 0)
        new_text = (self.tmp / "a.py").read_text()
        line = [x for x in new_text.splitlines() if "updated_date" in x][0]
        self.assertRegex(line, rf"^# updated_date: '{TODAY} \d\d:\d\d'  # 커밋 때 자동$")
        self.assertEqual(new_text.replace(line, ""), text.replace(
            "# updated_date: '2026-10-02 08:00'  # 커밋 때 자동", ""))


class TestStatusAndNew(GitCase):
    """TASK-1#8 status·new 명령"""

    def setUp(self) -> None:
        super().setUp()
        self.write("src/a.py", py_file(fields_with(task="TASK-1", updated_date="2026-10-30")))
        self.write("b.ts", sh.render_header(dict(PUBLISHED, task="TASK-2"), "//") + "x\n")
        self.write("c.py", py_file(fields_with(task=None)))
        self.write("plain.py", "print(1)\n")

    def test_status_table(self) -> None:
        """TASK-1#8 status는 헤더를 모아 STATUS·FILE·TASK·UPDATED 표를 출력한다"""
        res = self.cli("status")
        self.assertEqual(res.returncode, 0, res.stderr)
        rows = [line.split() for line in res.stdout.splitlines()]
        self.assertEqual(rows, [
            ["STATUS", "FILE", "TASK", "UPDATED"],
            ["published", "b.ts", "TASK-2", "2026-10-31"],
            ["draft", "c.py", "-", "2026-10-31", "09:30"],
            ["draft", "src/a.py", "TASK-1", "2026-10-30"],
        ])
        # 열이 맞춰져 있다: 모든 줄에서 FILE 열이 같은 위치에서 시작한다
        starts = {line.index(row[1]) for line, row in zip(res.stdout.splitlines(), rows)}
        self.assertEqual(len(starts), 1)

    def test_status_filters(self) -> None:
        """TASK-1#8 --status/--task로 거른다"""
        res = self.cli("status", "--status", "published")
        self.assertEqual([line.split()[1] for line in res.stdout.splitlines()[1:]], ["b.ts"])
        res = self.cli("status", "--task", "TASK-1")
        self.assertEqual([line.split()[1] for line in res.stdout.splitlines()[1:]], ["src/a.py"])
        res = self.cli("status", "--task", "task-1")  # Backlog.md ID는 대소문자를 가리지 않는다
        self.assertEqual([line.split()[1] for line in res.stdout.splitlines()[1:]], ["src/a.py"])

    def test_new_creates_file_with_header(self) -> None:
        """TASK-1#8 new는 헤더가 들어간 새 파일을 만든다"""
        res = self.cli("new", "pkg/tool.sh", "--title", "tool", "--task", "TASK-9",
                       "--description", "도구 설명", "--license", "MIT")
        self.assertEqual(res.returncode, 0, res.stdout + res.stderr)
        text = (self.tmp / "pkg/tool.sh").read_text()
        self.assertTrue(text.startswith("#!/usr/bin/env bash\n# ---\n"))
        self.assertEqual(sh.extract_header(text, "tool.sh").fields, {
            "title": "tool",
            "description": "도구 설명",
            "authors": ["tester"],
            "license": "MIT",
            "status": "draft",
            "task": "TASK-9",
            "created_date": TODAY,
            "updated_date": TODAY,
        })
        self.assertEqual(self.cli("lint", "pkg/tool.sh").returncode, 0)

    def test_new_refuses_existing_or_unknown(self) -> None:
        """TASK-1#8 이미 있는 파일은 덮지 않고(exit 1), 주석을 못 다는 형식은 거부한다(exit 2)"""
        before = (self.tmp / "plain.py").read_text()
        self.assertEqual(self.cli("new", "plain.py", "--title", "x").returncode, 1)
        self.assertEqual((self.tmp / "plain.py").read_text(), before)
        self.assertEqual(self.cli("new", "data.json", "--title", "x").returncode, 2)
        self.assertFalse((self.tmp / "data.json").exists())


# == Coverage ==


if __name__ == "__main__":
    unittest.main()
