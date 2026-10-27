import { useEffect, useState } from "react";
import { users as usersApi } from "@/lib/api";

const TTL = 50 * 60 * 1000;
const cache = new Map();

export function avatarUrl(userId) {
    const entry = cache.get(userId);
    if (entry && entry.expires > Date.now()) return entry.promise;
    const promise = usersApi.avatarUrl(userId).catch(() => null);
    cache.set(userId, { promise, expires: Date.now() + TTL });
    return promise;
}

export function forgetAvatar(userId) {
    cache.delete(userId);
}

export function useAvatarUrl(userId) {
    const [known, setKnown] = useState({ userId: null, url: null });

    useEffect(() => {
        let cancelled = false;
        avatarUrl(userId).then((url) => !cancelled && setKnown({ userId, url }));
        return () => {
            cancelled = true;
        };
    }, [userId]);

    return known.userId === userId ? known.url : null;
}
