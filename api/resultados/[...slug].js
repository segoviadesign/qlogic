// Ejecuta en Edge (rápido y sin cold starts)
export const config = { runtime: "edge" };

const UPSTREAM = "https://resultados.mininterior.gob.ar/api";

export default async function handler(req) {
  const url = new URL(req.url);

  // Viene como /api/resultados/...
  const path = url.pathname; // ej: /api/resultados/getResultados

  // Aceptamos SÓLO /api/resultados/*
  if (!path.startsWith("/api/resultados/")) {
    return new Response("Not allowed", { status: 403 });
  }

  // Construimos la URL real al upstream: /resultados/*
  const upstream = new URL(UPSTREAM);
  upstream.pathname = path.replace(/^\/api/, ""); // -> /resultados/...
  upstream.search = url.search;

  const headers = new Headers(req.headers);
  headers.set("User-Agent", "Mozilla/5.0 (compatible; qlogic-proxy/1.0)");
  headers.set("Accept", "application/json");

  // Si alguna vez te dan token oficial, descomentá:
  // const token = process.env.BEARER_TOKEN;
  // if (token) headers.set("Authorization", `Bearer ${token}`);

  const resp = await fetch(upstream.toString(), { method: "GET", headers });

  const out = new Headers(resp.headers);
  // Cache opcional:
  // out.set("Cache-Control", "public, max-age=60");

  return new Response(resp.body, { status: resp.status, headers: out });
}
