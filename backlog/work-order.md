<!-- work-order-hash: ea2dce535a0c6cc46404a88e77cc276b59172f52d4c8e25443f50e770ab74efb -->
# 작업 순서

`work_order.py`가 backlog/tasks의 의존(`dependencies`)으로 만든 파일이다 — 직접 고치지 말고 다시 생성한다. 같은 단계의 태스크는 병렬로, 단계는 위에서 아래로 순차로 진행한다. Done 태스크와 없는 태스크에 대한 의존은 충족된 것으로 본다.

| 단계 | ID | 제목 |
|---|---|---|
| 1 | TASK-4 | source-header 적용: dev-tools/central-docs-collector |
| 1 | TASK-5 | source-header 적용: dev-tools/omnivim |
| 1 | TASK-6 | source-header 적용: dev-tools/source-header |
| 1 | TASK-7 | source-header 적용: freeride |
