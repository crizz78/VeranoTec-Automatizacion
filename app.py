from flask import Flask, render_template_string, request, redirect, url_for, flash
from datetime import datetime

app = Flask(__name__)
app.secret_key = "veranotec_scc1007_clave_segura"

# ==========================================
# BASE DE DATOS SIMULADA (SIN DATOS REALES)
# ==========================================
ALUMNOS = {
    "SIM-2401": {"nombre": "Alumno Simulado 01", "carrera": "Ing. Sistemas Comp.", "aprobadas": ["MAT-01", "PRO-01"], "reprobadas": []},
    "SIM-2402": {"nombre": "Alumno Simulado 02", "carrera": "Ing. Sistemas Comp.", "aprobadas": ["PRO-01"], "reprobadas": ["MAT-01"]},
    "SIM-2403": {"nombre": "Alumno Simulado 03", "carrera": "Ing. Sistemas Comp.", "aprobadas": ["MAT-01", "PRO-01", "FIS-01"], "reprobadas": []},
    "SIM-2404": {"nombre": "Alumno Simulado 04", "carrera": "Ing. Sistemas Comp.", "aprobadas": ["MAT-01", "PRO-01"], "reprobadas": []},
}

MATERIAS = {
    "FIS-01": {
        "nombre": "Fundamentos de Ing. de Software",
        "clave": "SCC-1007",
        "prerrequisito": "PRO-01",
        "minimo": 10,
        "inscritos": ["SIM-901", "SIM-902", "SIM-903", "SIM-904", "SIM-905", "SIM-906", "SIM-907", "SIM-908", "SIM-909"],
        "estado": "En espera de mínimo",
        "docente": None,
        "horario": "Lun-Vie 08:00 - 10:00 | Aula CC-2"
    },
    "MAT-02": {
        "nombre": "Cálculo Integral",
        "clave": "ACF-0902",
        "prerrequisito": "MAT-01",
        "minimo": 10,
        "inscritos": ["SIM-910", "SIM-911", "SIM-912", "SIM-913", "SIM-914"],
        "estado": "En espera de mínimo",
        "docente": None,
        "horario": "Lun-Vie 10:00 - 12:00 | Aula B-4"
    }
}

DOCENTES = ["Ing. Roberto Martínez (Simulado)", "M.C. Laura Sánchez (Simulado)", "Ing. Carlos Hernández (Simulado)"]
PAGOS = {}      # {(alumno_id, materia_id): {"referencia": str, "pagado": bool}}
BITACORA = []

def registrar_evento(actor, accion):
    hora = datetime.now().strftime("%H:%M:%S")
    BITACORA.insert(0, f"[{hora}] ({actor}) -> {accion}")

# ==========================================
# INTERFAZ DE USUARIO (UX VERANOTEC)
# ==========================================
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>VeranoTec | Automatización de Cursos de Verano</title>
    <style>
        body { font-family: 'Segoe UI', sans-serif; background: #f1f5f9; color: #1e293b; margin: 0; padding: 20px; }
        .container { max-width: 1100px; margin: auto; }
        header { background: #0f172a; color: white; padding: 20px 25px; border-radius: 10px; display: flex; justify-content: space-between; align-items: center; }
        header h1 { margin: 0; font-size: 22px; color: #38bdf8; }
        header span { font-size: 13px; color: #cbd5e1; }
        .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-top: 20px; }
        .card { background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 6px rgba(0,0,0,0.06); }
        h2 { margin-top: 0; font-size: 17px; border-bottom: 2px solid #e2e8f0; padding-bottom: 8px; color: #0f172a; }
        select, button { padding: 8px 12px; border-radius: 6px; border: 1px solid #cbd5e1; font-size: 14px; }
        button { background: #0284c7; color: white; border: none; cursor: pointer; font-weight: 600; }
        button:hover { background: #0369a1; }
        button.btn-green { background: #16a34a; }
        button.btn-green:hover { background: #15803d; }
        button.btn-amber { background: #d97706; }
        table { width: 100%; border-collapse: collapse; margin-top: 10px; font-size: 13px; }
        th, td { padding: 8px; border-bottom: 1px solid #e2e8f0; text-align: left; }
        .badge { padding: 3px 8px; border-radius: 12px; font-size: 11px; font-weight: bold; }
        .wait { background: #fef3c7; color: #92400e; }
        .open { background: #dcfce7; color: #166534; }
        .alert { padding: 12px; border-radius: 6px; margin-top: 15px; font-weight: 500; }
        .alert-ok { background: #dcfce7; color: #166534; border: 1px solid #86efac; }
        .alert-err { background: #fee2e2; color: #991b1b; border: 1px solid #fca5a5; }
        .log { background: #0f172a; color: #38bdf8; font-family: monospace; padding: 12px; border-radius: 6px; max-height: 180px; overflow-y: auto; font-size: 12px; }
    </style>
</head>
<body>
<div class="container">
    <header>
        <div>
            <h1>VeranoTec · Sistema Automatizado de Cursos de Verano</h1>
            <span>TecNM Campus Matehuala · División de Estudios Profesionales (Datos 100% Simulados)</span>
        </div>
        <div>Consultora: <strong>VeranoTec</strong></div>
    </header>

    {% with messages = get_flashed_messages(with_categories=true) %}
      {% if messages %}
        {% for category, message in messages %}
          <div class="alert {{ 'alert-ok' if category == 'ok' else 'alert-err' }}">{{ message }}</div>
        {% endfor %}
      {% endif %}
    {% endwith %}

    <div class="grid">
        <!-- VISTA 1: ALUMNO -->
        <div class="card">
            <h2>1. Portal del Alumno (Solicitud y Validación de Kárdex)</h2>
            <form action="/solicitar" method="POST">
                <label>Selecciona Alumno:</label><br>
                <select name="alumno_id" style="width: 100%; margin: 6px 0 12px;">
                    {% for aid, a in alumnos.items() %}
                    <option value="{{ aid }}" {{ 'selected' if aid == 'SIM-2404' else '' }}>
                        {{ aid }} - {{ a.nombre }} (Aprobadas: {{ a.aprobadas|join(', ') }})
                    </option>
                    {% endfor %}
                </select>
                <label>Materia a solicitar:</label><br>
                <select name="materia_id" style="width: 100%; margin: 6px 0 12px;">
                    {% for mid, m in materias.items() %}
                    <option value="{{ mid }}">{{ m.clave }} - {{ m.nombre }} (Req: {{ m.prerrequisito }})</option>
                    {% endfor %}
                </select>
                <button type="submit">Solicitar Materia en Línea</button>
            </form>

            <h2 style="margin-top: 20px;">Referencias de Pago Generadas Automáticamente</h2>
            {% if pagos %}
            <table>
                <tr><th>Alumno</th><th>Materia</th><th>Referencia</th><th>Estado</th></tr>
                {% for (aid, mid), p in pagos.items() %}
                <tr>
                    <td>{{ aid }}</td>
                    <td>{{ materias[mid].nombre }}</td>
                    <td><code>{{ p.referencia }}</code></td>
                    <td>
                        {% if p.pagado %}
                            <span class="badge open">PAGADO · {{ materias[mid].horario }}</span>
                        {% else %}
                            <form action="/pagar" method="POST" style="display:inline;">
                                <input type="hidden" name="alumno_id" value="{{ aid }}">
                                <input type="hidden" name="materia_id" value="{{ mid }}">
                                <button type="submit" class="btn-green">Simular Pago</button>
                            </form>
                        {% endif %}
                    </td>
                </tr>
                {% endfor %}
            </table>
            {% else %}
            <p style="font-size: 13px; color: #64748b;">Aún no hay referencias. Se generan automáticamente al abrirse el grupo y asignarse docente.</p>
            {% endif %}
        </div>

        <!-- VISTA 2: JEFATURA Y DIVISIÓN -->
        <div class="card">
            <h2>2. Jefatura Académica y División de Estudios</h2>
            <table>
                <tr><th>Materia</th><th>Demanda</th><th>Estado del Grupo</th><th>Docente / Acción</th></tr>
                {% for mid, m in materias.items() %}
                <tr>
                    <td><strong>{{ m.nombre }}</strong><br><small>{{ m.clave }}</small></td>
                    <td><strong>{{ m.inscritos|length }} / {{ m.minimo }}</strong></td>
                    <td>
                        <span class="badge {{ 'open' if m.inscritos|length >= m.minimo else 'wait' }}">
                            {{ m.estado }}
                        </span>
                    </td>
                    <td>
                        {% if m.docente %}
                            <strong>{{ m.docente }}</strong>
                        {% elif m.inscritos|length >= m.minimo %}
                            <form action="/asignar_docente" method="POST">
                                <input type="hidden" name="materia_id" value="{{ mid }}">
                                <select name="docente">
                                    {% for d in docentes %}<option value="{{ d }}">{{ d }}</option>{% endfor %}
                                </select>
                                <button type="submit" class="btn-green" style="margin-top:4px;">Asignar Docente</button>
                            </form>
                        {% else %}
                            <form action="/excepcion" method="POST">
                                <input type="hidden" name="materia_id" value="{{ mid }}">
                                <button type="submit" class="btn-amber">Abrir por Excepción (División)</button>
                            </form>
                        {% endif %}
                    </td>
                </tr>
                {% endfor %}
            </table>

            <h2 style="margin-top: 20px;">3. Bitácora de Automatización (Auditoría)</h2>
            <div class="log">
                {% for linea in bitacora %}
                    <div>{{ linea }}</div>
                {% else %}
                    <div>[Sistema listo] Esperando solicitudes de alumnos...</div>
                {% endfor %}
            </div>
        </div>
    </div>
</div>
</body>
</html>
"""

# ==========================================
# RUTAS Y REGLAS DE NEGOCIO AUTOMATIZADAS
# ==========================================
@app.route("/")
def index():
    return render_template_string(
        HTML_TEMPLATE, alumnos=ALUMNOS, materias=MATERIAS, docentes=DOCENTES, pagos=PAGOS, bitacora=BITACORA
    )

@app.route("/solicitar", methods=["POST"])
def solicitar():
    aid = request.form["alumno_id"]
    mid = request.form["materia_id"]
    alumno = ALUMNOS[aid]
    materia = MATERIAS[mid]

    # Regla 1: No cursar materia ya aprobada
    if mid in alumno["aprobadas"]:
        registrar_evento("Validación Kárdex", f"RECHAZADO: {aid} ya aprobó {materia['nombre']}.")
        flash(f"Bloqueado: {alumno['nombre']} ya tiene acreditada {materia['nombre']} en su kárdex.", "err")
        return redirect(url_for("index"))

    # Regla 2: Cumplir prerrequisito
    if materia["prerrequisito"] not in alumno["aprobadas"]:
        registrar_evento("Validación Kárdex", f"RECHAZADO: {aid} no cumple prerrequisito {materia['prerrequisito']}.")
        flash(f"Bloqueado: {alumno['nombre']} no ha aprobado el prerrequisito ({materia['prerrequisito']}).", "err")
        return redirect(url_for("index"))

    # Regla 3: Evitar duplicados
    if aid in materia["inscritos"]:
        flash(f"{alumno['nombre']} ya está registrado en la solicitud de {materia['nombre']}.", "err")
        return redirect(url_for("index"))

    materia["inscritos"].append(aid)
    registrar_evento("Solicitud", f"{aid} se registró en {materia['nombre']} ({len(materia['inscritos'])}/{materia['minimo']}).")

    # Regla 4: Apertura automática al llegar al mínimo
    if len(materia["inscritos"]) >= materia["minimo"] and materia["estado"] == "En espera de mínimo":
        materia["estado"] = "Grupo Abierto · Pendiente Docente"
        registrar_evento("Motor Reglas", f"¡MÍNIMO ALCANZADO! {materia['nombre']} cambió a Grupo Abierto y notificó a Jefatura.")
        flash(f"¡Solicitud aceptada y GRUPO ABIERTO automáticamente ({len(materia['inscritos'])}/{materia['minimo']})!", "ok")
    else:
        flash(f"Solicitud registrada correctamente para {alumno['nombre']}.", "ok")

    return redirect(url_for("index"))

@app.route("/asignar_docente", methods=["POST"])
def asignar_docente():
    mid = request.form["materia_id"]
    docente = request.form["docente"]
    materia = MATERIAS[mid]
    materia["docente"] = docente
    materia["estado"] = "Confirmado · Referencias Emitidas"

    # Generación automática de referencias de pago solo para alumnos simulados registrados
    for aid in materia["inscritos"]:
        if aid in ALUMNOS:
            PAGOS[(aid, mid)] = {"referencia": f"REF-2026-{mid}-{aid.split('-')[1]}", "pagado": False}

    registrar_evento("Jefatura", f"Asignó a {docente} en {materia['nombre']}. Referencias de pago generadas.")
    flash(f"Docente asignado y referencias de pago emitidas automáticamente.", "ok")
    return redirect(url_for("index"))

@app.route("/excepcion", methods=["POST"])
def excepcion():
    mid = request.form["materia_id"]
    materia = MATERIAS[mid]
    materia["estado"] = "Abierto por Excepción · Pendiente Docente"
    registrar_evento("División Est. Prof.", f"Autorizó apertura por excepción de {materia['nombre']} sin llegar al mínimo.")
    flash(f"División autorizó excepción para {materia['nombre']}. Ya se puede asignar docente.", "ok")
    return redirect(url_for("index"))

@app.route("/pagar", methods=["POST"])
def pagar():
    aid = request.form["alumno_id"]
    mid = request.form["materia_id"]
    PAGOS[(aid, mid)]["pagado"] = True
    registrar_evento("Conciliación Bancaria", f"Pago confirmado para {aid} en {MATERIAS[mid]['nombre']}. Horario liberado.")
    flash(f"Pago confirmado por referencia. Horario oficial generado para {aid}.", "ok")
    return redirect(url_for("index"))

if __name__ == "__main__":
    app.run(debug=True, port=5000)