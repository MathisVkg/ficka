import Link from "next/link";
import { FolderOpen, ArrowLeft } from "lucide-react";
import { Button } from "@/components/ui/button";
export const metadata = { title: "Income" };
export default function Page() {
  return (
    <>
      <div className="eyebrow">YOUR WORKSPACE</div>
      <header className="page-header">
        <div>
          <h1>Income</h1>
          <p>Money coming in, clearly tracked.</p>
        </div>
        <span className="quiet-tag">Foundation preview</span>
      </header>
      <section className="route-empty">
        <FolderOpen size={36} strokeWidth={1.2} />
        <span className="quiet-tag">Coming in a future update</span>
        <h2>Your income starts here</h2>
        <p>
          Income entry creation will arrive in a future update. Your received
          and outstanding income will then live here.
        </p>
        <Button asChild variant="outline">
          <Link href="/">
            <ArrowLeft size={16} />
            Back to dashboard
          </Link>
        </Button>
      </section>
    </>
  );
}
