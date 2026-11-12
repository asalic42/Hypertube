import { useState, useEffect, useRef } from "react";
import { Button } from "@/components/ui/button"
import {
  CardHeader,
  CardTitle,
  CardDescription,
  CardAction,
  CardContent
} from "@/components/ui/card";
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Link } from "react-router-dom";
import { useNavigate } from "react-router-dom";
import { NativeSelect, NativeSelectOption } from "@/components/ui/native-select";
import { toast } from "@/components/ui/toast";
import { auth as authApi, users as usersApi } from "@/lib/api";
import { useAuth } from "@/hooks/useAuth";
import { Avatar, AvatarImage, AvatarFallback } from "@/components/ui/avatar";
import AuthLayout from "@/components/AuthLayout";
import { LANGUAGES } from "@/lib/languages";
import { languageName } from "@/lib/i18n";
import { PASSWORD_MIN_LENGTH, PASSWORD_PROBLEM_PARAMS, passwordProblem } from "@/lib/passwordRules";
import { useTranslation } from "@/hooks/useTranslation";
import { AVATAR_TYPES, avatarFileProblem } from "@/lib/avatarFile";


/** Saves the new account's profile: created, or completed when the users service already holds one. */
async function saveProfile(userId, profile) {
    try {
        return await usersApi.create(profile);
    } catch (err) {
        if (err.status !== 409) throw err;
        return usersApi.update(userId, profile);
    }
}

export default function Signup() {
    const navigate = useNavigate();
    const { updateUser } = useAuth();
    const { t, language, setLanguage } = useTranslation();
    const [formData, setFormData] = useState({
        email: '',
        username: '',
        password: '',
        confirm_password: '',
        lastname: '',
        firstname: '',
        avatar: null,
        preferredLanguage: "en"
    });
    const [preview, setPreview] = useState(null);
    const [submitting, setSubmitting] = useState(false);
    const fileInputRef = useRef(null);

    // nettoyage memoire au demontage du composant
    // The preview is an object URL: release it when replaced or when leaving the page.
    useEffect(() => () => preview && URL.revokeObjectURL(preview), [preview]);

    async function handleFileChange(e) {
        const input = e.target;
        const file = input.files[0];
        if (!file) return;
        // Same limits as the users service, and a decode, so a bad picture is
        // refused here and never blocks the rest of the form.
        const problem = await avatarFileProblem(file);
        if (problem) {
            toast.add({ title: t(problem.title), description: t(problem.description), type: "error" });
            input.value = "";
            return;
        }
        setFormData((current) => ({ ...current, avatar: file }));
        setPreview(URL.createObjectURL(file));
    }

    function handleRemovePhoto() {
        if (preview) {
            URL.revokeObjectURL(preview);
        }
        setFormData({ ...formData, avatar: null });
        setPreview(null);
        if (fileInputRef.current) {
            fileInputRef.current.value = "";
        }
    }

    function handleChange(e) {
        setFormData({ ...formData, [e.target.name]: e.target.value });
    }

    async function handleSubmit(e) {
        e.preventDefault();
        if (formData.password !== formData.confirm_password) {
            toast.add({ title: t("Error"), description: t("The passwords do not match."), type: "error" });
            return;
        }
        // Checked before the account exists: the users service would refuse a
        // blank name once it is created, leaving an account without a profile.
        const firstname = formData.firstname.trim();
        const lastname = formData.lastname.trim();
        if (!firstname || !lastname) {
            toast.add({ title: t("Error"), description: t("The first and last names cannot be empty."), type: "error" });
            return;
        }
        const problem = passwordProblem(formData.password, { username: formData.username, email: formData.email });
        if (problem) {
            toast.add({ title: t("Could not create the account"), description: t(problem, PASSWORD_PROBLEM_PARAMS), type: "error" });
            return;
        }
        setSubmitting(true);

        const account = {
            username: formData.username,
            email: formData.email,
            password: formData.password,
            password_confirmation: formData.confirm_password,
        };
        const profile = {
            firstname,
            lastname,
            preferredLanguage: formData.preferredLanguage,
            avatar: formData.avatar,
        };

        let me;
        try {
            // The account first: its token is what allows the profile to be created.
            me = await authApi.register(account);
        } catch (err) {
            toast.add({ title: t("Could not create the account"), description: err.message, type: "error" });
            setSubmitting(false);
            return;
        }
        // The profile is saved before the app learns of the login: once it does, the
        // language provider reads the profile, and the users service would create an
        // empty one for the owner, which the creation below would then collide with.
        let pictureError = null;
        try {
            await saveProfile(me.id, profile);
        } catch (err) {
            // Only the picture refused: the names are saved without it.
            const retried = profile.avatar && err.data?.avatar
                ? await saveProfile(me.id, { ...profile, avatar: null }).then(() => null, (retryErr) => retryErr)
                : err;
            if (retried) {
                // The account exists and is logged in: the profile can be completed from its page.
                updateUser(me);
                toast.add({ title: t("Account created, profile incomplete"), description: retried.message, type: "error" });
                navigate('/profile');
                return;
            }
            pictureError = err;
        }
        updateUser(me);
        setLanguage(formData.preferredLanguage);
        if (pictureError) {
            toast.add({ title: t("Account created without the picture"), description: pictureError.message, type: "error" });
            navigate('/profile');
            return;
        }
        toast.add({
            title: t("Welcome!"),
            description: t("Your account is ready."),
            type: "success",
        });
        navigate('/home');
    }

    return (
        <AuthLayout>
            <CardHeader>
                <CardTitle>{t("Create account")}</CardTitle>
                <CardDescription>
                    {t("Enter your information to create an account")}
                </CardDescription>
                <CardAction>
                    <Button render={<Link to="/login" />} nativeButton={false} variant="link">
                        {t("Login")}
                    </Button>
                </CardAction>
            </CardHeader>

            <CardContent>
                <form id="signup-form" onSubmit={handleSubmit}>
                    <div className="flex flex-col gap-5 sm:gap-6">

                        <div className="grid gap-2">
                            <Label htmlFor="username">{t("Username")}</Label>
                            <Input
                                id="username"
                                type="text"
                                name="username"
                                autoComplete="username"
                                value={formData.username}
                                onChange={handleChange}
                                required
                                minLength={3}
                                maxLength={30}
                                pattern="[A-Za-z0-9][A-Za-z0-9._\-]*"
                                title={t("3 to 30 letters, digits, dots, underscores or dashes, starting with a letter or digit.")}
                            />
                        </div>

                        <div className="grid gap-2">
                            <Label htmlFor="email">{t("Email")}</Label>
                            <Input
                                id="email"
                                type="email"
                                name="email"
                                autoComplete="email"
                                value={formData.email}
                                onChange={handleChange}
                                required
                            />
                        </div>

                        <div className="grid gap-5 sm:grid-cols-2 sm:gap-4">
                            <div className="grid gap-2">
                                <Label htmlFor="firstname">{t("First name")}</Label>
                                <Input
                                    id="firstname"
                                    type="text"
                                    name="firstname"
                                    autoComplete="given-name"
                                    value={formData.firstname}
                                    onChange={handleChange}
                                    required
                                    maxLength={128}
                                />
                            </div>

                            <div className="grid gap-2">
                                <Label htmlFor="lastname">{t("Last name")}</Label>
                                <Input
                                    id="lastname"
                                    type="text"
                                    name="lastname"
                                    autoComplete="family-name"
                                    value={formData.lastname}
                                    onChange={handleChange}
                                    required
                                    maxLength={128}
                                />
                            </div>
                        </div>

                        <div className="grid gap-5 sm:grid-cols-2 sm:gap-4">
                            <div className="grid gap-2">
                                <Label htmlFor="password">{t("Password")}</Label>
                                <Input
                                    id="password"
                                    type="password"
                                    name="password"
                                    autoComplete="new-password"
                                    value={formData.password}
                                    onChange={handleChange}
                                    required
                                    minLength={PASSWORD_MIN_LENGTH}
                                />
                            </div>

                            <div className="grid gap-2">
                                <Label htmlFor="confirm_password">{t("Password confirmation")}</Label>
                                <Input
                                    id="confirm_password"
                                    type="password"
                                    name="confirm_password"
                                    autoComplete="new-password"
                                    value={formData.confirm_password}
                                    onChange={handleChange}
                                    required
                                />
                            </div>
                        </div>

                        <div className="grid gap-2">
                            <Label htmlFor="profilePic">{t("Avatar")}</Label>
                            {preview && (
                            <div className="flex items-center gap-3">
                                <Avatar className="size-20 sm:size-24">
                                    <AvatarImage src={preview} alt={t("Preview")} />
                                    <AvatarFallback>?</AvatarFallback>
                                </Avatar>
                                <Button
                                    type="button"
                                    variant="ghost"
                                    size="sm"
                                    onClick={handleRemovePhoto}
                                >{t("Remove photo")}</Button>
                            </div>
                            )}
                            <Input
                                ref={fileInputRef}
                                id="profilePic"
                                type="file"
                                name="avatar"
                                accept={AVATAR_TYPES.join(",")}
                                className="h-auto py-2"
                                onChange={handleFileChange}
                            />
                        </div>

                        <div className="grid gap-2">
                            <Label htmlFor="preferredLanguage">{t("Language")}</Label>
                            <NativeSelect
                                id="preferredLanguage"
                                name="preferredLanguage"
                                className="w-full"
                                value={formData.preferredLanguage}
                                onChange={handleChange}
                            >
                                {LANGUAGES.map(([value]) => (
                                    <NativeSelectOption key={value} value={value}>{languageName(value, language)}</NativeSelectOption>
                                ))}
                            </NativeSelect>
                        </div>

                        <Button type="submit" className="h-10 w-full sm:h-9" disabled={submitting}>
                            {submitting ? t("Creating the account...") : t("Signup")}
                        </Button>
                    </div>
                </form>
            </CardContent>
        </AuthLayout>
    )
}
