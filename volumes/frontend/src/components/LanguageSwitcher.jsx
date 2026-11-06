import { SUPPORTED, languageName } from "@/lib/i18n";
import { useTranslation } from "@/hooks/useTranslation";

/** Three small buttons, one per interface language; the current one is highlighted. */
export default function LanguageSwitcher({ className = "" }) {
    const { language, setLanguage, t } = useTranslation();
    return (
        <div
            role="group"
            aria-label={t("Language")}
            className={`flex items-center gap-1 rounded-md border border-border bg-card p-1 ${className}`}
        >
            {SUPPORTED.map((code) => {
                const selected = code === language;
                // Each language is named in itself ("Français", "Español"), so everyone finds their own.
                const name = languageName(code, code);
                return (
                    <button
                        key={code}
                        type="button"
                        onClick={() => setLanguage(code)}
                        aria-pressed={selected}
                        aria-label={name}
                        title={name}
                        className={`min-w-9 rounded px-2 py-1.5 text-xs font-semibold uppercase focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand/70 ${
                            selected
                                ? "bg-brand text-white"
                                : "text-muted-foreground hover:bg-accent hover:text-foreground"
                        }`}
                    >
                        {code}
                    </button>
                );
            })}
        </div>
    );
}
