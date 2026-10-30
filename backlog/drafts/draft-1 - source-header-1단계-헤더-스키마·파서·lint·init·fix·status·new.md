---
id: DRAFT-1
title: 'source-header 1단계: 헤더 스키마·파서·lint·init·fix·status·new'
status: Draft
assignee: []
created_date: '2026-10-30T18:57:00Z'
updated_date: '2026-10-30T18:57:00Z'
labels:
  - tool
  - ssot
dependencies: []
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
## 배경
유저 결정(2026-10-31): 프로젝트 상태 관리와 간단한 소스 코드 관리의 SSOT는 소스 파일 자체와 그 주석이다.
파일 맨 위 주석 안의 YAML 프론트 매터(Backlog.md 필드 관례)를 기준으로 삼고, 이를 검사·유지하는 단일 도구를 만든다.
전체 계획: ~/.claude/plans/giggly-kindling-snowglobe.md (6단계 중 1단계 = 도구 핵심).
install·git pre-commit 연결(2단계), Backlog.md 교차 검사(3단계), CI·에이전트 안내(4단계), Claude Write 가드(5단계), 확대 적용(6단계)은 이 카드 범위 밖.

## 헤더 형식
shebang·encoding 줄 다음, 언어 주석 접두사(# // --)를 붙인 `---` YAML 블록. .md는 일반 `---`.
필수: title, description, authors, license, status, created_date, updated_date
선택: task, reviewers, reviewed_date, published_date, deprecated_date, superseded_by, labels, version, upstream
status: draft · review · published · deprecated · archived

## 비즈니스 규칙
- B1 (AC #3) status가 review·published·deprecated·archived면 reviewers가 있어야 한다
- B2 (AC #3) status가 published면 reviewed_date와 published_date가 있어야 한다
- B3 (AC #3) status가 deprecated·archived면 deprecated_date와 superseded_by가 있어야 한다
- B4 (AC #3) created_date ≤ reviewed_date ≤ published_date ≤ deprecated_date, created_date ≤ updated_date
- B5 (AC #4) license는 SPDX 식별자 또는 AND/OR/WITH 식이어야 한다
- B6 (AC #4) upstream이 있는 파일은 THIRD_PARTY_NOTICES.md에 그 출처가 적혀 있어야 한다
- B7 (AC #6) init이 유도하는 created_date는 파일이 처음 추가된 커밋 날짜, authors는 git 작성자, license는 저장소 LICENSE다
- B8 (AC #7) 본문이 HEAD와 달라진 staged 파일의 updated_date는 오늘 날짜다
- B9 (AC #7) 일부만 staged된 파일은 자동 수정하지 않고 오류로 멈춘다
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 헤더 추출·렌더: 확장자별 주석 접두사(# // --, .md는 일반 ---)를 처리하고 shebang·encoding 줄을 건너뛴다. 접두사 제거 후 파싱은 agile-hooks parse_frontmatter와 같은 결과를 내고, render는 FIELD_ORDER 순서를 고정하며 모르는 필드를 보존한다. extract→render 왕복이 무손실이다
- [ ] #2 lint 형식 규칙: 필수 필드 누락, status enum 위반, 날짜 형식(YYYY-MM-DD 또는 YYYY-MM-DD HH:MM)·실존 날짜, 리스트 필드 타입을 검사한다. 출력은 path:line: level: message (code), 오류가 있으면 exit 1, 모르는 필드는 경고이고 --strict면 오류다
- [ ] #3 lint 상태 조건·날짜 순서 규칙(B1~B4)을 검사한다
- [ ] #4 lint 라이선스 규칙(B5, B6): SPDX-License-Identifier 줄도 인식해 license와 일치를 확인하고, 저장소 LICENSE에서 감지한 기본 라이선스와 다르면 경고한다
- [ ] #5 lint 대상 선택: 경로 인자(디렉터리는 재귀), --staged는 git show :path로 커밋될 내용을 검사, --since <ref>는 그 이후 바뀐 파일만 검사, .source-header.json include/exclude를 따른다
- [ ] #6 init: 헤더 없는 파일에 git에서 유도한 헤더(B7)와 status: draft, 빈 description을 넣는다. 여러 번 실행해도 결과가 같다
- [ ] #7 fix --staged: B8에 따라 updated_date를 갱신하고 다시 stage하며, B9에 해당하면 수정하지 않고 exit 1
- [ ] #8 status 명령은 헤더를 모아 STATUS·FILE·TASK·UPDATED 표를 출력하고 --status/--task로 거른다. new 명령은 헤더가 들어간 새 파일을 만든다
- [ ] #9 README 규칙 문서와 언어별 templates/(필드마다 설명 주석)를 만들고, 도구 자신의 소스·테스트 파일이 자기 lint를 통과한다. ruff check 통과
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. 저장소 설정: .tool-versions(python 3.12.13, ruff), .gitignore, .claude-code-agile-hooks.json(testCommand: python3 -m unittest -q, testFirst sourceGlobs=source-header.py testGlobs=test_*.py)
2. source-header.py 단일 파일(표준 라이브러리만): COMMENT_PREFIX → extract_header/render_header → parse_frontmatter(agile-hooks scripts/work_order.py 사본) → git 유도 함수 → RULES 목록 → argparse 서브커맨드(lint, init, fix, status, new)
3. AC마다 test_source_header.py에 <ID>#n·<ID>#Bk 표식 테스트 먼저 → 구현 → 커밋. 구현은 서브에이전트(워크트리)에 위임, 메인이 리뷰·재실행
4. 주석: 모듈 머리에 이 헤더 형식 자체를 적용(dogfooding) + 핵심 함수마다 무엇/왜 주석
5. README.md(규칙 표·status 전이·사용법), templates/(python, shell, typescript, go, sql, markdown) 필드마다 설명 주석
6. bin 링크(bin/source-header)는 2단계에서 git-pre-commit과 함께 만든다
<!-- SECTION:PLAN:END -->
