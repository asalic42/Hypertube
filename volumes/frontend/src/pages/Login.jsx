import { useState } from "react";
import './Auth.css'

export default function Login() {
    const [formData, setFormData] = useState({email: '', password: ''});

    function handleChange(e) {
        setFormData({ ...formData, [e.target.name]: e.target.value });
    }

    function handleSubmit(e) {
        e.preventDefault();
        console.log(formData);
    }

    return (
        <div className="login-container">
            <h1>Login</h1>
            <form onSubmit={handleSubmit}>
                <label>Email:</label>
                    <input
                        type="email"
                        name="email"
                        value={formData.email}
                        onChange={handleChange}
                    />
                <label>Password:</label>
                    <input
                        type="password"
                        name="password"
                        value={formData.password}
                        onChange={handleChange}
                    />
                <button type="submit">Login</button>
            </form>
            <a href="./forgot-password">Forgot password</a>
            <a href="./signup">Create an account</a>
        </div>
    )
}