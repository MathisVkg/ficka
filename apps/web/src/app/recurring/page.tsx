import Link from "next/link";
import { FolderOpen, ArrowLeft } from "lucide-react";
import { Button } from "@/components/ui/button";
export const metadata = { title: "Recurring" };
export default function Page() {
  return (
    <>
      <div className="eyebrow">YOUR WORKSPACE</div>
      <header className="page-header">
        <div>
          <h1>Recurring</h1>
          <p>Build a rhythm for your finances.</p>
        </div>
        <span className="quiet-tag">Foundation preview</span>
      </header>
      <section className="route-empty">
        <FolderOpen size={36} strokeWidth={1.2} />
        <span className="quiet-tag">Coming in a future update</span>
        <h2>Your recurring routine, in one place</h2>
        <p>
          Recurring schedules and proposal approvals are planned. No payments or
          entries are generated yet.
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
