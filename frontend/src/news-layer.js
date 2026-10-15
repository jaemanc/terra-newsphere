import * as Cesium from 'cesium';
import { MARKER_HEIGHT } from './map-layers.js';
import { shortHeadline, latestNewsEntity } from './news-labels.js';
import { primaryLocation } from './geo.js';

const RIPPLE_IMAGE = '/images/news-ripple.svg';
const labelStyle = {
  font: '600 12px sans-serif', fillColor: Cesium.Color.WHITE,
  outlineColor: Cesium.Color.fromCssColorString('#17120d'), outlineWidth: 3,
  style: Cesium.LabelStyle.FILL_AND_OUTLINE, showBackground: false,
  horizontalOrigin: Cesium.HorizontalOrigin.CENTER, pixelOffset: new Cesium.Cartesian2(0, -28),
};

function headline(item, globe, locale) {
  return shortHeadline(item.translations?.[locale.current]?.title || item.title,
    globe.canvas.clientWidth < 600 ? 18 : 26);
}

export function createNewsLayer(globe, locale) {
  const news = new Cesium.CustomDataSource('news');
  news.clustering.enabled = true;
  // Cesium also includes the headline width; only add a small grouping margin.
  news.clustering.pixelRange = globe.canvas.clientWidth < 600 ? 8 : 6;
  news.clustering.minimumClusterSize = 2;
  news.clustering.clusterEvent.addEventListener((entities, cluster) => {
    const representative = latestNewsEntity(entities);
    if (!representative) return;
    Object.assign(cluster.label, labelStyle, {
      show: true, text: headline(representative.news, globe, locale), id: representative,
      pixelOffset: new Cesium.Cartesian2(0, -40),
    });
    cluster.point.show = false;
    Object.assign(cluster.billboard, {
      show: true, id: representative, image: RIPPLE_IMAGE, width: 68, height: 68,
    });
    globe.scene.requestRender();
  });
  return news;
}

export function updateNewsLayer(layer, items, globe, locale) {
  layer.entities.removeAll();
  for (const item of items) {
    const location = primaryLocation(item.locations);
    if (location) {
      const entity = layer.entities.add({
        id: item.news_id,
        position: Cesium.Cartesian3.fromDegrees(location.longitude, location.latitude, MARKER_HEIGHT),
        billboard: { image: RIPPLE_IMAGE, width: 44, height: 44, heightReference: Cesium.HeightReference.NONE },
        label: { ...labelStyle, text: new Cesium.CallbackProperty(() => headline(item, globe, locale), false) },
      });
      entity.news = item;
      entity.newsLocation = location;
    }
  }
}
