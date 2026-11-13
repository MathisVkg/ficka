"use client";
import { useEffect, useState } from "react";
import { CircleCheck, CircleAlert } from "lucide-react";
import { getReadiness } from "@/lib/api/client";
import { Button } from "@/components/ui/button";
export function ConnectionStatus() {
  const [state, setState] = useState<"checking" | "ready" | "error">(
    "checking",
  );
  useEffect(() => {
    const controller = new AbortController();
    getReadiness(controller.signal).then(
      () => {
        if (!controller.signal.aborted) setState("ready");
      },
      () => {
        if (!controller.signal.aborted) setState("error");
      },
    );
    return () => controller.abort();
  }, []);
  async function retry() {
    setState("checking");
    try {
      await getReadiness();
      setState("ready");
    } catch {
      setState("error");
    }
  }
  return (
    <div
      role="status"
      className={
        state === "error" ? "connection connection-error" : "connection"
      }
    >
      {state === "ready" ? (
        <>
          <CircleCheck size={15} /> All systems connected
        </>
      ) : state === "checking" ? (
        "Checking connection…"
      ) : (
        <>
          <CircleAlert size={17} />
          <span>API or database unavailable. Check your services.</span>
          <Button variant="outline" size="sm" onClick={() => void retry()}>
            Retry
          </Button>
        </>
      )}
    </div>
  );
}
