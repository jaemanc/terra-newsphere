# 정적 지리 데이터

국가 경계는 Natural Earth 5.1.2 50m, 행정구역은 geoBoundaries gbOpen의 KR ADM1/ADM2부터 포함한다. 다른 국가는 ADM0와 수도 fallback을 사용할 수 있고 상세 행정구역 파일이 없으면 로드하지 않는다. 전 세계 상세 파일을 한 번에 내려받지 않는다.

`scripts/build_geo.py`는 최초 source manifest를 만들 때 geoBoundaries API의 `boundaryID`와 commit URL을 고정한다. 이후에는 `geo/sources.json`의 URL을 사용한다. 소스 갱신은 명시적으로 `--refresh-sources`를 전달한다. 프런트와 서버 매핑은 반드시 같은 실행 결과로 배포한다.

원본 좌표로 중심점·ADM2 부모를 계산하고, 경계는 topology-preserving simplification으로 줄인다. ADM0/ADM1/ADM2 허용 오차는 0.01도다. 국가 경계는 ISO 코드 236개(238개 feature), 약 1.6MiB다. GeoJSON을 Cesium이 직접 읽을 수 있어 별도 TopoJSON 변환 라이브러리를 추가하지 않았다. 파일 크기·SHA-256·출처·버전·라이선스는 `frontend/public/geo/manifest.json`에 기록한다.

지리 ID는 `boundaryID:shapeID`다. 국가·지역 계층은 `geo/generated/regions.json`에 있으며 Redis 뉴스의 위치 ID와 동일하다. Natural Earth의 이름/국가 코드와 수도 레코드가 일치하지 않는 국가에는 임의 수도를 만들지 않는다. 해당 국가의 경계는 보여도 국가 fallback 마커는 표시하지 않는다.

현재 고정한 한국 ADM1과 ADM2는 원래 출처와 해상도가 다르다. ADM1과 80% 이상 중첩되지 않는 ADM2는 부모를 추측하지 않고 화면·서버 매핑에서 제외한다. 제외한 원본 ID·이름·이유는 manifest의 `unresolved_regions`에 기록한다. 따라서 한국 전체 구·군을 지원한다고 표시하지 않는다. 부모 관계는 해당 버전 경계의 공간 중첩이며 공식 행정 코드와 동일하다고 가정하지 않는다.

초기 경계 로드는 ADM0뿐이다. 선택 국가를 확대하면 ADM1, 더 확대하면 ADM2를 로드한다. 상세 데이터는 한 국가만 유지하며 파일이 없는 국가는 정상적으로 ADM0에 머문다. 경계는 일반 폴리곤과 별도의 polyline으로 표시한다. 폴리곤·마커·선에는 타원체와의 깊이 충돌을 피하는 표시용 높이를 적용한다. 이 높이는 뉴스의 실제 고도나 3D 지형이 아니다.

사용자의 2026-10-13 요청에 따라 배경 지도만 온라인 타일을 허용한다. 전 지구 화면은 기존 `/cesium/Assets/Textures/NaturalEarthII` 로컬 타일(level 0–2)을 사용한다. 3000km 미만으로 확대하면 기본 OpenStreetMap 타일을 필요한 화면 범위에서만 받아온다. 최대 level 13으로 행정구역을 식별할 정도의 상세도를 제공하며, 수동 일괄 다운로드·오프라인 타일 묶음·서버 프록시·선행 타일 다운로드는 추가하지 않는다. OSM 타일은 기본 브라우저 캐시와 Referer를 사용하며 출처 링크를 지도에 항상 표시한다. 서버에 120GB 지도를 저장하지 않는다.

`VITE_OSM_TILE_URL`로 정책과 출처 표시가 호환되는 OSM 타일 서버를 설정할 수 있다. 위성 배경이 필요하면 사용자 계정의 `VITE_CESIUM_ION_TOKEN`을 설정하고 프런트를 다시 빌드한다. 토큰은 공개 브라우저용 imagery 접근 권한과 허용 origin만 부여한다. 기본 공유 토큰을 사용하지 않는다. 실제 token이 없는 현재 환경에서는 OSM만 검증했다. 개발 Vite는 프로젝트 루트 .env를 읽으며 Docker Compose는 해당 값을 빌드 인자로 전달한다. 외부 지도가 실패하면 로컬 경계 지도로 되돌아가고 화면에 연결 실패를 표시한다.

Cesium 1.131의 중앙 줌은 동일한 두 방향의 cross product가 0이 되는 회전을 요청할 수 있다. 이 카메라의 길이 0 회전만 no-op으로 처리해 정규화 오류와 카메라 NaN을 막는다. 일반 회전·줌·핀치 입력은 기존 Cesium 처리로 유지한다.

지역명 라벨은 배경 박스 없이 텍스트와 얇은 halo로 표시한다. 밝은 일반 지도에는 어두운 글씨·경계, 위성/로컬 배경에는 밝은 글씨·경계를 사용한다. 배경 위 지역 폴리곤은 매우 얕은 tint만 적용해 지도 정보를 가리지 않는다. 정적 행정 경계·지역 ID·뉴스 좌표·Redis 보관 규칙은 온라인 배경 타일과 분리한다.

공식 근거: [Cesium imagery](https://cesium.com/learn/cesiumjs-learn/cesiumjs-imagery/), [OSM provider](https://cesium.com/learn/cesiumjs/ref-doc/OpenStreetMapImageryProvider.html), [OSM tile usage policy](https://operations.osmfoundation.org/policies/tiles/).

원본 라이선스와 가공 내용은 `geo/licenses/ATTRIBUTION.md`에 기록하고 UI에 출처 링크를 표시한다.

빌드 시 국가 코드는 고정 버전 pycountry의 ISO 3166-1 목록으로 검증한다. Natural Earth의 비표준 코드에 임의 ISO 값을 할당하지 않는다. pycountry와 Shapely는 지리 빌드 의존성이며 API 이미지에는 포함하지 않는다.

국가와 행정구역 이름은 확대 단계·면적·화면 너비에 맞춰 표시 밀도를 조절한다. 라벨 위치는 폴리곤 내부 대표점이며 뉴스 좌표와 분리한다. 국가명은 브라우저의 지역 이름을 사용하고, 한국 광역시·도와 포함된 서울 구 이름은 UI 한국어 이름표를 제공한다. 나머지 지역명은 데이터셋 원문을 유지한다. 뉴스 목록·hover·카드에는 검증된 국가·지역·구 이름만 표시하며, 국가 수준 뉴스에 수도 이름을 보도 지역으로 붙이지 않는다.

50m 소스에서 여러 ISO 국가에 걸치는 FIPS NT는 모호한 매핑으로 제외해 manifest의 `unresolved_fips_codes`에 기록한다. 기존 검증된 행정구역 ID는 유지한다.
