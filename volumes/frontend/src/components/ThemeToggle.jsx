import { Moon, Sun } from "lucide-react";
import { useTheme } from "@/hooks/useTheme";
import { useTranslation } from "@/hooks/useTranslation";

/** One button: sun in the dark, moon in the light. */
export default function ThemeToggle({ className = "" }) {
    const { theme, toggleTheme } = useTheme();
    const { t } = useTranslation();
    const label = theme === "dark" ? t("Switch to light mode") : t("Switch to dark mode");
    return (
        <button
            type="button"
            onClick={toggleTheme}
            aria-label={label}
            title={label}
            className={`flex size-11 shrink-0 items-center justify-center rounded-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand/70 sm:size-10 ${className}`}
        >
            {theme === "dark" ? <Sun className="size-5" aria-hidden="true" /> : <Moon className="size-5" aria-hidden="true" />}
        </button>
    );
}
