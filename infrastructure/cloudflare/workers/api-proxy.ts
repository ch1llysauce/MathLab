/**
 * Lightweight Cloudflare Worker / Pages Function edge proxy for MathLab.
 * Handles edge health checks, CORS/security headers, and forwarding /api/* requests
 * to the FastAPI Python backend without executing heavy symbolic math at the edge.
 */

export interface Env {
  BACKEND_API_URL?: string;
  ALLOWED_ORIGIN?: string;
}

export async function proxyApiRequest(request: Request, env: Env): Promise<Response> {
  const url = new URL(request.url);

  if (url.pathname === "/edge/health") {
    return Response.json({ status: "ok", layer: "cloudflare-worker" });
  }

  if (!url.pathname.startsWith("/api/")) {
    return new Response("Not Found", { status: 404 });
  }

  if (!env.BACKEND_API_URL) {
    return Response.json(
      {
        error: {
          code: "PROXY_NOT_CONFIGURED",
          message: "BACKEND_API_URL is not configured in Cloudflare environment variables.",
        },
      },
      { status: 503 }
    );
  }

  if (request.method === "OPTIONS" && env.ALLOWED_ORIGIN) {
    return new Response(null, {
      status: 204,
      headers: {
        "Access-Control-Allow-Origin": env.ALLOWED_ORIGIN,
        "Access-Control-Allow-Methods": "GET, POST, PUT, PATCH, DELETE, OPTIONS",
        "Access-Control-Allow-Headers":
          request.headers.get("Access-Control-Request-Headers") ?? "Content-Type, Authorization",
        "Access-Control-Max-Age": "86400",
      },
    });
  }

  const upstreamBase = env.BACKEND_API_URL.replace(/\/$/, "");
  const targetUrl = `${upstreamBase}${url.pathname}${url.search}`;

  const upstreamHeaders = new Headers(request.headers);
  upstreamHeaders.delete("host");

  const proxiedRequest = new Request(targetUrl, {
    method: request.method,
    headers: upstreamHeaders,
    body: request.method === "GET" || request.method === "HEAD" ? undefined : request.body,
  });

  const upstreamResp = await fetch(proxiedRequest);
  const headers = new Headers(upstreamResp.headers);
  headers.set("X-Content-Type-Options", "nosniff");
  headers.set("Referrer-Policy", "strict-origin-when-cross-origin");
  if (env.ALLOWED_ORIGIN) {
    headers.set("Access-Control-Allow-Origin", env.ALLOWED_ORIGIN);
  }

  return new Response(upstreamResp.body, {
    status: upstreamResp.status,
    statusText: upstreamResp.statusText,
    headers,
  });
}

export default {
  fetch(request: Request, env: Env): Promise<Response> {
    return proxyApiRequest(request, env);
  },
};
