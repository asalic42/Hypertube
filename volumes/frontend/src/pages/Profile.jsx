import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { CalendarDays, Camera, Languages, Mail, ShieldAlert, Trash2, UserRound } from "lucide-react";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import { Dialog, DialogClose, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { NativeSelect } from "@/components/ui/native-select";
import { toast } from "@/components/ui/toast";
import { auth as authApi, users as usersApi } from "@/lib/api";
import { LANGUAGES } from "@/lib/languages";
import { forgetAvatar } from "@/lib/avatars";
import { useAuth } from "@/hooks/useAuth";

// Same limits as the users service, so a bad picture is refused before the upload.
const AVATAR_TYPES = ["image/jpeg", "image/png", "image/webp"];
const AVATAR_MAX_BYTES = 5 * 1024 * 1024;
const TOO_LARGE = "The picture is too large: choose an image of 5 MB or less.";
const BAD_TYPE = "Use a JPEG, PNG or WebP image.";

// A plain sentence for a failed picture upload, whatever layer refused it.
function pictureError(err) {
    if (err.status === 413) return TOO_LARGE;
    if (err.status === 400) {
        const reason = String(err.data?.avatar?.[0] || err.message);
        if (/d[ée]passer|too large|size/i.test(reason)) return TOO_LARGE;
        if (/JPEG|PNG|WebP|image/i.test(reason)) return BAD_TYPE;
    }
    return err.message;
}

/**
 * The account of the connected user. The email lives in the auth service
 * (it is the login), everything else in the users service.
 */
export default function Profile() {
    const { user, updateUser, clearSession } = useAuth();
    const navigate = useNavigate();
    const [form, setForm] = useState(null);
    // Values as last stored, to know what changed on save.
    const [saved, setSaved] = useState(null);
    const [error, setError] = useState(null);
    const [saving, setSaving] = useState(false);

    const [avatarUrl, setAvatarUrl] = useState(null);
    const [avatarFile, setAvatarFile] = useState(null);
    const [avatarPreview, setAvatarPreview] = useState(null);
    const [removingAvatar, setRemovingAvatar] = useState(false);
    const fileInputRef = useRef(null);

    const [confirmingDelete, setConfirmingDelete] = useState(false);
    const [deleting, setDeleting] = useState(false);

    useEffect(() => {
        let cancelled = false;
        Promise.all([usersApi.get(user.username), usersApi.avatarUrl(user.username).catch(() => null)])
            .then(([profile, url]) => {
                if (cancelled) return;
                const values = {
                    firstname: profile.firstname || "",
                    lastname: profile.lastname || "",
                    email: user.email || profile.email || "",
                    preferredLanguage: profile.preferredLanguage || "en",
                };
                setForm(values);
                setSaved(values);
                setAvatarUrl(url);
            })
            .catch((err) => !cancelled && setError(err.message));
        return () => {
            cancelled = true;
        };
    }, [user.username, user.email]);

    // The preview of a chosen picture is an object URL: release it when replaced or on leave.
    useEffect(() => () => avatarPreview && URL.revokeObjectURL(avatarPreview), [avatarPreview]);

    function handleChange(e) {
        setForm({ ...form, [e.target.name]: e.target.value });
    }

    function choosePicture(e) {
        const file = e.target.files[0];
        if (!file) return;
        if (!AVATAR_TYPES.includes(file.type)) {
            toast.add({ title: "Unsupported picture", description: BAD_TYPE, type: "error" });
            e.target.value = "";
            return;
        }
        if (file.size > AVATAR_MAX_BYTES) {
            toast.add({ title: "Picture too large", description: TOO_LARGE, type: "error" });
            e.target.value = "";
            return;
        }
        setAvatarFile(file);
        setAvatarPreview(URL.createObjectURL(file));
    }

    // Removing the picture takes effect at once: it is erased from the storage
    // and the profile without waiting for "Save changes".
    async function removePicture() {
        setAvatarFile(null);
        setAvatarPreview(null);
        if (fileInputRef.current) fileInputRef.current.value = "";
        if (!avatarUrl) return;
        setRemovingAvatar(true);
        try {
            await usersApi.deleteAvatar(user.username);
            forgetAvatar(user.username);
            setAvatarUrl(null);
            toast.add({ title: "Picture removed", description: "Your profile has no picture anymore.", type: "success" });
        } catch (err) {
            // Already gone on the server: reflect it rather than complain.
            if (err.status === 404) setAvatarUrl(null);
            else toast.add({ title: "Could not remove the picture", description: err.message, type: "error" });
        } finally {
            setRemovingAvatar(false);
        }
    }

    const changed = form && saved && (Object.keys(saved).some((key) => form[key] !== saved[key]) || avatarFile);

    function discard() {
        setForm(saved);
        setAvatarFile(null);
        setAvatarPreview(null);
        if (fileInputRef.current) fileInputRef.current.value = "";
    }

    async function save(e) {
        e.preventDefault();
        if (!changed) return;
        setSaving(true);
        try {
            let profile;
            try {
                // The auth service owns the email: change it there first, the users copy follows.
                if (form.email !== saved.email) {
                    updateUser(await authApi.updateMe({ email: form.email }));
                }
                profile = await usersApi.update(user.username, form);
            } catch (err) {
                toast.add({ title: "Could not save your information", description: err.message, type: "error" });
                return;
            }
            const values = {
                firstname: profile.firstname || "",
                lastname: profile.lastname || "",
                email: profile.email || form.email,
                preferredLanguage: profile.preferredLanguage || "en",
            };
            setForm(values);
            setSaved(values);

            // The picture is a separate upload: its failure must not hide that the rest was saved.
            try {
                if (avatarFile) {
                    await usersApi.updateAvatar(user.username, avatarFile);
                    forgetAvatar(user.username);
                    setAvatarUrl(await usersApi.avatarUrl(user.username));
                }
            } catch (err) {
                toast.add({ title: "Could not save the picture", description: pictureError(err), type: "error" });
                return;
            }
            setAvatarFile(null);
            setAvatarPreview(null);
            if (fileInputRef.current) fileInputRef.current.value = "";
            toast.add({ title: "Profile updated", description: "Your information has been saved.", type: "success" });
        } finally {
            setSaving(false);
        }
    }

    async function deleteAccount() {
        setDeleting(true);
        try {
            await usersApi.remove(user.username);
            await authApi.deleteMe();
        } catch (err) {
            toast.add({ title: "Could not delete the account", description: err.message, type: "error" });
            setDeleting(false);
            return;
        }
        clearSession();
        navigate("/login", { replace: true });
        toast.add({ title: "Account deleted", description: "Your account has been removed.", type: "success" });
    }

    if (error) return <p className="p-8 text-destructive">{error}</p>;
    if (!form) return <p className="p-8 text-muted-foreground">Loading...</p>;

    const picture = avatarPreview || avatarUrl;
    const memberSince = user.date_joined
        ? new Date(user.date_joined).toLocaleDateString(undefined, { year: "numeric", month: "long" })
        : null;
    const languageName = LANGUAGES.find(([value]) => value === form.preferredLanguage)?.[1];

    return (
        <div className="w-full max-w-3xl p-4 sm:py-8">
            <input
                ref={fileInputRef}
                type="file"
                accept={AVATAR_TYPES.join(",")}
                className="sr-only"
                aria-label="Profile picture"
                onChange={choosePicture}
            />

            <form id="profile-form" onSubmit={save} className="flex flex-col gap-5">
                {/* Identity: banner, picture and the facts that do not change here. */}
                <section className="overflow-hidden rounded-2xl bg-card text-card-foreground shadow-xs ring-1 ring-foreground/10">
                    <div className="h-28 bg-linear-to-r from-black via-primary/70 to-primary sm:h-32" aria-hidden="true" />
                    <div className="px-5 pb-5 sm:px-6 sm:pb-6">
                        <div className="-mt-14 flex flex-col gap-4 sm:-mt-16 sm:flex-row sm:items-end sm:gap-5">
                            <div className="relative w-fit">
                                <Avatar className="size-28 ring-4 ring-card sm:size-32">
                                    {picture && <AvatarImage src={picture} alt="Your profile picture" />}
                                    <AvatarFallback className="text-4xl">{user.username[0].toUpperCase()}</AvatarFallback>
                                </Avatar>
                                <button
                                    type="button"
                                    onClick={() => fileInputRef.current?.click()}
                                    aria-label={picture ? "Change picture" : "Add a picture"}
                                    title={picture ? "Change picture" : "Add a picture"}
                                    className="absolute right-0 bottom-0 flex size-10 items-center justify-center rounded-full bg-primary text-primary-foreground shadow-md ring-2 ring-card hover:bg-primary/80 focus-visible:outline-none focus-visible:ring-3 focus-visible:ring-ring/50"
                                >
                                    <Camera className="size-4" aria-hidden="true" />
                                </button>
                            </div>
                            <div className="flex min-w-0 flex-1 flex-col gap-1 sm:pb-1">
                                <h1 className="truncate text-2xl font-bold tracking-tight">{user.username}</h1>
                                <div className="flex flex-wrap gap-x-4 gap-y-1 text-sm text-muted-foreground">
                                    <span className="flex items-center gap-1.5"><Mail className="size-3.5" aria-hidden="true" />{saved.email}</span>
                                    {languageName && (
                                        <span className="flex items-center gap-1.5"><Languages className="size-3.5" aria-hidden="true" />{languageName}</span>
                                    )}
                                    {memberSince && (
                                        <span className="flex items-center gap-1.5"><CalendarDays className="size-3.5" aria-hidden="true" />Member since {memberSince}</span>
                                    )}
                                </div>
                            </div>
                            {picture && (
                                <Button type="button" variant="ghost" size="sm" className="w-fit sm:self-end" onClick={removePicture} disabled={removingAvatar}>
                                    <Trash2 aria-hidden="true" />
                                    {removingAvatar ? "Removing..." : avatarPreview ? "Discard picture" : "Remove picture"}
                                </Button>
                            )}
                        </div>
                        {avatarPreview && (
                            <p className="mt-3 text-xs text-muted-foreground">New picture selected. Save your changes to keep it.</p>
                        )}
                    </div>
                </section>

                <Section
                    icon={UserRound}
                    title="Personal information"
                    description="Your name as other viewers see it on your comments, and the email you log in with."
                >
                    <div className="grid gap-4 sm:grid-cols-2">
                        <div className="grid gap-2">
                            <Label htmlFor="firstname">First name</Label>
                            <Input id="firstname" name="firstname" autoComplete="given-name" value={form.firstname} onChange={handleChange} required />
                        </div>
                        <div className="grid gap-2">
                            <Label htmlFor="lastname">Last name</Label>
                            <Input id="lastname" name="lastname" autoComplete="family-name" value={form.lastname} onChange={handleChange} required />
                        </div>
                    </div>
                    <div className="grid gap-2">
                        <Label htmlFor="email">Email</Label>
                        <Input id="email" type="email" name="email" autoComplete="email" value={form.email} onChange={handleChange} required />
                    </div>
                </Section>

                <Section
                    icon={Languages}
                    title="Preferences"
                    description="Subtitles are requested in this language whenever a film has them."
                >
                    <div className="grid gap-2 sm:max-w-xs">
                        <Label htmlFor="preferredLanguage">Language</Label>
                        <NativeSelect id="preferredLanguage" name="preferredLanguage" className="w-full" value={form.preferredLanguage} onChange={handleChange}>
                            {LANGUAGES.map(([value, name]) => (
                                <option key={value} value={value}>{name}</option>
                            ))}
                        </NativeSelect>
                    </div>
                </Section>

                <Section
                    icon={ShieldAlert}
                    title="Danger zone"
                    description="Deleting the account removes your login, profile and picture for good."
                    tone="danger"
                >
                    <Button type="button" variant="destructive" className="w-fit" onClick={() => setConfirmingDelete(true)}>
                        <Trash2 aria-hidden="true" />
                        Delete account
                    </Button>
                </Section>

                {/* Follows the viewer while something is unsaved, so the action is never out of reach. */}
                {changed && (
                    <div className="sticky bottom-4 z-10 flex flex-wrap items-center justify-between gap-3 rounded-xl bg-primary px-4 py-3 text-primary-foreground shadow-lg">
                        <p className="text-sm font-medium">You have unsaved changes</p>
                        <div className="flex gap-2">
                            <Button type="button" variant="ghost" size="sm" className="text-primary-foreground hover:bg-primary-foreground/15 hover:text-primary-foreground" onClick={discard} disabled={saving}>
                                Discard
                            </Button>
                            <Button type="submit" variant="secondary" size="sm" disabled={saving}>
                                {saving ? "Saving..." : "Save changes"}
                            </Button>
                        </div>
                    </div>
                )}
            </form>

            <Dialog open={confirmingDelete} onOpenChange={(open) => !deleting && setConfirmingDelete(open)}>
                <DialogContent showCloseButton={!deleting}>
                    <DialogHeader>
                        <DialogTitle>Delete your account?</DialogTitle>
                        <DialogDescription>
                            This cannot be undone. Your profile and picture are erased and you are logged out.
                        </DialogDescription>
                    </DialogHeader>
                    <DialogFooter>
                        <DialogClose render={<Button variant="outline" />} disabled={deleting}>Cancel</DialogClose>
                        <Button type="button" variant="destructive" onClick={deleteAccount} disabled={deleting}>
                            {deleting ? "Deleting..." : "Delete my account"}
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </div>
    );
}

/** A settings block: heading and explanation on the left, fields on the right from tablets up. */
function Section({ icon: Icon, title, description, tone, children }) {
    const danger = tone === "danger";
    return (
        <section
            className={`grid gap-4 rounded-2xl bg-card p-5 text-card-foreground shadow-xs ring-1 sm:p-6 md:grid-cols-[240px_1fr] md:gap-8 ${danger ? "ring-destructive/30" : "ring-foreground/10"}`}
        >
            <div className="flex flex-col gap-1">
                <h2 className={`flex items-center gap-2 text-base font-semibold ${danger ? "text-destructive" : ""}`}>
                    <Icon className="size-4" aria-hidden="true" />
                    {title}
                </h2>
                <p className="text-sm text-muted-foreground">{description}</p>
            </div>
            <div className="flex flex-col gap-4">{children}</div>
        </section>
    );
}
