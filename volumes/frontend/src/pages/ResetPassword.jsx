import { useState } from "react";
import { Button } from "@/components/ui/button"
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent
} from "@/components/ui/card";
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { toast } from "@/components/ui/toast";
import { ensureCsrfToken } from "@/lib/csrf";

export default function ResetPassword() {
    const navigate = useNavigate();
    const [searchParams] = useSearchParams();

    const uid = searchParams.get('uid');
    const token = searchParams.get('token');

    const [formData, setFormData] = useState({
        new_password: '',
        confirm_password: '',
    })
    const [loading, setLoading] = useState(false)

    function handleChange(e) {
        setFormData({ ...formData, [e.target.name]: e.target.value });
    }

    async function handleSubmit(e) {
        e.preventDefault();

        if (formData.new_password !== formData.confirm_password) {
            toast.add({
                title: "Error",
                description: "Les mots de passe ne correspondent pas.",
                type: "error",
            });
            return;
        }

        setLoading(true);

        try {
            const csrfToken = await ensureCsrfToken();

            const response = await fetch(
                `https://localhost:8080/api/auth/reset-password/?uid=${encodeURIComponent(uid)}&token=${encodeURIComponent(token)}`,
                {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': csrfToken,
                    },
                    credentials: 'include',
                    body: JSON.stringify({
                        new_password: formData.new_password,
                        confirm_password: formData.confirm_password,
                    }),
                });

            if (!response.ok) {
                const errorData = await response.json();
                console.error('Détail de l\'erreur :', errorData);
                throw new Error(errorData.detail);
            }

            toast.add({
                title: "Mot de passe mis à jour",
                description: "Vous pouvez maintenant vous connecter.",
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
            <Card className="w-full max-w-sm">
            <CardHeader>
                <CardTitle>Reset password</CardTitle>
                <CardDescription>
                Ce lien est invalide. Merci de demander un nouveau lien de réinitialisation.
                </CardDescription>
            </CardHeader>
            <CardContent>
                <Button
                    render={<Link to="/forgot-password" />}
                    nativeButton={false}
                    className="w-full"
                >
                    Demander un nouveau lien
                </Button>
            </CardContent>
            </Card>
        )
    }

    return(
        <Card className="w-full max-w-sm">
            <CardHeader>
            <CardTitle>Reset password</CardTitle>
            <CardDescription>
            Enter your new password below
            </CardDescription>
            </CardHeader>
            <CardContent>
                <form id="reset-password-form" onSubmit={handleSubmit}>
                <div className="flex flex-col gap-6">
                    <div className="grid gap-2">
                    <Label htmlFor="new_password">New password</Label>
                    <Input
                        id="new_password"
                        type="password"
                        name="new_password"
                        value={formData.new_password}
                        onChange={handleChange}
                        required
                    />
                    </div>
                    <div className="grid gap-2">
                    <Label htmlFor="confirm_password">Confirm password</Label>
                    <Input
                        id="confirm_password"
                        type="password"
                        name="confirm_password"
                        value={formData.confirm_password}
                        onChange={handleChange}
                        required
                    />
                    </div>
                </div>
                <Button
                    type="submit"
                    className="w-full mt-6"
                    disabled={loading}
                >
                Change password
                </Button>
                </form>
            </CardContent>
        </Card>
    )
}