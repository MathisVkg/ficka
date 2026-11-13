"use client";
import dynamic from "next/dynamic";
const View = dynamic(
  () =>
    import("@/components/reporting/reports-view").then(
      (module) => module.ReportsView,
    ),
  {
    ssr: false,
    loading: () => (
      <>
        <h1>Reports</h1>
        <p className="report-state">Loading reporting workspace…</p>
      </>
    ),
  },
);
export function Reports() {
  return <View />;
}
