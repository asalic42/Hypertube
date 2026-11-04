import { Link } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import AuthLayout from "@/components/AuthLayout";
import { useAuth } from "@/hooks/useAuth";
import { useTranslation } from "@/hooks/useTranslation";

/** Shown for any URL no route matches. Logged-in visitors are sent back to the
 *  library; anonymous ones get the auth frame (the header is hidden for them). */
export default function NotFound() {
    const { user, loading } = useAuth();
    const { t } = useTranslation();

    if (loading) {
        return <p className="text-muted-foreground p-4">{t("Loading...")}</p>;
    }

    const body = (
        <CardContent className="flex flex-col items-center gap-4 py-8 text-center sm:py-10">
            <span className="text-5xl leading-none" aria-hidden="true">🎞</span>
            <p className="text-6xl font-bold tracking-tight text-brand sm:text-7xl">404</p>
            <h1 className="text-2xl font-bold tracking-tight">{t("Page not found")}</h1>
            <p className="max-w-sm text-muted-foreground">
                {t("This reel seems to be missing. The page you are looking for does not exist or has moved.")}
            </p>
            {user
                ? <Button render={<Link to="/home" />} nativeButton={false} className="mt-2">{t("Back to the library")}</Button>
                : <Button render={<Link to="/login" />} nativeButton={false} className="mt-2">{t("Login")}</Button>}
        </CardContent>
    );

    if (!user) {
        return <AuthLayout className="max-w-md">{body}</AuthLayout>;
    }
    return (
        <div className="w-full max-w-md p-4 sm:py-12">
            <Card className="[--card-spacing:--spacing(4)] sm:[--card-spacing:--spacing(6)]">{body}</Card>
        </div>
    );
}
