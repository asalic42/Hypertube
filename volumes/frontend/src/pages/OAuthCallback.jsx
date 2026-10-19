import { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "@/hooks/useAuth";

// The auth service lands here after setting the refresh cookie. The page is a
// full reload, so AuthProvider already exchanges that cookie for an access
// token and loads the user on mount: a second refresh call here would burn the
// single-use rotating refresh token. We only wait for it and route.
export default function OAuthCallback() {
    const navigate = useNavigate();
    const { user, loading } = useAuth();

    useEffect(() => {
        if (loading) return;
        if (user) {
            navigate("/home", { replace: true });
        } else {
            navigate("/login?error=oauth_failed", { replace: true });
        }
    }, [loading, user, navigate]);

    return <p className="text-muted-foreground">Signing you in...</p>;
}
