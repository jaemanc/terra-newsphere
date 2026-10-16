import React, { useEffect, useLayoutEffect, useRef, useState } from 'react';
import * as Cesium from 'cesium';
import { initialLocale, messages } from './i18n.js';
import { countryName, regionName, locationName, locationsName, primaryLocation } from './geo.js';
import { decorateLayer, MARKER_HEIGHT } from './map-layers.js';
import { overviewLayer, detailLayer, satellite } from './imagery.js';
import { createNewsLayer, updateNewsLayer } from './news-layer.js';
import { countryAreas, markerPosition, uncertainLocation } from './marker-placement.js';
import { declutterHeadlines } from './headline-declutter.js';
import { assetUrl } from './paths.js';
import { demoMode, newsRequest } from './news-data.js';

const FALLBACK = assetUrl('images/fallback.svg');

function Thumbnail({ url, className }) {
  return <img className={className} src={url || FALLBACK} alt="" loading="lazy"
    referrerPolicy="no-referrer" onError={(event) => { event.currentTarget.onerror = null; event.currentTarget.src = FALLBACK; }} />;
}

export default function App() {
  const [locale, setLocale] = useState(initialLocale);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const text = messages[locale];
  const [country, setCountry] = useState('');
  const [adm1, setAdm1] = useState('');
  const [adm2, setAdm2] = useState('');
  const [countries, setCountries] = useState([]);
  const [regions, setRegions] = useState({ adm1: [], adm2: [] });
  const [items, setItems] = useState([]);
  const [mapItems, setMapItems] = useState([]);
  const [areas, setAreas] = useState(null);
  const [mapStatus, setMapStatus] = useState('loading');
  const [mapLimited, setMapLimited] = useState(false);
  const [cursor, setCursor] = useState(null);
  const [pageHistory, setPageHistory] = useState([0]);
  const [overview, setOverview] = useState(null);
  const [status, setStatus] = useState('loading');
  const [view, setView] = useState(null);
  const [refresh, setRefresh] = useState(0);
  const [hover, setHover] = useState(null);
  const [selected, setSelected] = useState(null);
  const [preview, setPreview] = useState(null);
  const [globeError, setGlobeError] = useState(false);
  const [imageryUnavailable, setImageryUnavailable] = useState(false);
  const [imageryLoading, setImageryLoading] = useState(false);
  const [ready, setReady] = useState(false);
  const host = useRef(null);
  const viewer = useRef(null);
  const markers = useRef(null);
  const countryLayer = useRef(null);
  const administrative = useRef(new Map());
  const manifest = useRef(null);
  const request = useRef(null);
  const viewUpdate = useRef(null);
  const generation = useRef(0);
  const bubble = useRef(null);
  const hoverCard = useRef(null);
  const mapLocale = useRef(locale);
  const mapSelection = useRef({ country, adm1, adm2 });

  useEffect(() => {
    mapLocale.current = locale;
    document.documentElement.lang = locale;
    try { localStorage.setItem('terra.locale', locale); } catch { /* Optional preference storage. */ }
    viewer.current?.scene.requestRender();
  }, [locale]);

  useEffect(() => {
    mapSelection.current = { country, adm1, adm2 };
    viewer.current?.scene.requestRender();
  }, [country, adm1, adm2]);

  useEffect(() => {
    let alive = true;
    let globe;
    let handler;
    let timer;
    let removeMove;
    let newsResize;
    let removeReadyRender;
    let removeHeadlineDeclutter;
    let removeImageryError;
    let removeImageryRender;
    let detail;
    let detailFailed = false;
    try {
      globe = new Cesium.Viewer(host.current, {
        baseLayer: overviewLayer(),
        baseLayerPicker: false, geocoder: false, homeButton: false,
        sceneModePicker: false, navigationHelpButton: false, animation: false, timeline: false,
        fullscreenButton: false, infoBox: false, selectionIndicator: false,
        skyBox: false, requestRenderMode: true, maximumRenderTimeChange: Infinity,
      });
      viewer.current = globe;
      let geometryReady = false;
      removeReadyRender = globe.scene.postUpdate.addEventListener(() => {
        const ready = globe.dataSourceDisplay.ready;
        if (!ready || ready !== geometryReady) globe.scene.requestRender();
        geometryReady = ready;
      });
      // Cesium 1.131 center zoom can rotate identical picked normals around a zero axis.
      // That rotation has no effect; skip it before the engine normalizes the axis.
      const rotate = globe.camera.rotate.bind(globe.camera);
      globe.camera.rotate = (axis, angle) => {
        if (Cesium.Cartesian3.magnitudeSquared(axis) !== 0) rotate(axis, angle);
      };
      // Fetch external imagery only for the visible close view, keeping local geography separate.
      globe.scene.globe.preloadAncestors = false;
      globe.scene.globe.preloadSiblings = false;
      detail = detailLayer();
      detail.alpha = 0;
      globe.imageryLayers.add(detail);
      let enabledAt = 0;
      let waitingForTiles = false;
      let previousFrame = performance.now();
      let failedTiles = 0;
      let lastTileFailure = 0;
      // Start visible tiles while zooming, independently of the debounced news query.
      // Keep NASA underneath until this view is ready, then fade rather than swap.
      removeImageryRender = globe.scene.postUpdate.addEventListener(() => {
        const now = performance.now();
        const elapsed = Math.min(64, now - previousFrame);
        previousFrame = now;
        const height = globe.camera.positionCartographic.height;
        const close = height < 3000000 && !detailFailed;
        if (close && !detail.show) {
          detail.show = true;
          enabledAt = now;
          waitingForTiles = true;
          setImageryLoading(true);
          globe.scene.requestRender();
        }
        if (waitingForTiles && now - enabledAt >= 150 && globe.scene.globe.tilesLoaded) {
          waitingForTiles = false;
          setImageryLoading(false);
        }
        const target = close && !waitingForTiles ? Cesium.Math.clamp((3000000 - height) / 700000, 0, 1) : 0;
        const remaining = target - detail.alpha;
        detail.alpha += Math.sign(remaining) * Math.min(Math.abs(remaining), elapsed / 400);
        if (Math.abs(target - detail.alpha) > 0.001 || (waitingForTiles && now - enabledAt < 150)) globe.scene.requestRender();
        if (!close && detail.alpha <= 0.001) {
          detail.show = false;
          if (waitingForTiles) { waitingForTiles = false; setImageryLoading(false); }
        }
      });
      const unavailable = () => {
        if (!alive || detailFailed) return;
        detailFailed = true; detail.show = false;
        setImageryLoading(false);
        setImageryUnavailable(true); updateView();
      };
      detail.errorEvent.addEventListener(unavailable);
      const watchProvider = provider => {
        if (alive) removeImageryError = provider.errorEvent.addEventListener(error => {
          if (error.timesRetried < 1) { error.retry = true; return; }
          const now = performance.now();
          failedTiles = now - lastTileFailure < 10000 ? failedTiles + 1 : 1;
          lastTileFailure = now;
          // A missing tile should not disable the entire map; a failed burst does.
          if (failedTiles >= 3) unavailable();
        });
      };
      if (detail.ready) watchProvider(detail.imageryProvider);
      else detail.readyEvent.addEventListener(watchProvider);
      globe.scene.globe.baseColor = Cesium.Color.fromCssColorString('#103441');
      globe.scene.backgroundColor = Cesium.Color.fromCssColorString('#071018');
      globe.scene.globe.showGroundAtmosphere = true;
      globe.scene.screenSpaceCameraController.minimumZoomDistance = 15000;
      globe.scene.screenSpaceCameraController.maximumZoomDistance = 32000000;
      globe.camera.setView({ destination: Cesium.Cartesian3.fromDegrees(55, 20, 22000000) });
      const news = createNewsLayer(globe, mapLocale);
      removeHeadlineDeclutter = declutterHeadlines(globe, news);
      newsResize = new ResizeObserver(() => {
        globe.resize();
        news.clustering.pixelRange = globe.canvas.clientWidth < 600 ? 8 : 6;
        setHover(null);
        globe.scene.requestRender();
        viewUpdate.current?.();
      });
      newsResize.observe(host.current);
      markers.current = news;
      globe.dataSources.add(news);
      Promise.all([
        fetch(assetUrl('geo/manifest.json')).then((response) => { if (!response.ok) throw new Error(); return response.json(); }),
        fetch(assetUrl('geo/countries.geojson')).then((response) => { if (!response.ok) throw new Error(); return response.json(); }),
      ]).then(async ([index, boundaries]) => {
        if (!alive) return;
        manifest.current = index;
        setAreas(countryAreas(boundaries.features));
        setCountries([...new Map(boundaries.features.map(feature =>
          [feature.properties.country_code, feature.properties])).values()].sort((a, b) => a.name.localeCompare(b.name)));
        const layer = await Cesium.GeoJsonDataSource.load(boundaries, {
          stroke: Cesium.Color.fromCssColorString('#51948f').withAlpha(0.65), strokeWidth: 1,
          fill: Cesium.Color.fromCssColorString('#285b53').withAlpha(0.08), clampToGround: false,
        });
        decorateLayer(layer, 'country', globe, mapLocale, mapSelection);
        if (!alive) return;
        countryLayer.current = layer;
        await globe.dataSources.add(layer);
        globe.scene.requestRender();
      }).catch(() => { if (alive) setGlobeError('geography'); });
      handler = new Cesium.ScreenSpaceEventHandler(globe.scene.canvas);
      handler.setInputAction((movement) => {
        const entity = globe.scene.pick(movement.endPosition)?.id;
        setHover(entity?.news ? { item: entity.news, location: entity.newsLocation, x: movement.endPosition.x, y: movement.endPosition.y } : null);
        globe.scene.canvas.style.cursor = entity?.news ? 'pointer' : 'grab';
      }, Cesium.ScreenSpaceEventType.MOUSE_MOVE);
      handler.setInputAction((movement) => {
        const entity = globe.scene.pick(movement.position)?.id;
        if (entity?.news) {
          setSelected({ item: entity.news, location: entity.newsLocation });
          setHover(null);
        } else if (entity?.properties?.country_code) {
          const properties = entity.properties.getValue();
          setCountry(properties.country_code);
          setAdm1(properties.adm1_id || '');
          setAdm2(properties.level === 'adm2' ? properties.region_id : '');
          setSelected(null);
        } else {
          setSelected(null);
        }
      }, Cesium.ScreenSpaceEventType.LEFT_CLICK);
      const updateView = () => {
        clearTimeout(timer);
        timer = setTimeout(() => {
          if (!alive) return;
          const rectangle = globe.camera.computeViewRectangle();
          const bounds = rectangle ? [rectangle.west, rectangle.south, rectangle.east, rectangle.north]
            .map(Cesium.Math.toDegrees).map((value) => value.toFixed(4)).join(',') : null;
          if (globe.imageryLayers.length) {
            const detailed = globe.camera.positionCartographic.height < 3000000;
            for (const entity of countryLayer.current?.entities.values || []) entity.polygon.fill = detailed;
            globe.scene.requestRender();
          }
          setView({ bbox: bounds, height: globe.camera.positionCartographic.height });
          // Camera motion changes the visible area, never the explicit news filters.
        }, 450);
      };
      viewUpdate.current = updateView;
      removeMove = globe.camera.moveEnd.addEventListener(updateView);
      updateView();
      setReady(true);
    } catch {
      setGlobeError('webgl');
    }
    return () => {
      alive = false; clearTimeout(timer); removeMove?.(); newsResize?.disconnect(); handler?.destroy();
      removeReadyRender?.();
      removeHeadlineDeclutter?.();
      removeImageryError?.();
      removeImageryRender?.();
      if (globe && !globe.isDestroyed()) globe.destroy();
      viewer.current = null;
      viewUpdate.current = null;
    };
  }, []);

  useEffect(() => {
    if (!ready || !view) return;
    let alive = true;
    const level = view.height < 300000 ? 'adm2' : view.height < 3000000 ? 'adm1' : null;
    for (const layer of administrative.current.values()) layer.show = false;
    setRegions({ adm1: [], adm2: [] });
    const files = manifest.current?.administrative[country];
    if (!files || !level) { viewer.current?.scene.requestRender(); return; }
    (async () => {
      const next = { adm1: [], adm2: [] };
      for (const current of level === 'adm2' ? ['adm1', 'adm2'] : ['adm1']) {
        if (!files[current]) continue;
        const key = `${country}:${current}`;
        let layer = administrative.current.get(key);
        if (!layer) {
          const response = await fetch(assetUrl(`geo/${files[current]}`));
          if (!response.ok) throw new Error('Boundary unavailable');
          const data = await response.json();
          next[current] = data.features.map((feature) => feature.properties);
          layer = await Cesium.GeoJsonDataSource.load(data, {
            stroke: Cesium.Color.fromCssColorString(current === 'adm1' ? '#8cbaa8' : '#bac9ac').withAlpha(0.75),
            strokeWidth: 1, fill: Cesium.Color.fromCssColorString('#366859').withAlpha(0.08), clampToGround: false,
          });
          decorateLayer(layer, current, viewer.current, mapLocale, mapSelection);
          if (!alive || !viewer.current) return;
          // Keep only the selected country's detail; never accumulate global ADM2 geometry.
          administrative.current.set(key, layer);
          await viewer.current.dataSources.add(layer);
          layer.options = next[current];
        } else next[current] = layer.options;
        if (!alive) return;
        layer.show = true;
      }
      if (alive) { setRegions(next); viewer.current?.scene.requestRender(); }
      for (const [key, layer] of administrative.current) {
        if (!key.startsWith(`${country}:`)) {
          viewer.current.dataSources.remove(layer, true);
          administrative.current.delete(key);
        }
      }
    })().catch(() => { if (alive) setGlobeError('geography'); });
    return () => { alive = false; };
  }, [country, view?.height, ready]);

  async function loadNews(nextCursor = 0, history = null) {
    request.current?.abort();
    const controller = new AbortController();
    request.current = controller;
    const current = ++generation.current;
    setStatus('loading');
    const params = new URLSearchParams({ limit: '200', cursor: String(nextCursor), include_demo: 'false' });
    if (!country) params.set('include_unlocated', 'true');
    if (country) params.set('country', country);
    if (adm1) params.set('adm1', adm1);
    if (adm2) params.set('adm2', adm2);
    if (view?.bbox) params.set('bbox', view.bbox);
    try {
      const data = { items: [], next_cursor: nextCursor };
      let pages = 0;
      do {
        params.set('cursor', String(data.next_cursor));
        params.set('limit', String(Math.min(200, 500 - data.items.length)));
        const response = await newsRequest(`/api/news/markers?${params}`, { signal: controller.signal, cache: 'no-store' });
        if (!response.ok) throw new Error();
        const page = await response.json();
        pages += 1;
        data.items.push(...page.items);
        data.next_cursor = page.next_cursor;
      } while (pages < 3 && data.next_cursor !== null && data.items.length < 500);
      if (current !== generation.current) return;
      // Keep one bounded page in memory; older news remains accessible on later pages.
      setItems([...new Map(data.items.map((item) => [item.news_id, item])).values()]);
      if (history) setPageHistory(history);
      setCursor(data.next_cursor);
      setStatus('ok');
    } catch (error) {
      if (error.name !== 'AbortError' && current === generation.current) setStatus('error');
    }
  }

  useEffect(() => {
    if (!view) return;
    setHover(null);
    setPageHistory([0]);
    loadNews();
    return () => { request.current?.abort(); };
  }, [country, adm1, adm2, view?.bbox]);

  useEffect(() => {
    if (refresh && view) loadNews(pageHistory.at(-1));
  }, [refresh]);

  // Map data is independent of sidebar pagination. Coordinates may be country-level
  // presentation anchors, so capital-based bbox filtering would hide dispersed dots.
  useEffect(() => {
    const controller = new AbortController();
    setMapStatus('loading');
    (async () => {
      const params = new URLSearchParams({ limit: '200', include_demo: 'false', located_only: 'true' });
      if (country) params.set('country', country);
      if (adm1) params.set('adm1', adm1);
      if (adm2) params.set('adm2', adm2);
      const next = new Map();
      let cursor = 0;
      for (let pages = 0; pages < 10 && cursor !== null && next.size < 1000; pages++) {
        params.set('cursor', String(cursor));
        params.set('limit', String(Math.min(200, 1000 - next.size)));
        const response = await newsRequest(`/api/news/markers?${params}`, { signal: controller.signal, cache: 'no-store' });
        if (!response.ok) throw new Error();
        const data = await response.json();
        for (const item of data.items) next.set(item.news_id, item);
        cursor = data.next_cursor;
      }
      if (controller.signal.aborted) return;
      setMapItems([...next.values()].filter(item => Date.parse(item.expires_at) > Date.now()));
      setMapLimited(cursor !== null);
      setMapStatus('ok');
    })().catch(error => {
      if (error.name !== 'AbortError' && !controller.signal.aborted) {
        setMapItems([]); setMapStatus('error');
      }
    });
    return () => controller.abort();
  }, [country, adm1, adm2, refresh]);

  useEffect(() => {
    const controller = new AbortController();
    newsRequest('/api/news/stats', { signal: controller.signal, cache: 'no-store' })
      .then((response) => { if (!response.ok) throw new Error(); return response.json(); })
      .then(setOverview).catch((error) => { if (error.name !== 'AbortError') setOverview(null); });
    return () => controller.abort();
  }, [refresh]);

  useEffect(() => {
    if (!overview?.expires_at) return;
    const timer = setTimeout(() => {
      setOverview(null);
      setRefresh((value) => value + 1);
    }, Math.max(0, Date.parse(overview.expires_at) - Date.now()) + 1);
    return () => clearTimeout(timer);
  }, [overview]);

  useEffect(() => {
    const timer = setInterval(() => setRefresh((value) => value + 1), items.length ? 60000 : 5000);
    return () => clearInterval(timer);
  }, [items.length > 0]);

  useEffect(() => {
    const loaded = [...items, ...mapItems];
    if (!loaded.length) return;
    const delay = Math.max(0, Math.min(...loaded.map((item) => Date.parse(item.expires_at))) - Date.now());
    const timer = setTimeout(() => {
      setItems((previous) => previous.filter((item) => Date.parse(item.expires_at) > Date.now()));
      setMapItems((previous) => previous.filter((item) => Date.parse(item.expires_at) > Date.now()));
      setSelected(null); setHover(null);
    }, delay + 1);
    return () => clearTimeout(timer);
  }, [items, mapItems]);

  useEffect(() => {
    if (!ready || !markers.current || !areas) return;
    updateNewsLayer(markers.current, mapItems, viewer.current, mapLocale, areas);
    // Label glyph atlases become ready after the data source's sticky ready flag.
    // Render a few frames on news changes, then return to the idle render mode.
    let frames = 0;
    let frame;
    const renderLabels = () => {
      viewer.current?.scene.requestRender();
      if (++frames < 4) frame = requestAnimationFrame(renderLabels);
    };
    renderLabels();
    return () => cancelAnimationFrame(frame);
  }, [mapItems, ready, locale, areas]);

  useEffect(() => {
    setPreview(null);
    if (!selected) return;
    const controller = new AbortController();
    newsRequest(`/api/news/${selected.item.news_id}`, { signal: controller.signal, cache: 'no-store' })
      .then((response) => { if (!response.ok) throw new Error(); return response.json(); })
      .then(setPreview).catch((error) => { if (error.name !== 'AbortError') setPreview({ error: true }); });
    return () => controller.abort();
  }, [selected]);

  useEffect(() => {
    if (!selected) return;
    const timer = setTimeout(() => { setSelected(null); setPreview(null); },
      Math.max(0, Date.parse(selected.item.expires_at) - Date.now()));
    return () => clearTimeout(timer);
  }, [selected]);

  useEffect(() => {
    const globe = viewer.current;
    if (!selected || !globe || !bubble.current) return;
    const anchor = selected.location && markerPosition(selected.item, selected.location, areas || new Map());
    const position = anchor && Cesium.Cartesian3.fromDegrees(anchor.longitude, anchor.latitude, MARKER_HEIGHT);
    const update = () => {
      const element = bubble.current;
      if (!element) return;
      if (!position) {
        element.style.visibility = 'visible';
        element.style.left = `${Math.max(12, globe.canvas.clientWidth - element.offsetWidth - 24)}px`;
        element.style.top = '128px';
        return;
      }
      const point = Cesium.SceneTransforms.worldToWindowCoordinates(globe.scene, position);
      const visible = new Cesium.EllipsoidalOccluder(Cesium.Ellipsoid.WGS84, globe.camera.position).isPointVisible(position);
      element.style.visibility = point && visible ? 'visible' : 'hidden';
      if (point) {
        element.style.left = `${Math.max(12, Math.min(globe.canvas.clientWidth - element.offsetWidth - 12, point.x + 16))}px`;
        element.style.top = `${Math.max(12, Math.min(globe.canvas.clientHeight - element.offsetHeight - 12, point.y - 40))}px`;
      }
    };
    const remove = globe.scene.postRender.addEventListener(update);
    update(); globe.scene.requestRender();
    return remove;
  }, [selected, preview, areas]);

  useLayoutEffect(() => {
    const element = hoverCard.current;
    const stage = host.current;
    if (!hover || !element || !stage) return;
    element.style.left = `${Math.max(12, Math.min(hover.x + 18, stage.clientWidth - element.offsetWidth - 12))}px`;
    element.style.top = `${Math.max(12, Math.min(hover.y - 70, stage.clientHeight - element.offsetHeight - 12))}px`;
  }, [hover, locale]);

  const title = (item) => item.translations?.[locale]?.title || item.title;
  const summary = (item) => item.translations?.[locale]?.summary || item.summary;
  const content = preview && !preview.error ? preview.content.translations?.[locale] || preview.content : null;
  const mapPath = [country && countryName(country, locale),
    regionName(regions.adm1.find(item => item.region_id === adm1)?.name, locale),
    regionName(regions.adm2.find(item => item.region_id === adm2)?.name, locale)].filter(Boolean).join(' › ');

  function chooseCountry(code) {
    setCountry(code); setAdm1(''); setAdm2(''); setSelected(null);
    if (code && countryLayer.current) {
      const positions = countryLayer.current.entities.values
        .filter((item) => item.properties?.country_code?.getValue() === code)
        .flatMap((item) => item.polygon?.hierarchy.getValue().positions || []);
      if (positions.length) {
        viewer.current.camera.flyTo({ destination: Cesium.Rectangle.fromCartesianArray(positions), duration: 1.2,
          complete: () => viewUpdate.current?.() });
        viewer.current.scene.requestRender();
      }
    }
  }

  return <main className={`app${sidebarOpen ? '' : ' sidebar-collapsed'}`}>
    <header className="topbar">
      <div className="brand-group">
        <button className="sidebar-toggle" aria-controls="news-sidebar" aria-expanded={sidebarOpen}
          aria-label={sidebarOpen ? text.hideSidebar : text.showSidebar}
          title={sidebarOpen ? text.hideSidebar : text.showSidebar}
          onClick={() => setSidebarOpen((open) => !open)}>
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" aria-hidden="true">
            <rect x="3" y="4" width="18" height="16" rx="2" /><path d="M9 4v16" />
            <path d={sidebarOpen ? 'm16 9-3 3 3 3' : 'm13 9 3 3-3 3'} />
          </svg>
        </button>
        <a className="brand" href={import.meta.env.BASE_URL} aria-label="TerraNewsphere"><span className="brand-icon">◎</span> TERRA<span>NEWS</span>PHERE</a>
      </div>
      <div className="top-actions"><span className="live-indicator"><i />{demoMode ? text.demo : text.live}</span>
        <select aria-label={text.language} value={locale} onChange={(event) => setLocale(event.target.value)}>
          <option value="en">English</option><option value="ko">한국어</option>
        </select></div>
    </header>
    {demoMode && <p className="demo-notice" role="status">{text.demoNotice}</p>}
    <div className="workspace">
      <aside id="news-sidebar" className="sidebar" hidden={!sidebarOpen}>
        <div className="eyebrow">{text.eyebrow}</div>
        <h1>{text.tagline}</h1><p className="subtitle">{text.subtitle}</p>
        <div className="stats"><div><strong>{overview ? `${overview.complete ? '' : '≥'}${overview.total.toLocaleString(locale)}` : '—'}</strong><span>{text.totalStored}</span></div>
          <div><strong>168<span>h</span></strong><span>{text.days}</span></div></div>
        <div className="marker-legend"><p><i className="marker-key confirmed" />{text.confirmedMarker}</p><p><i className="marker-key uncertain" />{text.uncertainMarker}</p><small>{text.markerExplanation}</small></div>
        <label className="region-label" htmlFor="country">{text.region}</label>
        <select id="country" value={country} onChange={(event) => chooseCountry(event.target.value)}>
          <option value="">{text.all}</option>{countries.map((item) => <option key={item.country_code} value={item.country_code}>{countryName(item.country_code, locale, item.name)}</option>)}
        </select>
        {regions.adm1.length > 0 && <select aria-label="ADM1" value={adm1} onChange={(event) => { setAdm1(event.target.value); setAdm2(''); }}>
          <option value="">{text.adm1} · {text.all}</option>{regions.adm1.map((item) => <option key={item.region_id} value={item.region_id}>{regionName(item.name, locale)}</option>)}
        </select>}
        {adm1 && regions.adm2.length > 0 && <select aria-label="ADM2" value={adm2} onChange={(event) => setAdm2(event.target.value)}>
          <option value="">{text.adm2} · {text.all}</option>{regions.adm2.filter((item) => item.adm1_id === adm1).map((item) => <option key={item.region_id} value={item.region_id}>{regionName(item.name, locale)}</option>)}
        </select>}
        <div className="feed-heading"><span>{text.live}</span><button onClick={() => setRefresh((value) => value + 1)} aria-label={text.refresh}>↻</button></div>
        <div className="feed" aria-live="polite">
          {status === 'loading' && <p className="status">{text.loading}</p>}
          {status === 'error' && <p className="status error">{text.unavailable}</p>}
          {status === 'ok' && !items.length && <p className="status">{text.empty}</p>}
          {items.map((item) => <article className={`story ${selected?.item.news_id === item.news_id ? 'active' : ''}`} key={item.news_id}>
            <div className="story-meta"><span>{locationsName(item.locations, locale) || text.unlocated}</span>
              <a href={item.url} target="_blank" rel="noopener noreferrer">{item.publisher} ↗</a></div>
            <button className="story-open" onClick={() => {
              const location = primaryLocation(item.locations); setSelected({ item, location });
              const anchor = location && markerPosition(item, location, areas || new Map());
              if (anchor) viewer.current?.camera.flyTo({ destination: Cesium.Cartesian3.fromDegrees(anchor.longitude, anchor.latitude, 2200000), duration: 1.2,
                complete: () => viewUpdate.current?.() });
            }}>
              <div className="story-body"><div className="story-copy"><h2>{title(item)}</h2>
                {summary(item) && <p className="story-summary">{summary(item)}</p>}</div><Thumbnail url={item.thumbnail_url} /></div>
            </button>
          </article>)}
        </div>
        <nav className="pagination" aria-label={text.pagination}>
          <button disabled={status === 'loading' || pageHistory.length === 1} onClick={() => {
            const previous = pageHistory.slice(0, -1); loadNews(previous.at(-1), previous);
          }}>{text.previous}</button>
          <span>{text.page} {pageHistory.length}<small>{items.length.toLocaleString(locale)} {text.stories}</small></span>
          <button disabled={status === 'loading' || cursor === null} onClick={() => {
            loadNews(cursor, [...pageHistory, cursor]);
          }}>{text.next}</button>
        </nav>
        <a className="attribution" href={assetUrl('geo/manifest.json')} target="_blank" rel="noopener noreferrer">{text.attribution} ↗</a>
      </aside>
      <section className="globe-stage" aria-label="Interactive news globe">
        <div ref={host} className="globe-layer" />
        <div className="globe-top"><span className="map-location" data-testid="map-location">{mapPath || text.all}</span><button onClick={() => {
          chooseCountry(''); viewer.current?.camera.flyTo({ destination: Cesium.Cartesian3.fromDegrees(55, 20, 22000000), duration: 1.2,
            complete: () => { chooseCountry(''); viewUpdate.current?.(); } });
        }} aria-label={text.reset}>◎</button></div>
        <div className="map-legend" aria-label={text.boundaries}>
          <span><i className="country-line" />{text.country}</span>
          <span><i className="adm1-line" />{text.adm1}</span>
          <span><i className="adm2-line" />{text.adm2}</span>
        </div>
        {globeError && <p className="globe-error">{globeError === 'webgl' ? text.globeError : text.geographyError}</p>}
        {hover && <div ref={hoverCard} className="hover-preview">
          <Thumbnail url={hover.item.thumbnail_url} /><div><small>{locationsName(hover.item.locations, locale)}</small><span>{title(hover.item)}</span>
            {hover.location && uncertainLocation(hover.location) && <small>{text.uncertainMarker}</small>}
            {summary(hover.item) && <p className="story-summary">{summary(hover.item)}</p>}</div>
        </div>}
        {selected && <article ref={bubble} className="news-bubble" aria-live="polite">
          <button className="close" onClick={() => setSelected(null)} aria-label={text.close}>×</button>
          <Thumbnail url={preview?.content?.thumbnail_url || selected.item.thumbnail_url} className="bubble-image" />
          <div className="bubble-body"><div className="story-meta"><span>{selected.item.publisher}</span>{selected.item.is_demo && <span>{text.demo}</span>}</div>
            <h2>{content?.title || title(selected.item)}</h2>
            <p className="news-location">{text.reportedLocation}: {preview?.locations
              ? locationsName(preview.locations, locale) || text.unlocated : selected.location ? locationName(selected.location, locale) : text.unlocated}</p>
            {preview?.error ? <p>{text.unavailable}</p> : <p>{content?.summary || (preview ? text.noSummary : text.loading)}</p>}
            {selected.location && <small>{selected.location.coordinate_source === 'capital_fallback' ? text.distributed : selected.location.coordinate_source === 'verified_place' ? (uncertainLocation(selected.location) ? text.uncertainMarker : text.confirmedMarker) : text.centroid}</small>}
            {selected.location?.association_kind === 'mentioned' && <small>{text.mentioned}</small>}
            {preview && !preview.error && <><small>{text.original}: {preview.content.language}</small>
              <a href={preview.source.url} target="_blank" rel="noopener noreferrer">{demoMode ? text.demoSource : text.source} ↗</a></>}
          </div>
        </article>}
        {(view?.height < 3000000 || imageryLoading) && <div className="map-mode">{imageryUnavailable ? text.imageryFallback : imageryLoading ? text.imageryLoading : satellite ? text.satelliteMap : text.detailMap}
          {country && !manifest.current?.administrative[country] && <span>{text.countryOnly}</span>}
        </div>}
        <div className="globe-bottom"><span>{text.instruction}</span><span className="view-count">{mapStatus === 'loading' ? text.loading : mapStatus === 'error' ? text.unavailable : `${mapItems.length} ${text.mapStories}${mapLimited ? ' · ' + text.mapLimit : ''}`}</span></div>
      </section>
    </div>
  </main>;
}
