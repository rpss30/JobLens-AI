export type Theme = "light" | "dark";

/*
 * Both preferences ride in cookies rather than local storage so the server can
 * render them. A choice only the browser knows has to be applied after the
 * HTML arrives, which is either a flash of the other theme or a hydration
 * mismatch; read from the request there is neither.
 */
export const THEME_COOKIE = "joblens-theme";
export const SIDEBAR_COOKIE = "joblens-sidebar";

const ONE_YEAR_SECONDS = 60 * 60 * 24 * 365;

export function readThemeCookie(value: string | undefined): Theme | null {
  return value === "light" || value === "dark" ? value : null;
}

function remember(name: string, value: string) {
  document.cookie = `${name}=${value};path=/;max-age=${ONE_YEAR_SECONDS};samesite=lax`;
}

/*
 * The theme is read back off the document rather than held in React: the
 * attribute is the truth, the server wrote it, and the toggle only changes it.
 */

const listeners = new Set<() => void>();

function readTheme(): Theme {
  const chosen = document.documentElement.dataset.theme;

  if (chosen === "light" || chosen === "dark") {
    return chosen;
  }

  // Nothing chosen, so the operating system is deciding.
  return window.matchMedia("(prefers-color-scheme: dark)").matches
    ? "dark"
    : "light";
}

export function subscribeToTheme(listener: () => void): () => void {
  listeners.add(listener);

  // Someone with no stored choice follows the system, which can change while
  // the page is open.
  const media = window.matchMedia("(prefers-color-scheme: dark)");
  media.addEventListener("change", listener);

  return () => {
    listeners.delete(listener);
    media.removeEventListener("change", listener);
  };
}

export const getTheme = readTheme;

export function setTheme(theme: Theme): void {
  document.documentElement.dataset.theme = theme;
  remember(THEME_COOKIE, theme);

  for (const listener of listeners) {
    listener();
  }
}

export function readSidebarCookie(value: string | undefined): boolean {
  return value === "collapsed";
}

export function rememberSidebar(isCollapsed: boolean): void {
  remember(SIDEBAR_COOKIE, isCollapsed ? "collapsed" : "expanded");
}
