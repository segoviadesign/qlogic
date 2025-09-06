// api/[...path].js
export const config = { runtime: "edge" };

// Origen oficial (¡sin /api final!)
const ORIGIN = "https://resultados.mininterior.gob.ar";

export default async function handler(req) {
  const url = new URL(req.url);
  // url.pathname viene como /api/lo-que-sigue
  // Quitamos el prefijo /api para construir la ruta real
  const upstreamPath = url.pathname.replace(/^\/api/, "") || "/";
  // Solo por seguridad: si por error no queda prefijo, devolvemos 404
  if (!upstreamPath.startsWith("/")) {
    return new Response("Not allowed", { status: 403 });
  }

  // Construimos la URL final al upstream, preservando query
  const upstream = new URL(ORIGIN);
  upstream.pathname = upstreamPath;   // p.ej: /resultados/getResultados
  upstream.search = url.search;       // p.ej: ?anioEleccion=...

  // Headers limpios hacia el upstream
  const headers = new Headers({
    "User-Agent": "Mozilla/5.0 (compatible; qlogic-proxy/1.0)",
    "Accept": "application/json",
  });

  // Si algún día te dan token oficial:
  // const token = process.env.BEARER_TOKEN;
  // if (token) headers.set("Authorization", `Bearer ${token}`);

  const resp = await fetch(upstream.toString(), {
    method: "GET",
    headers,
    // signal: no es necesario en Edge
  });

  // Clonamos headers de respuesta y (opcional) agregamos cache corto
  const out = new Headers(resp.headers);
  // out.set("Cache-Control", "public, max-age=60");

  return new Response(resp.body, { status: resp.status, headers: out });
}
