// Public display configuration only. Leaflet coordinates always come from F7.
const customUrl = import.meta.env.VITE_MAP_TILE_URL?.trim();

export const mapTiles = {
  url: customUrl || 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
  attribution: import.meta.env.VITE_MAP_TILE_ATTRIBUTION?.trim() || (customUrl ? '' : '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'),
  maxZoom: 19,
};
