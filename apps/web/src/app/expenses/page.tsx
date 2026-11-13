import Link from "next/link";
import { FolderOpen, ArrowLeft } from "lucide-react";
import { Button } from "@/components/ui/button";
export const metadata = { title: "Expenses" };
export default function Page() {
  return (
    <>
      <div className="eyebrow">YOUR WORKSPACE</div>
      <header className="page-header">
        <div>
          <h1>Expenses</h1>
          <p>Understand where your money goes.</p>
        </div>
        <span className="quiet-tag">Foundation preview</span>
      </header>
      <section className="route-empty">
        <FolderOpen size={36} strokeWidth={1.2} />
        <span className="quiet-tag">Coming in a future update</span>
        <h2>A clearer picture of spending</h2>
        <p>
          Expense entry creation will arrive in a future update. Track and
          categorize business spending here.
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
