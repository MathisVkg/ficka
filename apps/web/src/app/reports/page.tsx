import Link from "next/link";
import { FolderOpen, ArrowLeft } from "lucide-react";
import { Button } from "@/components/ui/button";
export const metadata = { title: "Reports" };
export default function Page() {
  return (
    <>
      <div className="eyebrow">YOUR WORKSPACE</div>
      <header className="page-header">
        <div>
          <h1>Reports</h1>
          <p>See the bigger picture.</p>
        </div>
        <span className="quiet-tag">Foundation preview</span>
      </header>
      <section className="route-empty">
        <FolderOpen size={36} strokeWidth={1.2} />
        <span className="quiet-tag">Coming in a future update</span>
        <h2>Insights need a little history</h2>
        <p>
          Cash-flow reports and country-aware VAT estimates will arrive after
          financial entries are available.
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
