import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button"
import { 
  Card, 
  CardHeader, 
  CardTitle, 
  CardDescription, 
  CardAction, 
  CardContent, 
  CardFooter 
} from "@/components/ui/card";
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Link } from "react-router-dom";
import { toast } from "@/components/ui/toast";
import { ensureCsrfToken } from "@/lib/csrf";
import { useNavigate, useSearchParams } from "react-router-dom";
import { GoogleIcon, FortyTwoIcon } from "@/components/icons/oauth-icons";


const OAUTH_ERRORS = {
    oauth_denied: "Authorization was cancelled.",
    oauth_state: "Invalid OAuth state, please try again.",
    oauth_failed: "OAuth login failed, please try again.",
    oauth_no_email: "Your provider did not share a verified email.",
    oauth_not_configured: "This provider is not configured.",
};


export default function Login({ onLoginSuccess }) {
    const navigate = useNavigate();
    const [searchParams] = useSearchParams();
    const [formData, setFormData] = useState({email: '', password: ''});

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
        window.location.assign(
            `https://localhost:8080/api/auth/oauth/${provider}/start/`
        );
    }

    function handleChange(e) {
        setFormData({ ...formData, [e.target.name]: e.target.value });
    }

    async function handleSubmit(e) {
        e.preventDefault();

        try {
            const csrfToken = await ensureCsrfToken();

            const response = await fetch('https://localhost:8080/api/auth/login/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken,
                },
                credentials: 'include',
                body: JSON.stringify(formData),
            });
            
            if(!response.ok) {
                const errorData = await response.json();
                console.error('Détail de l\'erreur :', errorData);
                throw new Error(errorData.detail);
            }
            
            const data = await response.json();
            const accessToken = data.access;

            localStorage.setItem('access_token', accessToken);

            onLoginSuccess();
            navigate('/home');
            
        } catch (err) {
            toast.add({
                title: "Error",
                description: err.message,
                type: "error",
            });
        }
    }

    return (
        <Card className="w-full max-w-lg">
            <CardHeader>
                <CardTitle>Login to your account</CardTitle>
                <CardDescription>
                Enter your email below to login to your account
                </CardDescription>
                <CardAction>
                <Button render={<Link to="/signup" />} nativeButton={false} variant="link">
                    Sign Up
                </Button>
                </CardAction>
            </CardHeader>
            <CardContent>
                <form id="login-form" onSubmit={handleSubmit}>
                <div className="flex flex-col gap-6">
                    <div className="grid gap-2">
                    <Label htmlFor="email">Email</Label>
                    <Input
                        id="email"
                        type="email"
                        name="email"
                        placeholder="m@example.com"
                        value={formData.email}
                        onChange={handleChange}
                        required
                    />
                    </div>
                    <div className="grid gap-2">
                    <div className="flex items-center">
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
                        value={formData.password}
                        onChange={handleChange}
                        required 
                    />
                    </div>
                <Button type="submit" className="w-full">
                Login
                </Button>
                </div>
                </form>
            </CardContent>
            <CardFooter className="flex-col gap-4">
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
                        aria-label="Login with Google"
                        title="Login with Google"
                        onClick={() => startOAuth('google')}
                    >
                        <GoogleIcon className="size-5" />
                    </Button>
                </div>
            </CardFooter>
        </Card>
    )
}