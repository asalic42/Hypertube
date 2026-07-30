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

export default function ForgotPassword() {
    const [formData, setFormData] = useState({ email: '' })

    function handleChange(e) {
        setFormData({ ...formData, [e.target.name]: e.target.value });
    }

    function handleSubmit(e) {
        e.preventDefault();
        console.log(formData);
    }
    return(
        <Card className="w-full max-w-sm">
            <CardHeader>
                <CardTitle>Forgot password</CardTitle>
                <CardDescription>
                Enter your email to reset your password 
                </CardDescription>
                <CardAction>
                <Button asChild variant="link">
                    <Link to="/login">Login</Link>
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
                <Button type="submit" className="w-full">
                Send
                </Button>
            </CardFooter>
        </Card>
    )
}