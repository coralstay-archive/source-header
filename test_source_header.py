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


# == Coverage ==


if __name__ == "__main__":
    unittest.main()
