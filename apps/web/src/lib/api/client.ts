export type Readiness = { status: "ready" };
export class ConnectionError extends Error {}
export async function getReadiness(signal?: AbortSignal): Promise<Readiness> {
  const response = await fetch("/api/health/ready", {
    cache: "no-store",
    signal,
  });
  if (!response.ok)
    throw new ConnectionError(
      "Ficka cannot reach its database. Check the API and database services, then retry.",
    );
  const data: unknown = await response.json();
  if (
    !data ||
    typeof data !== "object" ||
    !("status" in data) ||
    data.status !== "ready"
  )
    throw new ConnectionError("The API returned an unexpected response.");
  return { status: "ready" };
}
