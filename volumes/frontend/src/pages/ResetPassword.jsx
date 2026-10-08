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
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { toast } from "@/components/ui/toast";
import { api } from "@/lib/api";
import AuthLayout from "@/components/AuthLayout";

export default function ResetPassword() {
    const navigate = useNavigate();
    const [searchParams] = useSearchParams();
    // Both come from the link in the reset email.
    const uid = searchParams.get('uid');
    const token = searchParams.get('token');

    const [formData, setFormData] = useState({ new_password: '', confirm_password: '' })
    const [loading, setLoading] = useState(false)

    function handleChange(e) {
        setFormData({ ...formData, [e.target.name]: e.target.value });
    }

    async function handleSubmit(e) {
        e.preventDefault();
        if (formData.new_password !== formData.confirm_password) {
            toast.add({ title: "Error", description: "The passwords do not match.", type: "error" });
            return;
        }
        setLoading(true);
        try {
            const query = new URLSearchParams({ uid, token });
            // Anonymous endpoint: no access token, but the CSRF cookie and header.
            await api(`/api/auth/reset-password/?${query}`, { method: 'POST', body: formData, auth: false, csrf: true });
            toast.add({
                title: "Password updated",
                description: "You can now log in with your new password.",
                type: "success",
            });
            navigate('/login');
        } catch (err) {
            toast.add({
                title: "Error",
                description: err.message,
                type: "error",
            });
        } finally {
            setLoading(false);
        }
    }

    if (!uid || !token) {
        return (
            <AuthLayout className="max-w-md">
                <CardHeader>
                    <CardTitle>Reset password</CardTitle>
                    <CardDescription>
                    This link is not valid. Please request a new reset link.
                    </CardDescription>
                </CardHeader>
                <CardFooter className="flex-col gap-2">
                    <Button render={<Link to="/forgot-password" />} nativeButton={false} className="h-10 w-full sm:h-9">
                        Request a new link
                    </Button>
                </CardFooter>
            </AuthLayout>
        )
    }

    return(
        <AuthLayout className="max-w-md">
            <CardHeader>
                <CardTitle>Reset password</CardTitle>
                <CardDescription>
                Choose a new password for your account
                </CardDescription>
                <CardAction>
                <Button render={<Link to="/login" />} nativeButton={false} variant="link">
                    Login
                </Button>
                </CardAction>
            </CardHeader>
            <CardContent>
                <form id="reset-password-form" onSubmit={handleSubmit}>
                <div className="flex flex-col gap-5 sm:gap-6">
                    <div className="grid gap-2">
                    <Label htmlFor="new_password">New password</Label>
                    <Input
                        id="new_password"
                        type="password"
                        name="new_password"
                        autoComplete="new-password"
                        value={formData.new_password}
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
                </form>
            </CardContent>
            <CardFooter className="flex-col gap-2">
                <Button type="submit" form="reset-password-form" className="h-10 w-full sm:h-9" disabled={loading}>
                {loading ? "Saving..." : "Change password"}
                </Button>
            </CardFooter>
        </AuthLayout>
    )
}
