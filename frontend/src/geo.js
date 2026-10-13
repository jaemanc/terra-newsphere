const countryNames = {
  en: new Intl.DisplayNames(['en'], { type: 'region' }),
  ko: new Intl.DisplayNames(['ko'], { type: 'region' }),
};

// UI names for the bundled Korean dataset; article text remains in its original language.
const koreanRegions = {
  Seoul: '서울', Busan: '부산', Daegu: '대구', Incheon: '인천', Gwangju: '광주',
  Daejeon: '대전', Ulsan: '울산', Sejong: '세종', Gyeonggi: '경기', Gangwon: '강원',
  'North Chungcheong': '충청북도', 'South Chungcheong': '충청남도',
  'North Jeolla': '전라북도', 'South Jeolla': '전라남도',
  'North Gyeongsang': '경상북도', 'South Gyeongsang': '경상남도', Jeju: '제주',
  'Sokcho-si': '속초시',
  'Songpa-gu': '송파구', 'Seocho-gu': '서초구', 'Gangnam-gu': '강남구',
  'Nowon-gu': '노원구', 'Dobong-gu': '도봉구', 'Gangbuk-gu': '강북구',
  'Jungnang-gu': '중랑구', 'Jongno-gu': '종로구', 'Seongbuk-gu': '성북구',
  'Dongdaemun-gu': '동대문구', 'Gwangjin-gu': '광진구', 'Seongdong-gu': '성동구',
  'Jung-gu [Central District]': '중구', 'Yongsan-gu': '용산구', 'Dongjak-gu': '동작구',
  'Seodaemun-gu': '서대문구', 'Mapo-gu': '마포구', 'Yeongdeungpo-gu': '영등포구',
  'Gwanak-gu': '관악구', 'Yangcheon-gu': '양천구',
};

export function countryName(code, locale, fallback = code) {
  if (!/^[A-Z]{2}$/.test(code || '')) return fallback || '';
  return countryNames[locale]?.of(code) || fallback;
}

export function regionName(name, locale) {
  return (locale === 'ko' && koreanRegions[name]) || name || '';
}

export function locationName(location, locale) {
  return [countryName(location.country_code, locale, location.country_name),
    regionName(location.region_name, locale), regionName(location.district_name, locale)]
    .filter(Boolean).join(' · ');
}

export function locationsName(locations, locale) {
  return [...new Set(locations.map(location => locationName(location, locale)))].join(' / ');
}
