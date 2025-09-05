// Proxy serverless para /api/resultados/getResultados
export default async function handler(req, res) {
  try {
    if (req.method !== "GET") return res.status(405).send("Method Not Allowed");

    // Permitimos solo el endpoint que usás
    const path = req.url.split("?")[0] || "";
    if (path !== "/api/resultados") return res.status(403).send("Not allowed");

    // Conservamos el query string original
    const query = req.url.includes("?") ? req.url.slice(req.url.indexOf("?")) : "";

    // Construimos la URL del upstream (OJO: /api + /resultados/getResultados)
    const upstream = "https://resultados.mininterior.gob.ar/api/resultados/getResultados" + query;

    const r = await fetch(upstream, {
      headers: {
        "User-Agent": "Mozilla/5.0 (compatible; qlogic-proxy/1.0)",
        "Accept": "application/json",
      },
      // Vercel maneja timeouts por función; no suele hacer falta AbortController
    });

    // Devolvemos tal cual el status y el cuerpo
    res.status(r.status);
    // cachecito opcional (60s) en el edge/CDN de Vercel:
    // res.setHeader("Cache-Control", "s-maxage=60, stale-while-revalidate=30");

    const body = await r.text(); // puede ser JSON o error HTML del origen
    return res.send(body);
  } catch (e) {
    return res.status(502).send("Upstream error: " + (e?.message ?? e));
  }
}
