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


# == Coverage ==


if __name__ == "__main__":
    unittest.main()
