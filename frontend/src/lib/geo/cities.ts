/*
 * Where American and Canadian cities sit, so a posting count can become a pin.
 *
 * Only places on the drawn outline are listed. A location with no entry here
 * is not dropped: the page counts it among the places it could not plot and
 * says so, rather than quietly showing a smaller total than the ranking
 * beside it. That is also where a whole state, a whole country and a remote
 * posting end up, none of which is a point you could put a pin through.
 *
 * A name can belong to two countries, so entries are grouped by name and the
 * region and country decide between them. Where they cannot decide, nothing
 * is placed: guessing which Richmond a posting means is worse than saying it
 * could not be placed.
 */

import type { Point } from "./northAmericaMap";

interface CityLocation {
  /** Province or state, where the name alone would be ambiguous. */
  region?: string;
  country: "Canada" | "United States";
  at: Point;
}

/** Keys are lowercase city names, matching the API's `city` field folded. */
export const CITY_COORDINATES: Record<string, CityLocation[]> = {
  // Canada
  toronto: [{ region: "ON", country: "Canada", at: [-79.38, 43.65] }],
  montreal: [{ region: "QC", country: "Canada", at: [-73.57, 45.5] }],
  vancouver: [{ region: "BC", country: "Canada", at: [-123.12, 49.28] }],
  calgary: [{ region: "AB", country: "Canada", at: [-114.07, 51.05] }],
  edmonton: [{ region: "AB", country: "Canada", at: [-113.49, 53.55] }],
  ottawa: [{ region: "ON", country: "Canada", at: [-75.7, 45.42] }],
  winnipeg: [{ region: "MB", country: "Canada", at: [-97.14, 49.9] }],
  "quebec city": [{ region: "QC", country: "Canada", at: [-71.21, 46.81] }],
  quebec: [{ region: "QC", country: "Canada", at: [-71.21, 46.81] }],
  halifax: [{ region: "NS", country: "Canada", at: [-63.57, 44.65] }],
  victoria: [{ region: "BC", country: "Canada", at: [-123.37, 48.43] }],
  saskatoon: [{ region: "SK", country: "Canada", at: [-106.67, 52.13] }],
  regina: [{ region: "SK", country: "Canada", at: [-104.62, 50.45] }],
  "st johns": [{ region: "NL", country: "Canada", at: [-52.71, 47.56] }],
  kitchener: [{ region: "ON", country: "Canada", at: [-80.49, 43.45] }],
  waterloo: [{ region: "ON", country: "Canada", at: [-80.52, 43.47] }],
  oakville: [{ region: "ON", country: "Canada", at: [-79.69, 43.45] }],
  mississauga: [{ region: "ON", country: "Canada", at: [-79.64, 43.59] }],
  brampton: [{ region: "ON", country: "Canada", at: [-79.76, 43.68] }],
  markham: [{ region: "ON", country: "Canada", at: [-79.34, 43.86] }],
  vaughan: [{ region: "ON", country: "Canada", at: [-79.5, 43.84] }],
  milton: [{ region: "ON", country: "Canada", at: [-79.88, 43.51] }],
  guelph: [{ region: "ON", country: "Canada", at: [-80.25, 43.55] }],
  oshawa: [{ region: "ON", country: "Canada", at: [-78.87, 43.9] }],
  barrie: [{ region: "ON", country: "Canada", at: [-79.69, 44.39] }],
  kingston: [{ region: "ON", country: "Canada", at: [-76.48, 44.23] }],
  windsor: [{ region: "ON", country: "Canada", at: [-83.02, 42.31] }],
  sudbury: [{ region: "ON", country: "Canada", at: [-80.99, 46.49] }],
  "thunder bay": [{ region: "ON", country: "Canada", at: [-89.25, 48.38] }],
  "niagara falls": [{ region: "ON", country: "Canada", at: [-79.07, 43.09] }],
  burnaby: [{ region: "BC", country: "Canada", at: [-122.98, 49.25] }],
  surrey: [{ region: "BC", country: "Canada", at: [-122.85, 49.19] }],
  kelowna: [{ region: "BC", country: "Canada", at: [-119.5, 49.89] }],
  laval: [{ region: "QC", country: "Canada", at: [-73.75, 45.61] }],
  gatineau: [{ region: "QC", country: "Canada", at: [-75.7, 45.48] }],
  sherbrooke: [{ region: "QC", country: "Canada", at: [-71.9, 45.4] }],
  fredericton: [{ region: "NB", country: "Canada", at: [-66.64, 45.96] }],
  moncton: [{ region: "NB", country: "Canada", at: [-64.78, 46.09] }],
  "saint john": [{ region: "NB", country: "Canada", at: [-66.06, 45.27] }],
  charlottetown: [{ region: "PE", country: "Canada", at: [-63.13, 46.24] }],
  whitehorse: [{ region: "YT", country: "Canada", at: [-135.06, 60.72] }],
  yellowknife: [{ region: "NT", country: "Canada", at: [-114.37, 62.45] }],
  iqaluit: [{ region: "NU", country: "Canada", at: [-68.52, 63.75] }],

  // Shared names, separated by region and country.
  london: [{ region: "ON", country: "Canada", at: [-81.25, 42.98] }],
  hamilton: [{ region: "ON", country: "Canada", at: [-79.87, 43.26] }],
  richmond: [
    { region: "BC", country: "Canada", at: [-123.14, 49.17] },
    { region: "VA", country: "United States", at: [-77.44, 37.54] },
  ],
  cambridge: [
    { region: "ON", country: "Canada", at: [-80.31, 43.36] },
    { region: "MA", country: "United States", at: [-71.11, 42.37] },
  ],
  burlington: [
    { region: "ON", country: "Canada", at: [-79.8, 43.32] },
    { region: "MA", country: "United States", at: [-71.2, 42.5] },
  ],

  // United States
  "san francisco": [{ region: "CA", country: "United States", at: [-122.42, 37.77] }],
  "san jose": [{ region: "CA", country: "United States", at: [-121.89, 37.34] }],
  "new york": [{ region: "NY", country: "United States", at: [-74.01, 40.71] }],
  brooklyn: [{ region: "NY", country: "United States", at: [-73.94, 40.68] }],
  seattle: [{ region: "WA", country: "United States", at: [-122.33, 47.61] }],
  "los angeles": [{ region: "CA", country: "United States", at: [-118.24, 34.05] }],
  austin: [{ region: "TX", country: "United States", at: [-97.74, 30.27] }],
  sunnyvale: [{ region: "CA", country: "United States", at: [-122.04, 37.37] }],
  "annapolis junction": [{ region: "MD", country: "United States", at: [-76.78, 39.14] }],
  chicago: [{ region: "IL", country: "United States", at: [-87.63, 41.88] }],
  livonia: [{ region: "MI", country: "United States", at: [-83.35, 42.37] }],
  atlanta: [{ region: "GA", country: "United States", at: [-84.39, 33.75] }],
  "santa clara": [{ region: "CA", country: "United States", at: [-121.96, 37.35] }],
  indianapolis: [{ region: "IN", country: "United States", at: [-86.16, 39.77] }],
  "mountain view": [{ region: "CA", country: "United States", at: [-122.08, 37.39] }],
  olathe: [{ region: "KS", country: "United States", at: [-94.82, 38.88] }],
  denver: [{ region: "CO", country: "United States", at: [-104.99, 39.74] }],
  miami: [{ region: "FL", country: "United States", at: [-80.19, 25.76] }],
  "palo alto": [{ region: "CA", country: "United States", at: [-122.14, 37.44] }],
  washington: [{ region: "DC", country: "United States", at: [-77.04, 38.91] }],
  bellevue: [{ region: "WA", country: "United States", at: [-122.2, 47.61] }],
  boston: [{ region: "MA", country: "United States", at: [-71.06, 42.36] }],
  "cedar rapids": [{ region: "IA", country: "United States", at: [-91.64, 41.98] }],
  charlotte: [{ region: "NC", country: "United States", at: [-80.84, 35.23] }],
  dallas: [{ region: "TX", country: "United States", at: [-96.8, 32.78] }],
  "fort meade": [{ region: "MD", country: "United States", at: [-76.74, 39.11] }],
  herndon: [{ region: "VA", country: "United States", at: [-77.39, 38.97] }],
  houston: [{ region: "TX", country: "United States", at: [-95.37, 29.76] }],
  irvine: [{ region: "CA", country: "United States", at: [-117.83, 33.68] }],
  laurel: [{ region: "MD", country: "United States", at: [-76.85, 39.1] }],
  philadelphia: [{ region: "PA", country: "United States", at: [-75.17, 39.95] }],
  raleigh: [{ region: "NC", country: "United States", at: [-78.64, 35.78] }],
  richardson: [{ region: "TX", country: "United States", at: [-96.73, 32.95] }],
  "san mateo": [{ region: "CA", country: "United States", at: [-122.33, 37.56] }],
  tucson: [{ region: "AZ", country: "United States", at: [-110.97, 32.22] }],
  "ann arbor": [{ region: "MI", country: "United States", at: [-83.74, 42.28] }],
  "san diego": [{ region: "CA", country: "United States", at: [-117.16, 32.72] }],
  "san antonio": [{ region: "TX", country: "United States", at: [-98.49, 29.42] }],
  "san bruno": [{ region: "CA", country: "United States", at: [-122.41, 37.63] }],
  "long beach": [{ region: "CA", country: "United States", at: [-118.19, 33.77] }],
  glendale: [{ region: "CA", country: "United States", at: [-118.25, 34.14] }],
  pasadena: [{ region: "CA", country: "United States", at: [-118.14, 34.15] }],
  fremont: [{ region: "CA", country: "United States", at: [-121.99, 37.55] }],
  "redwood city": [{ region: "CA", country: "United States", at: [-122.24, 37.49] }],
  huntsville: [{ region: "AL", country: "United States", at: [-86.59, 34.73] }],
  reston: [{ region: "VA", country: "United States", at: [-77.36, 38.96] }],
  vienna: [{ region: "VA", country: "United States", at: [-77.27, 38.9] }],
  chantilly: [{ region: "VA", country: "United States", at: [-77.43, 38.89] }],
  dulles: [{ region: "VA", country: "United States", at: [-77.45, 38.96] }],
  springfield: [{ region: "VA", country: "United States", at: [-77.19, 38.78] }],
  manassas: [{ region: "VA", country: "United States", at: [-77.48, 38.75] }],
  quantico: [{ region: "VA", country: "United States", at: [-77.3, 38.52] }],
  blacksburg: [{ region: "VA", country: "United States", at: [-80.41, 37.23] }],
  "silver spring": [{ region: "MD", country: "United States", at: [-77.03, 38.99] }],
  bethesda: [{ region: "MD", country: "United States", at: [-77.1, 38.98] }],
  odenton: [{ region: "MD", country: "United States", at: [-76.7, 39.08] }],
  halethorpe: [{ region: "MD", country: "United States", at: [-76.68, 39.23] }],
  columbus: [{ region: "OH", country: "United States", at: [-82.99, 39.96] }],
  cleveland: [{ region: "OH", country: "United States", at: [-81.69, 41.5] }],
  beavercreek: [{ region: "OH", country: "United States", at: [-84.06, 39.71] }],
  "st louis": [{ region: "MO", country: "United States", at: [-90.2, 38.63] }],
  "des moines": [{ region: "IA", country: "United States", at: [-93.61, 41.59] }],
  grimes: [{ region: "IA", country: "United States", at: [-93.79, 41.69] }],
  madison: [{ region: "WI", country: "United States", at: [-89.4, 43.07] }],
  durham: [{ region: "NC", country: "United States", at: [-78.9, 35.99] }],
  "fort worth": [{ region: "TX", country: "United States", at: [-97.33, 32.76] }],
  irving: [{ region: "TX", country: "United States", at: [-96.94, 32.81] }],
  mckinney: [{ region: "TX", country: "United States", at: [-96.61, 33.2] }],
  bastrop: [{ region: "TX", country: "United States", at: [-97.32, 30.11] }],
  "farmers branch": [{ region: "TX", country: "United States", at: [-96.9, 32.93] }],
  scottsdale: [{ region: "AZ", country: "United States", at: [-111.93, 33.49] }],
  chandler: [{ region: "AZ", country: "United States", at: [-111.84, 33.31] }],
  boulder: [{ region: "CO", country: "United States", at: [-105.27, 40.01] }],
  aurora: [{ region: "CO", country: "United States", at: [-104.83, 39.73] }],
  "jersey city": [{ region: "NJ", country: "United States", at: [-74.08, 40.73] }],
  collingswood: [{ region: "NJ", country: "United States", at: [-75.07, 39.92] }],
  totowa: [{ region: "NJ", country: "United States", at: [-74.22, 40.9] }],
  louisville: [{ region: "KY", country: "United States", at: [-85.76, 38.25] }],
  memphis: [{ region: "TN", country: "United States", at: [-90.05, 35.15] }],
  nashville: [{ region: "TN", country: "United States", at: [-86.78, 36.16] }],
  "grand rapids": [{ region: "MI", country: "United States", at: [-85.67, 42.96] }],
  southfield: [{ region: "MI", country: "United States", at: [-83.22, 42.47] }],
  warren: [{ region: "MI", country: "United States", at: [-83.01, 42.49] }],
  zeeland: [{ region: "MI", country: "United States", at: [-86.02, 42.81] }],
  harrisburg: [{ region: "PA", country: "United States", at: [-76.88, 40.27] }],
  pittsburgh: [{ region: "PA", country: "United States", at: [-79.99, 40.44] }],
  "cranberry twp": [{ region: "PA", country: "United States", at: [-80.11, 40.68] }],
  reno: [{ region: "NV", country: "United States", at: [-119.81, 39.53] }],
  "las vegas": [{ region: "NV", country: "United States", at: [-115.14, 36.17] }],
  "salt lake city": [{ region: "UT", country: "United States", at: [-111.89, 40.76] }],
  "west valley city": [{ region: "UT", country: "United States", at: [-112.0, 40.69] }],
  "fort wayne": [{ region: "IN", country: "United States", at: [-85.14, 41.08] }],
  redmond: [{ region: "WA", country: "United States", at: [-122.12, 47.67] }],
  kirkland: [{ region: "WA", country: "United States", at: [-122.21, 47.68] }],
  kent: [{ region: "WA", country: "United States", at: [-122.23, 47.38] }],
  "east hartford": [{ region: "CT", country: "United States", at: [-72.61, 41.78] }],
  greenwich: [{ region: "CT", country: "United States", at: [-73.63, 41.03] }],
  pittsfield: [{ region: "MA", country: "United States", at: [-73.25, 42.45] }],
  wilmington: [{ region: "MA", country: "United States", at: [-71.17, 42.55] }],
  "huntington beach": [{ region: "CA", country: "United States", at: [-117.99, 33.66] }],
  "newport beach": [{ region: "CA", country: "United States", at: [-117.93, 33.62] }],
  carson: [{ region: "CA", country: "United States", at: [-118.28, 33.83] }],
  hawthorne: [{ region: "CA", country: "United States", at: [-118.35, 33.92] }],
  goleta: [{ region: "CA", country: "United States", at: [-119.83, 34.44] }],
  "san luis obispo": [{ region: "CA", country: "United States", at: [-120.66, 35.28] }],
  deerfield: [{ region: "IL", country: "United States", at: [-87.84, 42.17] }],
  sunrise: [{ region: "FL", country: "United States", at: [-80.29, 26.13] }],
  melbourne: [{ region: "FL", country: "United States", at: [-80.61, 28.08] }],
  anderson: [{ region: "SC", country: "United States", at: [-82.65, 34.5] }],
  "fort mill": [{ region: "SC", country: "United States", at: [-80.94, 35.01] }],
  charleston: [{ region: "WV", country: "United States", at: [-81.63, 38.35] }],
  kalispell: [{ region: "MT", country: "United States", at: [-114.31, 48.2] }],
  yarmouth: [{ region: "ME", country: "United States", at: [-70.19, 43.8] }],
  copperhill: [{ region: "TN", country: "United States", at: [-84.38, 35.01] }],
  crane: [{ region: "IN", country: "United States", at: [-86.9, 38.89] }],
};

/*
 * Spellings a posting uses for a city that the table keys under its full
 * name. Only unambiguous ones: "LA" heads twelve postings in the bundled
 * early-career snapshot and would otherwise sit in the list with no pin.
 */
const CITY_ALIASES: Record<string, string> = {
  la: "los angeles",
  nyc: "new york",
  sf: "san francisco",
  dc: "washington",
  "washington dc": "washington",
  "saint louis": "st louis",
  "st. louis": "st louis",
};

/** Folds a city name to the form the table is keyed by. */
function cityKey(city: string): string {
  const folded = city
    .normalize("NFKD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .replace(/[.']/g, "")
    .replace(/\s+/g, " ")
    .trim();

  return CITY_ALIASES[folded] ?? folded;
}

/**
 * Finds a city's coordinates, refusing a match when the region or country
 * disagrees. That is what stops London, UK being pinned in southern Ontario,
 * and Richmond, VA in British Columbia.
 */
export function coordinatesFor(
  city: string,
  region: string,
  country: string,
): Point | null {
  if (!city) {
    return null;
  }

  if (country && country !== "Canada" && country !== "United States") {
    return null;
  }

  const entries = CITY_COORDINATES[cityKey(city)];

  if (!entries) {
    return null;
  }

  const matches = entries.filter(
    (entry) =>
      (!region || !entry.region || region === entry.region) &&
      (!country || country === entry.country),
  );

  // Two candidates and nothing to tell them apart is not a placement. The
  // page lists the row among the ones it could not plot instead.
  if (matches.length !== 1) {
    return null;
  }

  return matches[0].at;
}
