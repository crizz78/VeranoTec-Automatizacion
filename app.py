import sqlite3
from flask import Flask, render_template_string, request, redirect, url_for, flash
from datetime import datetime

app = Flask(__name__)
app.secret_key = "veranotec_scc1007_clave_segura"
DB_NAME = "veranotec.db"

# ==========================================
# BASE DE DATOS RELACIONAL (SQLITE)
# ==========================================
def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()

    c.execute('''CREATE TABLE IF NOT EXISTS alumnos (
        id TEXT PRIMARY KEY,
        nombre TEXT,
        carrera TEXT,
        aprobadas TEXT,
        nota_ux TEXT
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS materias (
        id TEXT PRIMARY KEY,
        nombre TEXT,
        clave TEXT,
        prerrequisito TEXT,
        prerrequisito_nombre TEXT,
        minimo INTEGER,
        estado TEXT,
        docente TEXT,
        horario TEXT
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS inscripciones (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        alumno_id TEXT,
        materia_id TEXT,
        fecha_registro TEXT,
        UNIQUE(alumno_id, materia_id)
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS pagos (
        alumno_id TEXT,
        materia_id TEXT,
        referencia TEXT,
        pagado INTEGER DEFAULT 0,
        fecha_pago TEXT,
        PRIMARY KEY (alumno_id, materia_id)
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS bitacora (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        hora TEXT,
        actor TEXT,
        accion TEXT
    )''')

    if c.execute("SELECT COUNT(*) FROM alumnos").fetchone()[0] == 0:
        alumnos_init = [
            ("SIM-2404", "Alumno Simulado 04 (Listo para abrir grupo)", "Ing. Sistemas Comp.", "MAT-01,PRO-01", "Cumple requisitos para Ing. de Software y Cálculo Integral"),
            ("SIM-2402", "Alumno Simulado 02 (Sin prerrequisito de Cálculo)", "Ing. Sistemas Comp.", "PRO-01", "Reprobó Cálculo Diferencial (MAT-01); el sistema debe bloquearlo en Cálculo Integral"),
            ("SIM-2403", "Alumno Simulado 03 (Materia ya cursada)", "Ing. Sistemas Comp.", "MAT-01,PRO-01,FIS-01", "Ya aprobó Ing. de Software (FIS-01); el sistema evita duplicados"),
            ("SIM-2401", "Alumno Simulado 01 (Alumno regular)", "Ing. Sistemas Comp.", "MAT-01,PRO-01", "Cumple todos los requisitos académicos")
        ]
        c.executemany("INSERT INTO alumnos VALUES (?, ?, ?, ?, ?)", alumnos_init)

        materias_init = [
            ("FIS-01", "Fundamentos de Ingeniería de Software", "SCC-1007", "PRO-01", "Fundamentos de Programación", 10, "En espera de mínimo", None, "Lun-Vie 08:00 - 10:00 | Aula CC-2"),
            ("MAT-02", "Cálculo Integral", "ACF-0902", "MAT-01", "Cálculo Diferencial", 10, "En espera de mínimo", None, "Lun-Vie 10:00 - 12:00 | Aula B-4")
        ]
        c.executemany("INSERT INTO materias VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", materias_init)

        # Precarga de 9 alumnos en FIS-01 para que al registrar 1 más se abra el grupo automáticamente
        precarga_fis = [(f"SIM-90{i}", "FIS-01", "2026-11-25 08:00:00") for i in range(1, 10)]
        precarga_mat = [(f"SIM-91{i}", "MAT-02", "2026-11-25 08:00:00") for i in range(0, 5)]
        c.executemany("INSERT INTO inscripciones (alumno_id, materia_id, fecha_registro) VALUES (?, ?, ?)", precarga_fis + precarga_mat)

    conn.commit()
    conn.close()

def registrar_evento(conn, actor, accion):
    hora = datetime.now().strftime("%H:%M:%S")
    conn.execute("INSERT INTO bitacora (hora, actor, accion) VALUES (?, ?, ?)", (hora, actor, accion))

DOCENTES = [
    "Ing. Roberto Martínez (Simulado)",
    "M.C. Laura Sánchez (Simulado)",
    "Ing. Carlos Hernández (Simulado)"
]

# ==========================================
# INTERFAZ DE USUARIO AMIGABLE (UX)
# ==========================================
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>VeranoTec | Portal de Cursos de Verano</title>
    <style>
        :root {
            --azul-oscuro: #0f172a;
            --azul-primario: #0284c7;
            --azul-claro: #e0f2fe;
            --verde: #16a34a;
            --verde-claro: #dcfce7;
            --ambar: #d97706;
            --ambar-claro: #fef3c7;
            --rojo: #dc2626;
            --gris-fondo: #f8fafc;
            --borde: #cbd5e1;
        }
        * { box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
            background: var(--gris-fondo);
            color: #1e293b;
            margin: 0;
            padding: 0;
            line-height: 1.5;
        }
        /* Encabezado Institucional VeranoTec */
        .topbar {
            background: var(--azul-oscuro);
            color: white;
            padding: 18px 30px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 15px;
        }
        .brand h1 { margin: 0; font-size: 22px; color: #38bdf8; }
        .brand p { margin: 3px 0 0; font-size: 13px; color: #cbd5e1; }
        .status-box { display: flex; align-items: center; gap: 12px; }
        .db-pill {
            background: #1e293b;
            border: 1px solid #38bdf8;
            color: #7dd3fc;
            padding: 6px 12px;
            border-radius: 20px;
            font-size: 12px;
        }
        .container { max-width: 1100px; margin: 22px auto; padding: 0 20px; }

        /* Guía rápida visual para el usuario */
        .stepper {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 12px;
            margin-bottom: 20px;
        }
        .step {
            background: white;
            border: 1px solid var(--borde);
            border-left: 4px solid var(--azul-primario);
            padding: 12px 14px;
            border-radius: 8px;
            font-size: 13px;
        }
        .step strong { display: block; color: var(--azul-oscuro); font-size: 13.5px; margin-bottom: 2px; }
        .step span { color: #475569; font-size: 12px; }

        /* Navegación por pestañas según el rol */
        .tabs {
            display: flex;
            gap: 8px;
            margin-bottom: 18px;
            border-bottom: 2px solid #e2e8f0;
            padding-bottom: 10px;
            flex-wrap: wrap;
        }
        .tab-btn {
            background: white;
            color: #334155;
            border: 1px solid var(--borde);
            padding: 10px 18px;
            border-radius: 8px;
            font-size: 14px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s;
        }
        .tab-btn:hover { background: #f1f5f9; }
        .tab-btn.active {
            background: var(--azul-primario);
            color: white;
            border-color: var(--azul-primario);
        }
        .tab-panel { display: none; }
        .tab-panel.active { display: block; }

        /* Tarjetas y formularios */
        .grid-2 { display: grid; grid-template-columns: 1.1fr 0.9fr; gap: 20px; }
        .card {
            background: white;
            border: 1px solid #e2e8f0;
            border-radius: 12px;
            padding: 22px;
            box-shadow: 0 2px 8px rgba(15, 23, 42, 0.04);
            margin-bottom: 20px;
        }
        .card h2 {
            margin: 0 0 6px;
            font-size: 18px;
            color: var(--azul-oscuro);
        }
        .card .subtitle {
            margin: 0 0 16px;
            font-size: 13.5px;
            color: #64748b;
        }
        label { display: block; font-weight: 600; font-size: 13.5px; margin-bottom: 6px; color: #334155; }
        select {
            width: 100%;
            padding: 10px 12px;
            border: 1px solid var(--borde);
            border-radius: 8px;
            font-size: 14px;
            background: #f8fafc;
            margin-bottom: 16px;
        }
        button.primary {
            background: var(--azul-primario);
            color: white;
            border: none;
            padding: 12px 18px;
            border-radius: 8px;
            font-size: 14.5px;
            font-weight: 600;
            cursor: pointer;
            width: 100%;
        }
        button.primary:hover { background: #0369a1; }
        button.success {
            background: var(--verde);
            color: white;
            border: none;
            padding: 8px 14px;
            border-radius: 6px;
            font-size: 13px;
            font-weight: 600;
            cursor: pointer;
        }
        button.warning {
            background: var(--ambar);
            color: white;
            border: none;
            padding: 8px 14px;
            border-radius: 6px;
            font-size: 13px;
            font-weight: 600;
            cursor: pointer;
        }
        button.reset {
            background: transparent;
            color: #fca5a5;
            border: 1px solid #f87171;
            padding: 6px 12px;
            border-radius: 6px;
            font-size: 12px;
            cursor: pointer;
        }
        button.reset:hover { background: var(--rojo); color: white; }

        /* Barra de progreso de demanda */
        .progress-wrap { background: #e2e8f0; border-radius: 99px; height: 10px; overflow: hidden; margin: 6px 0; }
        .progress-bar { height: 100%; background: var(--azul-primario); transition: width 0.3s; }
        .progress-bar.full { background: var(--verde); }

        /* Tablas y etiquetas */
        table { width: 100%; border-collapse: collapse; font-size: 13.5px; }
        th { background: #f1f5f9; color: #334155; font-weight: 600; text-align: left; padding: 10px; border-bottom: 2px solid #e2e8f0; }
        td { padding: 11px 10px; border-bottom: 1px solid #e2e8f0; vertical-align: middle; }
        .pill { padding: 4px 10px; border-radius: 99px; font-size: 12px; font-weight: 600; display: inline-block; }
        .pill-wait { background: var(--ambar-claro); color: #92400e; }
        .pill-open { background: var(--verde-claro); color: #166534; }

        /* Alertas amigables */
        .alert {
            padding: 14px 18px;
            border-radius: 8px;
            margin-bottom: 18px;
            font-size: 14px;
            font-weight: 500;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        .alert-ok { background: var(--verde-claro); color: #14532d; border-left: 5px solid var(--verde); }
        .alert-err { background: #fee2e2; color: #7f1d1d; border-left: 5px solid var(--rojo); }

        .log-box {
            background: #0f172a;
            color: #38bdf8;
            font-family: Consolas, monospace;
            padding: 14px;
            border-radius: 8px;
            font-size: 12.5px;
            max-height: 260px;
            overflow-y: auto;
        }
        @media (max-width: 820px) {
            .stepper, .grid-2 { grid-template-columns: 1fr; }
        }
    </style>
</head>
<body>

<div class="topbar">
    <div class="brand">
        <h1>VeranoTec · Gestión Automatizada de Cursos de Verano</h1>
        <p>Tecnológico Nacional de México · Campus Matehuala (Prototipo con datos simulados)</p>
    </div>
    <div class="status-box">
        <span class="db-pill">💾 Guardado automático en: <strong>veranotec.db</strong></span>
        <form action="/reiniciar_demo" method="POST" style="margin:0;">
            <button type="submit" class="reset">Reiniciar Demo</button>
        </form>
    </div>
</div>

<div class="container">

    <!-- FLUJO VISUAL EN 4 PASOS CLAROS -->
    <div class="stepper">
        <div class="step">
            <strong>Paso 1 · Solicitud del Alumno</strong>
            <span>El sistema valida el kárdex antes de contar la solicitud.</span>
        </div>
        <div class="step">
            <strong>Paso 2 · Apertura Automática</strong>
            <span>Al llegar a 10 alumnos, el grupo se abre sin listas en papel.</span>
        </div>
        <div class="step">
            <strong>Paso 3 · Jefatura Asigna Docente</strong>
            <span>Con 1 clic se asigna profesor y se liberan referencias de pago.</span>
        </div>
        <div class="step">
            <strong>Paso 4 · Pago y Horario Listo</strong>
            <span>Al pagar por referencia, se entrega el horario oficial al instante.</span>
        </div>
    </div>

    <!-- MENSAJES DE RETROALIMENTACIÓN AL USUARIO -->
    {% with messages = get_flashed_messages(with_categories=true) %}
      {% if messages %}
        {% for category, message in messages %}
          <div class="alert {{ 'alert-ok' if category == 'ok' else 'alert-err' }}">
              <span>{{ '✅' if category == 'ok' else '⚠️' }}</span>
              <div>{{ message }}</div>
          </div>
        {% endfor %}
      {% endif %}
    {% endwith %}

    <!-- PESTAÑAS POR ROL DE USUARIO -->
    <div class="tabs">
        <button class="tab-btn active" onclick="abrirTab(event, 'tab-alumno')">1. Vista del Alumno (Solicitar y Pagar)</button>
        <button class="tab-btn" onclick="abrirTab(event, 'tab-jefatura')">2. Jefatura y División (Abrir Grupos y Docente)</button>
        <button class="tab-btn" onclick="abrirTab(event, 'tab-bd')">3. Base de Datos y Auditoría ({{ inscripciones|length }} registros)</button>
    </div>

    <!-- ==========================================
         PESTAÑA 1: PORTAL DEL ALUMNO
         ========================================== -->
    <div id="tab-alumno" class="tab-panel active">
        <div class="grid-2">
            <div class="card">
                <h2>Solicitar Materia de Verano</h2>
                <p class="subtitle">Elige tu perfil simulado y la materia que deseas adelantar o repetir. El sistema revisará automáticamente tu historial académico.</p>

                <form action="/solicitar" method="POST">
                    <label for="alumno_id">¿Quién realiza la solicitud?</label>
                    <select name="alumno_id" id="alumno_id">
                        {% for a in alumnos %}
                        <option value="{{ a['id'] }}" {{ 'selected' if a['id'] == 'SIM-2404' else '' }}>
                            {{ a['id'] }} — {{ a['nombre'] }}
                        </option>
                        {% endfor %}
                    </select>

                    <label for="materia_id">¿Qué materia deseas cursar?</label>
                    <select name="materia_id" id="materia_id">
                        {% for m in materias %}
                        <option value="{{ m['id'] }}">
                            {{ m['clave'] }} · {{ m['nombre'] }} (Requiere: {{ m['prerrequisito_nombre'] }})
                        </option>
                        {% endfor %}
                    </select>

                    <button type="submit" class="primary">Validar Kárdex y Registrar Solicitud</button>
                </form>
            </div>

            <div class="card">
                <h2>Disponibilidad de Grupos en Tiempo Real</h2>
                <p class="subtitle">Se necesitan mínimo 10 alumnos validados para que el sistema abra el grupo automáticamente.</p>

                {% for m in materias %}
                {% set pct = (m['total_inscritos'] / m['minimo'] * 100)|int %}
                <div style="margin-bottom: 18px; padding: 12px; background: #f8fafc; border-radius: 8px; border: 1px solid #e2e8f0;">
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <strong>{{ m['nombre'] }} ({{ m['clave'] }})</strong>
                        <span class="pill {{ 'pill-open' if m['total_inscritos'] >= m['minimo'] or 'Excepción' in m['estado'] else 'pill-wait' }}">
                            {{ m['estado'] }}
                        </span>
                    </div>
                    <div class="progress-wrap">
                        <div class="progress-bar {{ 'full' if pct >= 100 else '' }}" style="width: {{ 100 if pct > 100 else pct }}%;"></div>
                    </div>
                    <small style="color:#475569;">
                        Demanda actual: <strong>{{ m['total_inscritos'] }} de {{ m['minimo'] }} alumnos</strong>
                        {% if m['docente'] %} · Docente: <strong>{{ m['docente'] }}</strong>{% endif %}
                    </small>
                </div>
                {% endfor %}
            </div>
        </div>

        <div class="card">
            <h2>Mis Referencias de Pago y Horarios Confirmados</h2>
            <p class="subtitle">Por seguridad del alumno, la referencia de pago solo se genera cuando el grupo ya alcanzó el mínimo y tiene docente asignado.</p>
            {% if pagos %}
            <table>
                <tr>
                    <th>Alumno</th>
                    <th>Materia</th>
                    <th>Referencia Bancaria</th>
                    <th>Acción / Horario Oficial</th>
                </tr>
                {% for p in pagos %}
                <tr>
                    <td><strong>{{ p['alumno_id'] }}</strong></td>
                    <td>{{ p['materia_nombre'] }}</td>
                    <td><code>{{ p['referencia'] }}</code></td>
                    <td>
                        {% if p['pagado'] == 1 %}
                            <span class="pill pill-open">PAGADO · {{ p['horario'] }}</span>
                        {% else %}
                            <form action="/pagar" method="POST" style="margin:0;">
                                <input type="hidden" name="alumno_id" value="{{ p['alumno_id'] }}">
                                <input type="hidden" name="materia_id" value="{{ p['materia_id'] }}">
                                <button type="submit" class="success">Simular Pago en Banco</button>
                            </form>
                        {% endif %}
                    </td>
                </tr>
                {% endfor %}
            </table>
            {% else %}
            <p style="color:#64748b; font-size:13.5px; margin:0;">Todavía no hay referencias emitidas. Completa el mínimo de alumnos en una materia y asigna un docente en la pestaña 2.</p>
            {% endif %}
        </div>
    </div>

    <!-- ==========================================
         PESTAÑA 2: JEFATURA Y DIVISIÓN
         ========================================== -->
    <div id="tab-jefatura" class="tab-panel">
        <div class="card">
            <h2>Panel de Control: Jefatura Académica y División de Estudios Profesionales</h2>
            <p class="subtitle">Aquí intervienen las personas: la Jefatura asigna docente cuando el grupo se abre, y la División puede autorizar excepciones si faltan alumnos.</p>
            <table>
                <tr>
                    <th>Materia</th>
                    <th>Alumnos Inscritos</th>
                    <th>Estado del Sistema</th>
                    <th>Decisión Humana (Jefatura / División)</th>
                </tr>
                {% for m in materias %}
                <tr>
                    <td><strong>{{ m['nombre'] }}</strong><br><small>{{ m['clave'] }}</small></td>
                    <td><strong>{{ m['total_inscritos'] }} / {{ m['minimo'] }}</strong></td>
                    <td>
                        <span class="pill {{ 'pill-open' if m['total_inscritos'] >= m['minimo'] or 'Excepción' in m['estado'] else 'pill-wait' }}">
                            {{ m['estado'] }}
                        </span>
                    </td>
                    <td>
                        {% if m['docente'] %}
                            <strong>Docente asignado:</strong> {{ m['docente'] }}
                        {% elif m['total_inscritos'] >= m['minimo'] or 'Excepción' in m['estado'] %}
                            <form action="/asignar_docente" method="POST" style="display:flex; gap:8px; align-items:center; margin:0;">
                                <input type="hidden" name="materia_id" value="{{ m['id'] }}">
                                <select name="docente" style="margin:0; width:auto;">
                                    {% for d in docentes %}<option value="{{ d }}">{{ d }}</option>{% endfor %}
                                </select>
                                <button type="submit" class="success">Asignar Docente</button>
                            </form>
                        {% else %}
                            <form action="/excepcion" method="POST" style="margin:0;">
                                <input type="hidden" name="materia_id" value="{{ m['id'] }}">
                                <button type="submit" class="warning">Autorizar Apertura por Excepción (División)</button>
                            </form>
                        {% endif %}
                    </td>
                </tr>
                {% endfor %}
            </table>
        </div>
    </div>

    <!-- ==========================================
         PESTAÑA 3: PERSISTENCIA EN BASE DE DATOS
         ========================================== -->
    <div id="tab-bd" class="tab-panel">
        <div class="grid-2">
            <div class="card">
                <h2>Solicitudes Guardadas en SQLite (veranotec.db)</h2>
                <p class="subtitle">Aunque recargues la página o reinicies el servidor, estos registros permanecen almacenados en la base de datos.</p>
                <table>
                    <tr><th>ID</th><th>Alumno</th><th>Materia</th><th>Fecha y Hora</th></tr>
                    {% for ins in inscripciones %}
                    <tr>
                        <td>#{{ ins['id'] }}</td>
                        <td><strong>{{ ins['alumno_id'] }}</strong></td>
                        <td>{{ ins['materia_nombre'] }}</td>
                        <td>{{ ins['fecha_registro'] }}</td>
                    </tr>
                    {% endfor %}
                </table>
            </div>

            <div class="card">
                <h2>Bitácora de Auditoría en Tiempo Real</h2>
                <p class="subtitle">Historial de cada regla de negocio validada por el sistema.</p>
                <div class="log-box">
                    {% for b in bitacora %}
                        <div>[{{ b['hora'] }}] <strong>{{ b['actor'] }}:</strong> {{ b['accion'] }}</div>
                    {% else %}
                        <div>[Sistema iniciado] Esperando interacciones del usuario...</div>
                    {% endfor %}
                </div>
            </div>
        </div>
    </div>

</div>

<script>
    function abrirTab(evt, tabId) {
        document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
        document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
        document.getElementById(tabId).classList.add('active');
        evt.currentTarget.classList.add('active');
    }
</script>
</body>
</html>
"""

# ==========================================
# LÓGICA DEL SERVIDOR Y REGLAS DE NEGOCIO
# ==========================================
@app.route("/")
def index():
    conn = get_db()
    alumnos = conn.execute("SELECT * FROM alumnos").fetchall()
    materias = conn.execute("""
        SELECT m.*, COUNT(i.id) as total_inscritos 
        FROM materias m LEFT JOIN inscripciones i ON m.id = i.materia_id 
        GROUP BY m.id
    """).fetchall()
    inscripciones = conn.execute("""
        SELECT i.id, i.alumno_id, m.nombre as materia_nombre, i.fecha_registro 
        FROM inscripciones i JOIN materias m ON i.materia_id = m.id 
        WHERE i.alumno_id LIKE 'SIM-24%' ORDER BY i.id DESC
    """).fetchall()
    pagos = conn.execute("""
        SELECT p.*, m.nombre as materia_nombre, m.horario 
        FROM pagos p JOIN materias m ON p.materia_id = m.id
    """).fetchall()
    bitacora = conn.execute("SELECT * FROM bitacora ORDER BY id DESC LIMIT 20").fetchall()
    conn.close()
    return render_template_string(
        HTML_TEMPLATE, alumnos=alumnos, materias=materias, docentes=DOCENTES,
        inscripciones=inscripciones, pagos=pagos, bitacora=bitacora
    )

@app.route("/solicitar", methods=["POST"])
def solicitar():
    aid = request.form["alumno_id"]
    mid = request.form["materia_id"]
    conn = get_db()
    alumno = conn.execute("SELECT * FROM alumnos WHERE id = ?", (aid,)).fetchone()
    materia = conn.execute("SELECT * FROM materias WHERE id = ?", (mid,)).fetchone()
    aprobadas = alumno["aprobadas"].split(",")

    if mid in aprobadas:
        registrar_evento(conn, "Validación Kárdex", f"Bloqueado {aid}: ya aprobó {materia['nombre']}.")
        conn.commit()
        conn.close()
        flash(f"Solicitud rechazada: {alumno['nombre']} ya aprobó {materia['nombre']} anteriormente.", "err")
        return redirect(url_for("index"))

    if materia["prerrequisito"] not in aprobadas:
        registrar_evento(conn, "Validación Kárdex", f"Bloqueado {aid}: le falta {materia['prerrequisito_nombre']}.")
        conn.commit()
        conn.close()
        flash(f"Solicitud rechazada: Para cursar {materia['nombre']} primero debes aprobar {materia['prerrequisito_nombre']}.", "err")
        return redirect(url_for("index"))

    existe = conn.execute("SELECT 1 FROM inscripciones WHERE alumno_id = ? AND materia_id = ?", (aid, mid)).fetchone()
    if existe:
        conn.close()
        flash(f"Aviso: {alumno['nombre']} ya está inscrito en la lista de {materia['nombre']}.", "err")
        return redirect(url_for("index"))

    fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn.execute("INSERT INTO inscripciones (alumno_id, materia_id, fecha_registro) VALUES (?, ?, ?)", (aid, mid, fecha))
    total = conn.execute("SELECT COUNT(*) FROM inscripciones WHERE materia_id = ?", (mid,)).fetchone()[0]
    registrar_evento(conn, "Base de Datos", f"Se guardó la solicitud de {aid} en {materia['nombre']} ({total}/{materia['minimo']}).")

    if total >= materia["minimo"] and materia["estado"] == "En espera de mínimo":
        conn.execute("UPDATE materias SET estado = 'Grupo Abierto · Pendiente Docente' WHERE id = ?", (mid,))
        registrar_evento(conn, "Motor de Reglas", f"¡Grupo abierto automáticamente! {materia['nombre']} llegó a {total} alumnos.")
        flash(f"¡Solicitud guardada en veranotec.db! Se alcanzó el mínimo ({total}/10) y el grupo se abrió automáticamente. Pasa a la pestaña 2 para asignar docente.", "ok")
    else:
        flash(f"¡Solicitud guardada con éxito para {alumno['nombre']}! Revisa la pestaña 3 para ver el registro en la base de datos.", "ok")

    conn.commit()
    conn.close()
    return redirect(url_for("index"))

@app.route("/asignar_docente", methods=["POST"])
def asignar_docente():
    mid = request.form["materia_id"]
    docente = request.form["docente"]
    conn = get_db()
    conn.execute("UPDATE materias SET docente = ?, estado = 'Confirmado · Referencias Listas' WHERE id = ?", (docente, mid))

    inscritos = conn.execute("SELECT alumno_id FROM inscripciones WHERE materia_id = ? AND alumno_id LIKE 'SIM-24%'", (mid,)).fetchall()
    for row in inscritos:
        aid = row["alumno_id"]
        ref = f"REF-2026-{mid}-{aid.split('-')[1]}"
        conn.execute("INSERT OR IGNORE INTO pagos (alumno_id, materia_id, referencia, pagado) VALUES (?, ?, ?, 0)", (aid, mid, ref))

    registrar_evento(conn, "Jefatura Académica", f"Asignó a {docente} en {mid} y se emitieron referencias de pago.")
    conn.commit()
    conn.close()
    flash("Docente asignado. Regresa a la pestaña 1 (Vista del Alumno) para simular el pago y ver el horario.", "ok")
    return redirect(url_for("index"))

@app.route("/excepcion", methods=["POST"])
def excepcion():
    mid = request.form["materia_id"]
    conn = get_db()
    conn.execute("UPDATE materias SET estado = 'Abierto por Excepción · Pendiente Docente' WHERE id = ?", (mid,))
    registrar_evento(conn, "División Est. Prof.", f"Autorizó abrir {mid} por excepción sin llegar a 10 alumnos.")
    conn.commit()
    conn.close()
    flash("Excepción autorizada por la División. Ahora puedes asignar un docente.", "ok")
    return redirect(url_for("index"))

@app.route("/pagar", methods=["POST"])
def pagar():
    aid = request.form["alumno_id"]
    mid = request.form["materia_id"]
    conn = get_db()
    fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn.execute("UPDATE pagos SET pagado = 1, fecha_pago = ? WHERE alumno_id = ? AND materia_id = ?", (fecha, aid, mid))
    registrar_evento(conn, "Banco / Conciliación", f"Pago confirmado para {aid} en {mid}. Horario oficial liberado.")
    conn.commit()
    conn.close()
    flash(f"¡Pago confirmado! El horario oficial de {aid} ha quedado registrado en la base de datos.", "ok")
    return redirect(url_for("index"))

@app.route("/reiniciar_demo", methods=["POST"])
def reiniciar_demo():
    conn = get_db()
    conn.executescript("""
        DROP TABLE IF EXISTS alumnos;
        DROP TABLE IF EXISTS materias;
        DROP TABLE IF EXISTS inscripciones;
        DROP TABLE IF EXISTS pagos;
        DROP TABLE IF EXISTS bitacora;
    """)
    conn.close()
    init_db()
    flash("Base de datos restaurada al estado inicial de prueba.", "ok")
    return redirect(url_for("index"))

if __name__ == "__main__":
    init_db()
    app.run(debug=True, port=5000)