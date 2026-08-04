import { useState } from "react";
import { Avatar, AvatarImage, AvatarFallback } from "@/components/ui/avatar";
import { Textarea } from "@/components/ui/textarea";
import { AspectRatio } from "@/components/ui/aspect-ratio";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { Button } from "@/components/ui/button";


const filmMock = {
  id: 1,
  title: "Inception",
  overview: "Dom Cobb est un voleur expérimenté dans l'art périlleux de l'extraction, une technique d'espionnage lui permettant d'infiltrer les rêves d'un individu pour lui voler ses secrets les plus précieux.",
  poster_path: "/9gk7adHYeDvHkCSEqAvQNLV5Uge.jpg",
  vote_average: 8.8,
  release_date: "2010-07-16",
  favori: false,
  videoUrl: "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4"
};

const commentairesMock = [
  { id: 1, author: "Anthony", text: "Super film, j'ai adoré la fin !", date: "2026-08-01" },
  { id: 2, author: "Marie", text: "Un peu long mais globalement bon.", date: "2026-08-02" },
];

export default function Watch ({ film = filmMock }) {
    const [comms, setComms] = useState(commentairesMock);
    const [newComment, setNewComm] = useState("");

    function handleSubmit(e) {
        e.preventDefault();
        if (!newComment.trim()) return;

        const comm = {
            id: Date.now(),
            author: "You",
            text: newComment,
            date: new Date().toISOString().slice(0,10),
        };

        setComms([comm, ...comms]);
        setNewComm("");
    }

    return (
        <div className="w-full max-w-4xl mx-auto p-4 flex flex-col gap-4">
            <AspectRatio ratio={16/9}>
                <video
                    src={film.videoUrl}
                    controls
                    className="w-full h-full rounded-lg"
                />
            </AspectRatio>
            <div className="flex items-center justify-between">
                <h1 className="text-2xl font-bold">{film.title}</h1>
                <Button variant="ghost" size="icon">
                    {film.favori ? '❤️' : '🤍'}
                </Button>
            </div>
            <div className="flex gap-2">
                <Badge>⭐ {film.vote_average}/10</Badge>
                <Badge variant="secondary">{film.release_date?.slice(0, 4)}</Badge>
            </div>
            <Separator />
            <p className="text-muted-foreground">{film.overview}</p>

            <Separator />

            <div className="flex flex-col gap-4">
                <h2 className="text-lg font-semibold">Comments</h2>

                <form onSubmit={handleSubmit} className="flex flex-col gap-2">
                    <Textarea
                        placeholder="write a comment..."
                        value={newComment}
                        onChange={(e) => setNewComm(e.target.value)}
                    />
                    <Button type="submit" className="self-end">Publish</Button>
                </form>

                <Separator />

                <div className="flex flex-col gap-4">
                    {comms.map((com) => (
                        <div key={com.id} className="flex gap-3">
                            <Avatar className="size-8 shrink-0">
                                <AvatarFallback>{com.author[0].toUpperCase()}</AvatarFallback>
                            </Avatar>
                            <div className="flex flex-col gap-1">
                                <div className="flex items-center gap-2">
                                    <span className="font-medium text-sm">{com.author}</span>
                                    <span className="text-xs text-muted-foreground">{com.date}</span>
                                </div>
                                <p className="text-sm">{com.text}</p>
                            </div>
                        </div>
                    ))}
                </div>
            </div>
        </div>
    );
}

// producteur, realisateur ,acteurs principaux, duree de film