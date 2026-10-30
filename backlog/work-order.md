<!-- work-order-hash: 95ab7a513f6beb26d017cd7b66c1a29f3f7a7b23b554dbb924b591ea47cdaf09 -->
# 작업 순서

`work_order.py`가 backlog/tasks의 의존(`dependencies`)으로 만든 파일이다 — 직접 고치지 말고 다시 생성한다. 같은 단계의 태스크는 병렬로, 단계는 위에서 아래로 순차로 진행한다. Done 태스크와 없는 태스크에 대한 의존은 충족된 것으로 본다.

| 단계 | ID | 제목 |
|---|---|---|
| 1 | TASK-2 | source-header 2단계: hook pre-commit 진입점 · bin 링크 · LICENSE |
