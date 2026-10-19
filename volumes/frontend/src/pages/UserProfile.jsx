import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { Languages, UserRound } from "lucide-react";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import { users as usersApi } from "@/lib/api";
import { useAvatarUrl } from "@/lib/avatars";
import { LANGUAGES } from "@/lib/languages";
import { useAuth } from "@/hooks/useAuth";

/** The public profile of any user: picture, username and name. The email stays private. */
export default function UserProfile() {
    const { username } = useParams();
    const { user: me } = useAuth();
    // Keyed by username, so switching profiles shows "Loading" instead of the previous user.
    const [loaded, setLoaded] = useState({ username: null, profile: null, error: null });
    const pictureUrl = useAvatarUrl(username);

    useEffect(() => {
        let cancelled = false;
        usersApi.get(username)
            .then((profile) => !cancelled && setLoaded({ username, profile, error: null }))
            .catch((err) => !cancelled && setLoaded({
                username,
                profile: null,
                error: err.status === 404 ? "This user does not exist." : err.message,
            }));
        return () => {
            cancelled = true;
        };
    }, [username]);

    const { profile, error } = loaded.username === username ? loaded : { profile: null, error: null };

    if (error) {
        return (
            <div className="w-full max-w-3xl p-4 sm:py-8 flex flex-col items-center gap-4 text-center">
                <h1 className="text-2xl font-bold tracking-tight break-all">{username}</h1>
                <p className="text-destructive">{error}</p>
                <Button render={<Link to="/home" />} nativeButton={false} variant="outline">Back to the library</Button>
            </div>
        );
    }
    if (!profile) {
        return <p className="text-muted-foreground p-4">Loading...</p>;
    }

    const fullName = [profile.firstname, profile.lastname].filter(Boolean).join(" ");
    const languageName = LANGUAGES.find(([code]) => code === profile.preferredLanguage)?.[1];
    const isMe = me?.username === profile.username;

    return (
        <div className="w-full max-w-3xl p-4 sm:py-8">
            <section className="overflow-hidden rounded-2xl bg-card text-card-foreground shadow-xs ring-1 ring-foreground/10">
                <div className="h-28 bg-linear-to-r from-black via-primary/70 to-primary sm:h-32" aria-hidden="true" />
                <div className="px-5 pb-5 sm:px-6 sm:pb-6">
                    <div className="-mt-14 flex flex-col gap-4 sm:-mt-16 sm:flex-row sm:items-end sm:gap-5">
                        <Avatar className="size-28 ring-4 ring-card sm:size-32">
                            {pictureUrl && <AvatarImage src={pictureUrl} alt={`Picture of ${profile.username}`} />}
                            <AvatarFallback className="text-4xl">{profile.username[0].toUpperCase()}</AvatarFallback>
                        </Avatar>
                        <div className="flex min-w-0 flex-1 flex-col gap-1 sm:pb-1">
                            <h1 className="truncate text-2xl font-bold tracking-tight">{profile.username}</h1>
                            <div className="flex flex-wrap gap-x-4 gap-y-1 text-sm text-muted-foreground">
                                <span className="flex items-center gap-1.5"><UserRound className="size-3.5" aria-hidden="true" />{fullName || "No name given"}</span>
                                {languageName && (
                                    <span className="flex items-center gap-1.5"><Languages className="size-3.5" aria-hidden="true" />{languageName}</span>
                                )}
                            </div>
                        </div>
                        {isMe && (
                            <Button render={<Link to="/profile" />} nativeButton={false} variant="outline" size="sm" className="w-fit sm:self-end">
                                Edit my profile
                            </Button>
                        )}
                    </div>
                    <dl className="mt-6 grid grid-cols-[auto_1fr] gap-x-6 gap-y-2 text-sm">
                        <dt className="font-medium">Username</dt>
                        <dd className="text-muted-foreground break-all">{profile.username}</dd>
                        <dt className="font-medium">First name</dt>
                        <dd className="text-muted-foreground">{profile.firstname || "—"}</dd>
                        <dt className="font-medium">Last name</dt>
                        <dd className="text-muted-foreground">{profile.lastname || "—"}</dd>
                    </dl>
                </div>
            </section>
        </div>
    );
}
