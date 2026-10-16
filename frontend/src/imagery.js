import * as Cesium from 'cesium';
import { assetUrl } from './paths.js';

export const satellite = Boolean(import.meta.env.VITE_CESIUM_ION_TOKEN);

export function overviewLayer() {
  return new Cesium.ImageryLayer(new Cesium.UrlTemplateImageryProvider({
    url: assetUrl('imagery/blue-marble-base-200407-v1/{z}/{x}/{y}.jpg'),
    tilingScheme: new Cesium.GeographicTilingScheme(),
    tileWidth: 675, tileHeight: 675, maximumLevel: 4, hasAlphaChannel: false,
    credit: new Cesium.Credit('<a href="https://science.nasa.gov/earth/earth-observatory/blue-marble-next-generation/base-map/" target="_blank" rel="noopener noreferrer">NASA Earth Observatory · Blue Marble</a>', true),
  }));
}

export function detailLayer() {
  if (satellite) {
    Cesium.Ion.defaultAccessToken = import.meta.env.VITE_CESIUM_ION_TOKEN;
    return Cesium.ImageryLayer.fromWorldImagery({ style: Cesium.IonWorldImageryStyle.AERIAL, show: false });
  }
  const provider = new Cesium.OpenStreetMapImageryProvider({
    url: import.meta.env.VITE_OSM_TILE_URL || 'https://tile.openstreetmap.org/',
    maximumLevel: 13,
    credit: new Cesium.Credit('<a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener noreferrer">© OpenStreetMap contributors</a>', true),
  });
  return new Cesium.ImageryLayer(provider, { show: false, saturation: 0.65 });
}

export function hasDetailImagery(globe) {
  return globe.imageryLayers.length > 1 && globe.imageryLayers.get(1).show && globe.imageryLayers.get(1).alpha > 0.5;
}
