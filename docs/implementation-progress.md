# 구현 진행 기록

마지막 갱신: 2026-10-13. 중단 후 이 파일과 git 상태를 확인해 첫 미완료 단계부터 재개한다.

## 요청과 승인
- AGENTS.md와 project-draft.md 기반 프로젝트 구현.
- 최상위 kafka/, spark/, redis/ 분리. 단순한 역할별 코드, 과도한 추상화 금지.
- 최종 검증을 한 사이클로 진행하고, 실패 수정 후 관련 검사만 다시 실행한다.
- Python/FastAPI, Kafka KRaft, Spark 4.0.2 local[1], Redis 단독 뉴스 저장, React/Cesium, ARM64/K3s.
- 최초 수집 기준 604800초 만료. 정적 지리와 뉴스 분리.
- 사용자는 로컬 설치·다운로드·Docker 검증, 준비 실행의 SSL 검증 생략, 작업물 커밋 및 origin으로 푸시를 명시적으로 승인했다. 이 범위는 재확인하지 않는다. 실행 환경의 권한 제한을 우회하거나 미승인 작업을 승인했다고 가정하지 않는다.

## 완료한 작업
- Python 기사 모델, URL ID, 지리 검증, Redis Lua 멱등 저장·7일 만료·인덱스, FastAPI.
- DOC/RSS 수집, 제한된 GKG 국가 언급 보완, Kafka 토픽 설정, 단일 Spark 처리기.
- React/Cesium UI, 호버/클릭 미리보기, 언어 선택, 단계별 지리 로드 코드.
- 지리 다운로드·가공·버전/라이선스 기록 스크립트.
- Compose, 역할별 이미지, K3s 배포·운영 문서, 핵심 Redis/API 검증 사이클.
- Python/npm 의존성과 uv.lock, frontend/package-lock.json 생성.
- TERRA_SKIP_TLS_VERIFY=1은 이번 준비 실행에만 uv/npm/지리 빌더 TLS 검증을 생략한다. 기본 서버·수집기 설정은 유지한다.
- Docker 빌더의 uv는 실제 잠금 파일 생성 버전 0.12.9에 고정했다.

## 실제 검증 결과
- Python 구문: 통과.
- 프런트 production build: 통과, 5.98초.
- YAML parse / Docker Compose config / K3s Kustomize render: 통과.
- 첫 빌드의 ZIP exports 오류는 고정 Cesium 1.131.0의 공식 사전 빌드 ESM 진입점으로 수정했다.
- 프런트 산출물: 380개 파일 / 10.68MiB. 미생성 지리 파일은 제외한 수치다.
- JS 번들: 4,443.89kB / gzip 1,243.79kB. 크기/eval 경고가 있다. 실제 WebGL 상호작용은 아직 미검증.
- Redis/Lua/API 핵심 사이클: 격리 포트 bind가 sandbox에서 차단되어 시작하지 못했다.
- Kafka→Spark→Redis→API 실제 연결, ARM64 컨테이너 실행: 아직 미검증.
- 지리 생성: sandbox DNS 오류로 미완료. regions.json과 geo manifest가 아직 없다. 실행 준비 완료나 전체 테스트 통과로 보고하면 안 된다.

## 현재 실행 상태
- 최신 요청에 맞춰 README를 준비 → 화면/API 데모 → Kafka/Spark 순서로 갱신했다. `setup.sh`가 TLS 생략 옵션·캐시 재사용·지리 생성·없는 .env 복사를 담당하고 complete-local.sh가 이를 재사용한다.
- .gitignore/.dockerignore는 실제 env·인증서/개인키·AWS 자격 증명을 제외하고 .env.example은 명시적으로 허용한다. 사용자 요청에 따라 안전한 프로젝트 파일은 모두 커밋한다.
- 파이프라인 검증은 실행별 고유 데모 URL로 기존 Redis 데모 데이터의 잘못된 통과를 방지하고, 실제 Compose 웹 포트를 조회한다. 이 변경의 구문 검사는 마지막에 묶어서 진행한다.
- 마지막 준비 재시도(session 7887)는 Python/npm 단계 성공 후 지리 다운로드에서 DNS 차단으로 종료했다.
- git add는 .git/index.lock 생성 권한 제한으로 실패했다. 아직 이번 작업의 커밋과 푸시는 완료하지 않았다.
- 기존 사용자 파일 .idea/와 AGENTS.md를 삭제하거나 되돌리지 않는다. 캐시·비밀 값·빌드 결과·node_modules는 커밋하지 않는다.
- 현재 브랜치 main, origin은 https://github.com/jaemanc/terra-newsphere.git 이다.
- 이전 통합 요청 cell 60은 응답이 없어 종료했다. 사용자 최신 요청에 따라 README·준비 스크립트·ignore 규칙을 정리하고 직접 git add/commit/push를 실행한다. 명령 결과의 커밋 SHA와 push 성공을 확인하기 전 완료로 보고하지 않는다. `.runtime/`는 커밋하지 않는다.
- 직접 `git add --all && git diff --cached --check && git commit ... && git push origin main` 실행 요청은 cell 72에서 응답 대기 중이다. 확인된 HEAD는 아직 `754525a Initial commit`이다. 커밋/푸시 성공으로 보고하지 않는다.
- 변경한 setup/complete-local shell 구문, seed_demo/check_pipeline/verify Python 구문 및 git diff 공백 검사 통과. 실제 env와 node_modules가 제외되고 .env.example이 포함되는 것을 git 목록으로 확인했다. 이미 통과한 프런트 빌드·배포 설정은 반복하지 않았다.

## 남은 작업과 재개 명령
### 2026-10-13 재개 확인
- 현재 파일과 git 상태를 다시 확인했다. `frontend/public/geo/`와 `geo/generated/regions.json`은 아직 없고, HEAD는 `754525a`다.
- `git diff --check`는 통과했다. 기존 빌드·설정 검사 결과를 재사용한다.
- `TERRA_SKIP_TLS_VERIFY=1 TERRA_VERIFY_SERVICES_ONLY=1 sh scripts/complete-local.sh`를 sandbox 밖 실행 권한으로 요청했다. 실행 결과가 아직 반환되지 않았으므로 다운로드·서비스 검증·커밋·푸시 완료로 보고하지 않는다.

1. 정적 지리 생성 후, 이미 통과한 빌드/설정 검사를 건너뛰고 서비스 검사만 재개한다.
2. 검증 결과를 정확히 기록한 작업물을 커밋하고 origin/main에 푸시한다.
3. 실제 서버 배포는 아직 하지 않는다.

```sh
TERRA_SKIP_TLS_VERIFY=1 TERRA_VERIFY_SERVICES_ONLY=1 sh scripts/complete-local.sh
```

현재 준비 단계는 .runtime/setup-stage.txt에 기록된다. uv/npm 캐시와 완성된 지리 파일을 재사용한다. 파일이 작성된 뒤 중단됐으면 다시 생성하지 말고 실제 존재 여부부터 확인한다.

## Vercel 관련 확인
Hobby의 2 vCPU / 8GB / 32GB는 빌드 자원이다. 프런트만 Vercel에 두고 FastAPI·수집기·Kafka·Spark·Redis는 Oracle Cloud에서 실행하는 구성을 설명했다. Vercel 배포나 API 라우팅 변경은 하지 않았다. 공식 문서와 관련 판단은 docs/operations.md에 있다.

## 2026-10-13 커밋·푸시 재개
- 사용자 요청으로 현재 구현 파일의 커밋과 origin/main 푸시를 재개한다. 시작 시 HEAD는 `754525a`이고 브랜치는 main이다.
- Git 포함 대상 목록과 ignore 규칙을 확인했다. 실제 .env, 자격 증명 파일, .runtime, node_modules, 빌드 산출물은 제외하고 .env.example은 포함한다.
- 기존 검증 결과를 유지한다. 지리 생성과 실제 서비스 연결 검증은 여전히 미완료이며, 이번 커밋·푸시 요청에서 다시 실행하지 않는다.
- 아래의 과거 실행 대기 기록은 성공 증거가 아니다. 이번 Git 명령의 종료 상태와 원격 HEAD로 커밋·푸시 결과를 확인한다.
- 사용자가 Git 권한 요청을 승인하고 푸시를 다시 명시적으로 요청했다. 현재 포함 대상과 ignore 규칙, `git diff --check HEAD`를 확인했다. 실제 Git 쓰기/네트워크 권한이 필요하면 실행 도구의 승인 절차로 요청한다.
- 이번 `git add --all`도 `.git/index.lock: Operation not permitted`로 실패했다. 권한 상승 요청을 두 번 보냈으나 결과가 반환되지 않았고, 사용자는 승인 창이 표시되지 않았다고 알렸다. 대기 요청을 종료했다. 커밋과 푸시는 아직 미완료다. 권한 변경 후 이 단계부터 재개한다.
- 사용자가 Full access로 전환했다. 실행 환경도 전체 파일 접근과 네트워크 허용으로 변경된 것을 확인했다. 위 실패 기록은 전환 전 결과이며, 현재 작업물을 커밋하고 origin/main으로 푸시하는 단계부터 재개한다.

## 2026-10-13 커밋·푸시 완료
- Full access 전환 후 `git add --all`이 성공했다. 새 파일 끝의 불필요한 빈 줄을 제거한 뒤 `git diff --cached --check`가 통과했다.
- 구현 커밋: `7eb18af8806bb2a9a773d22ba21c9a1d205d2d46` (`feat: add globe UI and news ingestion pipeline`).
- `git push origin main`이 성공했다. `git ls-remote origin refs/heads/main`으로 원격 SHA가 구현 커밋과 일치하는 것을 확인했고, 작업 트리는 깨끗했다.
- 위 Git 권한 실패·미완료 기록은 과거 결과다. Git 커밋·푸시 작업은 완료했으며, 남은 구현 검증은 정적 지리 생성과 실제 서비스 연결/ARM64 실행 검증이다. 이번 요청에서는 이를 다시 실행하거나 서버를 배포하지 않았다.

## 2026-10-13 정적 지리 번들 완료
- `feature/static-geography`에서 실제 원본의 ADM1/ADM2 불일치를 확인했다. 부모 중첩률이 80% 미만인 ADM2는 임의 할당하지 않고 제외 목록을 manifest에 기록한다. 정상 경계 전체 생성을 중단하던 동작을 수정했다.
- 생성 결과: 국가 경계 174개, 한국 ADM1 17개/ADM2 189개, 미확정 ADM2 39개. GeoJSON 합계 510727바이트. 버전·출처·라이선스·SHA256과 서버용 매핑을 함께 버전 관리한다.
- 한국 ADM2 원본 라이선스는 CC BY 3.0임을 확인하고 출처 문서를 수정했다. 전체 구·군 지원으로 표현하지 않는다.
- 실제 Redis/API와 Kafka/Spark 연결 검증은 다음 dev 통합 단계에서 한 번에 진행한다.

## 2026-10-13 로컬 실행 준비
- `feature/local-runtime`에서 Vite를 수정 버전 6.4.4로 고정하고 `vite-plugin-static-copy`를 제거했다. Cesium 자산은 Node 표준 `fs`로 dev/build 전에 복사한다. 생성 자산은 Git·Docker 입력에서 제외한다.
- 의존성 설치의 npm audit 결과는 취약점 0개다. dev 서버와 preview는 localhost에만 바인딩한다.
- 준비 명령을 완료해 Python/npm과 버전 관리된 지리 번들을 사용할 수 있다. 테스트·ARM64 이미지 빌드·전체 파이프라인 검증은 dev 통합 뒤 진행한다.

## 2026-10-13 dev 통합 검증과 컨테이너 수정
- 지리 PR #1과 로컬 실행 준비 PR #2를 dev로 merge commit 병합했다.
- dev 검증: Python 구문, Vite 6.4.4 프런트 빌드(9.53초), YAML/Compose/Kustomize, 실제 격리 Redis의 뉴스 사이클·계층 검사 2개 모두 통과했다. 프런트 번들 크기/eval 경고는 남아 있다.
- 컨테이너 의존성 설치는 로컬 네트워크 CA 미신뢰로 실패했다. `feature/container-runtime`에서 기존 시스템 trust store에 있는 CA와 일치하는 인증서만 선택하고, 선택적 BuildKit secret으로 설치하도록 수정했다. 기본 TLS 검증을 끄지 않는다. 인증서 파일은 .runtime에만 보관한다.
- 컨테이너 빌드 재개 중이다. 이미 통과한 Python/프런트/Redis 전체 사이클은 반복하지 않고 수정한 이미지와 서비스 연결 단계만 이어간다.
