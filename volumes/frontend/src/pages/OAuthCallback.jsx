import { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { refreshAccessToken } from "@/lib/refreshFlow";

// Guard so React StrictMode's double effect does not trigger two refresh
// calls with the same (single-use, rotating) refresh cookie.
let handled = false;

export default function OAuthCallback({ onLoginSuccess }) {
    const navigate = useNavigate();

    useEffect(() => {
        if (handled) return;
        handled = true;

        (async () => {
            try {
                await refreshAccessToken();
                onLoginSuccess();
                navigate("/home", { replace: true });
            } catch {
                navigate("/login?error=oauth_failed", { replace: true });
            }
        })();
    }, [navigate, onLoginSuccess]);

    return <p>Connexion en cours...</p>;
}
