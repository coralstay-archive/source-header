---
id: TASK-16
title: '공개 전환 전 라이선스·저작권 정리: 이력 재생성 5곳 + LICENSE 보강'
status: To Do
assignee: []
created_date: '2026-10-31T11:41:00Z'
updated_date: '2026-10-31T11:45:00Z'
labels:
  - license
  - public
dependencies: []
documentation:
  - /Users/flynn_macpro/.claude/plans/giggly-kindling-snowglobe.md
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
## 배경
유저 결정(2026-10-31): ~/githubs 저장소를 공개(Public)로 전환할 예정이므로, 헤더 적용보다 먼저 라이선스·저작권 문제를 정리한다. 공개되면 git 이력도 공개되므로, 이력에 제3자 저작물이 있는 저장소는 이력을 새로 만들고 GitHub 저장소를 삭제 후 같은 이름으로 다시 만든다(force-push만으로는 refs/pull·캐시 객체가 남음). 책 원문 등은 로컬에 남기고 .gitignore로 추적에서 뺀다.

## 감사 결과 (2026-10-31, Explore 서브에이전트 + 메인 표본 확인)
| 저장소 | 문제 | 조치 |
|---|---|---|
| freeride/handcrafted-cpp | practice/c-and-cpp/07_extreme_c·08_prof_cpp, practice/jongmanbook, practice/stone-lecture(책 원본 약 4,000+), googletest 복사본, 큰 .in/.zip/.pdf/.eps, 이력의 scripts/book*_data, README '.gitignore로 격리' 허위 문구 | ignore + README 수정 + re-init + GitHub 재생성 |
| freeride/coding-style-refactoring-principles | docs/.ocr-cache 233개(교보eBook 워터마크·구매 ID), 책 9권 전체 목차(contents-overview-tocs.md, docs/*TOC*.json, docs/TREE_METADATA.*, docs/TESTING_AND_REFACTORING_METADATA.*), 이력의 tracks/** | ignore + re-init + 재생성 |
| dev-tools/omnivim | official_sources/** (Practical Vim 공식 예제 137), MIT | ignore + MIT→AGPL + re-init + 재생성 |
| freeride/handcrafted-java | 이력의 jls-spec/*.pdf(Oracle JLS/JVMS), .gitignore의 build.gradle.kts 모순 | ignore + re-init + 재생성 |
| freeride/databases | 책별 장·페이지·개념 요약 데이터 scripts/content*_data(이력엔 book*_data) | 유저 결정: 책 기반 데이터 ignore + re-init + 재생성 |
| dev-tools/central-docs-collector, dev-tools/ebpf-wire-to-code-tracer, freeride(루트) | 문제 없음. LICENSE 없음, ebpf는 .opensource/가 info/exclude로만 무시 | LICENSE + .gitignore 보강 |
| backlog 저장소(devOps-LifeCycle TASK-208, toy-project TASK-68, dev-toolchain TASK-175, factory TASK-23, git-commit-tool GF-150) | MIT→AGPL(devOps, dev-toolchain), LICENSE 없음(toy), gitleaks 오탐(toy 11건), devOps 로컬 쓰레기 1.2GB | 각 저장소 헤더 카드의 '라이선스 조치' AC를 먼저 진행(훅상 그 저장소 task 브랜치에서만 커밋 가능) |
| 나중(진행 중 작업): agent-orchestrator, claude-code-agile-hooks, doctree | 이미 AGPL 또는 문제 없음(doctree 서재 목록은 유지 결정) | 각 헤더 카드에서 |

## 원칙
- 되돌릴 수 없는 작업(.git 삭제, GitHub 저장소 삭제) 전에 git bundle 전체 백업 + bundle verify
- 재생성한 GitHub 저장소는 일단 Private. 공개 전환은 모든 정리가 끝난 뒤 유저가 따로 결정
- 공개 전 마지막으로 gitleaks와 서드파티 경로 재검사
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 재생성·변경 대상 저장소 전부를 git bundle로 ~/githubs-backup/2026-10-31/에 백업하고 git bundle verify가 통과한다
- [ ] #2 handcrafted-cpp: 책 원본 트랙·googletest·데이터 파일을 .gitignore로 빼고(로컬 파일 유지) README 문구를 사실대로 고친 뒤 새 이력으로 다시 만들고, GitHub 저장소를 삭제 후 같은 이름(Private)으로 재생성해 push한다
- [ ] #3 coding-style: OCR 캐시와 책 목차 파생 파일을 빼고 같은 방식으로 재생성한다
- [ ] #4 omnivim: official_sources를 빼고 MIT→AGPL-3.0-only로 바꾼 뒤 같은 방식으로 재생성한다
- [ ] #5 handcrafted-java: jls-spec을 빼고 .gitignore 모순을 고친 뒤 같은 방식으로 재생성한다
- [ ] #6 databases: 책 기반 데이터(scripts/content*_data 등)를 빼고 같은 방식으로 재생성한다
- [ ] #7 central-docs-collector, ebpf-wire-to-code-tracer, freeride 루트에 AGPL-3.0 LICENSE와 .gitignore 보강을 커밋한다(ebpf의 미커밋 변경은 건드리지 않음)
- [ ] #8 재생성한 5곳의 새 이력(git rev-list --objects --all)에 서드파티 경로·PDF가 0이고 gitleaks가 no leaks(또는 확인된 오탐만)임을 기록한다
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 모든 백업 bundle verify 통과 로그를 Implementation Notes에 첨부
- [ ] #2 재생성 저장소마다 gh repo view로 Private·새 커밋 수를 확인
- [ ] #3 로컬의 무시된 원본 파일(책 코드 등)이 삭제되지 않고 남아 있음을 확인
<!-- DOD:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
### Subjective
유저가 공개 전환을 전제로 라이선스 이슈를 헤더 적용보다 먼저 모두 정리하라고 했다. 필요하면 .git을 삭제하고 ignore하라고 승인했고, 이력 재생성 4곳은 GitHub 저장소를 삭제 후 같은 이름으로 재생성, databases도 재생성하기로 정했다(2026-10-31).

### Objective
감사 결과는 Description 표. 재생성 대상 5곳 모두 PR·태그·해시 참조가 0이고 커밋은 34/2/23/5/2개다. backlog 저장소는 pre_commit_check 때문에 그 저장소 task 브랜치에서만 커밋할 수 있다.

### Assessment
filter-repo로 경로 목록을 맞추는 것보다, 로컬 파일은 유지한 채 .gitignore로 빼고 새 init 하는 편이 단순하고 누락 위험이 낮다. 재생성 후 첫 커밋에 LICENSE·.gitignore·.mailmap을 함께 넣는다. 공개 전환 자체는 이 카드에서 하지 않는다.

### Plan
1. 대상 전체 git bundle 백업(~/githubs-backup/2026-10-31/) + verify
2. 재생성 5곳: .gitignore 보강 → README·LICENSE 정리 → 추적 대상 목록을 미리 출력해 서드파티 경로가 0인지 확인 → .git 삭제 → git init → 첫 커밋 → gh repo delete → gh repo create(Private) → push
3. 문제없는 3곳: LICENSE + .gitignore 커밋
4. 전체 gitleaks·서드파티 경로 재검사 → Implementation Notes
<!-- SECTION:PLAN:END -->
