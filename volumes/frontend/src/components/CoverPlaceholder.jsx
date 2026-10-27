import { useTranslation } from "@/hooks/useTranslation";

/** A cover drawn from the title, for the films whose sources ship no picture. */
export default function CoverPlaceholder({ title, year, className = "" }) {
    const { t } = useTranslation();
    const hue = [...title].reduce((sum, char) => (sum * 31 + char.charCodeAt(0)) % 360, 7);
    return (
        <div
            role="img"
            aria-label={t("Cover of {title}", { title })}
            className={`flex h-full w-full flex-col items-center justify-center gap-2 p-4 text-center text-white ${className}`}
            style={{ background: `linear-gradient(160deg, hsl(${hue} 45% 28%), hsl(${(hue + 40) % 360} 55% 12%))` }}
        >
            <span className="text-4xl leading-none opacity-80" aria-hidden="true">🎞</span>
            <span className="line-clamp-3 text-sm font-semibold leading-snug drop-shadow">{title}</span>
            {year && <span className="text-xs opacity-75">{year}</span>}
        </div>
    );
}
