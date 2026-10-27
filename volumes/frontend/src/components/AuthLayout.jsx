import { Link } from "react-router-dom";
import { Card } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import ThemeToggle from "@/components/ThemeToggle";
import LanguageSwitcher from "@/components/LanguageSwitcher";


export default function AuthLayout({ className, children }) {
    return (
        <div className="relative flex w-full flex-1 flex-col items-center self-stretch px-4 py-6 sm:justify-center sm:py-12">
            <div className="mb-4 flex w-full items-center justify-end gap-2 sm:absolute sm:top-3 sm:right-3 sm:mb-0 sm:w-auto">
                <LanguageSwitcher />
                <ThemeToggle className="text-foreground hover:bg-accent" />
            </div>
            <Link to="/login" className="mb-5 text-2xl font-bold tracking-tight text-foreground sm:mb-8">
                Hyper<span className="text-brand">tube</span>
            </Link>
            <Card className={cn("w-full max-w-lg [--card-spacing:--spacing(4)] sm:[--card-spacing:--spacing(6)]", className)}>
                {children}
            </Card>
        </div>
    );
}
