import { EntriesPage } from "@/components/financial/entries-page";
export const metadata = { title: "Income" };
export default function Page() {
  return <EntriesPage kind="income" />;
}
