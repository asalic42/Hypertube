import { useEffect, useState } from "react";
import { users as usersApi } from "@/lib/api";

// Presigned picture URLs last an hour on the server: keep them a little less.
const TTL = 50 * 60 * 1000;
// username -> { promise, expires }; one request per user, shared by every avatar on screen.
const cache = new Map();

/** The profile picture URL of a user, or null when they have none. Never rejects. */
export function avatarUrl(username) {
    const entry = cache.get(username);
    if (entry && entry.expires > Date.now()) return entry.promise;
    const promise = usersApi.avatarUrl(username).catch(() => null);
    cache.set(username, { promise, expires: Date.now() + TTL });
    return promise;
}

/** After a user changed or removed their picture, so the next lookup asks again. */
export function forgetAvatar(username) {
    cache.delete(username);
}

/** The picture URL of a user for rendering: null until known or when there is none. */
export function useAvatarUrl(username) {
    const [known, setKnown] = useState({ username: null, url: null });

    useEffect(() => {
        let cancelled = false;
        avatarUrl(username).then((url) => !cancelled && setKnown({ username, url }));
        return () => {
            cancelled = true;
        };
    }, [username]);

    return known.username === username ? known.url : null;
}
