/** Token storage for the browser. Next.js renders this module on the server
 * too (during SSR/build), where `window` doesn't exist — every method
 * no-ops there instead of throwing, since auth state only ever matters
 * client-side anyway. */
const isBrowser = typeof window !== "undefined";

export const storage = {
  getItem(key: string): string | null {
    if (!isBrowser) return null;
    return window.localStorage.getItem(key);
  },
  setItem(key: string, value: string): void {
    if (!isBrowser) return;
    window.localStorage.setItem(key, value);
  },
  deleteItem(key: string): void {
    if (!isBrowser) return;
    window.localStorage.removeItem(key);
  },
};
