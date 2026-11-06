import { useCallback, useContext, useEffect, useMemo, useState } from "react";
import { AuthContext } from "@/lib/authContext";
import { I18nContext } from "@/lib/i18nContext";
import { initialLanguage, normalizeLanguage, rememberLanguage, translate } from "@/lib/i18n";
import { users as usersApi } from "@/lib/api";

/**
 * The language of the interface. It starts from the browser or the last visit,
 * then follows the preferred language of the account as soon as the viewer is
 * known, and changes at once when that preference is saved.
 */
export function I18nProvider({ children }) {
  const { user } = useContext(AuthContext);
  const [language, setLanguageState] = useState(initialLanguage);

  const setLanguage = useCallback((code) => {
    const next = normalizeLanguage(code) || "en";
    setLanguageState(next);
  }, []);

  useEffect(() => {
    rememberLanguage(language);
  }, [language]);

  // The profile holds the preference: read it on login (and on every page load, which logs in again).
  useEffect(() => {
    if (!user) return undefined;
    let cancelled = false;
    usersApi.get(user.id)
      .then((profile) => !cancelled && profile.preferredLanguage && setLanguage(profile.preferredLanguage))
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, [user, setLanguage]);

  const value = useMemo(
    () => ({ language, setLanguage, t: (key, params) => translate(language, key, params) }),
    [language, setLanguage],
  );
  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>;
}
