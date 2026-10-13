# 정적 지리 데이터

국가 경계는 Natural Earth 5.1.2 110m, 행정구역은 geoBoundaries gbOpen의 KR ADM1/ADM2부터 포함한다. 다른 국가는 ADM0와 수도 fallback을 사용할 수 있고 상세 행정구역 파일이 없으면 로드하지 않는다. 전 세계 상세 파일을 한 번에 내려받지 않는다.

`scripts/build_geo.py`는 최초 source manifest를 만들 때 geoBoundaries API의 `boundaryID`와 commit URL을 고정한다. 이후에는 `geo/sources.json`의 URL을 사용한다. 소스 갱신은 명시적으로 `--refresh-sources`를 전달한다. 프런트와 서버 매핑은 반드시 같은 실행 결과로 배포한다.

원본 좌표로 중심점·ADM2 부모를 계산하고, 경계는 topology-preserving simplification으로 줄인다. ADM0 허용 오차는 0.05도, ADM1/ADM2는 0.01도다. GeoJSON을 Cesium이 직접 읽을 수 있어 별도 TopoJSON 변환 라이브러리를 추가하지 않았다. 파일 크기·SHA-256·출처·버전·라이선스는 `frontend/public/geo/manifest.json`에 기록한다.

지리 ID는 `boundaryID:shapeID`다. 국가·지역 계층은 `geo/generated/regions.json`에 있으며 Redis 뉴스의 위치 ID와 동일하다. Natural Earth의 이름/국가 코드와 수도 레코드가 일치하지 않는 국가에는 임의 수도를 만들지 않는다. 해당 국가의 경계는 보여도 국가 fallback 마커는 표시하지 않는다.

현재 고정한 한국 ADM1과 ADM2는 원래 출처와 해상도가 다르다. ADM1과 80% 이상 중첩되지 않는 ADM2는 부모를 추측하지 않고 화면·서버 매핑에서 제외한다. 제외한 원본 ID·이름·이유는 manifest의 `unresolved_regions`에 기록한다. 따라서 한국 전체 구·군을 지원한다고 표시하지 않는다. 부모 관계는 해당 버전 경계의 공간 중첩이며 공식 행정 코드와 동일하다고 가정하지 않는다.

초기 로드는 ADM0뿐이다. 선택 국가를 확대하면 ADM1, 더 확대하면 ADM2를 로드한다. 상세 데이터는 한 국가만 유지하며 파일이 없는 국가는 정상적으로 ADM0에 머문다. 지구 표면은 기본 타원체를 사용하고 위성 영상·유료 지형·외부 지도 API는 필요하지 않다.

원본 라이선스와 가공 내용은 `geo/licenses/ATTRIBUTION.md`에 기록하고 UI에 출처 링크를 표시한다.

빌드 시 국가 코드는 고정 버전 pycountry의 ISO 3166-1 목록으로 검증한다. Natural Earth의 비표준 코드에 임의 ISO 값을 할당하지 않는다. pycountry와 Shapely는 지리 빌드 의존성이며 API 이미지에는 포함하지 않는다.
