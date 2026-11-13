export const dynamic = "force-dynamic";
export async function GET() {
  try {
    const origin = process.env.API_INTERNAL_URL ?? "http://127.0.0.1:8000";
    const response = await fetch(new URL("/api/v1/health/ready", origin), {
      cache: "no-store",
      signal: AbortSignal.timeout(5000),
    });
    if (!response.ok) throw new Error("Backend unavailable");
    const data = await response.json();
    if (data.status !== "ready") throw new Error("Unexpected response");
    return Response.json({ status: "ready" });
  } catch {
    return Response.json(
      {
        error: {
          code: "service_unavailable",
          message: "API or database unavailable",
        },
      },
      { status: 503 },
    );
  }
}
