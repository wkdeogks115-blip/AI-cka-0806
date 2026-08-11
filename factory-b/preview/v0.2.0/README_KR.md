# Factory B v1 바로사용 체험판 PREVIEW v0.2.0

이 패키지는 **페이지/세션이 끊겨도 바로 다시 사용할 수 있는 독립형 UX 체험판**이다.

## 상태
- `PREVIEW_READY`
- `STANDALONE_RESTARTABLE`
- `UX_REHEARSAL_ONLY`
- `NOT_ACTIVATION_EVIDENCE`
- `NO_EXTERNAL_WRITE`

## v0.1.0 대비 핵심 변경
v0.1.0은 옆 폴더의 Factory Candidate ZIP을 hash-lock으로 요구했다.
v0.2.0은 **외부 ZIP 없이 Python 표준 라이브러리만으로 실행**된다.
따라서 현재 ChatGPT 페이지가 끊겨도 이 ZIP 하나로 흐름을 재개할 수 있다.

단, 이 내부 규칙은 **체험용 스냅샷**이다. Canonical Factory Runtime이나 ACTIVE 증거가 아니다.
Live CURRENT와 GitHub frozen evidence가 접근 가능하면 그것들이 상태의 우선 기준이다.

## 30초 사용
### 새 ChatGPT 페이지
이 ZIP을 첨부하고 `새페이지_한줄재개.txt`의 한 줄을 사용한다.

### PC에서 바로 체험
- `START_HERE.html`을 브라우저에서 연다. 서버/설치 불필요.
- 또는 Python 3가 있으면:
  `python -B run_preview.py examples/01_skill_idea.json`

## 체험 흐름
`아이디어 → Artifact Type → Assetization → 6W+ 초안 → Implementation Handoff → LOCAL Preview`

실제 실행하지 않는 것:
- 실제 Codex/External Agent
- GitHub/Drive write
- Production/Public release
- Final Approval
- Portable State write
- ACTIVE 승격

## 현재 live proof links
- CURRENT: https://docs.google.com/document/d/1-jaUDcVtj0jtNDz4SR9MMIv_ewIWNUAwO0vHkmSt4kQ/edit?usp=drivesdk
- F6.2 PR #14: https://github.com/wkdeogks115-blip/AI-cka-0806/pull/14
- External Proof Gate #15: https://github.com/wkdeogks115-blip/AI-cka-0806/issues/15
- F5 Transfer PR #10: https://github.com/wkdeogks115-blip/AI-cka-0806/pull/10

## Source references
- Minimal Factory Contract v0.2.1 SHA-256: `a168ce214c93059e1b9986fe831646a61356b029ec72a397025df45e7efbd709`
- Answer Pack v2.0.1 SHA-256: `98ebc18670ee2a0faf487fab6b95ba1247bc841fe4c419344a951cb2b1af3d96`

답변팩은 전체 Runtime으로 이식하지 않고 VISIBLE_RESULT_LOOP / Artifact Release /
Coverage Handoff / GitHub Adoption / Simulation Failure / Promotion Gate 원칙만 선택 참조한다.
