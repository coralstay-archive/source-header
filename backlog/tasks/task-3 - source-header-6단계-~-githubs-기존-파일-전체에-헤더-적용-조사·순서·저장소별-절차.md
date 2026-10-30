---
id: TASK-3
title: 'source-header 6단계: ~/githubs 기존 파일 전체에 헤더 적용 (조사·순서·저장소별 절차)'
status: To Do
assignee: []
created_date: '2026-10-30T19:31:00Z'
updated_date: '2026-10-30T19:35:00Z'
labels:
  - rollout
dependencies: []
documentation:
  - /Users/flynn_macpro/.claude/plans/giggly-kindling-snowglobe.md
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
## 배경
유저 결정(2026-10-31): ~/githubs에서 관리하는 기존 파일 전체에 소스 헤더를 적용한다.
- freeride: 내가 짠 코드만. 책 예제 코드는 저장소별 규칙(디렉터리 패턴)을 먼저 조사해 .source-header.json exclude로 뺀다
- description: 서브에이전트가 파일을 읽고 한 줄 초안을 쓴다. 저장소마다 커밋을 나눠 diff로 검토한다
- .md: README·CHANGELOG 같은 표지 문서는 제외하고 design/·docs/ 설계 문서는 포함. backlog/는 원래 제외
- MIT 저장소(dev-toolchain, omnivim, devOps-LifeCycle)는 AGPL-3.0-only로 전환

## 조사 결과 (2026-10-31)
- 대상: factory·dev-tools·toy-project 9개 저장소(소스 약 860 / md 약 280), freeride 7개(소스 약 8,200 / md 약 3,300, 책 예제 분리 전)
- 제외: opensource/, ebpf-wire-to-code-tracer/references/*(외부 클론 3개), backlog/
- 지금 작업 중이라 나중에 할 저장소: agent-orchestrator(task/AO-32, 변경 있음), claude-code-agile-hooks(task/TASK-71), ebpf-wire-to-code-tracer(변경 24), freeride/doctree(변경 9), freeride(변경 1)
- 작성자: cpu-once·amosQP·coralstay는 같은 계정의 옛 이름 → .mailmap으로 coralstay로 묶어 authors에 반영
- ⚠️ dev-toolchain 커밋에 sunrisesong6@gmail.com 작성자가 있다 → 다른 사람이면 그 코드는 MIT 유지 또는 동의 필요. AGPL 전환 전에 유저 확인

## 저장소별 절차 (저장소 하나 = 커밋 묶음 하나)
1. backlog 프로젝트면 그 저장소에 카드(draft → 승인 → promote)를 만들고 그 저장소의 task 브랜치에서 진행
2. .source-header.json(include/exclude) 작성 → source-header init → 서브에이전트가 description 초안 → lint 오류 0
3. 유저가 diff 검토 → 병합
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 freeride 각 저장소의 '내가 짠 코드 vs 책 예제' 구분 규칙을 조사해 표로 정리하고 유저 승인을 받는다
- [ ] #2 dev-toolchain의 외부 작성자 커밋을 확인해 AGPL 전환 가능 여부를 유저에게 보고한다
- [ ] #3 적용 순서표(바로 가능한 저장소 → 작업 끝난 뒤 할 저장소)를 work-order에 반영하고, 저장소마다 후속 카드를 만든다
- [ ] #4 .mailmap 기반 authors 정규화를 source-header init에 반영한다(테스트 포함)
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 조사 결과 표(freeride 구분 규칙, dev-toolchain 작성자)를 Implementation Notes에 기록하고 유저 승인을 받음
- [ ] #2 .mailmap 테스트 포함 전체 테스트 통과, ruff 통과
- [ ] #3 저장소별 후속 draft가 만들어지고 work-order에 반영됨
<!-- DOD:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
### Subjective
유저 결정(2026-10-31): ~/githubs 기존 파일 전체 적용. freeride는 내가 짠 코드만, description은 에이전트 초안, README 제외·설계 문서 포함, MIT 저장소는 AGPL로 전환.

### Objective
조사 결과는 Description 참고. 저장소 16개(외부 클론 제외), 그중 5개는 작업 중이다. dev-toolchain에 외부 이메일 작성자가 있다.

### Assessment
규모가 커서 이 카드는 조사·순서·공통 기능(.mailmap)까지만 한다. 실제 적용은 저장소별 후속 카드로 나눠 하나씩 검토 가능하게 한다.

### Plan
1. freeride 책 예제 구분 규칙 조사(서브에이전트) → 표로 유저 승인
2. dev-toolchain 외부 작성자 커밋 확인 → 보고
3. .mailmap 정규화를 init에 추가(테스트 먼저)
4. 순서표 + 저장소별 후속 draft 생성
<!-- SECTION:PLAN:END -->
