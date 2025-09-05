export default async function handler(req, res) {
  if (req.method !== "GET") return res.status(405).send("Method Not Allowed");

  const query = req.url.includes("?") ? req.url.slice(req.url.indexOf("?")) : "";
  const upstream = "https://resultados.mininterior.gob.ar/api/resultados/getResultados" + query;

  try {
    const r = await fetch(upstream, {
      headers: {
        "User-Agent": "Mozilla/5.0 (compatible; qlogic-proxy/1.0)",
        "Accept": "application/json",
      },
    });
    res.status(r.status);
    const data = await r.text();
    res.send(data);
  } catch (e) {
    res.status(502).send("Upstream error: " + (e?.message ?? e));
  }
}
