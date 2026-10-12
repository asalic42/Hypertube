// Playback through Media Source Extensions: the page fetches the video itself
// and pushes it into the <video> element's buffers, instead of handing the
// browser a URL. The server is untouched: the same stream endpoints are read,
// by byte ranges when it allows them, front to back otherwise.
//
// mp4box.js turns whatever MP4 the server sends (index at the start or at the
// end, already fragmented or not) into the fragmented segments MSE requires.

import { createFile, MP4BoxBuffer } from "mp4box";

// Bytes asked per request. Large enough to amortise the round trip, small
// enough that a seek is not stuck behind a big download.
export const CHUNK_SIZE = 1024 * 1024;
// Fetching pauses when this much is buffered ahead of the playhead, and resumes below the low mark.
export const BUFFER_AHEAD = 45;
export const BUFFER_RESUME = 20;
// Frames per media segment handed to the SourceBuffer.
const SEGMENT_SAMPLES = 250;

/** True when this browser can play H.264/AAC MP4 through MSE (the format every stored film uses). */
export function supportsMse() {
    return typeof MediaSource !== "undefined" && MediaSource.isTypeSupported('video/mp4; codecs="avc1.42E01E, mp4a.40.2"');
}

// --- Demuxer ----------------------------------------------------------------
// Everything that does not need a browser lives here, so it can be tested in Node.

/**
 * Feeds file bytes to mp4box and reports, per track, the initialisation
 * segment then the media segments. `append` returns the file offset the
 * next bytes should start at, which is how a file with its index at the end
 * tells the loader to jump there.
 */
export class Demuxer {
    constructor({ onReady, onSegment, onError }) {
        this.onReady = onReady;
        this.onSegment = onSegment;
        this.onError = onError;
        this.info = null;
        this.tracks = [];
        this.file = createFile();
        this.file.onError = (module, message) => onError(new Error(`${module}: ${message}`));
        this.file.onReady = (info) => this._ready(info);
        this.file.onSegment = (id, user, buffer, nextSample, last) => {
            // Samples already turned into segments can be dropped from memory.
            this.file.releaseUsedSamples(id, nextSample);
            onSegment(id, buffer, last);
        };
    }

    _ready(info) {
        this.info = info;
        // Only what MSE can play: subtitle or hint tracks stay out.
        this.tracks = [...info.videoTracks, ...info.audioTracks].map((track) => ({
            id: track.id,
            kind: info.videoTracks.includes(track) ? "video" : "audio",
            mime: `${info.videoTracks.includes(track) ? "video" : "audio"}/mp4; codecs="${track.codec}"`,
            duration: track.duration / track.timescale,
        }));
        if (this.tracks.length === 0) {
            this.onError(new Error("the file has no video or audio track"));
            return;
        }
        for (const track of this.tracks) {
            this.file.setSegmentOptions(track.id, null, { nbSamples: SEGMENT_SAMPLES, rapAlignement: true });
        }
        const inits = this.file.initializeSegmentation("per-track");
        this.onReady({
            duration: info.duration / info.timescale,
            tracks: this.tracks,
            initSegments: Object.fromEntries(inits.map((init) => [init.id, init.buffer])),
        });
        this.file.start();
    }

    /** Parse bytes that sit at `offset` in the file. Returns where the next bytes should start. */
    append(bytes, offset) {
        return this.file.appendBuffer(MP4BoxBuffer.fromArrayBuffer(bytes, offset));
    }

    /** Restart segmentation at the keyframe before `time`; returns the file offset to fetch from. */
    seek(time) {
        return this.file.seek(time, true).offset;
    }

    /** No more bytes will come: emit what is still pending. */
    flush() {
        this.file.flush();
    }
}

// --- Loader -----------------------------------------------------------------

/**
 * Reads a URL piece by piece. With HTTP ranges, any offset can be asked and
 * `size` is known after the first answer. Without them (a live conversion),
 * the body is read in order and seeking is not possible.
 */
export class Loader {
    constructor(url, fetchImpl = (...args) => fetch(...args)) {
        this.url = url;
        this.fetch = fetchImpl;
        this.size = null;
        this.ranges = null; // unknown until the first answer
        this.reader = null;
        this.controller = null;
    }

    /** Bytes starting at `offset`: `{ bytes, offset }`, or null at the end of the file. */
    async read(offset) {
        if (this.ranges === false) return this._readStream();
        this.controller = new AbortController();
        const response = await this.fetch(this.url, {
            headers: { Range: `bytes=${offset}-${offset + CHUNK_SIZE - 1}` },
            credentials: "include",
            signal: this.controller.signal,
        });
        if (response.status === 206) {
            this.ranges = true;
            const total = /\/(\d+)$/.exec(response.headers.get("Content-Range") || "");
            if (total) this.size = Number(total[1]);
            const bytes = await response.arrayBuffer();
            return bytes.byteLength ? { bytes, offset } : null;
        }
        if (response.status === 200 && this.ranges === null) {
            // The server ignores ranges: read the body as it comes, from the start.
            this.ranges = false;
            this.reader = response.body.getReader();
            this.streamOffset = 0;
            return this._readStream();
        }
        if (response.status === 416) return null;
        throw new Error(`stream request failed (${response.status})`);
    }

    async _readStream() {
        const { value, done } = await this.reader.read();
        if (done) return null;
        const offset = this.streamOffset;
        this.streamOffset += value.byteLength;
        return { bytes: value.buffer.slice(value.byteOffset, value.byteOffset + value.byteLength), offset };
    }

    abort() {
        this.controller?.abort();
        this.reader?.cancel().catch(() => {});
        this.reader = null;
    }
}

// --- Player -----------------------------------------------------------------

/** Seconds buffered from `time` onwards in `ranges`, 0 when `time` is not buffered. */
export function bufferedAhead(ranges, time) {
    for (let index = 0; index < ranges.length; index += 1) {
        if (ranges.start(index) <= time + 0.1 && time < ranges.end(index)) return ranges.end(index) - time;
    }
    return 0;
}

/**
 * Drive a <video> element from `url` through MSE. Returns a handle with
 * `destroy()`. `onFallback(reason)` is called when MSE cannot play this
 * file, so the caller can give the URL to the element directly instead.
 */
export function attachMse(video, url, { onFallback, onStatus } = {}) {
    const mediaSource = new MediaSource();
    const loader = new Loader(url);
    const buffers = new Map(); // track id -> { sourceBuffer, queue, busy }
    let destroyed = false;
    let ended = false;
    let nextOffset = 0;
    let fetching = false;
    let waiting = false; // paused because enough is buffered
    let generation = 0; // bumped on every seek, so stale fetches are ignored

    function fail(reason) {
        if (destroyed) return;
        destroy();
        onFallback?.(reason);
    }

    const demuxer = new Demuxer({
        onError: (error) => fail(error.message),
        onReady: ({ tracks, duration, initSegments }) => {
            try {
                for (const track of tracks) {
                    if (!MediaSource.isTypeSupported(track.mime)) throw new Error(`unsupported codec ${track.mime}`);
                    const sourceBuffer = mediaSource.addSourceBuffer(track.mime);
                    const state = { sourceBuffer, queue: [], busy: false };
                    sourceBuffer.addEventListener("updateend", () => {
                        state.busy = false;
                        pump(state);
                        schedule();
                    });
                    sourceBuffer.addEventListener("error", () => fail("the browser refused the segments"));
                    buffers.set(track.id, state);
                    enqueue(state, initSegments[track.id]);
                }
                if (Number.isFinite(duration) && duration > 0) mediaSource.duration = duration;
                onStatus?.({ tracks: tracks.map((track) => track.mime), ranges: loader.ranges });
            } catch (error) {
                fail(error.message);
            }
        },
        onSegment: (id, buffer) => {
            const state = buffers.get(id);
            if (state) enqueue(state, buffer);
        },
    });

    function enqueue(state, buffer) {
        state.queue.push(buffer);
        pump(state);
    }

    function pump(state) {
        if (destroyed || state.busy || state.queue.length === 0) return;
        if (mediaSource.readyState !== "open") return;
        try {
            state.busy = true;
            state.sourceBuffer.appendBuffer(state.queue.shift());
        } catch (error) {
            // QuotaExceededError: the browser is full, evict what was already played.
            state.busy = false;
            if (error.name === "QuotaExceededError") {
                evict(state);
            } else {
                fail(error.message);
            }
        }
    }

    function evict(state) {
        const keepFrom = Math.max(0, video.currentTime - 10);
        if (keepFrom > 0 && !state.sourceBuffer.updating) {
            state.busy = true;
            state.sourceBuffer.remove(0, keepFrom);
        }
    }

    function queuesEmpty() {
        for (const state of buffers.values()) if (state.busy || state.queue.length) return false;
        return true;
    }

    async function fetchLoop() {
        if (fetching || destroyed || ended) return;
        fetching = true;
        const mine = generation;
        try {
            while (!destroyed && mine === generation) {
                // Backpressure: the segments already handed over must be appended first,
                // and there is no point fetching minutes ahead of the viewer.
                if (!queuesEmpty()) {
                    waiting = true;
                    return;
                }
                if (buffers.size && bufferedAhead(video.buffered, video.currentTime) > BUFFER_AHEAD) {
                    waiting = true;
                    return;
                }
                const chunk = await loader.read(nextOffset);
                if (mine !== generation || destroyed) return;
                if (chunk === null) {
                    ended = true;
                    demuxer.flush();
                    finish();
                    return;
                }
                nextOffset = demuxer.append(chunk.bytes, chunk.offset);
                if (loader.size !== null && nextOffset >= loader.size) {
                    ended = true;
                    demuxer.flush();
                    finish();
                    return;
                }
            }
        } catch (error) {
            if (error.name !== "AbortError") fail(error.message);
        } finally {
            if (mine === generation) fetching = false;
        }
    }

    function finish() {
        // endOfStream must wait until every queued segment is appended.
        const tryEnd = () => {
            if (destroyed || mediaSource.readyState !== "open") return;
            if (!queuesEmpty()) {
                setTimeout(tryEnd, 100);
                return;
            }
            try {
                mediaSource.endOfStream();
            } catch {
                // The element may already have been detached.
            }
        };
        tryEnd();
    }

    function schedule() {
        if (destroyed || ended || fetching) return;
        if (!waiting) return;
        if (!queuesEmpty()) return;
        if (buffers.size && bufferedAhead(video.buffered, video.currentTime) > BUFFER_RESUME) return;
        waiting = false;
        fetchLoop();
    }

    function onSeeking() {
        if (destroyed || loader.ranges !== true || !demuxer.info) return;
        const target = video.currentTime;
        if (bufferedAhead(video.buffered, target) > 0) return; // already there, the element handles it
        generation += 1;
        loader.abort();
        ended = false;
        fetching = false;
        waiting = false;
        for (const state of buffers.values()) {
            state.queue.length = 0;
            if (state.sourceBuffer.updating) {
                try {
                    state.sourceBuffer.abort();
                } catch {
                    // Not open any more: nothing to abort.
                }
                state.busy = false;
            }
        }
        nextOffset = demuxer.seek(target);
        fetchLoop();
    }

    function onTimeUpdate() {
        schedule();
    }

    function onSourceOpen() {
        URL.revokeObjectURL(video.src);
        fetchLoop();
    }

    function destroy() {
        if (destroyed) return;
        destroyed = true;
        loader.abort();
        video.removeEventListener("seeking", onSeeking);
        video.removeEventListener("timeupdate", onTimeUpdate);
        video.removeEventListener("waiting", onTimeUpdate);
        mediaSource.removeEventListener("sourceopen", onSourceOpen);
        if (mediaSource.readyState === "open") {
            try {
                mediaSource.endOfStream();
            } catch {
                // Already closed.
            }
        }
    }

    mediaSource.addEventListener("sourceopen", onSourceOpen);
    video.addEventListener("seeking", onSeeking);
    video.addEventListener("timeupdate", onTimeUpdate);
    video.addEventListener("waiting", onTimeUpdate);
    video.src = URL.createObjectURL(mediaSource);

    return { destroy };
}
