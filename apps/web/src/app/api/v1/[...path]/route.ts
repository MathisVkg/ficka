import type { NextRequest } from "next/server";
export const dynamic = "force-dynamic";
type Context = { params: Promise<{ path: string[] }> };
async function forward(request: NextRequest, context: Context) {
  const { path } = await context.params;
  const [resource, id] = path;
  const allowed =
    ["income", "expenses", "categories"].includes(resource) &&
    path.length <= 2 &&
    (!id || /^[0-9a-f-]{36}$/i.test(id));
  if (!allowed)
    return Response.json(
      { error: { message: "API route not found" } },
      { status: 404 },
    );
  if (request.method !== "GET") {
    const origin = request.headers.get("origin");
    let originHost: string | null = null;
    try {
      originHost = origin ? new URL(origin).host : null;
    } catch {
      return Response.json(
        { error: { message: "Invalid request origin" } },
        { status: 403 },
      );
    }
    if (
      (origin && originHost !== request.headers.get("host")) ||
      request.headers.get("sec-fetch-site") === "cross-site"
    )
      return Response.json(
        { error: { message: "Cross-site write refused" } },
        { status: 403 },
      );
    if (
      request.method !== "DELETE" &&
      !request.headers.get("content-type")?.startsWith("application/json")
    )
      return Response.json(
        { error: { message: "Send JSON request data" } },
        { status: 415 },
      );
  }
  try {
    const body =
      request.method === "GET" || request.method === "DELETE"
        ? undefined
        : await request.text();
    if (body && body.length > 65536)
      return Response.json(
        { error: { message: "Request is too large" } },
        { status: 413 },
      );
    const url = new URL(
      "/api/v1/" + path.join("/"),
      process.env.API_INTERNAL_URL ?? "http://127.0.0.1:8000",
    );
    url.search = request.nextUrl.search;
    const response = await fetch(url, {
      method: request.method,
      headers: {
        "Content-Type": "application/json",
        Accept: "application/json",
      },
      body,
      cache: "no-store",
      signal: AbortSignal.timeout(10000),
    });
    if (response.status === 204) return new Response(null, { status: 204 });
    return Response.json(await response.json(), { status: response.status });
  } catch {
    return Response.json(
      {
        error: {
          message:
            "API unavailable. Check the API and database services, then retry.",
        },
      },
      { status: 503 },
    );
  }
}
export const GET = forward;
export const POST = forward;
export const PATCH = forward;
export const DELETE = forward;
