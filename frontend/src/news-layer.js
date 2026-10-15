import * as Cesium from 'cesium';
import { MARKER_HEIGHT } from './map-layers.js';
import { shortHeadline, latestNewsEntity } from './news-labels.js';

const pointStyle = {
  color: Cesium.Color.fromCssColorString('#ff932e'),
  outlineColor: Cesium.Color.fromCssColorString('#fff4df'), outlineWidth: 2,
};
const labelStyle = {
  font: '600 12px sans-serif', fillColor: Cesium.Color.WHITE,
  outlineColor: Cesium.Color.fromCssColorString('#17120d'), outlineWidth: 3,
  style: Cesium.LabelStyle.FILL_AND_OUTLINE, showBackground: false,
  horizontalOrigin: Cesium.HorizontalOrigin.CENTER, pixelOffset: new Cesium.Cartesian2(0, -20),
};

function headline(item, globe, locale) {
  return shortHeadline(item.translations?.[locale.current]?.title || item.title,
    globe.canvas.clientWidth < 600 ? 18 : 26);
}

export function createNewsLayer(globe, locale) {
  const news = new Cesium.CustomDataSource('news');
  news.clustering.enabled = true;
  news.clustering.pixelRange = 64;
  news.clustering.minimumClusterSize = 2;
  news.clustering.clusterEvent.addEventListener((entities, cluster) => {
    const representative = latestNewsEntity(entities);
    if (!representative) return;
    Object.assign(cluster.label, labelStyle, {
      show: true, text: headline(representative.news, globe, locale), id: representative,
    });
    cluster.billboard.show = false;
    Object.assign(cluster.point, pointStyle, { show: true, id: representative, pixelSize: 22 });
    globe.scene.requestRender();
  });
  return news;
}

export function updateNewsLayer(layer, items, globe, locale) {
  layer.entities.removeAll();
  for (const item of items) {
    item.locations.forEach((location, index) => {
      const entity = layer.entities.add({
        id: `${item.news_id}:${index}`,
        position: Cesium.Cartesian3.fromDegrees(location.longitude, location.latitude, MARKER_HEIGHT),
        point: { ...pointStyle, pixelSize: 12, heightReference: Cesium.HeightReference.NONE },
        label: { ...labelStyle, text: new Cesium.CallbackProperty(() => headline(item, globe, locale), false) },
      });
      entity.news = item;
      entity.newsLocation = location;
    });
  }
}
