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
import { useNavigate } from "react-router-dom";


export default function Login({ onLoginSuccess }) {
    const navigate = useNavigate();
    const [formData, setFormData] = useState({email: '', password: ''});

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

        } catch (err) {
            toast.add({
                title: "Error",
                description: err.message,
                type: "error",
            });
        }
        onLoginSuccess();
        navigate('/home');
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
            <CardFooter className="flex-col gap-2">
                <Button variant="outline" className="w-full">
                Login with Google
                </Button>
            </CardFooter>
        </Card>
    )
}