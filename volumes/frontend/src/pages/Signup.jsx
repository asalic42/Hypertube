import { useState, useEffect, useRef } from "react";
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
import { useNavigate } from "react-router-dom";
import { NativeSelect } from "@/components/ui/native-select";
import { toast } from "@/components/ui/toast";
import { Avatar, AvatarImage, AvatarFallback } from "@/components/ui/avatar";


export default function Signup() {
    const navigate = useNavigate();
    const [formData, setFormData] = useState({
        email: '',
        username: '',
        password: '',
        confirm_password: '',
        lastname: '',
        firstname: '',
        avatar: null,
        preferredLanguage: ''
    });
    const [preview, setPreview] = useState(null);
    const fileInputRef = useRef(null);

    // nettoyage memoire au demontage du composant
    useEffect(() => {
        return () => {
            if (preview) {
                URL.revokeObjectURL(preview);
            }
        };
    }, []);

    function handleFileChange(e) {
        const file = e.target.files[0];
        if (preview) {
            URL.revokeObjectURL(preview);
        }
        setFormData({ ...formData, avatar: file });
        if (file) {
            setPreview(URL.createObjectURL(file));
        }
    }

    function handleRemovePhoto() {
        if (preview) {
            URL.revokeObjectURL(preview);
        }
        setFormData({ ...formData, avatar: null });
        setPreview(null);
        if (fileInputRef.current) {
            fileInputRef.current.value = "";
        }
    }

    function handleChange(e) {
        setFormData({ ...formData, [e.target.name]: e.target.value });
    }

    async function handleSubmit(e) {
        e.preventDefault();

        const data = new FormData();
        data.append('username', formData.username);
        data.append('password', formData.password)
        data.append('confirm_password', formData.confirm_password)
        data.append('firstname', formData.firstname);
        data.append('lastname', formData.lastname);
        data.append('email', formData.email);
        if (formData.avatar) {
            data.append('avatar', formData.avatar);
        }
        data.append('preferredLanguage', formData.preferredLanguage);

        try {
            const response_reg = await fetch('https://localhost:8080/api/auth/register/', {
                method: 'POST',
                body: data,
            });
            
            if (!response_reg.ok) {
                const errorData = await response_reg.json();
                console.error('Détail de l\'erreur :', errorData);
                throw new Error('Error register user');
            }
            

            const response_cr = await fetch('https://localhost:8080/api/users/create/', {
                method: 'POST',
                body: data,
            });
            
            if (!response_cr.ok) {
                const result_reg = await response_reg.json();
                const user_id = result_reg.id;
                console.log("user id :", user_id);
                const del = await fetch(`https://localhost:8080/api/auth/delete/${user_id}/`, {
                    method: 'DELETE',
                });

                if (!del.ok) {
                    throw new Error('Error deleting user');
                }

                throw new Error('Error creating user');
            }

            toast.add({
                title: "Account created",
                description: "Account successfully created !",
                type : "success",
            });
            navigate('/login');
        
        } catch (err) {
            console.error(err);
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
                <CardTitle>Create account</CardTitle>
                <CardDescription>
                    Enter your information to create an account
                </CardDescription>
                <CardAction>
                    <Button render={<Link to="/login" />} nativeButton={false} variant="link">
                        Login
                    </Button>
                </CardAction>
            </CardHeader>

            <CardContent>
                <form id="signup-form" onSubmit={handleSubmit}>
                    <div className="flex flex-col gap-6">

                        <div className="grid gap-2">
                            <Label htmlFor="username">Username</Label>
                            <Input
                                id="username"
                                type="text"
                                name="username"
                                value={formData.username}
                                onChange={handleChange}
                                required
                            />
                        </div>

                        <div className="grid gap-2">
                            <Label htmlFor="password">Password</Label>
                            <Input
                                id="password"
                                type="password"
                                name="password"
                                value={formData.password}
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
                                value={formData.confirm_password}
                                onChange={handleChange}
                                required
                            />
                        </div>

                        <div className="grid gap-2">
                            <Label htmlFor="firstname">First name</Label>
                            <Input
                                id="firstname"
                                type="text"
                                name="firstname"
                                value={formData.firstname}
                                onChange={handleChange}
                                required
                            />
                        </div>

                        <div className="grid gap-2">
                            <Label htmlFor="lastname">Last name</Label>
                            <Input
                                id="lastname"
                                type="text"
                                name="lastname"
                                value={formData.lastname}
                                onChange={handleChange}
                                required
                            />
                        </div>

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
                            <Label htmlFor="password">Avatar</Label>
                            {preview && (
                            <div className="flex justify-center gap-2">
                                <Avatar className="size-40">
                                    <AvatarImage src={preview} alt="Preview" />
                                    <AvatarFallback>?</AvatarFallback>
                                </Avatar>
                                <Button
                                    type="button"
                                    variant="ghost"
                                    size="sm"
                                    onClick={handleRemovePhoto}
                                >x</Button>
                            </div>
                            )}
                            <Input
                                ref={fileInputRef}
                                id="profilePic"
                                type="file"
                                name="avatar"
                                accept="image/*"
                                onChange={handleFileChange}
                            />
                        </div>

                        <div className="grid gap-2">
                            <Label htmlFor="password">Language</Label>
                            <NativeSelect
                                name="preferredLanguage"
                                value={formData.preferredLanguage}
                                onChange={handleChange}
                            >
                                <option value="en">English</option>
                                <option value="fr">French</option>
                                <option value="es">Spanish</option>
                                <option value="de">German</option>
                                <option value="it">Italian</option>
                                <option value="pt">Portuguese</option>
                                <option value="ru">Russian</option>
                                <option value="zh">Chinese</option>
                                <option value="ja">Japanese</option>
                                <option value="ko">Korean</option>
                            </NativeSelect>
                        </div>

                        <Button type="submit" className="w-full">
                            Signup
                        </Button>
                    </div>
                </form>
            </CardContent>
        </Card>
    )
}