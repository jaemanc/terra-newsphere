# TerraNewsphere 프로젝트 구조 초안

> 구현 시 사용자 요청으로 `kafka/`, `spark/`, `redis/`를 최상위 디렉토리로 분리했다. 현재 실제 구조와 실행 방법은 README.md를 따른다. 아래는 최초 설계 초안으로 보존한다.

이 문서는 AGENTS.md에 따른 설계 초안이다. 아래 파일과 디렉토리는 앞으로 만들 작업물이며, 현재는 이 문서만 추가한다. 실행 코드, 의존성 설치, 클라우드 배포는 포함하지 않는다.

## 1. 기본 구성

한 저장소에서 관리하고, Oracle Cloud A1 ARM64 VM 한 대의 단일 노드 K3s에 배포한다. Python 코드는 하나의 패키지로 관리하되 API, 수집기, Spark 처리기는 각각 별도 프로세스와 컨테이너로 실행한다.

```text
GDELT / RSS / 허용된 API
          ↓
Python collector
          ↓
Kafka KRaft: news.raw
          ↓
PySpark Structured Streaming: local[1]
          ↓
Redis: 기사 + 지역 인덱스, 최초 수집 후 최대 7일
          ↓
FastAPI
          ↓
React + CesiumJS

Natural Earth / geoBoundaries
          ↓ 빌드 시 정제·단순화
정적 지리 파일 + 동일 버전 위치 매핑 파일
          ↓
프런트엔드 / Spark 위치 검증
```

사용자 조회는 FastAPI와 Redis가 담당한다. Kafka와 Spark는 수집 파이프라인에만 참여한다. 지리 파일은 버전 관리하는 정적 자산으로 배포한다.

## 2. 제안 디렉토리

```text
terra-newsphere/
├── AGENTS.md
├── README.md                       # 개발 실행 방법과 프로젝트 진입점
├── pyproject.toml                  # Python 패키지와 역할별 의존성
├── uv.lock                         # 검증한 Python 의존성 고정
├── .env.example                    # 설정 이름과 예시, 실제 비밀 값 제외
├── .gitignore
│
├── src/terra_newsphere/
│   ├── config.py                   # 환경변수 설정
│   ├── models.py                   # Pydantic 처리 기사 모델
│   ├── urls.py                     # URL 정규화와 안정적 기사 ID
│   ├── geography.py                # 버전 지정 지리 ID·좌표 검증
│   ├── storage/
│   │   ├── redis_news.py           # 멱등 저장, TTL, 지역 인덱스 조회
│   │   └── write_news.lua          # 기사·인덱스 갱신의 원자성 보장
│   ├── api/
│   │   ├── main.py                # FastAPI 앱과 상태 점검
│   │   └── news.py                # 마커 목록·기사 미리보기
│   ├── collector/
│   │   ├── main.py                # 수집 주기, 호출 제한, 재시도
│   │   ├── gdelt.py               # 1차 뉴스 발견
│   │   ├── rss.py                 # 필요한 소스의 메타데이터 보완
│   │   └── producer.py            # news.raw 발행
│   └── processor/
│       ├── main.py                # 단일 Spark 스트리밍 앱
│       ├── normalize.py           # 검증·정규화·중복 처리
│       ├── locations.py           # 보도 장소 해석과 지리 매핑
│       └── sink.py                # 제한된 배치의 Redis 저장
│
├── frontend/
│   ├── package.json
│   ├── package-lock.json
│   ├── src/
│   │   ├── App.tsx
│   │   ├── api/news.ts            # 영역·지역별 조회
│   │   ├── globe/                 # Cesium 초기화·경계·마커·클러스터
│   │   ├── components/            # 호버·클릭 카드, 언어 선택
│   │   └── i18n/                  # 브라우저 언어 감지, ko/en UI
│   └── public/
│       ├── geo/
│       │   ├── manifest.json      # 출처·버전·라이선스·파일 목록
│       │   ├── countries.topojson
│       │   ├── adm1/              # KR.topojson 등 국가별 파일
│       │   └── adm2/              # 필요한 국가만 단계적으로 추가
│       └── images/                # 썸네일 대체 이미지
│
├── geo/
│   ├── sources.json               # 원본 출처·버전·가공 조건
│   ├── licenses/                  # 원본 데이터 라이선스와 저작자 표시
│   └── generated/
│       ├── regions.json           # 지리 ID, 부모 관계, 중심점
│       ├── aliases.json           # 검증한 위치 이름 매핑
│       └── capitals.json          # 국가만 알려진 경우의 표시용 수도
│
├── scripts/
│   ├── build_geo.py               # 지리 파일과 매핑을 같은 버전으로 생성
│   └── seed_demo.py               # 개발용 가상 기사, Redis TTL 적용
│
├── tests/
│   ├── test_parsing.py
│   ├── test_deduplication.py
│   ├── test_locations.py
│   ├── test_expiry.py
│   └── test_api.py
│
├── deploy/
│   ├── docker/
│   │   ├── api.Dockerfile
│   │   ├── collector.Dockerfile
│   │   ├── processor.Dockerfile   # Spark 4.x + Java + Python
│   │   └── frontend.Dockerfile    # 빌드한 UI·지리 파일 정적 제공
│   ├── compose.yaml               # 로컬 개발용
│   └── k3s/
│       ├── kustomization.yaml
│       ├── configmap.yaml
│       ├── secrets.example.yaml   # 템플릿만 저장
│       ├── kafka.yaml             # 단일 KRaft 브로커·지속 볼륨
│       ├── redis.yaml             # 뉴스용 휘발 저장, 영속화 비활성
│       ├── api.yaml
│       ├── collector.yaml
│       ├── processor.yaml         # 1개 프로세스·체크포인트 볼륨
│       ├── frontend.yaml
│       └── ingress.yaml           # HTTPS, /api와 정적 UI 라우팅
│
└── docs/
    ├── project-draft.md
    ├── data-contract.md           # 원시 이벤트·처리 기사·API 계약
    ├── geography.md               # 출처·가공·ID 매핑 규칙
    └── operations.md              # 배포·자원·보존·장애 복구
```

초기 구현 때 필요한 파일부터 만든다. 별도 마이크로서비스 저장소, 범용 플러그인 구조, 다중 Spark 노드는 만들 필요가 없다. API·수집기 이미지에는 Spark 의존성을 설치하지 않도록 역할별 의존성을 분리한다.

## 3. Oracle Cloud 배치

| 구성요소 | 역할 | 저장·노출 방식 |
| --- | --- | --- |
| Ingress + frontend | HTTPS 진입점, UI와 정적 지리 제공 | 브라우저 접근 허용 |
| FastAPI | 현재 뉴스와 미리보기 조회 | Ingress의 `/api` 경유 |
| Redis | 처리 기사와 뉴스 인덱스 | 클러스터 내부 접근, 뉴스 영속화 비활성 |
| Kafka | 수집 버퍼와 제한된 재처리 | 내부 접근, 로그 전용 지속 볼륨 |
| Collector | 외부 소스 수집과 발행 | 내부 실행, 외부 소스로 아웃바운드 |
| Spark processor | 정규화·위치 해석·Redis 쓰기 | `local[1]`, 체크포인트 전용 지속 볼륨 |

Kafka는 KRaft 단일 노드로 구성한다. Spark 처리기도 하나만 실행하며 배포 교체 중 두 처리기가 같은 체크포인트를 사용하지 않도록 한다. 이 구성은 VM 장애 시 전체 서비스가 중단되는 단일 서버 구성이므로 고가용성으로 취급하지 않는다.

VM의 실제 CPU·RAM·디스크 용량을 확인한 뒤 각 컨테이너의 requests/limits, Kafka JVM과 로그 한도, Spark 메모리·배치 크기를 정한다. 모든 이미지와 의존성은 ARM64에서 검증한 정확한 버전으로 고정하며 Spark도 특정 4.x 패치 버전을 고정한다. 이 초안에서는 검증하지 않은 버전이나 자원 수치를 확정하지 않는다.

## 4. 데이터와 조회 설계

- 원시 Kafka 이벤트는 소스 정보, 원본 URL, 수집 시각, 원문 메타데이터와 위치 근거를 담는다. 소스별 입력 형식과 처리 기사 모델은 구분한다.
- URL 정규화로 기사 ID를 만들고, Redis 저장 전에 Pydantic과 버전 지정 지리 데이터로 검증한다. 국가 단위 표시용 수도와 실제 보도 위치는 구분한다.
- `collected_at`은 최초 성공 수집 시각이다. 만료는 항상 이 시각에서 604800초 후이며 재수집·재시도·업데이트로 연장하지 않는다. Kafka 재처리에서도 기존 수집 시각을 사용하며 만료된 이벤트를 되살리지 않는다. 키 만료 이후 중복 재발견 처리 규칙도 구현 전에 데이터 계약에 명시한다.
- 기사와 인덱스 변경은 원자적으로 처리한다. Redis 인덱스는 만료 시각을 점수로 저장하고 조회 시 만료 멤버와 없는 기사 키를 제외한다. 위치 변경 시 기존 인덱스 연결도 제거한다.
- ADM2 기사도 해당 ADM1·국가 인덱스에 연결한다. 여러 위치에 연결된 기사는 응답에서 기사 ID로 중복 제거한다.
- 초기 화면에는 국가별 제한된 마커를 제공한다. 가까운 확대 수준에서는 지역 ID로 조회한다. 좌표 범위 조회가 필요하면 Redis GEO 보조 인덱스로 후보를 찾고 실제 좌표·만료를 다시 확인하며 후보 수를 제한한다. GEO 인덱스의 오래된 연결도 정리한다.
- API 초안은 `GET /api/news/markers`와 `GET /api/news/{news_id}`다. 마커 조회에는 국가·지역·bbox 필터와 결과 제한·페이지 구분을 적용한다. 상세 응답도 간결한 미리보기만 반환한다.
- 호버 정보는 마커 응답의 제목·작은 썸네일로 표시한다. 클릭 시 필요한 미리보기를 조회하고 원문 링크에 `target="_blank"`, `rel="noopener noreferrer"`를 적용한다. 없는 요약이나 번역은 생성된 것처럼 표시하지 않는다.
- UI 언어는 브라우저 선호 언어, 수동 선택, 영어 기본값을 사용한다. 기사 원문 언어와 UI 언어를 분리한다.
- 지구는 기본 타원체와 번들 경계를 사용하고 유료 지도·지형 서비스 의존성을 두지 않는다. ADM0부터 로드하고 ADM1·ADM2는 확대 수준과 화면 영역에 따라 필요한 파일만 로드한다.

Redis 뉴스 persistence와 뉴스 백업은 기본적으로 비활성화한다. Kafka 로그·Spark 체크포인트·앱 로그는 별도 보존 정책을 문서화하고, 원문 이벤트를 불필요하게 로깅하지 않는다. 모든 뉴스 파생 데이터의 엄격한 삭제까지 요구하면 체크포인트와 재처리 정책도 함께 설계해야 한다.

## 5. 단계별 작업물과 완료 기준

| 단계 | 작업물 | 완료 기준 |
| --- | --- | --- |
| 1 | React/Cesium 지구, ADM0 정적 데이터 | 회전·확대와 국가 경계 표시, 출처 기록 |
| 2 | 국가별 ADM1/ADM2와 위치 매핑 | 경계·매핑 버전 일치, 필요한 파일만 로드 |
| 3 | FastAPI·Redis·개발용 기사 | 지역별 제한 조회, 만료 기사 제외 |
| 4 | GDELT 수집기와 메타데이터 보완 | 원문 URL·제목·수집 시각 보존 |
| 5 | Kafka·단일 Spark 파이프라인 | 수집→처리→저장 연결, 중복·재시도 멱등성 |
| 6 | 호버·클릭 미리보기와 언어 선택 | 작은 카드, 안전한 원문 링크, 언어 기본값 |
| 7 | ARM64 이미지·K3s 배포 문서 | 버전 고정, 자원 한도·디스크 보존 정책 검증 |

테스트는 파싱, URL 중복, 지리 검증, 최초 수집 기준 만료, 중요한 API 응답에 집중한다. 가상 개발 기사는 실제 뉴스로 표시하지 않으며 같은 TTL 규칙을 적용한다.

실제 구현 전에 확인할 운영 입력은 VM의 CPU/RAM/디스크, 사용할 도메인, 초기 ADM1/ADM2 대상 국가다. 이 정보는 현재 구조 초안 작성을 막지 않는다.
