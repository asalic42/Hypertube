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
import { NativeSelect } from "@/components/ui/native-select";
import { toast } from "@/components/ui/toast";
import { auth as authApi, users as usersApi } from "@/lib/api";
import { useAuth } from "@/hooks/useAuth";
import { Avatar, AvatarImage, AvatarFallback } from "@/components/ui/avatar";
import AuthLayout from "@/components/AuthLayout";
import { LANGUAGES } from "@/lib/languages";

const AVATAR_TYPES = ["image/jpeg", "image/png", "image/webp"];
const AVATAR_MAX_BYTES = 5 * 1024 * 1024;


export default function Signup() {
    const navigate = useNavigate();
    const { updateUser } = useAuth();
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

    function handleFileChange(e) {
        const file = e.target.files[0];
        if (!file) return;
        // Same limits as the users service, so a bad picture is refused before the upload.
        if (!AVATAR_TYPES.includes(file.type)) {
            toast.add({ title: "Unsupported picture", description: "Use a JPEG, PNG or WebP image.", type: "error" });
            e.target.value = "";
            return;
        }
        if (file.size > AVATAR_MAX_BYTES) {
            toast.add({ title: "Picture too large", description: "Choose an image of 5 MB or less.", type: "error" });
            e.target.value = "";
            return;
        }
        setFormData({ ...formData, avatar: file });
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
            toast.add({ title: "Error", description: "The passwords do not match.", type: "error" });
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
            firstname: formData.firstname,
            lastname: formData.lastname,
            preferredLanguage: formData.preferredLanguage,
            avatar: formData.avatar,
        };

        let me;
        try {
            // The account first: its token is what allows the profile to be created.
            me = await authApi.register(account);
        } catch (err) {
            toast.add({ title: "Could not create the account", description: err.message, type: "error" });
            setSubmitting(false);
            return;
        }
        updateUser(me);
        try {
            await usersApi.create(profile);
        } catch (err) {
            // The account exists and is logged in: the profile can be completed from its page.
            toast.add({ title: "Account created, profile incomplete", description: err.message, type: "error" });
            navigate('/profile');
            return;
        }
        toast.add({
            title: "Welcome!",
            description: "Your account is ready.",
            type: "success",
        });
        navigate('/home');
    }

    return (
        <AuthLayout>
            <CardHeader>
                <CardTitle>Create account</CardTitle>
                <CardDescription>
                    Enter your information to create an account
                </CardDescription>
                <CardAction>
                    <Button render={<Link to="/login" />} nativeButton={false} variant="link">
                        Login
                    </Button>
                </CardAction>
            </CardHeader>

            <CardContent>
                <form id="signup-form" onSubmit={handleSubmit}>
                    <div className="flex flex-col gap-5 sm:gap-6">

                        <div className="grid gap-2">
                            <Label htmlFor="username">Username</Label>
                            <Input
                                id="username"
                                type="text"
                                name="username"
                                autoComplete="username"
                                value={formData.username}
                                onChange={handleChange}
                                required
                            />
                        </div>

                        <div className="grid gap-2">
                            <Label htmlFor="email">Email</Label>
                            <Input
                                id="email"
                                type="email"
                                name="email"
                                autoComplete="email"
                                placeholder="m@example.com"
                                value={formData.email}
                                onChange={handleChange}
                                required
                            />
                        </div>

                        <div className="grid gap-5 sm:grid-cols-2 sm:gap-4">
                            <div className="grid gap-2">
                                <Label htmlFor="firstname">First name</Label>
                                <Input
                                    id="firstname"
                                    type="text"
                                    name="firstname"
                                    autoComplete="given-name"
                                    value={formData.firstname}
                                    onChange={handleChange}
                                    required
                                />
                            </div>

                            <div className="grid gap-2">
                                <Label htmlFor="lastname">Last name</Label>
                                <Input
                                    id="lastname"
                                    type="text"
                                    name="lastname"
                                    autoComplete="family-name"
                                    value={formData.lastname}
                                    onChange={handleChange}
                                    required
                                />
                            </div>
                        </div>

                        <div className="grid gap-5 sm:grid-cols-2 sm:gap-4">
                            <div className="grid gap-2">
                                <Label htmlFor="password">Password</Label>
                                <Input
                                    id="password"
                                    type="password"
                                    name="password"
                                    autoComplete="new-password"
                                    value={formData.password}
                                    onChange={handleChange}
                                    required
                                />
                            </div>

                            <div className="grid gap-2">
                                <Label htmlFor="confirm_password">Password confirmation</Label>
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
                            <Label htmlFor="profilePic">Avatar</Label>
                            {preview && (
                            <div className="flex items-center gap-3">
                                <Avatar className="size-20 sm:size-24">
                                    <AvatarImage src={preview} alt="Preview" />
                                    <AvatarFallback>?</AvatarFallback>
                                </Avatar>
                                <Button
                                    type="button"
                                    variant="ghost"
                                    size="sm"
                                    onClick={handleRemovePhoto}
                                >Remove photo</Button>
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
                            <Label htmlFor="preferredLanguage">Language</Label>
                            <NativeSelect
                                id="preferredLanguage"
                                name="preferredLanguage"
                                className="w-full"
                                value={formData.preferredLanguage}
                                onChange={handleChange}
                            >
                                {LANGUAGES.map(([value, name]) => (
                                    <option key={value} value={value}>{name}</option>
                                ))}
                            </NativeSelect>
                        </div>

                        <Button type="submit" className="h-10 w-full sm:h-9" disabled={submitting}>
                            {submitting ? "Creating the account..." : "Signup"}
                        </Button>
                    </div>
                </form>
            </CardContent>
        </AuthLayout>
    )
}
