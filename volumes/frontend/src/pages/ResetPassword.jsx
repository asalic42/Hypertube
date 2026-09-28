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
import AuthLayout from "@/components/AuthLayout";

export default function ResetPassword() {
    const [formData, setFormData] = useState({ new_password: '', confirm_password: '' })

    function handleChange(e) {
        setFormData({ ...formData, [e.target.name]: e.target.value });
    }

    function handleSubmit(e) {
        e.preventDefault();
        console.log(formData);
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
                <Button type="submit" form="reset-password-form" className="h-10 w-full sm:h-9">
                Change password
                </Button>
            </CardFooter>
        </AuthLayout>
    )
}
