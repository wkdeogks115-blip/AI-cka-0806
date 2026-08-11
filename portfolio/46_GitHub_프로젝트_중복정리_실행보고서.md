# GitHub 프로젝트 중복정리 실제 실행 보고서

기준: 2026-08-12 08:19 KST

## 결론

현재 접근 가능한 저장소 8개를 직접 읽어 역할을 재분류했다.

최종 방향:

- **유지 5개**
- **ORCA 통합 대기 Satellite 1개**
- **폐기/Archive 후보 2개**
- 지금은 Repository 삭제/강제 병합을 하지 않는다.
- 기존 자산을 먼저 쓰고, 새 Repository는 만들지 않는다.

## 판단

### KEEP — 읽어드림
`wkdeogks115-blip/rkskekfk123`

읽어드림 Figma/디자인 Source Truth를 보존하는 독립 제품 저장소다. AI 오케스트레이션/ORCA/DH와 실질 역할이 다르므로 통합하지 않는다.

### KEEP — DH 실제 사이트
`wkdeogks115-blip/dh-setup-center-web`

실제 DH 정적 홈페이지 source와 QA/배포 후보를 보관한다. Private 유지가 맞다.

### KEEP_SEPARATE — DH Control Archive
`wkdeogks115-blip/DH-`

실제 사이트 source가 아니라 AI continuity/Control Archive다. `dh-setup-center-web`과 내용 일부가 겹쳐 보여도 책임이 다르다.

권장:
- `dh-setup-center-web` = 실제 source
- `DH-` = control/evidence/continuation

따라서 둘을 한 저장소로 합치지 않는다.

### KEEP — AI 오케스트레이션 연구소
`wkdeogks115-blip/AI-cka-0806`

Portable v2 / Factory B / evidence chain의 연구 저장소다. 제품 저장소와 통합하지 않는다. 이번 Portfolio Audit의 비파괴 기록 위치로 재사용한다.

### KEEP_CANONICAL_ORCA
`wkdeogks115-blip/orca-ai-cowork-runtime-`

ORCA 전체 governance/handoff/runtime-design 쪽의 Canonical 후보로 둔다.

### MERGE_LATER_THEN_ARCHIVE_CANDIDATE
`wkdeogks115-blip/orca-ai-token-efficiency-multiai-cowork-v3`

ORCA 전체 시스템이라기보다 Antigravity usage bridge / token-efficiency patch와 evidence에 특화되어 있다.

현재 1.4.176 runtime 검증이 HOLD이므로 지금 통합하면 검증된/미검증 상태가 섞인다. 따라서:

1. 지금은 유지.
2. 1.4.176 실제 검증 완료.
3. 검증된 delta만 `orca-ai-cowork-runtime-`의 적절한 patch/evidence/archive 구조로 이동.
4. readback/hash 확인.
5. 그 뒤 Satellite repo archive/retire 여부 결정.

### RETIRE_CANDIDATE
`wkdeogks115-blip/bochanco-orca-house`

현재 README 1개뿐인 ORCA stub이다. 이미 ORCA canonical 후보가 있으므로 새 ORCA 작업을 이 저장소에서 시작하지 않는다.

### RETIRE_CANDIDATE
`wkdeogks115-blip/-`

현재 empty repository다. 새 작업 대상에서 제외한다.

## 목표 Portfolio

```text
GitHub
├─ 읽어드림
│  └─ rkskekfk123                        KEEP
│
├─ DH
│  ├─ dh-setup-center-web                KEEP / SOURCE
│  └─ DH-                                KEEP / CONTROL ARCHIVE
│
├─ AI 연구
│  └─ AI-cka-0806                        KEEP
│
└─ ORCA
   ├─ orca-ai-cowork-runtime-            KEEP / CANONICAL
   ├─ orca-ai-token-efficiency...        TEMP SATELLITE → MERGE LATER
   ├─ bochanco-orca-house                RETIRE CANDIDATE
   └─ -                                  RETIRE CANDIDATE
```

## 지금 실행하는 것

- 새 Repository 생성: 하지 않음
- Repository merge: 하지 않음
- Repository delete: 하지 않음
- ORCA canonical 역할: `orca-ai-cowork-runtime-`로 고정 Candidate
- token-efficiency repo: 검증 완료 전 Satellite 유지
- `bochanco-orca-house`, `-`: 신규 작업 금지/폐기 후보
- 이 Portfolio 판단은 `AI-cka-0806`의 별도 Candidate branch/Draft PR에 기록

## 다음 실제 Gate

가장 먼저 할 가치가 있는 통합은 ORCA 두 저장소다.

하지만 `orca-ai-token-efficiency-multiai-cowork-v3`의 1.4.176 후보가 아직 unit/typecheck/bundle/runtime UI 검증 HOLD이므로, 현재는 파일을 옮기지 않는다.

이 검증이 실제로 완료된 뒤 **검증된 delta만** canonical ORCA 저장소로 옮기는 것이 가장 안전하다.
