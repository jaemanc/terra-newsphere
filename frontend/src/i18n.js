export const messages = {
  en: {
    eyebrow: 'A WORLD IN MOTION', tagline: 'Every story has a place.', subtitle: 'Explore the last seven days of news, around the globe.',
    live: 'RECENT NEWS', language: 'Interface language', all: 'All regions', region: 'Explore a region',
    loading: 'Loading current news…', unavailable: 'News is temporarily unavailable. Try refreshing.',
    empty: 'No current news in this view.', refresh: 'Refresh', stories: 'stories in view',
    instruction: 'Drag to explore · Scroll to zoom · Select a dot for the story',
    source: 'Read original article', close: 'Close preview', demo: 'DEMO',
    demoNotice: 'Interactive demo · All stories are fictional examples. No live news is collected here.',
    demoSource: 'Open example link',
    distributed: 'Country association only · illustrative position, not an event location', centroid: 'Region known · shown at its center',
    mentioned: 'Country mentioned in the article · location uncertain',
    original: 'Original language', noSummary: 'A summary is not provided by this source.',
    attribution: 'Boundaries: Natural Earth & geoBoundaries', globeError: 'The globe needs a browser with WebGL support.',
    geographyError: 'Geographic boundaries could not be loaded.',
    days: '7-day window',
    reset: 'Reset globe', country: 'Country', adm1: 'Administrative region', adm2: 'District / subdivision', boundaries: 'Boundary legend',
    reportedLocation: 'Reported location', countryOnly: 'Only country boundaries are bundled here',
    detailMap: 'Detailed map', satelliteMap: 'Satellite map', imageryFallback: 'Background unavailable · local boundary map',
    imageryLoading: 'Loading detailed map…',
    unlocated: 'Location unconfirmed',
    totalStored: 'All stored stories', pagination: 'News pages', previous: 'Previous', next: 'Next', page: 'Page',
    confirmedMarker: 'Mint · verified event location',
    uncertainMarker: 'Orange · exact location unconfirmed',
    markerExplanation: 'Orange markers stay within the associated country; country-only stories are spread for display, not placed at the event site. Regional centers and mixed clusters are also orange. Numbers indicate grouped stories.',
    mapStories: 'located stories loaded', mapLimit: 'latest subset · select a region for more',
    showSidebar: 'Show news sidebar', hideSidebar: 'Hide news sidebar',
  },
  ko: {
    eyebrow: '지금, 세계의 이야기', tagline: '지구 위의 뉴스', subtitle: '지구를 돌려 최근 7일의 뉴스를 만나보세요.',
    live: '최근 뉴스', language: '화면 언어', all: '모든 지역', region: '지역 둘러보기',
    loading: '최근 뉴스를 불러오는 중…', unavailable: '뉴스를 불러오지 못했습니다. 새로고침해 주세요.',
    empty: '현재 화면에 표시할 최근 뉴스가 없습니다.', refresh: '새로고침', stories: '개 기사 표시',
    instruction: '드래그로 회전 · 스크롤로 확대 · 마커를 선택해 기사 보기',
    source: '원문 기사 읽기', close: '미리보기 닫기', demo: '데모',
    demoNotice: '체험용 데모 · 모든 기사는 가상 예시이며 실제 뉴스를 수집하지 않습니다.',
    demoSource: '예시 링크 열기',
    distributed: '국가만 연결됨 · 국가 내 예시 위치이며 실제 사건 지점이 아닙니다', centroid: '행정구역 확인됨 · 중심점에 표시',
    mentioned: '기사에서 언급된 국가 · 보도 장소 불확실',
    original: '기사 원문 언어', noSummary: '출처에서 제공한 요약이 없습니다.',
    attribution: '경계 데이터: Natural Earth · geoBoundaries', globeError: 'WebGL을 지원하는 브라우저가 필요합니다.',
    geographyError: '지리 경계 파일을 불러오지 못했습니다.',
    days: '최근 7일',
    reset: '지구 초기화', country: '국가', adm1: '1차 행정구역', adm2: '2차 행정구역', boundaries: '경계 범례',
    reportedLocation: '보도 지역', countryOnly: '이 국가는 국가 경계만 제공됩니다',
    detailMap: '상세 지도', satelliteMap: '위성 지도', imageryFallback: '배경 지도 연결 실패 · 기본 경계 지도',
    imageryLoading: '상세 지도 연결 중…',
    unlocated: '위치 미확인',
    totalStored: '전체 보관 기사', pagination: '뉴스 페이지', previous: '이전', next: '다음', page: '페이지',
    confirmedMarker: '민트색 · 확인된 사건 지점',
    uncertainMarker: '주황색 · 정확한 위치 미확인',
    markerExplanation: '주황색은 연결된 국가 안에 표시됩니다. 국가만 알려진 기사는 보기 쉽게 분산한 것으로 실제 사건 지점이 아닙니다. 행정구역 중심점과 혼합 묶음도 주황색이며, 숫자는 묶인 기사 수입니다.',
    mapStories: '개 위치 기사 로드', mapLimit: '최신 일부 표시 · 지역을 선택해 더 보기',
    showSidebar: '뉴스 사이드바 열기', hideSidebar: '뉴스 사이드바 접기',
  },
};

export function initialLocale() {
  try {
    const stored = localStorage.getItem('terra.locale');
    if (stored && messages[stored]) return stored;
  } catch { /* Browser storage may be disabled. */ }
  for (const preferred of navigator.languages || [navigator.language]) {
    const language = preferred?.split('-')[0].toLowerCase();
    if (messages[language]) return language;
  }
  return 'en';
}
