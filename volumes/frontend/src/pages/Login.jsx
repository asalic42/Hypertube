import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button"
import {
  CardHeader,
  CardTitle,
  CardDescription,
  CardAction,
  CardContent,
  CardFooter
} from "@/components/ui/card";
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Link, useLocation, useNavigate, useSearchParams } from "react-router-dom";
import { toast } from "@/components/ui/toast";
import { useAuth } from "@/hooks/useAuth";
import AuthLayout from "@/components/AuthLayout";
import { GoogleIcon, GithubIcon, DiscordIcon, FortyTwoIcon } from "@/components/icons/oauth-icons";

const OAUTH_ERRORS = {
    oauth_denied: "Authorization was cancelled.",
    oauth_state: "Invalid OAuth state, please try again.",
    oauth_failed: "OAuth login failed, please try again.",
    oauth_no_email: "Your provider did not share a verified email.",
    oauth_not_configured: "This provider is not configured.",
};

export default function Login() {
    const { login } = useAuth();
    const navigate = useNavigate();
    const location = useLocation();
    const [searchParams] = useSearchParams();
    const [formData, setFormData] = useState({username: '', password: ''});
    const [submitting, setSubmitting] = useState(false);

    useEffect(() => {
        const error = searchParams.get('error');
        if (error) {
            toast.add({
                title: "Error",
                description: OAUTH_ERRORS[error] || "OAuth login failed.",
                type: "error",
            });
        }
    }, [searchParams]);

    function startOAuth(provider) {
        window.location.assign(`/api/auth/oauth/${provider}/start/`);
    }

    function handleChange(e) {
        setFormData({ ...formData, [e.target.name]: e.target.value });
    }

    async function handleSubmit(e) {
        e.preventDefault();
        setSubmitting(true);
        try {
            await login(formData.username, formData.password);
            navigate(location.state?.from?.pathname || '/home', { replace: true });
        } catch (err) {
            toast.add({
                title: "Login failed",
                description: err.message,
                type: "error",
            });
        } finally {
            setSubmitting(false);
        }
    }

    return (
        <AuthLayout className="max-w-md">
            <CardHeader>
                <CardTitle>Login to your account</CardTitle>
                <CardDescription>
                Enter your username below to login to your account
                </CardDescription>
                <CardAction>
                <Button render={<Link to="/signup" />} nativeButton={false} variant="link">
                    Sign Up
                </Button>
                </CardAction>
            </CardHeader>
            <CardContent>
                <form id="login-form" onSubmit={handleSubmit}>
                <div className="flex flex-col gap-5 sm:gap-6">
                    <div className="grid gap-2">
                    <Label htmlFor="username">Username</Label>
                    <Input
                        id="username"
                        type="text"
                        name="username"
                        autoComplete="username"
                        placeholder="jane.doe"
                        value={formData.username}
                        onChange={handleChange}
                        required
                    />
                    </div>
                    <div className="grid gap-2">
                    <div className="flex flex-wrap items-center gap-x-4 gap-y-1">
                        <Label htmlFor="password">Password</Label>
                        <Link
                          to="/forgot-password"
                          className="ml-auto inline-block text-sm underline-offset-4 hover:underline"
                        >
                          Forgot your password?
                        </Link>
                    </div>
                    <Input
                        id="password"
                        type="password"
                        name="password"
                        autoComplete="current-password"
                        value={formData.password}
                        onChange={handleChange}
                        required
                    />
                    </div>
                </div>
                </form>
            </CardContent>
            <CardFooter className="flex-col gap-4">
                <Button type="submit" form="login-form" className="h-10 w-full sm:h-9" disabled={submitting}>
                {submitting ? "Logging in..." : "Login"}
                </Button>
                <div className="relative w-full">
                    <span className="absolute inset-0 flex items-center">
                        <span className="w-full border-t border-border" />
                    </span>
                    <span className="relative flex justify-center text-xs uppercase">
                        <span className="bg-card px-2 text-muted-foreground">
                            or continue with
                        </span>
                    </span>
                </div>
                <div className="flex flex-row justify-center gap-3">
                    <Button
                        type="button"
                        variant="outline"
                        size="icon-lg"
                        className="rounded-full"
                        aria-label="Login with 42"
                        title="Login with 42"
                        onClick={() => startOAuth('42')}
                    >
                        <FortyTwoIcon className="size-5" />
                    </Button>
                    <Button
                        type="button"
                        variant="outline"
                        size="icon-lg"
                        className="rounded-full"
                        aria-label="Login with GitHub"
                        title="Login with GitHub"
                        onClick={() => startOAuth('github')}
                    >
                        <GithubIcon className="size-5" />
                    </Button>
                    <Button
                        type="button"
                        variant="outline"
                        size="icon-lg"
                        className="rounded-full"
                        aria-label="Login with Google"
                        title="Login with Google"
                        onClick={() => startOAuth('google')}
                    >
                        <GoogleIcon className="size-5" />
                    </Button>
                    <Button
                        type="button"
                        variant="outline"
                        size="icon-lg"
                        className="rounded-full"
                        aria-label="Login with Discord"
                        title="Login with Discord"
                        onClick={() => startOAuth('discord')}
                    >
                        <DiscordIcon className="size-5" />
                    </Button>
                </div>
            </CardFooter>
        </AuthLayout>
    )
}
