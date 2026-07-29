import { Card, CardContent, CardFooter } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

function FilmCard({ film }) {
    const root_path = 'https://image.tmdb.org/t/p/w500';
    
    return(
        <Card className="overflow-hidden py-0 gap-2">
            <img
                src={`${root_path}${film.poster_path}`}
                alt={film.title}
                className="w-full h-80 object-cover"
            />
            <CardContent className="px-3">
                <h4 className="font-semibold text-sm line-clamp-2">{film.title}</h4>
                <p className="text-sm text-muted-foreground">Note : {film.vote_average}/10</p>
            </CardContent>
            <CardFooter className="px-3 pb-3">
                <Button variant="ghost" size="icon">{film.favori ? '❤️' : '🤍'}</Button>
            </CardFooter>
        </Card>
    );
}

export default FilmCard;