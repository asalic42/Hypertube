import { useEffect, useLayoutEffect, useRef, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import { NativeSelect, NativeSelectOption } from "@/components/ui/native-select";
import { Separator } from "@/components/ui/separator";
import { toast } from "@/components/ui/toast";
import { movies as moviesApi, comments as commentsApi } from "@/lib/api";
import { COMMENT_MAX_LENGTH } from "@/lib/limits";
import { appendPage } from "@/lib/pages";
import { useAuth } from "@/hooks/useAuth";
import { useAvatarUrl } from "@/lib/avatars";
import CoverPlaceholder from "@/components/CoverPlaceholder";
import { useTranslation } from "@/hooks/useTranslation";
import { languageName, t as translate } from "@/lib/i18n";

const POLL_INTERVAL = 2000;
// How often the position is reported while the film plays.
const PROGRESS_INTERVAL = 10000;
// Below this many seconds in, there is nothing worth resuming.
const RESUME_MIN_SECONDS = 30;
// Before the video is reloaded after an error while the film still downloads
// (a part of it was not on the server yet: the API answers 503 and fetches it first).
const RETRY_DELAY = 3000;

// Whether the browser lets the film start on its own. Firefox and Chrome block
// an audible video until the viewer has interacted with the page (a direct load
// or a refresh of this page has had none), and Firefox warns in the console at
// every blocked attempt: the film is then left for the viewer to start.
function autoplayAllowed() {
    if (typeof navigator.getAutoplayPolicy === "function") return navigator.getAutoplayPolicy("mediaelement") === "allowed";
    return navigator.userActivation?.hasBeenActive ?? true;
}

function formatTime(seconds) {
    const total = Math.floor(seconds);
    const h = Math.floor(total / 3600);
    const m = Math.floor((total % 3600) / 60);
    const sec = total % 60;
    const mm = h ? String(m).padStart(2, "0") : String(m);
    return `${h ? `${h}:` : ""}${mm}:${String(sec).padStart(2, "0")}`;
}

function Badge({ children, variant = "default" }) {
    const styles = variant === "secondary"
        ? "bg-secondary text-secondary-foreground"
        : "bg-primary text-primary-foreground";
    return <span className={`inline-flex items-center rounded-md px-2 py-0.5 text-xs font-medium ${styles}`}>{children}</span>;
}

// Key of a quality in the download resource: the source file, or the height of a lower rendition.
function qualityKey(quality) {
    return quality.original ? "original" : String(quality.height);
}

function Player({ movieId, initialStatus, initialProgress }) {
    const { t, language } = useTranslation();
    const [download, setDownload] = useState(null);
    const [requested, setRequested] = useState(Boolean(initialStatus));
    const renewRef = useRef(Boolean(initialStatus) && initialStatus !== "failed");
    const [error, setError] = useState(null);
    const videoRef = useRef(null);

    const [starting, setStarting] = useState(false);

    // The stream URL of each quality, with the version of the file behind it.
    // Each poll signs a new token, and a changing src would restart the film:
    // the URL is kept until the API serves another file under it (the stored
    // copy once the download is complete), when the player reloads at the same position.
    const [sources, setSources] = useState({});
    // Likewise for the subtitle tracks, renewed only when a track was lined up on the sound track.
    const [tracks, setTracks] = useState({});
    const [quality, setQuality] = useState("original");
    // Position and play state to restore after a change of quality.
    const resumeRef = useRef(null);
    // Where the viewer stopped last time, used once, when the video first loads.
    const startAtRef = useRef(initialProgress?.position || 0);
    // Last position seen, saved when the page is left (the video element is gone by then).
    const progressRef = useRef({ position: 0, duration: 0, sentAt: 0 });
    // Whether the film was playing, as of the last play/pause event.
    const playingRef = useRef(false);
    // The latest download resource and the pending reload after an error.
    const downloadRef = useRef(initialStatus ? { status: initialStatus } : null);
    const retryRef = useRef(null);

    function saveProgress() {
        const { position, duration } = progressRef.current;
        if (!duration) return;
        progressRef.current.sentAt = Date.now();
        moviesApi.saveProgress(movieId, position, duration).catch(() => {});
    }

    function trackProgress(event) {
        const video = event.currentTarget;
        // A reload is under way: the events it fires (pause, time reset to 0) are not the viewer's.
        if (resumeRef.current) return;
        if (!Number.isFinite(video.duration) || video.duration <= 0) return;
        progressRef.current.position = video.ended ? video.duration : video.currentTime;
        progressRef.current.duration = video.duration;
        if (event.type !== "timeupdate" || Date.now() - progressRef.current.sentAt >= PROGRESS_INTERVAL) saveProgress();
    }

    // The last position goes out when the page is left: another route, a reload, a closed tab.
    useEffect(() => {
        window.addEventListener("pagehide", saveProgress);
        return () => {
            window.removeEventListener("pagehide", saveProgress);
            clearTimeout(retryRef.current);
            saveProgress();
        };
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [movieId]);

    function follow(data) {
        downloadRef.current = data;
        setDownload(data);
        // Another file under a known URL is only taken up when the player can tell
        // where it is: a live conversion has no known length, and keeps its stream.
        const video = videoRef.current;
        const resumable = Number.isFinite(video?.duration) && video.duration > 0;
        setSources((current) => {
            const next = { ...current };
            for (const item of data.qualities) {
                const key = qualityKey(item);
                if (item.stream_url && (!next[key] || (next[key].version !== item.version && resumable))) {
                    next[key] = { url: item.stream_url, version: item.version };
                }
            }
            return next;
        });
        setTracks((current) => {
            const next = { ...current };
            for (const subtitle of data.subtitles) {
                if (subtitle.url && (!next[subtitle.language] || next[subtitle.language].aligned !== subtitle.aligned)) {
                    next[subtitle.language] = { url: subtitle.url, aligned: subtitle.aligned };
                }
            }
            return next;
        });
    }

    async function requestDownload() {
        setStarting(true);
        setError(null);
        try {
            follow(await moviesApi.requestDownload(movieId));
            setRequested(true);
        } catch (err) {
            setError(err.message);
        } finally {
            setStarting(false);
        }
    }

    // Follow the download until the video is stored, the lower resolutions encoded and the subtitles resolved.
    useEffect(() => {
        if (!requested) return undefined;
        let timer;
        let cancelled = false;
        async function poll() {
            try {
                const renew = renewRef.current;
                renewRef.current = false;
                const data = renew ? await moviesApi.requestDownload(movieId) : await moviesApi.download(movieId);
                if (cancelled) return;
                follow(data);
                setError(null);
                const settled = data.status === "ready" || data.status === "failed";
                const subtitlesPending = data.subtitles.some((subtitle) => subtitle.status === "pending" || (subtitle.status === "ready" && !subtitle.aligned));
                const qualitiesPending = data.qualities.some((item) => item.status === "pending");
                if (!settled || subtitlesPending || qualitiesPending) timer = setTimeout(poll, POLL_INTERVAL);
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

    const source = (sources[quality] || sources.original)?.url ?? null;
    const readySubtitles = download?.subtitles.filter((subtitle) => subtitle.status === "ready") ?? [];
    const defaultSubtitle = (readySubtitles.find((subtitle) => subtitle.language !== "en") || readySubtitles[0])?.language;
    const qualities = download?.qualities ?? [];
    const selectable = qualities.filter((item) => item.status === "ready" && sources[qualityKey(item)]);

    function changeQuality(event) {
        const video = videoRef.current;
        if (video) resumeRef.current = { time: video.currentTime, playing: !video.paused && !video.ended };
        setQuality(event.target.value);
    }

    // The src is about to be replaced by another file of the same film (its
    // stored copy): note where the viewer is, so that the new one resumes there.
    // A change of quality has already done so, with the exact position.
    const sourceRef = useRef(null);
    useLayoutEffect(() => {
        const previous = sourceRef.current;
        sourceRef.current = source;
        if (!previous || !source || previous === source || resumeRef.current) return;
        resumeRef.current = { time: progressRef.current.position, playing: playingRef.current };
    }, [source]);

    // An error while the film still downloads is transient: a part of it was
    // not on the server yet (503), or the stream stopped while waiting for it.
    // The video is reloaded where it was once the worker had time to fetch it.
    function retryLater(event) {
        const video = event.currentTarget;
        const status = downloadRef.current?.status;
        if (status !== "downloading" && status !== "processing") return;
        if (!resumeRef.current) resumeRef.current = { time: progressRef.current.position, playing: playingRef.current };
        clearTimeout(retryRef.current);
        retryRef.current = setTimeout(() => video.load(), RETRY_DELAY);
    }

    function resume() {
        const video = videoRef.current;
        const state = resumeRef.current;
        resumeRef.current = null;
        if (!video) return;
        if (state) {
            if (state.time > 0 && Number.isFinite(video.duration)) video.currentTime = state.time;
            // The autoplay attribute would otherwise start a film the viewer had paused.
            if (state.playing && autoplayAllowed()) video.play().catch(() => {});
            else video.pause();
            return;
        }
        // First load: pick up where the viewer left off.
        const startAt = startAtRef.current;
        startAtRef.current = 0;
        if (startAt >= RESUME_MIN_SECONDS && Number.isFinite(video.duration) && startAt < video.duration) {
            video.currentTime = startAt;
            toast.add({ title: t("Resumed at {time}", { time: formatTime(startAt) }), type: "success" });
        }
    }

    return (
        <div className="flex flex-col gap-3">
            <div className="aspect-video w-full overflow-hidden rounded-lg bg-black flex items-center justify-center">
                {source ? (
                    <video
                        ref={videoRef}
                        src={source}
                        controls
                        autoPlay={autoplayAllowed()}
                        className="h-full w-full"
                        crossOrigin="use-credentials"
                        onLoadedMetadata={resume}
                        onPlay={() => { playingRef.current = true; }}
                        onTimeUpdate={trackProgress}
                        onPause={(event) => { playingRef.current = false; trackProgress(event); }}
                        onEnded={(event) => { playingRef.current = false; trackProgress(event); }}
                        onError={retryLater}
                    >
                        {readySubtitles.map((subtitle) => (
                            <track
                                key={subtitle.language}
                                kind="subtitles"
                                src={tracks[subtitle.language]?.url || subtitle.url}
                                srcLang={subtitle.language}
                                label={languageName(subtitle.language, language)}
                                default={subtitle.language === defaultSubtitle}
                            />
                        ))}
                    </video>
                ) : !requested ? (
                    <Button size="lg" onClick={requestDownload} disabled={starting}>{starting ? t("Starting...") : t("▶ Play")}</Button>
                ) : download?.status === "failed" ? (
                    <div className="text-center text-white p-4">
                        <p className="font-medium">{t("This movie could not be downloaded.")}</p>
                        <p className="text-sm text-white/70">{download.error}</p>
                        <Button className="mt-3" variant="secondary" onClick={requestDownload}>{t("Retry")}</Button>
                    </div>
                ) : (
                    <div className="text-center text-white p-4">
                        <p className="font-medium">
                            {download?.status === "queued" && t("Waiting for the download to start...")}
                            {download?.status === "downloading" && t(download.num_peers === 1 ? "Downloading {progress}% ({rate} KiB/s, {peers} peer)" : "Downloading {progress}% ({rate} KiB/s, {peers} peers)", { progress: download.progress, rate: Math.round(download.download_rate / 1024), peers: download.num_peers })}
                            {download?.status === "processing" && t("Preparing the file...")}
                            {!download && t("Starting...")}
                        </p>
                        <p className="text-sm text-white/70">{t("Playback starts as soon as enough data is available.")}</p>
                    </div>
                )}
            </div>
            {error && <p className="text-sm text-destructive">{error}</p>}
            {download && (
                <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-muted-foreground">
                    {qualities.length > 1 && (
                        <label className="flex items-center gap-2">
                            <span>{t("Quality")}</span>
                            <NativeSelect size="sm" value={sources[quality] ? quality : "original"} onChange={changeQuality} disabled={!source}>
                                {qualities.map((item) => {
                                    const key = qualityKey(item);
                                    const ready = selectable.includes(item);
                                    return (
                                        <NativeSelectOption key={key} value={key} disabled={!ready}>
                                            {item.label}{item.original ? ` ${t("(source)")}` : ""}{ready ? "" : ` ${t("– preparing...")}`}
                                        </NativeSelectOption>
                                    );
                                })}
                            </NativeSelect>
                        </label>
                    )}
                    <p>
                        {download.status === "ready" ? t("Stored on the server.") : download.status === "downloading" ? t("Download: {progress}%", { progress: download.progress }) : null}
                        {download.subtitles.length > 0 && (
                            <> · {t("Subtitles: {list}", { list: download.subtitles.map((subtitle) => `${languageName(subtitle.language, language)} (${t(subtitle.status === "ready" && !subtitle.aligned ? "syncing" : subtitle.status)})`).join(", ") })}</>
                        )}
                    </p>
                </div>
            )}
        </div>
    );
}

function CommentItem({ comment, own, onChanged }) {
    const { t, language } = useTranslation();
    const [editing, setEditing] = useState(false);
    const [text, setText] = useState(comment.comment);

    async function save(e) {
        e.preventDefault();
        try {
            onChanged(await commentsApi.update(comment.id, text));
            setEditing(false);
        } catch (err) {
            toast.add({ title: t("Error"), description: err.message, type: "error" });
        }
    }

    async function remove() {
        try {
            await commentsApi.remove(comment.id);
            onChanged(null);
        } catch (err) {
            toast.add({ title: t("Error"), description: err.message, type: "error" });
        }
    }

    const profilePath = `/users/${comment.user_id}`;
    const pictureUrl = useAvatarUrl(comment.user_id);

    return (
        <div className="flex gap-3">
            <Link to={profilePath} aria-label={t("Profile of {username}", { username: comment.username })} className="shrink-0 rounded-full focus-visible:outline-none focus-visible:ring-3 focus-visible:ring-ring/50">
                <Avatar className="size-8">
                    {pictureUrl && <AvatarImage src={pictureUrl} alt="" />}
                    <AvatarFallback>{comment.username[0].toUpperCase()}</AvatarFallback>
                </Avatar>
            </Link>
            {/* min-w-0: a flex item otherwise grows with its longest word and overflows the page. */}
            <div className="flex min-w-0 flex-1 flex-col gap-1">
                <div className="flex items-center gap-2">
                    <Link to={profilePath} className="font-medium text-sm underline-offset-4 hover:underline">{comment.username}</Link>
                    <span className="text-xs text-muted-foreground">{new Date(comment.created_at).toLocaleString(language)}</span>
                    {own && !editing && (
                        <span className="ml-auto flex gap-1">
                            <Button type="button" variant="ghost" size="sm" onClick={() => setEditing(true)}>{t("Edit")}</Button>
                            <Button type="button" variant="ghost" size="sm" onClick={remove}>{t("Delete")}</Button>
                        </span>
                    )}
                </div>
                {editing ? (
                    <form onSubmit={save} className="flex flex-col gap-2">
                        <textarea
                            className="min-h-16 rounded-md border border-input bg-transparent px-2.5 py-1 text-sm"
                            value={text}
                            maxLength={COMMENT_MAX_LENGTH}
                            required
                            onChange={(e) => setText(e.target.value)}
                        />
                        <div className="flex gap-2 self-end">
                            <Button type="button" variant="outline" size="sm" onClick={() => { setEditing(false); setText(comment.comment); }}>{t("Cancel")}</Button>
                            <Button type="submit" size="sm">{t("Save")}</Button>
                        </div>
                    </form>
                ) : (
                    // Sentences wrap at their spaces; a single word too long for the line scrolls instead of being cut.
                    <p className="overflow-x-auto text-sm whitespace-pre-wrap">{comment.comment}</p>
                )}
            </div>
        </div>
    );
}

// Used from effects too: the module-level translation keeps them free of the hook.
function showError(err) {
    toast.add({ title: translate("Error"), description: err.message, type: "error" });
}

function Comments({ movieId }) {
    const { user } = useAuth();
    const { t } = useTranslation();
    const [comments, setComments] = useState([]);
    const [nextPage, setNextPage] = useState(null);
    const [text, setText] = useState("");

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
            setComments((current) => appendPage(current, data.results));
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
            showError(err);
        }
    }

    function replace(id, updated) {
        setComments((current) => (updated ? current.map((c) => (c.id === id ? updated : c)) : current.filter((c) => c.id !== id)));
    }

    return (
        <div className="flex flex-col gap-4">
            <h2 className="text-lg font-semibold">{t("Comments")}</h2>
            <form onSubmit={submit} className="flex flex-col gap-2">
                <textarea
                    className="min-h-20 rounded-md border border-input bg-transparent px-2.5 py-1 text-sm"
                    placeholder={t("Write a comment...")}
                    value={text}
                    maxLength={COMMENT_MAX_LENGTH}
                    onChange={(e) => setText(e.target.value)}
                />
                <Button type="submit" className="self-end" disabled={!text.trim()}>{t("Publish")}</Button>
            </form>
            <Separator />
            <div className="flex flex-col gap-4">
                {comments.length === 0 && <p className="text-sm text-muted-foreground">{t("No comment yet.")}</p>}
                {comments.map((comment) => (
                    <CommentItem
                        key={comment.id}
                        comment={comment}
                        own={comment.user_id === user.id}
                        onChanged={(updated) => replace(comment.id, updated)}
                    />
                ))}
                {nextPage && (
                    <Button type="button" variant="outline" className="self-center" onClick={loadMore}>{t("Load more")}</Button>
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
    const { t } = useTranslation();
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
    if (!film) return <p className="p-8 text-muted-foreground">{t("Loading...")}</p>;

    const people = [
        ["Director", "Directors", film.directors],
        ["Producer", "Producers", film.producers],
    ].filter(([, , names]) => names.length > 0);

    return (
        <div className="w-full max-w-4xl mx-auto p-4 flex flex-col gap-4">
            <Player movieId={film.id} initialStatus={film.download_status} initialProgress={film.progress} />

            <div className="flex items-start justify-between gap-4">
                <h1 className="text-2xl font-bold">{film.title}</h1>
                {film.watched && <Badge variant="secondary">{t("Watched")}</Badge>}
            </div>
            <div className="flex flex-wrap gap-2">
                {film.rating != null && <Badge>⭐ {film.rating.toFixed(1)}/10</Badge>}
                {film.year && <Badge variant="secondary">{film.year}</Badge>}
                {film.runtime && <Badge variant="secondary">{t("{runtime} min", { runtime: film.runtime })}</Badge>}
                {film.genres.map((genre) => <Badge key={genre} variant="secondary">{genre}</Badge>)}
                {film.imdb_id && (
                    <a className="text-xs underline self-center" href={`https://www.imdb.com/title/${film.imdb_id}/`} target="_blank" rel="noreferrer">IMDb</a>
                )}
            </div>
            <Separator />
            <div className="grid gap-6 md:grid-cols-[200px_1fr]">
                {film.cover_url ? (
                    <img src={film.cover_url} alt="" className="w-full rounded-lg object-cover" />
                ) : (
                    <div className="aspect-[2/3] w-full overflow-hidden rounded-lg">
                        <CoverPlaceholder title={film.title} year={film.year} />
                    </div>
                )}
                <div className="flex flex-col gap-3">
                    <p className="text-muted-foreground">{film.overview || t("No summary available.")}</p>
                    {people.map(([one, many, names]) => (
                        <p key={one} className="text-sm"><span className="font-medium">{t(names.length > 1 ? many : one)}:</span> {names.join(", ")}</p>
                    ))}
                    {film.cast.length > 0 && (
                        <div>
                            <p className="text-sm font-medium">{t("Cast")}</p>
                            <ul className="mt-1 flex flex-wrap gap-2">
                                {film.cast.map((member) => (
                                    <li key={member.name} className="flex items-center gap-2 rounded-md bg-muted px-2 py-1 text-xs">
                                        <Avatar className="size-6">
                                            {/* The fallback initial only shows while there is no picture, or when it fails to load. */}
                                            {member.picture_url && <AvatarImage src={member.picture_url} alt="" />}
                                            <AvatarFallback>{member.name[0]}</AvatarFallback>
                                        </Avatar>
                                        <span>{member.character ? t("{name} as {character}", { name: member.name, character: member.character }) : member.name}</span>
                                    </li>
                                ))}
                            </ul>
                        </div>
                    )}
                    <p className="text-xs text-muted-foreground">
                        {t(film.sources.length > 1 ? "Sources" : "Source")}: {film.sources.map((source, index) => (
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
