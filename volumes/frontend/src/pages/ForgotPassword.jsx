import { useState } from "react";
import "./Auth.css"

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
        <div className="login-container">
            <h1>Forgot password</h1>
            <form onSubmit={handleSubmit}>
                <label>Email:</label>
                <input
                    type="email"
                    name="email"
                    value={formData.email}
                    onChange={handleChange}
                />
                <button type="submit">Send</button>
            </form>
        </div>
    )
}