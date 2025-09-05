import io
import os
import datetime as dt
import requests
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter

import pandas as pd
from flask import Flask, render_template, request, jsonify, send_file
from dotenv import load_dotenv

# -------------------------------------------------------------------
# Configuración de sesión HTTP con reintentos
# -------------------------------------------------------------------
session = requests.Session()
retry = Retry(
    total=4,
    connect=4,
    read=4,
    backoff_factor=0.6,
    status_forcelist=(429, 500, 502, 503, 504),
    allowed_methods=("GET",),
    raise_on_status=False,
)
adapter = HTTPAdapter(max_retries=retry, pool_connections=20, pool_maxsize=20)
session.mount("https://", adapter)
session.mount("http://", adapter)

DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; qlogic/1.0; +https://qlogic.alwaysdata.net)",
    "Accept": "application/json",
}

# -------------------------------------------------------------------
# Motor de PDF
# -------------------------------------------------------------------
PDF_ENGINE = None
try:
    from xhtml2pdf import pisa  # noqa: F401
    PDF_ENGINE = "xhtml2pdf"
except Exception:
    try:
        from weasyprint import HTML  # noqa: F401
        PDF_ENGINE = "weasyprint"
    except Exception:
        PDF_ENGINE = None

# -------------------------------------------------------------------
# Configuración
# -------------------------------------------------------------------
load_dotenv()
# Ejemplos:
#   - Producción directa (no recomendable desde Alwaysdata por timeouts):
#       https://resultados.mininterior.gob.ar/api
#   - Proxy Vercel (recomendado): https://<tu-app>.vercel.app/api
API_BASE = os.getenv("API_BASE", "https://resultados.mininterior.gob.ar/api").rstrip("/")

# Si usás Vercel con Deployment Protection activada, poné el secreto en el entorno:
#   VERCEL_BYPASS_TOKEN=f9a1c4d6e7b28f3c91ab45de67f0c2a8
VERCEL_BYPASS_TOKEN = os.getenv("VERCEL_BYPASS_TOKEN", "").strip()

app = Flask(__name__)

# Catálogos básicos
TIPOS_RECUENTO = [
    {"value": "1", "label": "Provisorio (1)"},
]
TIPOS_ELECCION = [
    {"value": "1", "label": "PASO (1)"},
    {"value": "2", "label": "Generales (2)"},
    {"value": "3", "label": "Balotaje (3)"},
]
CATEGORIAS = [
    {"value": 1, "label": "Presidente/a"},
    {"value": 2, "label": "Senador/a Nacional"},
    {"value": 3, "label": "Diputado/a Nacional"},
    {"value": 8, "label": "Parlasur - Distrito Nacional"},
    {"value": 9, "label": "Parlasur - Distrito Regional"},
]
DISTRITOS = [
    {"value": "1", "label": "CABA"},
    {"value": "2", "label": "Buenos Aires"},
    {"value": "3", "label": "Catamarca"},
    {"value": "4", "label": "Córdoba"},
    {"value": "5", "label": "Corrientes"},
    {"value": "6", "label": "Chaco"},
    {"value": "7", "label": "Chubut"},
    {"value": "8", "label": "Entre Ríos"},
    {"value": "9", "label": "Formosa"},
    {"value": "10", "label": "Jujuy"},
    {"value": "11", "label": "La Pampa"},
    {"value": "12", "label": "La Rioja"},
    {"value": "13", "label": "Mendoza"},
    {"value": "14", "label": "Misiones"},
    {"value": "15", "label": "Neuquén"},
    {"value": "16", "label": "Río Negro"},
    {"value": "17", "label": "Salta"},
    {"value": "18", "label": "San Juan"},
    {"value": "19", "label": "San Luis"},
    {"value": "20", "label": "Santa Cruz"},
    {"value": "21", "label": "Santa Fe"},
    {"value": "22", "label": "Santiago del Estero"},
    {"value": "23", "label": "Tucumán"},
    {"value": "24", "label": "Tierra del Fuego A.I.A.S."},
]
ANIOS = [str(y) for y in range(2011, dt.datetime.now().year + 1)]

# -------------------------------------------------------------------
# Helper para llamadas externas (agrega bypass de Vercel si aplica)
# -------------------------------------------------------------------
def _session_get(path: str, params: dict | None):
    """
    Realiza GET a {API_BASE}{path} reusando la sesión global, con headers
    y timeouts. Si VERCEL_BYPASS_TOKEN está definido, agrega los parámetros
    de bypass para setear la cookie en Vercel (cuando hay Deployment Protection).
    """
    url = f"{API_BASE}{path}"
    final_params = dict(params or {})
    if VERCEL_BYPASS_TOKEN:
        final_params["x-vercel-set-bypass-cookie"] = "true"
        final_params["x-vercel-protection-bypass"] = VERCEL_BYPASS_TOKEN

    r = session.get(url, params=final_params, headers=DEFAULT_HEADERS, timeout=(5, 30))
    r.raise_for_status()
    return r

# -------------------------------------------------------------------
# Home
# -------------------------------------------------------------------
@app.route("/")
def index():
    return render_template(
        "index.html",
        tipos_recuento=TIPOS_RECUENTO,
        tipos_eleccion=TIPOS_ELECCION,
        categorias=CATEGORIAS,
        anios=ANIOS,
        distritos=DISTRITOS,
    )

# -------------------------------------------------------------------
# Proxy hacia la API (oficial o proxy) con filtros
# -------------------------------------------------------------------
@app.route("/api/resultados")
def api_resultados():
    params = {
        "anioEleccion": request.args.get("anioEleccion"),
        "tipoRecuento": request.args.get("tipoRecuento"),
        "tipoEleccion": request.args.get("tipoEleccion"),
        "categoriaId": request.args.get("categoriaId"),
        "distritoId": request.args.get("distritoId"),
        "seccionProvincialId": request.args.get("seccionProvincialId"),
        "seccionId": request.args.get("seccionId"),
        "circuitoId": request.args.get("circuitoId"),
        "mesaId": request.args.get("mesaId"),
    }
    params = {k: v for k, v in params.items() if v not in (None, "", "null")}

    if "categoriaId" not in params:
        return jsonify({"error": "categoriaId es requerido"}), 400

    try:
        # IMPORTANTE:
        # Mantener este path: "/resultados/getResultados"
        #   - Si API_BASE = https://<tu-app>.vercel.app/api  -> pega al proxy Vercel
        #   - Si API_BASE = https://resultados.mininterior.gob.ar/api -> pega directo
        r = _session_get("/resultados/getResultados", params)
    except requests.Timeout:
        return jsonify({"error": "Timeout conectando a la API/proxy"}), 504
    except requests.RequestException as e:
        return jsonify({"error": f"Fallo consultando API: {e}"}), 502

    data = r.json()
    return jsonify({"query": params, "data": data})

# -------------------------------------------------------------------
# Funciones auxiliares para exportar
# -------------------------------------------------------------------
def _armar_dataframes(data_json):
    val = data_json.get("valoresTotalizadosPositivos") or []
    otros = data_json.get("valoresTotalizadosOtros") or []

    df_positivos = pd.DataFrame([
        {
            "idAgrupacion": x.get("idAgrupacion"),
            "idAgrupacionTelegrama": x.get("idAgrupacionTelegrama"),
            "nombreAgrupacion": x.get("nombreAgrupacion"),
            "votos": x.get("votos"),
            "votosPorcentaje": x.get("votosPorcentaje"),
            "urlLogo": x.get("urlLogo"),
        }
        for x in val
    ])
    df_otros = pd.DataFrame(otros)
    return df_positivos, df_otros

# -------------------------------------------------------------------
# Exportar Excel
# -------------------------------------------------------------------
@app.route("/export/excel")
def export_excel():
    # Reutilizamos nuestro propio endpoint /api/resultados para no duplicar lógica
    qs = request.query_string.decode()
    prox = requests.get(request.host_url.rstrip("/") + "/api/resultados?" + qs, timeout=30)
    prox.raise_for_status()
    payload = prox.json()
    data = payload.get("data", {})

    df_pos, df_otros = _armar_dataframes(data)

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df_pos.to_excel(writer, index=False, sheet_name="Positivos")
        if not df_otros.empty:
            df_otros.to_excel(writer, index=False, sheet_name="Otros")

    output.seek(0)
    filename = f"resultados_{dt.datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    return send_file(
        output,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name=filename,
    )

# -------------------------------------------------------------------
# Exportar PDF
# -------------------------------------------------------------------
@app.route("/export/pdf")
def export_pdf():
    qs = request.query_string.decode()
    prox = requests.get(request.host_url.rstrip("/") + "/api/resultados?" + qs, timeout=30)
    prox.raise_for_status()
    payload = prox.json()
    data = payload.get("data", {})

    df_pos, df_otros = _armar_dataframes(data)

    html = render_template(
        "pdf.html",
        fecha=data.get("fechaTotalizacion"),
        estado=data.get("estadoRecuento"),
        df_pos=df_pos.fillna(""),
        df_otros=df_otros.fillna(""),
        query=payload.get("query", {}),
    )

    if PDF_ENGINE == "xhtml2pdf":
        pdf_io = io.BytesIO()
        result = pisa.CreatePDF(html, dest=pdf_io)  # type: ignore[name-defined]
        if result.err:
            return f"Error generando PDF (xhtml2pdf): {result.err}", 500
        pdf_io.seek(0)
    elif PDF_ENGINE == "weasyprint":
        from weasyprint import HTML
        pdf_io = io.BytesIO()
        HTML(string=html, base_url=request.host_url).write_pdf(pdf_io)
        pdf_io.seek(0)
    else:
        return "No hay motor de PDF disponible.", 500

    filename = f"resultados_{dt.datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    return send_file(pdf_io, mimetype="application/pdf", as_attachment=True, download_name=filename)

# -------------------------------------------------------------------
# Entry point
# -------------------------------------------------------------------
if __name__ == "__main__":
    app.run(debug=True)
