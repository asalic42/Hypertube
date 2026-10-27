import { useContext } from "react";
import { I18nContext } from "@/lib/i18nContext";

/** `t(sentence, params)` in the language of the page, plus the language itself and its setter. */
export function useTranslation() {
  return useContext(I18nContext);
}
