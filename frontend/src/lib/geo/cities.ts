/*
 * Where Canadian cities sit, so a posting count can become a pin.
 *
 * Only Canadian places are listed, because the map is a Canadian outline. A
 * location with no entry here is not dropped: the page counts it among the
 * places it could not plot and says so, rather than quietly showing a smaller
 * total than the ranking beside it.
 */

import type { Point } from "./canadaMap";

interface CityLocation {
  /** Province, where the name alone would be ambiguous. */
  region?: string;
  at: Point;
}

/** Keys are lowercase city names, matching the API's `city` field folded. */
export const CITY_COORDINATES: Record<string, CityLocation> = {
  toronto: { region: "ON", at: [-79.38, 43.65] },
  montreal: { region: "QC", at: [-73.57, 45.5] },
  vancouver: { region: "BC", at: [-123.12, 49.28] },
  calgary: { region: "AB", at: [-114.07, 51.05] },
  edmonton: { region: "AB", at: [-113.49, 53.55] },
  ottawa: { region: "ON", at: [-75.7, 45.42] },
  winnipeg: { region: "MB", at: [-97.14, 49.9] },
  "quebec city": { region: "QC", at: [-71.21, 46.81] },
  quebec: { region: "QC", at: [-71.21, 46.81] },
  halifax: { region: "NS", at: [-63.57, 44.65] },
  victoria: { region: "BC", at: [-123.37, 48.43] },
  saskatoon: { region: "SK", at: [-106.67, 52.13] },
  regina: { region: "SK", at: [-104.62, 50.45] },
  "st johns": { region: "NL", at: [-52.71, 47.56] },
  kitchener: { region: "ON", at: [-80.49, 43.45] },
  waterloo: { region: "ON", at: [-80.52, 43.47] },
  hamilton: { region: "ON", at: [-79.87, 43.26] },
  london: { region: "ON", at: [-81.25, 42.98] },
  oakville: { region: "ON", at: [-79.69, 43.45] },
  mississauga: { region: "ON", at: [-79.64, 43.59] },
  brampton: { region: "ON", at: [-79.76, 43.68] },
  markham: { region: "ON", at: [-79.34, 43.86] },
  vaughan: { region: "ON", at: [-79.5, 43.84] },
  burlington: { region: "ON", at: [-79.8, 43.32] },
  milton: { region: "ON", at: [-79.88, 43.51] },
  guelph: { region: "ON", at: [-80.25, 43.55] },
  oshawa: { region: "ON", at: [-78.87, 43.9] },
  barrie: { region: "ON", at: [-79.69, 44.39] },
  kingston: { region: "ON", at: [-76.48, 44.23] },
  windsor: { region: "ON", at: [-83.02, 42.31] },
  sudbury: { region: "ON", at: [-80.99, 46.49] },
  "thunder bay": { region: "ON", at: [-89.25, 48.38] },
  "niagara falls": { region: "ON", at: [-79.07, 43.09] },
  burnaby: { region: "BC", at: [-122.98, 49.25] },
  richmond: { region: "BC", at: [-123.14, 49.17] },
  surrey: { region: "BC", at: [-122.85, 49.19] },
  kelowna: { region: "BC", at: [-119.5, 49.89] },
  laval: { region: "QC", at: [-73.75, 45.61] },
  gatineau: { region: "QC", at: [-75.7, 45.48] },
  sherbrooke: { region: "QC", at: [-71.9, 45.4] },
  fredericton: { region: "NB", at: [-66.64, 45.96] },
  moncton: { region: "NB", at: [-64.78, 46.09] },
  "saint john": { region: "NB", at: [-66.06, 45.27] },
  charlottetown: { region: "PE", at: [-63.13, 46.24] },
  whitehorse: { region: "YT", at: [-135.06, 60.72] },
  yellowknife: { region: "NT", at: [-114.37, 62.45] },
  iqaluit: { region: "NU", at: [-68.52, 63.75] },
};

/** Folds a city name to the form the table is keyed by. */
function cityKey(city: string): string {
  return city
    .normalize("NFKD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .replace(/[.']/g, "")
    .replace(/\s+/g, " ")
    .trim();
}

/**
 * Finds a city's coordinates, refusing a match when the province disagrees.
 * That is what stops London, UK being pinned in southern Ontario.
 */
export function coordinatesFor(
  city: string,
  region: string,
  country: string,
): Point | null {
  if (!city) {
    return null;
  }

  if (country && country !== "Canada") {
    return null;
  }

  const entry = CITY_COORDINATES[cityKey(city)];

  if (!entry) {
    return null;
  }

  if (region && entry.region && region !== entry.region) {
    return null;
  }

  return entry.at;
}
