import * as Cesium from 'cesium';
import { countryName, regionName } from './geo.js';
import { hasDetailImagery, satellite } from './imagery.js';

// Presentation offsets keep vector faces, borders and points clear of the ellipsoid.
export const MAP_HEIGHT = 1000;
export const MARKER_HEIGHT = 1500;
const LAND = ['#294a40', '#2d4c52', '#354e45', '#3c5054', '#31564d'];

export function decorateLayer(layer, level, globe, locale, selection) {
  const labelled = new Set();
  for (const entity of layer.entities.values) {
    if (!entity.polygon) continue;
    const props = entity.properties.getValue();
    const key = level === 'country' ? props.country_code : props.region_id;
    const index = [...key].reduce((sum, character) => sum + character.charCodeAt(0), 0) % LAND.length;
    const base = Cesium.Color.fromCssColorString(LAND[index]);
    const light = base.withAlpha(level === 'country' ? 0.08 : 0.12);
    const active = Cesium.Color.fromCssColorString('#467e67').withAlpha(0.55);
    const lightStroke = Cesium.Color.fromCssColorString(level === 'country' ? '#83b7af' : level === 'adm1' ? '#b9dcc7' : '#e8c687');
    const darkStroke = Cesium.Color.fromCssColorString(level === 'country' ? '#3a6b71' : level === 'adm1' ? '#197769' : '#ac641b');
    const lightMap = () => hasDetailImagery(globe) && !satellite;
    const stroke = () => lightMap() ? darkStroke : lightStroke;
    const height = MAP_HEIGHT + (level === 'adm1' ? 40 : level === 'adm2' ? 80 : 0);
    entity.polygon.height = height;
    entity.polygon.outline = false;
    if (level === 'country') entity.polygon.fill = globe.camera.positionCartographic.height < 3000000;
    entity.polygon.material = new Cesium.ColorMaterialProperty(new Cesium.CallbackProperty(() => {
      if (hasDetailImagery(globe)) return selection.current[level] === props.region_id
        ? active.withAlpha(0.12) : base.withAlpha(0.015);
      if (level === 'country') return globe.camera.positionCartographic.height < 3000000 ? base : light;
      return selection.current[level] === props.region_id ? active : light;
    }, false));
    const hierarchy = entity.polygon.hierarchy.getValue();
    entity.polyline = new Cesium.PolylineGraphics({
      positions: hierarchy.positions.map(position => {
        const point = Cesium.Cartographic.fromCartesian(position);
        return Cesium.Cartesian3.fromRadians(point.longitude, point.latitude, height + 200);
      }),
      material: new Cesium.ColorMaterialProperty(new Cesium.CallbackProperty(stroke, false)),
      width: level === 'adm2' ? 2 : 1.5, arcType: Cesium.ArcType.GEODESIC,
    });
    if (labelled.has(key) || !Number.isFinite(props.label_longitude) || !Number.isFinite(props.label_latitude)) continue;
    labelled.add(key);
    entity.position = Cesium.Cartesian3.fromDegrees(props.label_longitude, props.label_latitude, MARKER_HEIGHT);
    entity.label = new Cesium.LabelGraphics({
      text: new Cesium.CallbackProperty(() => level === 'country'
        ? countryName(props.country_code, locale.current, props.name) : regionName(props.name, locale.current), false),
      show: new Cesium.CallbackProperty(() => {
        const cameraHeight = globe.camera.positionCartographic.height;
        const density = Math.min(1, globe.canvas.clientWidth / 1000);
        if (level === 'country') return cameraHeight > 700000
          && cameraHeight < Math.sqrt(props.label_area) * 2000000 * density + 2000000;
        if (level === 'adm1') return cameraHeight > 100000
          && cameraHeight < Math.min(3000000, Math.sqrt(props.label_area) * 1000000 * density + 150000);
        return cameraHeight < 150000 && (!selection.current.adm1 || props.adm1_id === selection.current.adm1);
      }, false),
      font: level === 'country' ? '600 15px sans-serif' : '600 13px sans-serif',
      fillColor: new Cesium.CallbackProperty(() => lightMap() ? Cesium.Color.fromCssColorString('#183b42') : lightStroke, false),
      outlineColor: new Cesium.CallbackProperty(() => lightMap() ? Cesium.Color.WHITE : Cesium.Color.fromCssColorString('#071018'), false),
      outlineWidth: 2,
      style: Cesium.LabelStyle.FILL_AND_OUTLINE,
      showBackground: false,
      scaleByDistance: new Cesium.NearFarScalar(100000, 1, 30000000, 0.7),
    });
  }
}
