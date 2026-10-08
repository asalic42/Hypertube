import { useState } from "react";
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
import { Link, useLocation, useNavigate } from "react-router-dom";
import { toast } from "@/components/ui/toast";
import { useAuth } from "@/hooks/useAuth";
import AuthLayout from "@/components/AuthLayout";

export default function Login() {
    const { login } = useAuth();
    const navigate = useNavigate();
    const location = useLocation();
    const [formData, setFormData] = useState({email: '', password: ''});
    const [submitting, setSubmitting] = useState(false);

    function handleChange(e) {
        setFormData({ ...formData, [e.target.name]: e.target.value });
    }

    async function handleSubmit(e) {
        e.preventDefault();
        setSubmitting(true);
        try {
            await login(formData.email, formData.password);
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
                <div className="flex flex-col gap-5 sm:gap-6">
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
            <CardFooter className="flex-col gap-2">
                <Button type="submit" form="login-form" className="h-10 w-full sm:h-9" disabled={submitting}>
                {submitting ? "Logging in..." : "Login"}
                </Button>
                <Button variant="outline" className="h-10 w-full sm:h-9">
                Login with Google
                </Button>
            </CardFooter>
        </AuthLayout>
    )
}
