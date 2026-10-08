import { useEffect, useState } from "react";
import { users as usersApi } from "@/lib/api";

const TTL = 50 * 60 * 1000;
const cache = new Map();

export function avatarUrl(username) {
    const entry = cache.get(username);
    if (entry && entry.expires > Date.now()) return entry.promise;
    const promise = usersApi.avatarUrl(username).catch(() => null);
    cache.set(username, { promise, expires: Date.now() + TTL });
    return promise;
}

export function forgetAvatar(username) {
    cache.delete(username);
}

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
