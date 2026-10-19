import { Link } from "react-router-dom";
import { Card } from "@/components/ui/card";
import { cn } from "@/lib/utils";


export default function AuthLayout({ className, children }) {
    return (
        <div className="flex w-full flex-1 flex-col items-center self-stretch px-4 py-6 sm:justify-center sm:py-12">
            <Link to="/login" className="mb-5 text-2xl font-bold tracking-tight text-white sm:mb-8">
                Hyper<span className="text-brand">tube</span>
            </Link>
            <Card className={cn("w-full max-w-lg [--card-spacing:--spacing(4)] sm:[--card-spacing:--spacing(6)]", className)}>
                {children}
            </Card>
        </div>
    );
}
