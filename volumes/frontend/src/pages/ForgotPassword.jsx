import { useState } from "react";
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
            const csrfToken = await ensureCsrfToken();

            const response = await fetch('https://localhost:8080/api/auth/forgot-password/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken,
                },
                credentials: 'include',
                body: JSON.stringify(formData),
            });

            if (!response.ok) {
                const errorData = await response.json();
                console.error('Détail de l\'erreur :', errorData);
                throw new Error(errorData.detail);
            }

            toast.add({
                title: "Email envoyé",
                description: "Si un compte est associé à cette adresse, vous allez recevoir un lien de réinitialisation.",
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
        <Card className="w-full max-w-sm">
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
                </div>
                </form>
            </CardContent>
            <CardFooter className="flex-col gap-2">
            <Button
                type="submit"
                form="forgot-password-form"
                className="w-full"
                disabled={loading}
            >
                Send
            </Button>
            </CardFooter>
        </Card>
    )
}