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

## 2026-10-13 dev/prd 브랜치와 로컬 테스트 재개
- 사용자 요청: 기능별 `feature/* → dev → prd`, dev 통합 테스트, prd 운영 버전. 운영 서버가 없으므로 이번에는 로컬로 실행한다.
- `dev`, `prd`를 기존 커밋에서 생성하고 원격에 push했다. GitHub 기본 브랜치를 dev로 변경하고 merge commit 방식을 사용한다. main은 과거 이력으로 보존한다.
- `feature/branch-workflow`에서 브랜치 규칙 문서와 ARM64 GitHub Actions 검증을 준비했다. 원격 보호 규칙은 실제 CI 결과 확인 후 설정한다.
- Docker Desktop을 시작했다. Docker는 aarch64, 메모리 약 8GiB, 12 CPU다.
- 준비를 재개했으나 KR ADM1(저해상도 Natural Earth 기반)과 ADM2(다른 출처) 경계 불일치로 228개 중 39개 ADM2가 부모 중첩률 80%를 통과하지 못했다. 임의 부모를 할당하지 않는다. 이 원인 해결 후 지리를 번들링한다.
- npm audit에서 높은 심각도 6개를 확인했다. 프런트 실행 준비와 함께 기존 빌드 의존성을 점검한다. 전체 서비스 검증은 아직 시작하지 않았다.

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

## 2026-10-13 실제 로컬 서비스 연결 통과·화면 수정 대기
- 컨테이너 CA 수정 PR #3을 dev에 병합했다. API·수집기·Spark·프런트 4개 이미지의 linux/arm64 빌드가 완료됐다.
- `docker compose --profile ingest up -d --wait` 성공. Redis/Kafka/API/프런트/수집기/Spark가 실행되고 Kafka 초기화 컨테이너는 exit 0이다. `http://localhost:8080/api/health`는 200이다.
- 실행별 신규 데모 URL을 Kafka로 보냈으며 `scripts/check_pipeline.py`가 Kafka→Spark→Redis→FastAPI→프런트 proxy 전달 성공을 확인했다. 직접 Redis에 seed한 결과가 아니다.
- 대기 상태 메모리 확인: Spark 약 456MiB, Kafka 약 410MiB, API 45MiB, 수집기 38MiB, Redis 11MiB, 프런트 10MiB. 본격 부하 테스트 수치는 아니다.
- GDELT DOC 첫 호출은 HTTP 429였다. 우회하거나 재호출 폭주하지 않으며, 현재 화면 검증은 명시적으로 표시한 데모 기사로 진행한다.
- 브랜치 workflow PR #4와 GitHub ARM64 CI가 실행 중이었다. Branch policy는 통과했고 Validate 최종 결과는 아직 확인하지 않았다. CI 완료 후 dev/prd의 필수 검사·PR·force push/삭제 금지 보호를 설정해야 한다.
- 로컬 Chrome 초기 캡처는 만들었으나 대륙 일부가 빠져 보이는 문제를 사용자가 확인했다. 중국/러시아/한국/일본 등 원본 폴리곤은 존재하고 유효하며 모든 좌표는 2차원이다. 렌더링 원인 진단과 수정·화면 재검증이 남았다.
- 세션 권한이 다시 제한 모드로 변경돼 Docker socket과 Git 인증 접근이 차단됐다. Docker/Chrome 권한 상승 요청은 실행 결과 없이 대기했다. 서비스가 종료됐다는 증거는 없다. 권한이 복구되면 새 feature/globe-rendering 브랜치에서 화면 문제부터 재개하고 PR #4/보호 설정을 마무리한다. 현재 진행 기록 변경은 아직 커밋하지 않았다.

## 2026-10-13 권한 복구와 지구본 렌더링 수정
- Full access 복구 후 컨테이너 6개가 계속 실행 중임을 확인했다.
- GitHub ARM64 CI 실행 38349758487은 Branch policy/Validate 모두 성공했다. PR #4를 dev에 병합했고 dev/prd에 GitHub Actions의 두 필수 검사, 최신 base, PR 필요, 관리자 포함 보호, force push/삭제 금지를 적용했다.
- `feature/globe-rendering`에서 화면 문제를 재현했다. 브라우저가 terrain-clamped polygon의 outline 미지원 경고를 남겼다. 현재 ellipsoid globe에는 경계의 일반 폴리곤 렌더링을 적용하고 실제 캡처로 비교 중이다.
- 최종 화면 수정: 경계는 높이 0의 일반 폴리곤으로 표시하고, Cesium 1.131.0에 포함된 Natural Earth II 정적 저해상도 타일(level 0–2)을 사용한다. 국가 선택은 렌더러의 bounding sphere 계산이 PENDING에 머물던 Entity flyTo 대신 실제 경계 좌표의 Rectangle로 직접 이동한다. 새 지도 서비스나 지형 의존성은 추가하지 않았다.
- 로컬 Chrome 검증 통과: 대륙/국가 경계, 한국 확대, 초기 ADM0만 로드, ADM1/ADM2 lazy load와 부모 필터, 클릭 카드/안전한 원문 링크, UI 언어와 저장, 모바일 레이아웃. 프런트 수정 후 브라우저 오류·경고는 없었다. Docker의 localhost:8080에서도 기본 화면 검사를 통과했다.
- Docker Desktop credential helper가 공개 이미지 metadata 조회에서 멈춘 것은 임시 익명 Docker 설정(.runtime 내부)으로 해결했다. 기존 Docker 자격 증명을 변경하지 않았다. 수정 프런트 linux/arm64 이미지 빌드와 컨테이너 교체를 완료했다.
- 코드·이미지·지역 번들 검증은 완료했다. 현재 운영 서버가 없으므로 prd는 보호된 운영 후보 브랜치로 유지하며 실제 배포를 하지 않는다. GDELT 429와 39개 미확정 ADM2 제외는 현재 한계다. 이후 기능은 dev에서 새 feature 브랜치를 만들어 진행한다.

## 2026-10-13 지도 확대·지역명 개선
- `feature/map-detail-labels`에서 국가 경계를 Natural Earth 5.1.2 50m로 올렸다. ISO 국가 코드 236개, feature 238개, 국가 파일 1,677,683바이트다. 기존 geoBoundaries ADM1/ADM2 ID와 검증된 부모 관계를 유지한다.
- 가까이 확대하면 저해상도 래스터를 숨기고 벡터 폴리곤·색상별 국가/ADM1/ADM2 경계를 표시한다. 확대 단계에 맞춰 내부 대표점에 국가·지역명을 표시하며, 라벨 좌표는 뉴스 위치와 분리한다.
- 한국어 국가명·광역시/도·포함된 서울 구 이름을 제공한다. 뉴스 목록·hover·클릭 카드에는 검증된 위치 이름만 표시한다. 수도 fallback 뉴스는 보도 지역을 국가 수준으로 유지한다.
- 소스가 공유하는 FIPS NT는 ISO 매핑이 모호해 제외하고 manifest에 기록한다. 한국의 미확정 ADM2 39개 제외는 유지한다.
- 통합 검증의 Python 구문·Node 위치 표시 테스트·프런트 빌드·YAML/Compose/Kustomize·격리 Redis/API/지리 테스트 3개가 통과했다. Docker npm 네트워크 실패 후 불필요한 package.json 변경을 제거하고 기존 의존성 설치 레이어를 재사용해 4개 ARM64 이미지 빌드를 완료했다. 한국어 구 이름 추가 후 영향받은 Node 검사와 프런트 이미지만 다시 확인했다.
- 6개 Docker 서비스 교체와 신규 데모 URL의 Kafka→Spark→Redis→API→프런트 proxy 전달을 통과했다. 실제 Chrome에서 ADM0 초기 로드·ADM1/ADM2 lazy load·부모 필터·보도 지역 표시·안전한 기사 링크·언어 저장·모바일·마커 hover/click을 확인했다. 마커 검사는 카메라 이동 뒤 뉴스 요청 완료를 기다리도록 수정했다.
- 실제 확대 캡처에서 경계 가림과 라벨 밀도를 확인한 뒤 polyline을 폴리곤과 같은 geodesic으로 맞추고 표시 높이를 200m만 추가했다. 작은 ADM1 라벨은 면적에 맞는 확대 단계에서 나타난다. 모바일에서는 화면 너비에 맞춰 국가·ADM1 라벨 밀도를 줄인다. 영향받은 프런트 이미지·지도 화면 검사를 다시 확인했다.
- 로컬은 Docker localhost:8080에서 실행 중이다. PR의 필수 ARM64 CI 통과 후 dev 병합 단계이며 prd 배포는 하지 않는다.

## 2026-10-13 온라인 상세 배경·라벨 스타일
- 지도/지역명 PR #6은 최종 ARM64 CI 38358233686의 Branch policy/Validate를 통과하고 dev에 merge commit `5336029`로 병합했다.
- 사용자가 지도 교체 대화와 함께 온라인 상세 배경 허용 및 라벨 배경 박스 제거를 요청했다. `feature/map-imagery-style`에서 Cesium/OSM 공식 문서와 타일 사용 정책을 확인했다.
- 토큰 없이 바로 사용 가능한 OSM을 확대 배경으로 적용한다. 전 지구 화면은 기존 로컬 타일이며, 화면 밖 선행 다운로드를 끄고 level 13까지 필요한 타일만 브라우저에서 받는다. 한국 경계 파일과 뉴스 좌표는 그대로 유지한다.
- `VITE_CESIUM_ION_TOKEN`을 제공하면 Cesium AERIAL 배경을 사용하도록 연결했다. 토큰이 없는 현재 환경에서는 위성 서비스 성공을 주장하지 않으며 OSM을 검증한다.
- 지역명 뒤 사각형을 제거하고 밝은 배경에 어두운 글씨/얇은 흰색 halo, 어두운 배경에 밝은 글씨/얇은 어두운 halo를 적용한다. 배경 위 폴리곤 tint도 낮춰 실제 지도 내용을 보존한다.
- 프런트 이미지 빌드·Compose 설정 검사가 통과했다. 최초 연결 검사는 `ImageryLayerCollection.add()`가 반환값이 없는 것을 수정했다. 확대 검사는 실제 OSM 응답 200을 확인했지만 화면 중앙 줌에서 Cesium 1.131의 zero-axis 정규화 오류로 렌더링이 중단됐다. Unminified 엔진 스택이 `handleZoom → Camera.rotate → Quaternion.fromAxisAngle`인 것을 확인하고, 해당 카메라의 길이 0 회전만 no-op 처리했다. 수정 프런트 ARM64 이미지와 Docker 컨테이너 교체를 완료했다. Docker localhost:8080에서 실제 OSM level 13 타일 응답 200, 중앙 휠 확대, ADM2 계층, 출처 표시, 모바일, 외부 타일 중단 시 로컬 fallback이 통과했고 console/page/렌더 오류는 없었다. 같은 구성의 Unminified 개발 화면에서도 재현 검사가 통과했다. 뉴스/저장 구성은 바뀌지 않아 기존 파이프라인 검증을 반복하지 않는다. 필수 CI 통과 후 dev에 병합한다.

- 마지막 화면 확인에서 비동기 경계 생성 완료 전에 렌더 요청이 끝나는 경우를 확인했다. 데이터 소스가 준비 중이거나 ready로 전환하는 프레임에만 렌더를 요청하고, 경계선은 ground-clamped polyline과 고정 색상으로 표시한다. 준비 후 idle 렌더 모드는 유지한다. 영향받은 프런트 이미지와 확대/모바일/fallback 검사는 다시 통과했다.

## 2026-10-14 GDELT 호출 제한 처리
- 사용자 제보와 기존 수집기 로그를 확인했다. DOC 호출은 기본 약 15분 간격이고 HTTP 429가 반복됐다. HTTP 200이라고 본문이 정상 JSON이라는 보장은 없으며, 단일 컨테이너가 5초 미만으로 DOC를 반복 호출했다는 증거는 없다.
- `feature/gdelt-backoff`에서 HTTP 200 제한 안내와 HTTP 429를 명시적으로 분류한다. 기본 간격의 지수 대기(900→1800→3600초), 숫자/HTTP-date Retry-After 존중, 성공 후 대기 초기화와 GDELT만 건너뛰는 처리를 추가했다. RSS 주기는 유지하며 빈 DOC 결과에서는 GKG 네트워크 요청을 생략한다.
- 응답 분류·최소 간격·지수 대기·정상화·RSS 유지·긴 Retry-After를 모의 HTTP/시계로 확인한다. 추가 실제 API 시험 호출은 하지 않는다. 수정 수집기 이미지와 dev 통합 검증을 진행한다.
- 영향받은 격리 Redis/API/수집/지리 검사 5개가 모두 통과했다. 일반 Dockerfile의 수집기 linux/arm64 빌드와 컨테이너 교체도 성공했다. 새 컨테이너의 첫 DOC 요청은 여전히 HTTP 429였고 `retry in at least 900s`를 기록해 오류를 정상적으로 대기 처리했다. 제공자 제한이 해제됐거나 실제 기사 수집이 성공했다고 주장하지 않는다.
