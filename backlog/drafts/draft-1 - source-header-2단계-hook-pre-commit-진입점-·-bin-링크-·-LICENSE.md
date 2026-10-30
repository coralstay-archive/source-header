---
id: DRAFT-1
title: 'source-header 2단계: hook pre-commit 진입점 · bin 링크 · LICENSE'
status: Draft
assignee: []
created_date: '2026-10-30T19:31:00Z'
updated_date: '2026-10-30T19:32:00Z'
labels:
  - tool
  - hooks
dependencies: []
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
## 배경
계획 2단계(2026-10-31 변경본). git 훅 연결은 coding-agent-git-commit-tool DRAFT-22가 `.githooks` + `core.hooksPath`로 맡는다. source-header는 그 디스패처가 부를 진입점만 제공한다.
유저 결정: ~/githubs 아래 코드는 AGPL-3.0-only. 이 저장소에 LICENSE 파일을 추가한다.

## 범위
- `source-header hook pre-commit`: `fix --staged` 후 `lint --staged`를 실행. `.source-header.json`이 없는 저장소에서는 아무것도 하지 않고 exit 0
- `~/githubs/bin/source-header` → `../dev-tools/source-header/source-header.py` 심볼릭 링크 (bin의 다른 항목과 같은 방식)
- LICENSE(AGPL-3.0 전문, 형제 저장소 claude-code-agile-hooks의 LICENSE와 동일), README에 라이선스 절

## 비즈니스 규칙
- B1 (AC #1) fix가 실패(exit≠0)하면 lint를 돌리지 않고 같은 코드로 끝낸다
- B2 (AC #1) .source-header.json이 없는 저장소에서는 검사하지 않는다(opt-in)
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 source-header hook pre-commit이 B1·B2에 따라 fix --staged → lint --staged를 실행하고 그 exit 코드를 돌려준다. 임시 저장소에서 통과·차단·opt-out 세 경우를 테스트한다
- [ ] #2 ~/githubs/bin/source-header 심볼릭 링크가 있고 PATH에서 source-header --help가 동작한다
- [ ] #3 LICENSE(AGPL-3.0 전문)와 README 라이선스 절이 있고, source-header lint .에서 L2 경고가 없다
<!-- AC:END -->
