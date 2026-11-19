// Display names. Origins and the canvas's destinations are from
// docs/ui-spec.md §2; the rest of the 25 destinations will come from the
// engine's place names (gap G3) and fall back to the code until then.
import type { Airport, Region } from './types';

export const ORIGIN_CITY: Record<Airport, string> = {
  BOM: 'Mumbai',
  BLR: 'Bengaluru',
  GOI: 'Goa',
  GOX: 'Goa',
  CCU: 'Kolkata',
  HYD: 'Hyderabad',
  MAA: 'Chennai',
  COK: 'Kochi',
};

/** Users pick cities; Goa is two airports (LLD §4). */
export const CITY_AIRPORTS: Record<string, Airport[]> = {
  BOM: ['BOM'],
  BLR: ['BLR'],
  GOA: ['GOI', 'GOX'],
  CCU: ['CCU'],
  HYD: ['HYD'],
  MAA: ['MAA'],
  COK: ['COK'],
};

export const DEST_CITY: Record<Airport, string> = {
  SGN: 'Ho Chi Minh City',
  BKK: 'Bangkok',
  FRA: 'Frankfurt',
  BAH: 'Bahrain',
  CMB: 'Colombo',
  DXB: 'Dubai',
  SHJ: 'Sharjah',
  // Stop cities shown on the canvas's deal pages.
  HYD: 'Hyderabad',
  AUH: 'Abu Dhabi',
  KWI: 'Kuwait City',
};

/** LLD §4 region map. */
export const REGIONS: Record<Region, Airport[]> = {
  gulf: ['DXB', 'AUH', 'SHJ', 'DOH', 'MCT', 'BAH', 'KWI'],
  sea: ['SIN', 'KUL', 'BKK', 'HKT', 'DPS', 'SGN'],
  near: ['CMB', 'MLE', 'KTM'],
  east: ['HKG', 'TYO', 'SEL'],
  europe: ['LON', 'PAR', 'FRA', 'AMS', 'IST'],
  aus: ['SYD'],
};

export function originCity(code: Airport): string {
  return ORIGIN_CITY[code] ?? code;
}
/** Deal-page subtitle only: GOX shows as "Goa (Mopa)". */
export function originCityLong(code: Airport): string {
  return code === 'GOX' ? 'Goa (Mopa)' : originCity(code);
}
export function destCity(code: Airport): string {
  return DEST_CITY[code] ?? ORIGIN_CITY[code] ?? code;
}
export function regionOf(dest: Airport): Region | null {
  for (const [r, codes] of Object.entries(REGIONS)) if (codes.includes(dest)) return r as Region;
  return null;
}
