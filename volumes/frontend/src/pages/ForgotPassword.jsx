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
import { Link } from "react-router-dom";
import { toast } from "@/components/ui/toast";
import { api } from "@/lib/api";
import AuthLayout from "@/components/AuthLayout";

export default function ForgotPassword() {
    const [formData, setFormData] = useState({ email: '' })
    const [loading, setLoading] = useState(false)

    function handleChange(e) {
        setFormData({ ...formData, [e.target.name]: e.target.value });
    }

    async function handleSubmit(e) {
        e.preventDefault();
        setLoading(true);
        try {
            // Anonymous endpoint: no access token, but the CSRF cookie and header.
            await api('/api/auth/forgot-password/', { method: 'POST', body: formData, auth: false, csrf: true });
            toast.add({
                title: "Email sent",
                description: "If an account matches this address, you will receive a reset link.",
                type: "success",
            });
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
    return(
        <AuthLayout className="max-w-md">
            <CardHeader>
                <CardTitle>Forgot password</CardTitle>
                <CardDescription>
                Enter your email to reset your password 
                </CardDescription>
                <CardAction>
                <Button render={<Link to="/login" />} nativeButton={false} variant="link">
                    Login
                </Button>
                </CardAction>
            </CardHeader>
            <CardContent>
                <form id="forgot-password-form" onSubmit={handleSubmit}>
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
                </div>
                </form>
            </CardContent>
            <CardFooter className="flex-col gap-2">
                <Button type="submit" form="forgot-password-form" className="h-10 w-full sm:h-9" disabled={loading}>
                {loading ? "Sending..." : "Send"}
                </Button>
            </CardFooter>
        </AuthLayout>
    )
}
