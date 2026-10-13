# 정적 지리 데이터

국가 경계는 Natural Earth 5.1.2 50m, 행정구역은 geoBoundaries gbOpen의 KR ADM1/ADM2부터 포함한다. 다른 국가는 ADM0와 수도 fallback을 사용할 수 있고 상세 행정구역 파일이 없으면 로드하지 않는다. 전 세계 상세 파일을 한 번에 내려받지 않는다.

`scripts/build_geo.py`는 최초 source manifest를 만들 때 geoBoundaries API의 `boundaryID`와 commit URL을 고정한다. 이후에는 `geo/sources.json`의 URL을 사용한다. 소스 갱신은 명시적으로 `--refresh-sources`를 전달한다. 프런트와 서버 매핑은 반드시 같은 실행 결과로 배포한다.

원본 좌표로 중심점·ADM2 부모를 계산하고, 경계는 topology-preserving simplification으로 줄인다. ADM0/ADM1/ADM2 허용 오차는 0.01도다. 국가 경계는 ISO 코드 236개(238개 feature), 약 1.6MiB다. GeoJSON을 Cesium이 직접 읽을 수 있어 별도 TopoJSON 변환 라이브러리를 추가하지 않았다. 파일 크기·SHA-256·출처·버전·라이선스는 `frontend/public/geo/manifest.json`에 기록한다.

지리 ID는 `boundaryID:shapeID`다. 국가·지역 계층은 `geo/generated/regions.json`에 있으며 Redis 뉴스의 위치 ID와 동일하다. Natural Earth의 이름/국가 코드와 수도 레코드가 일치하지 않는 국가에는 임의 수도를 만들지 않는다. 해당 국가의 경계는 보여도 국가 fallback 마커는 표시하지 않는다.

현재 고정한 한국 ADM1과 ADM2는 원래 출처와 해상도가 다르다. ADM1과 80% 이상 중첩되지 않는 ADM2는 부모를 추측하지 않고 화면·서버 매핑에서 제외한다. 제외한 원본 ID·이름·이유는 manifest의 `unresolved_regions`에 기록한다. 따라서 한국 전체 구·군을 지원한다고 표시하지 않는다. 부모 관계는 해당 버전 경계의 공간 중첩이며 공식 행정 코드와 동일하다고 가정하지 않는다.

초기 경계 로드는 ADM0뿐이다. 선택 국가를 확대하면 ADM1, 더 확대하면 ADM2를 로드한다. 상세 데이터는 한 국가만 유지하며 파일이 없는 국가는 정상적으로 ADM0에 머문다. 전 지구 화면은 기본 타원체와 고정 Cesium 패키지에 포함된 저해상도 Natural Earth II 지도를 사용한다. 카메라 높이 3000km 미만에서는 래스터를 숨기고 색상 폴리곤을 표시해 확대 시 흐려지지 않도록 한다. 지도 타일은 `/cesium/Assets/Textures/NaturalEarthII`에서 정적으로 제공하고 최대 단계는 2다. 위성 영상·유료 지형·외부 지도 API는 필요하지 않다. 경계는 일반 폴리곤과 별도의 polyline으로 표시한다. 폴리곤·마커·선에는 타원체와의 깊이 충돌을 피하는 표시용 높이를 적용한다. 이 높이는 뉴스의 실제 고도나 3D 지형이 아니다.

원본 라이선스와 가공 내용은 `geo/licenses/ATTRIBUTION.md`에 기록하고 UI에 출처 링크를 표시한다.

빌드 시 국가 코드는 고정 버전 pycountry의 ISO 3166-1 목록으로 검증한다. Natural Earth의 비표준 코드에 임의 ISO 값을 할당하지 않는다. pycountry와 Shapely는 지리 빌드 의존성이며 API 이미지에는 포함하지 않는다.

국가와 행정구역 이름은 확대 단계·면적·화면 너비에 맞춰 표시 밀도를 조절한다. 라벨 위치는 폴리곤 내부 대표점이며 뉴스 좌표와 분리한다. 국가명은 브라우저의 지역 이름을 사용하고, 한국 광역시·도와 포함된 서울 구 이름은 UI 한국어 이름표를 제공한다. 나머지 지역명은 데이터셋 원문을 유지한다. 뉴스 목록·hover·카드에는 검증된 국가·지역·구 이름만 표시하며, 국가 수준 뉴스에 수도 이름을 보도 지역으로 붙이지 않는다.

50m 소스에서 여러 ISO 국가에 걸치는 FIPS NT는 모호한 매핑으로 제외해 manifest의 `unresolved_fips_codes`에 기록한다. 기존 검증된 행정구역 ID는 유지한다.
