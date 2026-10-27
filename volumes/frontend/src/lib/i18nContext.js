import { createContext } from "react";

export const I18nContext = createContext({ language: "en", setLanguage: () => {}, t: (key) => key });
