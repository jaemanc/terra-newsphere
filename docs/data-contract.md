# 데이터 계약

## 원시 이벤트 v1

`news.raw` 메시지는 128KiB 이하의 JSON이다. 필수 필드는 `schema_version=1`, `source`(provider/publisher/url), `content.title`, 시간대가 있는 `collected_at`이다. 선택 필드는 `published_at`, `content.language/summary/thumbnail_url/translations`, `category`, `location_references`, 소스 발견 시각과 출판사 국가다.

`published_at`을 모르면 null이다. GDELT DOC의 `seendate`는 `source_discovered_at`으로 구분한다. `sourcecountry`는 출판사 메타데이터로만 남긴다. RSS 요약 HTML을 그대로 카드에 넣지 않으며, 현재 수집기는 제목만 사용한다. 신뢰할 수 있는 요약이나 번역은 처리 기사 계약을 따르는 별도 입력에 있을 때만 사용한다.

보도 장소를 명시할 수 있는 입력은 다음 형태다.

```json
{"country_code":"KR","role":"event","confidence":0.7}
```

국가만 알려진 경우 Natural Earth의 수도 좌표를 표시용으로 사용한다. 행정구역 입력은 `geo/generated/regions.json`의 실제 `adm1_id`, `adm2_id`, `dataset_version`을 함께 사용한다. 예시 AGENTS.md의 공식 코드처럼 보이는 값을 복사하지 않는다. 좌표·ID·부모 관계는 번들 매핑과 정확히 일치해야 한다. 모호한 이름, 데이터 버전 불일치, 출판사 위치는 마커로 바꾸지 않는다. 현재 자동 지명 추측은 하지 않으며 검증된 도시 입력은 추후 같은 매핑에 추가한다.

GDELT DOC 기사는 최신 15분 GKG 파일의 동일 URL과 연결해 국가 언급을 보완한다. 압축 파일 16MiB, 압축 해제 256MiB, 행 50000개로 작업량을 제한하고 임시 파일은 즉시 삭제한다. FIPS10-4 코드는 Natural Earth의 검증 가능한 매핑으로 ISO로 변환한다. GKG 언급은 `association_kind=mentioned`, confidence 0.5로 기록하고 실제 사건 발생지로 단정하지 않는다. 문서 URL이 맞지 않거나 매핑할 수 없는 국가는 위치 없이 남긴다.

## 처리 기사와 Redis

Pydantic `News`가 AGENTS.md 필드를 검증한다. `schema_version=1`, `coordinate_source`, `association_kind`, `dataset_version`, 개발용 `is_demo`를 추가한다. URL의 tracking 파라미터·fragment를 제거하고 나머지 쿼리를 정렬한 URL의 SHA-256을 `news_id`로 사용한다. 제목은 원본을 유지한다.

Redis Lua가 기존 기사와 입력의 수집 시각 중 더 이른 값을 적용한다. `expires_at=collected_at+604800초`, 키 만료는 절대 시각 `EXAT`이다. 초 단위 Redis 만료로 최대 1초 일찍 삭제될 수 있지만 늦게 연장하지 않는다. 국가/ADM1/ADM2 sorted set과 제한 조회용 `news:all`도 가장 늦은 연결 기사 만료에 맞춰 만료한다. 위치 업데이트는 이전 연결을 제거한다.

수집기의 `news:seen:{id}`는 첫 수집 시각만 담고 같은 7일 TTL로 소멸한다. 재처리 이벤트는 원래 `collected_at`을 그대로 사용한다. 오래된 GDELT 발견/발행 RSS 기사는 수집 단계에서 제외한다. RSS의 발행 시각을 확인할 수 없으면 입력하지 않는다. 영구 중복 tombstone은 뉴스 파생 메타데이터를 무기한 남기므로 두지 않는다. Redis 완전 손실이나 소스가 발견 시각을 새로 발급하는 URL의 장기 재등장까지 전역 최초 수집 이력을 보장하지는 못한다. 이 경우를 엄격하게 금지하려면 뉴스 보존 정책과 양립하는 외부 소스의 불변 발견 이력 계약을 먼저 확정해야 한다.

캐시 응답은 만들지 않으며 API 응답에 `Cache-Control: no-store`를 설정한다. 뉴스 본문·이미지 바이너리·기사 파일 백업은 만들지 않는다.

## HTTP API

- `GET /api/health`: Redis 연결 상태. 장애 시 503.
- `GET /api/news/markers`: 제목·작은 이미지 URL·출처·위치·만료·선택적 제목 번역. `country`, `adm1`, `adm2`, `bbox=west,south,east,north`, `limit`(1~200), `cursor` 사용.
- `GET /api/news/{news_id}`: 출처 URL·원본 콘텐츠·선택적 요약/번역을 포함한 처리 기사 미리보기. 없는 기사와 만료 기사는 404.

ADM1은 국가를, ADM2는 국가와 ADM1을 함께 요청한다. bbox는 날짜변경선을 넘는 범위도 허용한다. 한 조회에서 최대 500개 후보만 검사하고 `next_cursor`로 이어간다. 갱신/만료가 동시에 일어나는 피드는 고정 snapshot 페이지가 아니므로 중복은 브라우저에서 ID로 제거한다. 밀도가 높아 영역 조회가 느려지는 경우에만 Redis GEO를 추가한다.
