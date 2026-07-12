import { useState } from "react";
import './Auth.css'

function Signup() {
    const [formData, setFormData] = useState({email: '', username: '', lastname: '', firstname: '', password: ''});

    function handleChange(e) {
        setFormData({ ...formData, [e.target.name]: e.target.value });
    }

    function handleSubmit(e) {
        e.preventDefault();
        console.log(formData);
    }

    return (
        <div className="login-container">
            <h1>Signup</h1>
            <form onSubmit={handleSubmit}>
                <label>Username:</label>
                    <input
                        type="username"
                        name="username"
                        value={formData.username}
                        onChange={handleChange}
                    />
                <label>Firstname:</label>
                    <input
                        type="firstname"
                        name="firstname"
                        value={formData.firstname}
                        onChange={handleChange}
                    />
                <label>Lastname:</label>
                    <input
                        type="lastname"
                        name="lastname"
                        value={formData.lastname}
                        onChange={handleChange}
                    />
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
                <button type="submit">Signup</button>
            </form>
            <a href="./login">Already an account ?</a>
        </div>
    )
}

export default Signup;