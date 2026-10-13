export const messages = {
  en: {
    eyebrow: 'A WORLD IN MOTION', tagline: 'Every story has a place.', subtitle: 'Explore the last seven days of news, around the globe.',
    live: 'RECENT NEWS', language: 'Interface language', all: 'All regions', region: 'Explore a region',
    loading: 'Loading current news…', unavailable: 'News is temporarily unavailable. Try refreshing.',
    empty: 'No current news in this view.', more: 'Load more', refresh: 'Refresh', stories: 'stories in view',
    instruction: 'Drag to explore · Scroll to zoom · Select a dot for the story',
    source: 'Read original article', close: 'Close preview', demo: 'DEMO',
    capital: 'Country known · shown at its capital', centroid: 'Region known · shown at its center',
    mentioned: 'Country mentioned in the article · location uncertain',
    original: 'Original language', noSummary: 'A summary is not provided by this source.',
    attribution: 'Boundaries: Natural Earth & geoBoundaries', globeError: 'The globe needs a browser with WebGL support.',
    geographyError: 'Geographic boundaries could not be loaded.',
    expires: 'Available until', detected: 'Browser language', count: 'Current stories', days: '7-day window',
    reset: 'Reset globe', unknown: 'Publication time unavailable',
    country: 'Country', adm1: 'Administrative region', adm2: 'District / subdivision', boundaries: 'Boundary legend',
    reportedLocation: 'Reported location', vectorMap: 'Detailed boundary map', countryOnly: 'Only country boundaries are bundled here',
    detailMap: 'Detailed map', satelliteMap: 'Satellite map', imageryFallback: 'Background unavailable · local boundary map',
  },
  ko: {
    eyebrow: '지금, 세계의 이야기', tagline: '모든 이야기에는 장소가 있습니다.', subtitle: '지구를 돌려 최근 7일의 뉴스를 만나보세요.',
    live: '최근 뉴스', language: '화면 언어', all: '모든 지역', region: '지역 둘러보기',
    loading: '최근 뉴스를 불러오는 중…', unavailable: '뉴스를 불러오지 못했습니다. 새로고침해 주세요.',
    empty: '현재 화면에 표시할 최근 뉴스가 없습니다.', more: '더 보기', refresh: '새로고침', stories: '개 기사 표시',
    instruction: '드래그로 회전 · 스크롤로 확대 · 마커를 선택해 기사 보기',
    source: '원문 기사 읽기', close: '미리보기 닫기', demo: '데모',
    capital: '국가만 확인됨 · 수도에 표시', centroid: '행정구역 확인됨 · 중심점에 표시',
    mentioned: '기사에서 언급된 국가 · 보도 장소 불확실',
    original: '기사 원문 언어', noSummary: '출처에서 제공한 요약이 없습니다.',
    attribution: '경계 데이터: Natural Earth · geoBoundaries', globeError: 'WebGL을 지원하는 브라우저가 필요합니다.',
    geographyError: '지리 경계 파일을 불러오지 못했습니다.',
    expires: '표시 만료', detected: '브라우저 언어', count: '현재 기사', days: '최근 7일',
    reset: '지구 초기화', unknown: '발행 시각 미제공',
    country: '국가', adm1: '1차 행정구역', adm2: '2차 행정구역', boundaries: '경계 범례',
    reportedLocation: '보도 지역', vectorMap: '상세 경계 지도', countryOnly: '이 국가는 국가 경계만 제공됩니다',
    detailMap: '상세 지도', satelliteMap: '위성 지도', imageryFallback: '배경 지도 연결 실패 · 기본 경계 지도',
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
