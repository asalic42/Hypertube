import { Link } from "react-router-dom";
import { Card, CardContent } from "@/components/ui/card";
import CoverPlaceholder from "@/components/CoverPlaceholder";
import { useTranslation } from "@/hooks/useTranslation";

function FilmCard({ film }) {
    const { t } = useTranslation();
    // A film left halfway: the API gives the position, the card shows how far.
    const ratio = film.progress ? Math.min(film.progress.position / film.progress.duration, 1) : 0;
    return (
        <Link to={`/movies/${film.id}`} className="block focus-visible:outline-2 focus-visible:outline-ring rounded-xl">
            <Card className={`overflow-hidden py-0 gap-2 h-full transition hover:shadow-lg ${film.watched ? "opacity-60" : ""}`}>
                <div className="relative bg-muted h-72">
                    {film.cover_url ? (
                        <img
                            src={film.cover_url}
                            alt=""
                            loading="lazy"
                            className="w-full h-full object-cover"
                        />
                    ) : (
                        <CoverPlaceholder title={film.title} year={film.year} />
                    )}
                    {film.watched && (
                        <span className="absolute top-2 right-2 rounded-full bg-black/70 px-2 py-0.5 text-xs text-white">
                            {t("Watched")}
                        </span>
                    )}
                    {ratio > 0 && (
                        <>
                            <span className="absolute top-2 right-2 rounded-full bg-black/70 px-2 py-0.5 text-xs text-white">
                                {t("Resume")}
                            </span>
                            <div
                                className="absolute inset-x-0 bottom-0 h-1 bg-black/40"
                                role="progressbar"
                                aria-label={t("Watched {percent}%", { percent: Math.round(ratio * 100) })}
                                aria-valuenow={Math.round(ratio * 100)}
                                aria-valuemin={0}
                                aria-valuemax={100}
                            >
                                <div className="h-full bg-brand" style={{ width: `${ratio * 100}%` }} />
                            </div>
                        </>
                    )}
                </div>
                <CardContent className="px-3 pb-3">
                    <h4 className="font-semibold text-sm line-clamp-2" title={film.title}>{film.title}</h4>
                    <p className="text-sm text-muted-foreground">
                        {film.year ?? t("Year unknown")}
                        {film.rating != null && <> · ⭐ {film.rating.toFixed(1)}</>}
                    </p>
                </CardContent>
            </Card>
        </Link>
    );
}

export default FilmCard;
