import { useState } from "react";
import "./Auth.css"

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
        <div className="login-container">
            <h1>Reset password</h1>
            <form onSubmit={handleSubmit}>
                <label>New password:</label>
                <input
                    type="password"
                    name="new-password"
                    value={formData.new_password}
                    onChange={handleChange}
                />

                <label>Confirmation password:</label>
                <input
                    type="password"
                    name="confirm-password"
                    value={formData.confirm_password}
                    onChange={handleChange}
                />
                <button type="submit">Change password</button>
            </form>
        </div>
    )
}