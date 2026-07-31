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
import { useNavigate } from "react-router-dom";
import { NativeSelect } from "@/components/ui/native-select";


function Signup() {
    const navigate = useNavigate();
    const [formData, setFormData] = useState({email: '', username: '', lastname: '', firstname: '', profilePic: null, preferredLanguage: ''});
    const [erreur, setErreur] = useState(null);

    function handleChange(e) {
        setFormData({ ...formData, [e.target.name]: e.target.value });
    }

    function handleFileChange(e) {
    const file = e.target.files[0]; // le premier (et seul) fichier sélectionné
    setFormData({ ...formData, profilePic: file });
    }

    async function handleSubmit(e) {
        e.preventDefault();
        console.log(formData);

        const data = new FormData();
        data.append('username', formData.username);
        data.append('firstname', formData.firstname);
        data.append('lastname', formData.lastname);
        data.append('email', formData.email);
        if (formData.profilePic) {
            data.append('profilePic', formData.profilePic);
        }
        data.append('preferredLanguage', formData.preferredLanguage);

        try {
            const response = await fetch('http://localhost:8000/api/app-users/create/', {
                method: 'POST',
                body: data,
            });

            if (!response.ok) {
                throw new Error('Error creating user');
            }

            const datares = await response.json();
            console.log('User created:', datares);
            navigate('https://localhost:8080/login');
        
        } catch (err) {
            console.error(err);
            setErreur(err.message);
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
                <Button asChild variant="link">
                    <Link to="/login">Login</Link>
                </Button>
                </CardAction>
            </CardHeader>
            <CardContent>
                <form id="signup-form" onSubmit={handleSubmit}>
                <div className="flex flex-col gap-6">
                    <div className="grid gap-2">
                    <Label htmlFor="username">User name</Label>
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
                    <Label htmlFor="password">Profile Picture</Label>
                    <Input
                        id="profilePic"
                        type="file"
                        name="profilePic"
                        accept="image/*"
                        value={formData.profilePic}
                        onChange={handleFileChange} 
                    />
                    </div>
                    <div className="grid gap-2">
                    <Label htmlFor="password">Language</Label>
                    <NativeSelect name="preferredLanguage" value={formData.preferredLanguage} onChange={handleChange}>
                        <option value="en">English</option>
                        <option value="fr">Français</option>
                        <option value="es">Español</option>
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

export default Signup;