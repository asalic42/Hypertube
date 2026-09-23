import { useEffect, useRef, useState } from "react";
import { useParams } from "react-router-dom";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { toast } from "@/components/ui/toast";
import { movies as moviesApi, comments as commentsApi } from "@/lib/api";
import { useAuth } from "@/hooks/useAuth";

const POLL_INTERVAL = 2000;
const LANGUAGE_NAMES = new Intl.DisplayNames(["en"], { type: "language" });

function languageName(code) {
    try {
        return LANGUAGE_NAMES.of(code);
    } catch {
        return code;
    }
}

function Badge({ children, variant = "default" }) {
    const styles = variant === "secondary"
        ? "bg-secondary text-secondary-foreground"
        : "bg-primary text-primary-foreground";
    return <span className={`inline-flex items-center rounded-md px-2 py-0.5 text-xs font-medium ${styles}`}>{children}</span>;
}

function Player({ movieId, initialStatus }) {
    const [download, setDownload] = useState(null);
    const [requested, setRequested] = useState(Boolean(initialStatus));
    const [error, setError] = useState(null);
    const videoRef = useRef(null);

    const [starting, setStarting] = useState(false);

    async function requestDownload() {
        setStarting(true);
        setError(null);
        try {
            setDownload(await moviesApi.requestDownload(movieId));
            setRequested(true);
        } catch (err) {
            setError(err.message);
        } finally {
            setStarting(false);
        }
    }

    // Follow the download until the video is stored and the subtitles resolved.
    useEffect(() => {
        if (!requested) return undefined;
        let timer;
        let cancelled = false;
        async function poll() {
            try {
                const data = await moviesApi.download(movieId);
                if (cancelled) return;
                setDownload(data);
                setError(null);
                const settled = data.status === "ready" || data.status === "failed";
                const subtitlesPending = data.subtitles.some((subtitle) => subtitle.status === "pending");
                if (!settled || subtitlesPending) timer = setTimeout(poll, POLL_INTERVAL);
            } catch (err) {
                // A transient failure (network, expired token being renewed) must not stop the follow-up.
                if (cancelled) return;
                setError(err.message);
                timer = setTimeout(poll, POLL_INTERVAL * 2);
            }
        }
        poll();
        return () => {
            cancelled = true;
            clearTimeout(timer);
        };
    }, [movieId, requested]);

    // The source is fixed once known: later polls must not restart the film.
    const [source, setSource] = useState(null);
    if (download?.stream_url && !source) {
        setSource(download.stream_url);
    }

    return (
        <div className="flex flex-col gap-3">
            <div className="aspect-video w-full overflow-hidden rounded-lg bg-black flex items-center justify-center">
                {source ? (
                    <video ref={videoRef} src={source} controls autoPlay className="h-full w-full" crossOrigin="use-credentials">
                        {download.subtitles
                            .filter((subtitle) => subtitle.status === "ready")
                            .map((subtitle) => (
                                <track
                                    key={subtitle.language}
                                    kind="subtitles"
                                    src={subtitle.url}
                                    srcLang={subtitle.language}
                                    label={languageName(subtitle.language)}
                                    default={subtitle.language === "en"}
                                />
                            ))}
                    </video>
                ) : !requested ? (
                    <Button size="lg" onClick={requestDownload} disabled={starting}>{starting ? "Starting..." : "▶ Play"}</Button>
                ) : download?.status === "failed" ? (
                    <div className="text-center text-white p-4">
                        <p className="font-medium">This movie could not be downloaded.</p>
                        <p className="text-sm text-gray-300">{download.error}</p>
                        <Button className="mt-3" variant="secondary" onClick={requestDownload}>Retry</Button>
                    </div>
                ) : (
                    <div className="text-center text-white p-4">
                        <p className="font-medium">
                            {download?.status === "queued" && "Waiting for the download to start..."}
                            {download?.status === "downloading" && `Downloading ${download.progress}% (${Math.round(download.download_rate / 1024)} KiB/s, ${download.num_peers} peer${download.num_peers === 1 ? "" : "s"})`}
                            {download?.status === "processing" && "Preparing the file..."}
                            {!download && "Starting..."}
                        </p>
                        <p className="text-sm text-gray-300">Playback starts as soon as enough data is available.</p>
                    </div>
                )}
            </div>
            {error && <p className="text-sm text-destructive">{error}</p>}
            {download && (
                <p className="text-xs text-muted-foreground">
                    {download.status === "ready" ? "Stored on the server." : download.status === "downloading" ? `Download: ${download.progress}%` : null}
                    {download.subtitles.length > 0 && (
                        <> · Subtitles: {download.subtitles.map((subtitle) => `${languageName(subtitle.language)} (${subtitle.status})`).join(", ")}</>
                    )}
                </p>
            )}
        </div>
    );
}

function CommentItem({ comment, own, onChanged }) {
    const [editing, setEditing] = useState(false);
    const [text, setText] = useState(comment.comment);

    async function save(e) {
        e.preventDefault();
        try {
            onChanged(await commentsApi.update(comment.id, text));
            setEditing(false);
        } catch (err) {
            toast.add({ title: "Error", description: err.message, type: "error" });
        }
    }

    async function remove() {
        try {
            await commentsApi.remove(comment.id);
            onChanged(null);
        } catch (err) {
            toast.add({ title: "Error", description: err.message, type: "error" });
        }
    }

    return (
        <div className="flex gap-3">
            <Avatar className="size-8 shrink-0">
                <AvatarFallback>{comment.username[0].toUpperCase()}</AvatarFallback>
            </Avatar>
            <div className="flex flex-1 flex-col gap-1">
                <div className="flex items-center gap-2">
                    <span className="font-medium text-sm">{comment.username}</span>
                    <span className="text-xs text-muted-foreground">{new Date(comment.created_at).toLocaleString()}</span>
                    {own && !editing && (
                        <span className="ml-auto flex gap-1">
                            <Button type="button" variant="ghost" size="sm" onClick={() => setEditing(true)}>Edit</Button>
                            <Button type="button" variant="ghost" size="sm" onClick={remove}>Delete</Button>
                        </span>
                    )}
                </div>
                {editing ? (
                    <form onSubmit={save} className="flex flex-col gap-2">
                        <textarea
                            className="min-h-16 rounded-md border border-input bg-transparent px-2.5 py-1 text-sm"
                            value={text}
                            maxLength={2000}
                            required
                            onChange={(e) => setText(e.target.value)}
                        />
                        <div className="flex gap-2 self-end">
                            <Button type="button" variant="outline" size="sm" onClick={() => { setEditing(false); setText(comment.comment); }}>Cancel</Button>
                            <Button type="submit" size="sm">Save</Button>
                        </div>
                    </form>
                ) : (
                    <p className="text-sm whitespace-pre-wrap break-words">{comment.comment}</p>
                )}
            </div>
        </div>
    );
}

function Comments({ movieId }) {
    const { user } = useAuth();
    const [comments, setComments] = useState([]);
    const [nextPage, setNextPage] = useState(null);
    const [text, setText] = useState("");

    function showError(err) {
        toast.add({ title: "Error", description: err.message, type: "error" });
    }

    useEffect(() => {
        let cancelled = false;
        moviesApi.comments(movieId, 1).then((data) => {
            if (cancelled) return;
            setComments(data.results);
            setNextPage(data.next_page);
        }).catch(showError);
        return () => {
            cancelled = true;
        };
    }, [movieId]);

    function loadMore() {
        moviesApi.comments(movieId, nextPage).then((data) => {
            setComments((current) => [...current, ...data.results]);
            setNextPage(data.next_page);
        }).catch(showError);
    }

    async function submit(e) {
        e.preventDefault();
        if (!text.trim()) return;
        try {
            const created = await moviesApi.addComment(movieId, text);
            setComments((current) => [created, ...current]);
            setText("");
        } catch (err) {
            toast.add({ title: "Error", description: err.message, type: "error" });
        }
    }

    function replace(id, updated) {
        setComments((current) => (updated ? current.map((c) => (c.id === id ? updated : c)) : current.filter((c) => c.id !== id)));
    }

    return (
        <div className="flex flex-col gap-4">
            <h2 className="text-lg font-semibold">Comments</h2>
            <form onSubmit={submit} className="flex flex-col gap-2">
                <textarea
                    className="min-h-20 rounded-md border border-input bg-transparent px-2.5 py-1 text-sm"
                    placeholder="Write a comment..."
                    value={text}
                    maxLength={2000}
                    onChange={(e) => setText(e.target.value)}
                />
                <Button type="submit" className="self-end" disabled={!text.trim()}>Publish</Button>
            </form>
            <Separator />
            <div className="flex flex-col gap-4">
                {comments.length === 0 && <p className="text-sm text-muted-foreground">No comment yet.</p>}
                {comments.map((comment) => (
                    <CommentItem key={comment.id} comment={comment} own={comment.username === user.username} onChanged={(updated) => replace(comment.id, updated)} />
                ))}
                {nextPage && (
                    <Button type="button" variant="outline" className="self-center" onClick={loadMore}>Load more</Button>
                )}
            </div>
        </div>
    );
}

export default function Watch() {
    const { id } = useParams();
    // Keyed on the id: navigating to another movie starts from a blank page.
    return <MoviePage key={id} id={id} />;
}

function MoviePage({ id }) {
    const [film, setFilm] = useState(null);
    const [error, setError] = useState(null);

    useEffect(() => {
        let cancelled = false;
        moviesApi.get(id).then((data) => !cancelled && setFilm(data)).catch((err) => !cancelled && setError(err.message));
        return () => {
            cancelled = true;
        };
    }, [id]);

    if (error) return <p className="p-8 text-destructive">{error}</p>;
    if (!film) return <p className="p-8 text-muted-foreground">Loading...</p>;

    const people = [
        ["Director", film.directors],
        ["Producer", film.producers],
    ].filter(([, names]) => names.length > 0);

    return (
        <div className="w-full max-w-4xl mx-auto p-4 flex flex-col gap-4">
            <Player movieId={film.id} initialStatus={film.download_status} />

            <div className="flex items-start justify-between gap-4">
                <h1 className="text-2xl font-bold">{film.title}</h1>
                {film.watched && <Badge variant="secondary">Watched</Badge>}
            </div>
            <div className="flex flex-wrap gap-2">
                {film.rating != null && <Badge>⭐ {film.rating.toFixed(1)}/10</Badge>}
                {film.year && <Badge variant="secondary">{film.year}</Badge>}
                {film.runtime && <Badge variant="secondary">{film.runtime} min</Badge>}
                {film.genres.map((genre) => <Badge key={genre} variant="secondary">{genre}</Badge>)}
                {film.imdb_id && (
                    <a className="text-xs underline self-center" href={`https://www.imdb.com/title/${film.imdb_id}/`} target="_blank" rel="noreferrer">IMDb</a>
                )}
            </div>
            <Separator />
            <div className="grid gap-6 md:grid-cols-[200px_1fr]">
                {film.cover_url && <img src={film.cover_url} alt="" className="w-full rounded-lg object-cover" />}
                <div className="flex flex-col gap-3">
                    <p className="text-muted-foreground">{film.overview || "No summary available."}</p>
                    {people.map(([role, names]) => (
                        <p key={role} className="text-sm"><span className="font-medium">{role}{names.length > 1 ? "s" : ""}:</span> {names.join(", ")}</p>
                    ))}
                    {film.cast.length > 0 && (
                        <div>
                            <p className="text-sm font-medium">Cast</p>
                            <ul className="mt-1 flex flex-wrap gap-2">
                                {film.cast.map((member) => (
                                    <li key={member.name} className="flex items-center gap-2 rounded-md bg-muted px-2 py-1 text-xs">
                                        <Avatar className="size-6">
                                            {member.picture_url && <img src={member.picture_url} alt="" className="size-full rounded-full object-cover" />}
                                            <AvatarFallback>{member.name[0]}</AvatarFallback>
                                        </Avatar>
                                        <span>{member.name}{member.character && <span className="text-muted-foreground"> as {member.character}</span>}</span>
                                    </li>
                                ))}
                            </ul>
                        </div>
                    )}
                    <p className="text-xs text-muted-foreground">
                        Source{film.sources.length > 1 ? "s" : ""}: {film.sources.map((source, index) => (
                            <span key={source.url}>{index > 0 && ", "}<a className="underline" href={source.url} target="_blank" rel="noreferrer">{source.provider}</a></span>
                        ))}
                    </p>
                </div>
            </div>
            <Separator />
            <Comments movieId={film.id} />
        </div>
    );
}
