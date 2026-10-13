import { cpSync, mkdirSync, rmSync } from 'node:fs';
import { fileURLToPath } from 'node:url';

const source = fileURLToPath(new URL('../node_modules/cesium/Build/Cesium/', import.meta.url));
const target = fileURLToPath(new URL('../public/cesium/', import.meta.url));
rmSync(target, { recursive: true, force: true });
mkdirSync(target, { recursive: true });
for (const name of ['Workers', 'ThirdParty', 'Assets', 'Widgets']) {
  cpSync(`${source}/${name}`, `${target}/${name}`, { recursive: true });
}
