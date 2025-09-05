function buildQuery() {
  const qs = new URLSearchParams();
  const get = id => document.getElementById(id).value.trim();

  const fields = [
    "anioEleccion", "tipoRecuento", "tipoEleccion", "categoriaId",
    "distritoId", "seccionProvincialId", "seccionId", "circuitoId", "mesaId"
  ];
  for (const f of fields) {
    const v = get(f);
    if (v) qs.set(f, v);
  }
  return qs;
}

async function consultar() {
  const qs = buildQuery();
  const url = `/api/resultados?${qs.toString()}`;

  const btn = document.getElementById("btnConsultar");
  btn.disabled = true; btn.textContent = "Consultando...";
  try {
    const r = await fetch(url);
    const payload = await r.json();
    if (!r.ok) throw new Error(payload.error || "Error de API");

    const data = payload.data || {};
    const positivos = data.valoresTotalizadosPositivos || [];
    const otros = data.valoresTotalizadosOtros || [];

    // Meta
    const meta = document.getElementById("meta");
    meta.textContent = `Totalizado: ${data.fechaTotalizacion || "-"} | Estado: ${JSON.stringify(data.estadoRecuento || {})}`;

    // Tabla
    const tbody = document.getElementById("tbodyPositivos");
    tbody.innerHTML = "";
    if (!positivos.length) {
      tbody.innerHTML = `<tr><td colspan="3" class="text-muted">Sin datos</td></tr>`;
    } else {
      for (const x of positivos) {
        const tr = document.createElement("tr");
        tr.innerHTML = `
          <td>${x.nombreAgrupacion || "-"}</td>
          <td class="text-end">${x.votos ?? "-"}</td>
          <td class="text-end">${(x.votosPorcentaje ?? 0).toFixed(2)}</td>
        `;
        tbody.appendChild(tr);
      }
    }

    // Otros
    const otrosWrap = document.getElementById("otrosWrap");
    const otrosPre = document.getElementById("otros");
    if (otros && Array.isArray(otros) && otros.length) {
      otrosWrap.classList.remove("d-none");
      otrosPre.textContent = JSON.stringify(otros, null, 2);
    } else {
      otrosWrap.classList.add("d-none");
      otrosPre.textContent = "";
    }

    // Habilitar export
    const q = qs.toString();
    const btnExcel = document.getElementById("btnExcel");
    const btnPDF = document.getElementById("btnPDF");
    btnExcel.classList.remove("disabled");
    btnPDF.classList.remove("disabled");
    btnExcel.href = `/export/excel?${q}`;
    btnPDF.href = `/export/pdf?${q}`;

    // Resumen del escrutinio (MOVIDO DENTRO DEL try, donde existe 'data')
    const resumenWrap = document.getElementById("resumenWrap");
    if (data.estadoRecuento) {
      const e = data.estadoRecuento;
      document.getElementById("resumenFecha").textContent =
        data.fechaTotalizacion || "-";
      document.getElementById("resumenElectores").textContent =
        e.cantidadElectores?.toLocaleString("es-AR") || "-";
      document.getElementById("resumenVotantes").textContent =
        e.cantidadVotantes?.toLocaleString("es-AR") || "-";
      document.getElementById("resumenMesasEsperadas").textContent =
        e.mesasEsperadas?.toLocaleString("es-AR") || "-";
      document.getElementById("resumenMesasTotalizadas").textContent =
        e.mesasTotalizadas?.toLocaleString("es-AR") || "-";
      document.getElementById("resumenMesasPorcentaje").textContent =
        (e.mesasTotalizadasPorcentaje ?? 0).toFixed(2);
      document.getElementById("resumenParticipacion").textContent =
        (e.participacionPorcentaje ?? 0).toFixed(2);

      resumenWrap.classList.remove("d-none");
    } else {
      resumenWrap.classList.add("d-none");
    }

  } catch (err) {
    alert(err.message);
  } finally {
    btn.disabled = false; btn.textContent = "Consultar";
  }
}

document.addEventListener("DOMContentLoaded", () => {
  document.getElementById("btnConsultar").addEventListener("click", consultar);
});
