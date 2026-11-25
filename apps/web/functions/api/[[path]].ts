import { type Env, proxyApiRequest } from "../../../../infrastructure/cloudflare/workers/api-proxy";

interface PagesContext {
  request: Request;
  env: Env;
}

/**
 * Cloudflare Pages Function handling all same-origin /api/* requests
 * and forwarding them to the Python FastAPI backend (BACKEND_API_URL).
 */
export function onRequest(context: PagesContext): Promise<Response> {
  return proxyApiRequest(context.request, context.env);
}
