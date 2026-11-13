import { EntriesPage } from "@/components/financial/entries-page";
export const metadata = { title: "Expenses" };
export default function Page() {
  return <EntriesPage kind="expense" />;
}
