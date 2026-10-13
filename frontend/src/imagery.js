import * as Cesium from 'cesium';

export const satellite = Boolean(import.meta.env.VITE_CESIUM_ION_TOKEN);

export function overviewLayer() {
  return Cesium.ImageryLayer.fromProviderAsync(Cesium.TileMapServiceImageryProvider.fromUrl(
    '/cesium/Assets/Textures/NaturalEarthII', { maximumLevel: 2, credit: 'Natural Earth II' }));
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
  return globe.imageryLayers.length > 1 && globe.imageryLayers.get(1).show;
}
