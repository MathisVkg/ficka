"use client";
import dynamic from "next/dynamic";
const View = dynamic(
  () =>
    import("@/components/reporting/dashboard-view").then(
      (module) => module.DashboardView,
    ),
  {
    ssr: false,
    loading: () => (
      <>
        <h1>Dashboard</h1>
        <p className="report-state">Loading financial overview…</p>
      </>
    ),
  },
);
export function Dashboard() {
  return <View />;
}
