import { Link } from "react-router-dom";
import { Card, CardContent } from "@/components/ui/card";

function FilmCard({ film }) {
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
                        <div className="flex h-full items-center justify-center text-muted-foreground text-sm">No cover</div>
                    )}
                    {film.watched && (
                        <span className="absolute top-2 right-2 rounded-full bg-black/70 px-2 py-0.5 text-xs text-white">
                            Watched
                        </span>
                    )}
                </div>
                <CardContent className="px-3 pb-3">
                    <h4 className="font-semibold text-sm line-clamp-2" title={film.title}>{film.title}</h4>
                    <p className="text-sm text-muted-foreground">
                        {film.year ?? "Year unknown"}
                        {film.rating != null && <> · ⭐ {film.rating.toFixed(1)}</>}
                    </p>
                </CardContent>
            </Card>
        </Link>
    );
}

export default FilmCard;
