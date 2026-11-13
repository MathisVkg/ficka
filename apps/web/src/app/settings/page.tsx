import Link from "next/link";
import { FolderOpen, ArrowLeft } from "lucide-react";
import { Button } from "@/components/ui/button";
export const metadata = { title: "Settings" };
export default function Page() {
  return (
    <>
      <div className="eyebrow">YOUR WORKSPACE</div>
      <header className="page-header">
        <div>
          <h1>Settings</h1>
          <p>Make Ficka feel like your business.</p>
        </div>
        <span className="quiet-tag">Foundation preview</span>
      </header>
      <section className="route-empty">
        <FolderOpen size={36} strokeWidth={1.2} />
        <span className="quiet-tag">Coming in a future update</span>
        <h2>A foundation for your preferences</h2>
        <p>
          Company preferences, Belgium VAT configuration and Sentinel sign-in
          are planned. No settings are stored yet.
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
