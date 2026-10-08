import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import { Dialog, DialogClose, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Separator } from "@/components/ui/separator";
import { users as usersApi } from "@/lib/api";
import { avatarUrl as cachedAvatarUrl } from "@/lib/avatars";
import { useAuth } from "@/hooks/useAuth";


export default function UserProfileDialog({ username, onClose }) {
    return (
        <Dialog open={Boolean(username)} onOpenChange={(open) => !open && onClose()}>
            <DialogContent>
                {username && <Profile key={username} username={username} />}
            </DialogContent>
        </Dialog>
    );
}

function Profile({ username }) {
    const { user: me } = useAuth();
    const [profile, setProfile] = useState(null);
    const [avatarUrl, setAvatarUrl] = useState(null);
    const [error, setError] = useState(null);

    useEffect(() => {
        let cancelled = false;
        usersApi.get(username)
            .then((data) => {
                if (cancelled) return;
                setProfile(data);
                return cachedAvatarUrl(username).then((url) => !cancelled && setAvatarUrl(url));
            })
            .catch((err) => {
                if (cancelled) return;
                setError(err.status === 404 ? "This user does not exist." : err.message);
            });
        return () => {
            cancelled = true;
        };
    }, [username]);

    if (error || !profile) {
        return (
            <DialogHeader>
                <DialogTitle>{username}</DialogTitle>
                <DialogDescription className={error ? "text-destructive" : undefined}>{error || "Loading..."}</DialogDescription>
            </DialogHeader>
        );
    }

    const fullName = [profile.firstname, profile.lastname].filter(Boolean).join(" ");
    const isMe = me?.username === profile.username;

    return (
        <>
            <DialogHeader className="items-center text-center">
                <Avatar className="size-24 sm:size-28">
                    {avatarUrl && <AvatarImage src={avatarUrl} alt={`Picture of ${profile.username}`} />}
                    <AvatarFallback className="text-2xl">{profile.username[0].toUpperCase()}</AvatarFallback>
                </Avatar>
                <DialogTitle className="mt-2 break-all">{profile.username}</DialogTitle>
                <DialogDescription>{fullName || "No name given"}</DialogDescription>
            </DialogHeader>
            <Separator />
            <dl className="grid grid-cols-[auto_1fr] gap-x-6 gap-y-2 text-sm">
                <dt className="font-medium">Username</dt>
                <dd className="text-muted-foreground break-all">{profile.username}</dd>
                <dt className="font-medium">First name</dt>
                <dd className="text-muted-foreground">{profile.firstname || "—"}</dd>
                <dt className="font-medium">Last name</dt>
                <dd className="text-muted-foreground">{profile.lastname || "—"}</dd>
            </dl>
            <DialogFooter>
                {isMe && (
                    <Button render={<Link to="/profile" />} nativeButton={false} variant="outline">
                        Edit my profile
                    </Button>
                )}
                <DialogClose render={<Button variant="ghost" />}>Close</DialogClose>
            </DialogFooter>
        </>
    );
}
