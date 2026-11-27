import re
import sqlite3
from flask import Flask, render_template_string, request, redirect, url_for, flash, session
from datetime import datetime

app = Flask(__name__)
app.secret_key = "veranotec_seguridad_itmh_2026"
DB_NAME = "veranotec.db"

# Formato oficial ITMH: Año (24, 25 o 26) + Plantel (660) + Consecutivo (001 al 500)
REGEX_CONTROL = re.compile(r"^(24|25|26)660(00[1-9]|0[1-9][0-9]|[1-4][0-9]{2}|500)$")

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
        num_control TEXT PRIMARY KEY,
        nombre TEXT,
        carrera TEXT,
        kardex_valido INTEGER DEFAULT 1
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS materias (
        id TEXT PRIMARY KEY,
        carrera TEXT,
        clave TEXT,
        nombre TEXT,
        docente TEXT,
        horario TEXT,
        prerrequisito TEXT,
        costo TEXT,
        minimo INTEGER,
        estado TEXT
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS inscripciones (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        num_control TEXT,
        materia_id TEXT,
        referencia TEXT,
        pagado INTEGER DEFAULT 0,
        fecha_registro TEXT,
        fecha_pago TEXT,
        UNIQUE(num_control, materia_id)
    )''')

    if c.execute("SELECT COUNT(*) FROM materias").fetchone()[0] == 0:
        # Alumnos precargados vinculados por número de control (ahorra volver a pedir datos)
        alumnos_init = [
            ("24660462", "Cristofer Yahir Herrera Rodríguez", "Ing. en Sistemas Computacionales", 1),
            ("24660101", "Alumno Simulado Sistemas 01", "Ing. en Sistemas Computacionales", 1),
            ("25660205", "Alumno Simulado Industrial 02", "Ing. Industrial", 1),
            ("26660015", "Alumno Simulado Gestión 03", "Ing. en Gestión Empresarial", 1),
            ("24660333", "Alumno Sin Prerrequisito (Prueba)", "Ing. en Sistemas Computacionales", 0)
        ]
        c.executemany("INSERT INTO alumnos VALUES (?, ?, ?, ?)", alumnos_init)

        materias_init = [
            ("FIS-01", "Ing. en Sistemas Computacionales", "SCC-1007", "Fundamentos de Ingeniería de Software", "Ing. Roberto Martínez", "Lun-Vie 08:00 - 10:00 | Aula CC-2", "Fundamentos de Programación", "$1,450.00 MXN", 6, "Disponible (Falta 1 lugar)"),
            ("MAT-02", "Ing. en Sistemas Computacionales", "ACF-0902", "Cálculo Integral", "M.C. Laura Sánchez", "Lun-Vie 10:00 - 12:00 | Aula B-4", "Cálculo Diferencial", "$1,450.00 MXN", 6, "Disponible"),
            ("BDD-03", "Ing. en Sistemas Computacionales", "AEF-1031", "Fundamentos de Bases de Datos", "Ing. Carlos Hernández", "Lun-Vie 12:00 - 14:00 | Lab. Cómputo 1", "Taller de Programación", "$1,450.00 MXN", 6, "Disponible"),
            ("IND-01", "Ing. Industrial", "INC-1009", "Estudio del Trabajo I", "Ing. Patricia Gómez", "Lun-Vie 08:00 - 10:00 | Aula D-1", "Probabilidad y Estadística", "$1,450.00 MXN", 6, "Disponible"),
            ("IGE-01", "Ing. en Gestión Empresarial", "GEC-0905", "Costos Empresariales", "M.A. Fernando Ruiz", "Lun-Vie 10:00 - 12:00 | Aula E-3", "Contabilidad Orientada a los Negocios", "$1,450.00 MXN", 6, "Disponible")
        ]
        c.executemany("INSERT INTO materias VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", materias_init)

        # Precarga interna de 5 lugares ocupados en SCC-1007 (al entrar 1 alumno se completa el grupo 6/6)
        precarga_fis = [(f"2466090{i}", "FIS-01", None, 0, "2026-11-26 08:00:00", None) for i in range(1, 6)]
        precarga_mat = [(f"2566091{i}", "MAT-02", None, 0, "2026-11-26 08:00:00", None) for i in range(1, 4)]
        c.executemany("INSERT INTO inscripciones (num_control, materia_id, referencia, pagado, fecha_registro, fecha_pago) VALUES (?, ?, ?, ?, ?, ?)", precarga_fis + precarga_mat)

    conn.commit()
    conn.close()

# ==========================================
# ESTILOS COMPARTIDOS Y ENCABEZADO OFICIAL
# ==========================================
BASE_CSS = """
    :root {
        --azul-tecnm: #1b396a;
        --azul-oscuro: #0f172a;
        --azul-claro: #e0f2fe;
        --verde: #16a34a;
        --verde-claro: #dcfce7;
        --ambar: #d97706;
        --ambar-claro: #fef3c7;
        --rojo: #dc2626;
        --rojo-claro: #fee2e2;
        --fondo: #f1f5f9;
        --borde: #cbd5e1;
    }
    * { box-sizing: border-box; }
    body {
        font-family: 'Segoe UI', system-ui, sans-serif;
        background: var(--fondo);
        color: #1e293b;
        margin: 0;
        padding: 0;
    }
    .topbar {
        background: white;
        border-bottom: 4px solid var(--azul-tecnm);
        padding: 12px 24px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        flex-wrap: wrap;
        gap: 12px;
        box-shadow: 0 2px 6px rgba(15, 23, 42, 0.06);
    }
    .brand-group { display: flex; align-items: center; gap: 14px; flex-wrap: wrap; }
    .logo-tecnm { height: 48px; width: auto; object-fit: contain; }
    .logo-itmh { height: 52px; width: auto; object-fit: contain; }
    .brand-text h1 { margin: 0; font-size: 19px; color: var(--azul-tecnm); }
    .brand-text p { margin: 2px 0 0; font-size: 12.5px; color: #475569; }
    .right-actions { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
    .container { max-width: 1060px; margin: 24px auto; padding: 0 16px; }
    .card {
        background: white;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 22px;
        box-shadow: 0 2px 8px rgba(15, 23, 42, 0.05);
        margin-bottom: 20px;
    }
    .card h2 { margin: 0 0 6px; font-size: 18px; color: var(--azul-oscuro); }
    .subtitle { margin: 0 0 16px; font-size: 13.5px; color: #64748b; line-height: 1.45; }
    label { display: block; font-weight: 600; font-size: 13.5px; margin-bottom: 6px; color: #334155; }
    input[type="text"], select {
        width: 100%;
        padding: 11px 12px;
        border: 1px solid var(--borde);
        border-radius: 8px;
        font-size: 14px;
        background: #f8fafc;
        margin-bottom: 14px;
    }
    .btn {
        display: inline-block;
        border: none;
        padding: 10px 16px;
        border-radius: 8px;
        font-size: 13.5px;
        font-weight: 600;
        cursor: pointer;
        text-decoration: none;
        text-align: center;
    }
    .btn-primary { background: var(--azul-tecnm); color: white; width: 100%; padding: 12px; font-size: 14.5px; }
    .btn-primary:hover { background: #13294d; }
    .btn-success { background: var(--verde); color: white; padding: 7px 12px; font-size: 12.5px; }
    .btn-doc { background: #0284c7; color: white; padding: 7px 12px; font-size: 12.5px; }
    .btn-outline { background: #f8fafc; color: #334155; border: 1px solid var(--borde); padding: 7px 12px; font-size: 12.5px; }
    .btn-danger { background: #fff1f2; color: var(--rojo); border: 1px solid #fecdd3; padding: 7px 12px; font-size: 12px; }
    .alert {
        padding: 13px 16px;
        border-radius: 8px;
        margin-bottom: 18px;
        font-size: 13.5px;
        font-weight: 500;
    }
    .alert-ok { background: var(--verde-claro); color: #14532d; border-left: 5px solid var(--verde); }
    .alert-err { background: var(--rojo-claro); color: #7f1d1d; border-left: 5px solid var(--rojo); }
    .pill { padding: 4px 10px; border-radius: 99px; font-size: 11.5px; font-weight: 600; white-space: nowrap; display: inline-block; }
    .pill-wait { background: var(--ambar-claro); color: #92400e; }
    .pill-open { background: var(--verde-claro); color: #166534; }
    .pill-full { background: var(--rojo-claro); color: #991b1b; }
"""

# ==========================================
# VISTA 1: INICIO DE SESIÓN OBLIGATORIO
# ==========================================
LOGIN_TEMPLATE = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Acceso Estudiantes | VeranoTec ITMH</title>
    <style>
        """ + BASE_CSS + """
        .login-box { max-width: 460px; margin: 36px auto; }
        .hint { font-size: 12px; color: #64748b; margin: -8px 0 14px; display: block; }
        .quick-box {
            background: #f8fafc;
            border: 1px dashed #94a3b8;
            border-radius: 8px;
            padding: 12px;
            margin-top: 16px;
            font-size: 12.5px;
            color: #475569;
        }
    </style>
</head>
<body>
<div class="topbar">
    <div class="brand-group">
        <img src="{{ url_for('static', filename='logo_tecnm.png') }}" alt="TecNM" class="logo-tecnm" onerror="this.style.display='none'">
        <div class="brand-text">
            <h1>VeranoTec · Acceso Institucional</h1>
            <p>Instituto Tecnológico de Matehuala · Cursos de Verano</p>
        </div>
    </div>
    <img src="{{ url_for('static', filename='logo_itmh.jpg') }}" alt="ITMH" class="logo-itmh" onerror="this.style.display='none'">
</div>

<div class="container">
    <div class="card login-box">
        <h2>Iniciar Sesión como Estudiante</h2>
        <p class="subtitle">Por privacidad y seguridad, ingresa con tu <strong>Número de Control oficial</strong> para consultar únicamente los cursos de tu carrera y tus trámites personales.</p>

        {% with messages = get_flashed_messages(with_categories=true) %}
          {% if messages %}
            {% for category, message in messages %}
              <div class="alert {{ 'alert-ok' if category == 'ok' else 'alert-err' }}">{{ message }}</div>
            {% endfor %}
          {% endif %}
        {% endwith %}

        <form action="/login" method="POST">
            <label for="num_control">Número de Control (ITMH):</label>
            <input type="text" id="num_control" name="num_control" placeholder="Ej. 24660462" maxlength="8"
                   pattern="(24|25|26)660(00[1-9]|0[1-9][0-9]|[1-4][0-9]{2}|500)"
                   title="Formato oficial: Año (24, 25 o 26) + Plantel (660) + Consecutivo (001 al 500)" required>
            <span class="hint">Formato válido: Año (<b>24-26</b>) + Plantel (<b>660</b>) + Lista (<b>001-500</b>).</span>

            <div id="campos_nuevos">
                <label for="nombre">Nombre Completo (si es tu primer ingreso):</label>
                <input type="text" id="nombre" name="nombre" placeholder="Opcional si ya estás registrado (ej. 24660462)">

                <label for="carrera">Carrera (si es tu primer ingreso):</label>
                <select id="carrera" name="carrera">
                    <option value="Ing. en Sistemas Computacionales">Ing. en Sistemas Computacionales</option>
                    <option value="Ing. Industrial">Ing. Industrial</option>
                    <option value="Ing. en Gestión Empresarial">Ing. en Gestión Empresarial</option>
                </select>
            </div>

            <button type="submit" class="btn btn-primary">Entrar a Mi Portal de Verano</button>
        </form>

        <div class="quick-box">
            <strong>Matrículas vinculadas precargadas (solo escribe el número y entra):</strong><br>
            • <code>24660462</code> — Cristofer Yahir Herrera (Sistemas · Kárdex válido)<br>
            • <code>24660101</code> — Alumno Sistemas 01 (Sistemas · Kárdex válido)<br>
            • <code>24660333</code> — Alumno Prueba Bloqueo (Sistemas · Sin prerrequisito)<br>
            • <code>25660205</code> — Alumno Industrial 02 (Ing. Industrial)
        </div>
    </div>
</div>
</body>
</html>
"""

# ==========================================
# VISTA 2: PORTAL PRIVADO DEL ALUMNO
# ==========================================
PORTAL_TEMPLATE = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Mi Portal | VeranoTec ITMH</title>
    <style>
        """ + BASE_CSS + """
        .profile-banner {
            background: var(--azul-tecnm);
            color: white;
            border-radius: 12px;
            padding: 18px 22px;
            margin-bottom: 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 12px;
        }
        .profile-banner h2 { margin: 0; font-size: 18px; color: #ffffff; }
        .profile-banner p { margin: 4px 0 0; font-size: 13px; color: #bae6fd; }
        .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(310px, 1fr)); gap: 16px; }
        .course-card {
            border: 1px solid #e2e8f0;
            border-radius: 10px;
            padding: 16px;
            background: #f8fafc;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
        }
        .course-title { font-weight: 700; color: var(--azul-oscuro); font-size: 15px; margin-bottom: 6px; }
        .course-meta { font-size: 13px; color: #475569; line-height: 1.55; margin-bottom: 12px; }
        .progress-wrap { background: #e2e8f0; border-radius: 99px; height: 8px; overflow: hidden; margin: 6px 0; }
        .progress-bar { height: 100%; background: #0284c7; }
        .progress-bar.full { background: var(--rojo); }
        .table-wrap { overflow-x: auto; }
        table { width: 100%; border-collapse: collapse; font-size: 13.5px; }
        th { background: #f1f5f9; text-align: left; padding: 10px; border-bottom: 2px solid #e2e8f0; color: #334155; }
        td { padding: 10px; border-bottom: 1px solid #e2e8f0; }
        .action-row { display: flex; gap: 6px; flex-wrap: wrap; align-items: center; }
    </style>
</head>
<body>

<div class="topbar">
    <div class="brand-group">
        <img src="{{ url_for('static', filename='logo_tecnm.png') }}" alt="TecNM" class="logo-tecnm" onerror="this.style.display='none'">
        <div class="brand-text">
            <h1>VeranoTec · Portal del Estudiante</h1>
            <p>Instituto Tecnológico de Matehuala · Sesión Privada</p>
        </div>
    </div>
    <div class="right-actions">
        <form action="/reiniciar_demo" method="POST" style="margin:0;">
            <button type="submit" class="btn btn-danger">Reiniciar Simulación</button>
        </form>
        <a href="/logout" class="btn btn-outline">Cerrar Sesión</a>
        <img src="{{ url_for('static', filename='logo_itmh.jpg') }}" alt="ITMH" class="logo-itmh" onerror="this.style.display='none'">
    </div>
</div>

<div class="container">

    {% with messages = get_flashed_messages(with_categories=true) %}
      {% if messages %}
        {% for category, message in messages %}
          <div class="alert {{ 'alert-ok' if category == 'ok' else 'alert-err' }}">{{ message }}</div>
        {% endfor %}
      {% endif %}
    {% endwith %}

    <!-- DATOS VINCULADOS AUTOMÁTICAMENTE AL NÚMERO DE CONTROL -->
    <div class="profile-banner">
        <div>
            <h2>Bienvenido(a), {{ alumno['nombre'] }}</h2>
            <p><strong>No. de Control:</strong> {{ alumno['num_control'] }} &nbsp;|&nbsp; <strong>Carrera:</strong> {{ alumno['carrera'] }} &nbsp;|&nbsp; <strong>Kárdex:</strong> {{ 'Aprobado para solicitar' if alumno['kardex_valido'] == 1 else 'Adeuda prerrequisitos' }}</p>
        </div>
        <span class="pill pill-open">Datos vinculados automáticamente</span>
    </div>

    <!-- PASO 1: CURSOS PERSONALIZADOS DE SU CARRERA -->
    <div class="card">
        <h2>Paso 1 · Cursos de Verano Disponibles para {{ alumno['carrera'] }}</h2>
        <p class="subtitle">Solo se muestran las materias de tu carrera. Cada grupo abre y cierra automáticamente al completar <strong>6 alumnos inscritos</strong>. Haz clic en <strong>Solicitar</strong> en la materia que deseas cursar.</p>

        <div class="grid">
            {% for m in materias %}
            {% set pct = (m['total_inscritos'] / m['minimo'] * 100)|int %}
            {% set lleno = m['total_inscritos'] >= m['minimo'] %}
            <div class="course-card">
                <div>
                    <div style="display:flex; justify-content:space-between; align-items:flex-start; gap:8px;">
                        <div class="course-title">{{ m['clave'] }} · {{ m['nombre'] }}</div>
                        <span class="pill {{ 'pill-full' if lleno else 'pill-wait' }}">
                            {{ 'Cupo Lleno (6/6)' if lleno else m['estado'] }}
                        </span>
                    </div>
                    <div class="course-meta">
                        <strong>Docente:</strong> {{ m['docente'] }}<br>
                        <strong>Horario:</strong> {{ m['horario'] }}<br>
                        <strong>Prerrequisito:</strong> {{ m['prerrequisito'] }}<br>
                        <strong>Costo del curso:</strong> {{ m['costo'] }}
                    </div>
                </div>
                <div>
                    <div class="progress-wrap">
                        <div class="progress-bar {{ 'full' if lleno else '' }}" style="width: {{ 100 if pct > 100 else pct }}%;"></div>
                    </div>
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-top:8px;">
                        <small><strong>{{ m['total_inscritos'] }} de {{ m['minimo'] }} lugares</strong></small>
                        {% if m['id'] in mis_ids %}
                            <span class="pill pill-open">Ya solicitada</span>
                        {% elif lleno %}
                            <button type="button" class="btn btn-outline" disabled>Grupo Lleno</button>
                        {% else %}
                            <form action="/solicitar" method="POST" style="margin:0;">
                                <input type="hidden" name="materia_id" value="{{ m['id'] }}">
                                <button type="submit" class="btn btn-primary" style="padding:7px 14px; font-size:13px;">Solicitar Curso</button>
                            </form>
                        {% endif %}
                    </div>
                </div>
            </div>
            {% endfor %}
        </div>
    </div>

    <!-- PASO 2: MIS SOLICITUDES PRIVADAS, PAGO Y COMPROBANTE PDF -->
    <div class="card">
        <h2>Paso 2 · Mis Solicitudes, Autorización de Pago y Comprobantes</h2>
        <p class="subtitle">Aquí solo ves tus propios trámites. Cuando el grupo llega a <strong>6 alumnos</strong>, se autoriza el curso y puedes descargar tu <strong>Orden de Pago</strong> o tu <strong>Comprobante Oficial de Inscripción</strong>.</p>

        {% if mis_solicitudes %}
        <div class="table-wrap">
            <table>
                <tr>
                    <th>Materia</th>
                    <th>Docente y Horario</th>
                    <th>Estado del Grupo</th>
                    <th>Referencia</th>
                    <th>Trámite y Documento Oficial</th>
                </tr>
                {% for s in mis_solicitudes %}
                <tr>
                    <td><strong>{{ s['clave'] }}</strong> · {{ s['materia_nombre'] }}</td>
                    <td>{{ s['docente'] }}<br><small style="color:#64748b;">{{ s['horario'] }}</small></td>
                    <td>
                        {% if s['total_grupo'] >= s['minimo'] %}
                            <span class="pill pill-open">Curso Autorizado ({{ s['total_grupo'] }}/{{ s['minimo'] }})</span>
                        {% else %}
                            <span class="pill pill-wait">Esperando alumnos ({{ s['total_grupo'] }}/{{ s['minimo'] }})</span>
                        {% endif %}
                    </td>
                    <td>
                        {% if s['total_grupo'] >= s['minimo'] %}
                            <code>{{ s['referencia'] }}</code>
                        {% else %}
                            <span style="color:#64748b; font-size:12px;">Pendiente de apertura</span>
                        {% endif %}
                    </td>
                    <td>
                        <div class="action-row">
                            {% if s['total_grupo'] < s['minimo'] %}
                                <span style="color:#64748b; font-size:12px;">Se libera al llegar a {{ s['minimo'] }} alumnos</span>
                            {% elif s['pagado'] == 0 %}
                                <a href="/comprobante/{{ s['id'] }}" target="_blank" class="btn btn-doc">Ver Orden de Pago</a>
                                <form action="/pagar" method="POST" style="margin:0;">
                                    <input type="hidden" name="id" value="{{ s['id'] }}">
                                    <button type="submit" class="btn btn-success">Pagar en Línea</button>
                                </form>
                            {% else %}
                                <span class="pill pill-open">PAGADO</span>
                                <a href="/comprobante/{{ s['id'] }}" target="_blank" class="btn btn-doc">Descargar Comprobante</a>
                            {% endif %}
                        </div>
                    </td>
                </tr>
                {% endfor %}
            </table>
        </div>
        {% else %}
        <p style="color:#64748b; font-size:13.5px; margin:0;">Aún no has solicitado ningún curso. Selecciona una materia en el <strong>Paso 1</strong> para comenzar.</p>
        {% endif %}
    </div>

</div>
</body>
</html>
"""

# ==========================================
# VISTA 3: COMPROBANTE OFICIAL IMPRIMIBLE / PDF
# ==========================================
COMPROBANTE_TEMPLATE = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>Comprobante Oficial VeranoTec - {{ doc['folio'] }}</title>
    <style>
        body { font-family: 'Segoe UI', system-ui, sans-serif; background: #e2e8f0; margin: 0; padding: 20px; color: #0f172a; }
        .sheet {
            max-width: 760px;
            margin: 0 auto;
            background: white;
            padding: 36px 42px;
            border-radius: 10px;
            box-shadow: 0 4px 14px rgba(0,0,0,0.12);
            border-top: 8px solid #1b396a;
        }
        .header { display: flex; justify-content: space-between; align-items: center; border-bottom: 2px solid #cbd5e1; padding-bottom: 16px; margin-bottom: 22px; }
        .header img { height: 55px; }
        .title-center { text-align: center; }
        .title-center h2 { margin: 0; font-size: 16px; color: #1b396a; }
        .title-center p { margin: 4px 0 0; font-size: 12.5px; color: #475569; }
        .badge {
            display: inline-block;
            padding: 6px 14px;
            border-radius: 6px;
            font-weight: 700;
            font-size: 13px;
            margin-bottom: 18px;
        }
        .badge-pagado { background: #dcfce7; color: #166534; border: 1px solid #86efac; }
        .badge-orden { background: #fef3c7; color: #92400e; border: 1px solid #fcd34d; }
        table { width: 100%; border-collapse: collapse; margin-bottom: 22px; font-size: 14px; }
        th, td { border: 1px solid #cbd5e1; padding: 10px 12px; text-align: left; }
        th { background: #f8fafc; width: 34%; color: #334155; }
        .footer-note { font-size: 12px; color: #475569; line-height: 1.5; background: #f8fafc; padding: 14px; border-radius: 8px; border: 1px solid #e2e8f0; }
        .no-print { text-align: center; margin-bottom: 16px; }
        .btn-print { background: #1b396a; color: white; border: none; padding: 11px 22px; border-radius: 8px; font-size: 14px; font-weight: 600; cursor: pointer; }
        @media print {
            body { background: white; padding: 0; }
            .sheet { box-shadow: none; border-radius: 0; }
            .no-print { display: none; }
        }
    </style>
</head>
<body>
    <div class="no-print">
        <button class="btn-print" onclick="window.print()">Imprimir / Guardar como PDF</button>
    </div>

    <div class="sheet">
        <div class="header">
            <img src="{{ url_for('static', filename='logo_tecnm.png') }}" alt="TecNM" onerror="this.style.display='none'">
            <div class="title-center">
                <h2>TECNOLÓGICO NACIONAL DE MÉXICO</h2>
                <p>Instituto Tecnológico de Matehuala · División de Estudios Profesionales</p>
                <p><strong>Sistema Automatizado de Cursos de Verano (VeranoTec)</strong></p>
            </div>
            <img src="{{ url_for('static', filename='logo_itmh.jpg') }}" alt="ITMH" onerror="this.style.display='none'">
        </div>

        {% if doc['pagado'] == 1 %}
            <div class="badge badge-pagado">COMPROBANTE OFICIAL DE INSCRIPCIÓN Y PAGO CONFIRMADO</div>
        {% else %}
            <div class="badge badge-orden">ORDEN DE PAGO AUTORIZADA · CURSO DE VERANO CONFIRMADO</div>
        {% endif %}

        <table>
            <tr><th>Folio del Documento</th><td><strong>{{ doc['folio'] }}</strong></td></tr>
            <tr><th>Número de Control</th><td><strong>{{ doc['num_control'] }}</strong></td></tr>
            <tr><th>Nombre del Estudiante</th><td>{{ doc['nombre'] }}</td></tr>
            <tr><th>Carrera</th><td>{{ doc['carrera'] }}</td></tr>
            <tr><th>Asignatura Autorizada</th><td><strong>{{ doc['clave'] }} · {{ doc['materia_nombre'] }}</strong></td></tr>
            <tr><th>Docente Asignado</th><td>{{ doc['docente'] }}</td></tr>
            <tr><th>Horario y Aula Oficial</th><td>{{ doc['horario'] }}</td></tr>
            <tr><th>Referencia Bancaria</th><td><strong>{{ doc['referencia'] }}</strong></td></tr>
            <tr><th>Importe Autorizado</th><td>{{ doc['costo'] }}</td></tr>
            <tr><th>Estatus Financiero</th><td>{{ 'PAGADO EL ' + doc['fecha_pago'] if doc['pagado'] == 1 else 'PENDIENTE DE PAGO EN VENTANILLA / BANCO (CURSO AUTORIZADO 6/6)' }}</td></tr>
        </table>

        <div class="footer-note">
            <strong>Validez Institucional (Simulación Académica SCC-1007):</strong> Este documento acredita que el grupo alcanzó el cupo reglamentario de 6 estudiantes validados en kárdex y cuenta con autorización oficial para su apertura en el periodo de verano del Instituto Tecnológico de Matehuala.
        </div>
    </div>
</body>
</html>
"""

# ==========================================
# RUTAS DE AUTENTICACIÓN Y NEGOCIO
# ==========================================
@app.route("/")
def index():
    if "num_control" not in session:
        return render_template_string(LOGIN_TEMPLATE)

    nc = session["num_control"]
    conn = get_db()
    alumno = conn.execute("SELECT * FROM alumnos WHERE num_control = ?", (nc,)).fetchone()
    if not alumno:
        session.clear()
        conn.close()
        return redirect(url_for("index"))

    # Solo muestra materias de la carrera del alumno logueado
    materias = conn.execute("""
        SELECT m.*, COUNT(i.id) as total_inscritos 
        FROM materias m LEFT JOIN inscripciones i ON m.id = i.materia_id 
        WHERE m.carrera = ?
        GROUP BY m.id
    """, (alumno["carrera"],)).fetchall()

    # Solo muestra solicitudes del alumno logueado (privacidad)
    mis_solicitudes = conn.execute("""
        SELECT i.*, m.clave, m.nombre as materia_nombre, m.docente, m.horario, m.minimo,
               (SELECT COUNT(*) FROM inscripciones WHERE materia_id = m.id) as total_grupo
        FROM inscripciones i JOIN materias m ON i.materia_id = m.id
        WHERE i.num_control = ?
        ORDER BY i.id DESC
    """, (nc,)).fetchall()

    mis_ids = {s["materia_id"] for s in mis_solicitudes}
    conn.close()
    return render_template_string(PORTAL_TEMPLATE, alumno=alumno, materias=materias, mis_solicitudes=mis_solicitudes, mis_ids=mis_ids)

@app.route("/login", methods=["POST"])
def login():
    nc = request.form.get("num_control", "").strip()
    nombre = request.form.get("nombre", "").strip()
    carrera = request.form.get("carrera", "Ing. en Sistemas Computacionales")

    if not REGEX_CONTROL.match(nc):
        flash(f"Acceso denegado: El número de control '{nc}' no cumple el formato oficial del ITMH (Año 24-26 + 660 + Consecutivo 001-500).", "err")
        return redirect(url_for("index"))

    conn = get_db()
    alumno = conn.execute("SELECT * FROM alumnos WHERE num_control = ?", (nc,)).fetchone()

    if not alumno:
        if not nombre:
            conn.close()
            flash("Como es tu primer ingreso con esta matrícula, escribe tu nombre completo y selecciona tu carrera para vincular tus datos.", "err")
            return redirect(url_for("index"))
        conn.execute("INSERT INTO alumnos (num_control, nombre, carrera, kardex_valido) VALUES (?, ?, ?, 1)", (nc, nombre, carrera))
        conn.commit()

    conn.close()
    session["num_control"] = nc
    flash("Sesión iniciada correctamente. Tus datos escolares y cursos disponibles fueron cargados.", "ok")
    return redirect(url_for("index"))

@app.route("/logout")
def logout():
    session.clear()
    flash("Has cerrado tu sesión de forma segura.", "ok")
    return redirect(url_for("index"))

@app.route("/solicitar", methods=["POST"])
def solicitar():
    if "num_control" not in session:
        return redirect(url_for("index"))

    nc = session["num_control"]
    mid = request.form.get("materia_id")

    conn = get_db()
    alumno = conn.execute("SELECT * FROM alumnos WHERE num_control = ?", (nc,)).fetchone()
    materia = conn.execute("SELECT * FROM materias WHERE id = ?", (mid,)).fetchone()

    if not alumno or not materia:
        conn.close()
        return redirect(url_for("index"))

    # Validación 1: Kárdex vinculado
    if alumno["kardex_valido"] != 1:
        conn.close()
        flash(f"Solicitud bloqueada: Tu kárdex indica que aún no apruebas el prerrequisito ({materia['prerrequisito']}).", "err")
        return redirect(url_for("index"))

    # Validación 2: Cupo máximo estricto (6 alumnos)
    total_actual = conn.execute("SELECT COUNT(*) FROM inscripciones WHERE materia_id = ?", (mid,)).fetchone()[0]
    if total_actual >= materia["minimo"]:
        conn.close()
        flash(f"Grupo lleno: {materia['nombre']} ya completó sus {materia['minimo']} lugares disponibles.", "err")
        return redirect(url_for("index"))

    # Validación 3: Máximo 2 materias de verano
    materias_alumno = conn.execute("SELECT COUNT(*) FROM inscripciones WHERE num_control = ?", (nc,)).fetchone()[0]
    if materias_alumno >= 2:
        conn.close()
        flash("Límite reglamentario alcanzado: Solo puedes solicitar hasta 2 materias en verano.", "err")
        return redirect(url_for("index"))

    # Validación 4: Evitar duplicados
    existe = conn.execute("SELECT 1 FROM inscripciones WHERE num_control = ? AND materia_id = ?", (nc, mid)).fetchone()
    if existe:
        conn.close()
        flash("Ya tienes registrada una solicitud para esta materia.", "err")
        return redirect(url_for("index"))

    fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ref = f"REF-2026-{mid}-{nc[-4:]}"
    conn.execute(
        "INSERT INTO inscripciones (num_control, materia_id, referencia, pagado, fecha_registro) VALUES (?, ?, ?, 0, ?)",
        (nc, mid, ref, fecha)
    )

    total = conn.execute("SELECT COUNT(*) FROM inscripciones WHERE materia_id = ?", (mid,)).fetchone()[0]
    if total >= materia["minimo"]:
        conn.execute("UPDATE materias SET estado = 'Grupo Lleno (6/6)' WHERE id = ?", (mid,))
        conn.execute("UPDATE inscripciones SET referencia = 'REF-2026-' || materia_id || '-' || substr(num_control, -4) WHERE materia_id = ? AND referencia IS NULL", (mid,))
        flash(f"¡Curso autorizado! Con tu inscripción se completó el grupo ({total}/6). Ya puedes descargar tu Orden de Pago o pagar en línea.", "ok")
    else:
        faltan = materia["minimo"] - total
        flash(f"Solicitud registrada. Faltan {faltan} alumnos para autorizar la apertura del grupo.", "ok")

    conn.commit()
    conn.close()
    return redirect(url_for("index"))

@app.route("/pagar", methods=["POST"])
def pagar():
    if "num_control" not in session:
        return redirect(url_for("index"))

    nc = session["num_control"]
    ins_id = request.form.get("id")
    fecha_pago = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    conn = get_db()
    conn.execute("UPDATE inscripciones SET pagado = 1, fecha_pago = ? WHERE id = ? AND num_control = ?", (fecha_pago, ins_id, nc))
    conn.commit()
    conn.close()
    flash("¡Pago confirmado! Ya puedes descargar tu Comprobante Oficial de Inscripción.", "ok")
    return redirect(url_for("index"))

@app.route("/comprobante/<int:ins_id>")
def comprobante(ins_id):
    if "num_control" not in session:
        return redirect(url_for("index"))

    nc = session["num_control"]
    conn = get_db()
    doc = conn.execute("""
        SELECT i.id, i.num_control, i.referencia, i.pagado, i.fecha_pago,
               a.nombre, a.carrera,
               m.clave, m.nombre as materia_nombre, m.docente, m.horario, m.costo, m.minimo,
               (SELECT COUNT(*) FROM inscripciones WHERE materia_id = m.id) as total_grupo
        FROM inscripciones i
        JOIN alumnos a ON i.num_control = a.num_control
        JOIN materias m ON i.materia_id = m.id
        WHERE i.id = ? AND i.num_control = ?
    """, (ins_id, nc)).fetchone()
    conn.close()

    if not doc or doc["total_grupo"] < doc["minimo"]:
        flash("El comprobante solo está disponible cuando el curso ya fue autorizado (6/6 alumnos).", "err")
        return redirect(url_for("index"))

    doc_dict = dict(doc)
    doc_dict["folio"] = f"ITMH-VER-2026-{doc['id']:04d}"
    return render_template_string(COMPROBANTE_TEMPLATE, doc=doc_dict)

@app.route("/reiniciar_demo", methods=["POST"])
def reiniciar_demo():
    conn = get_db()
    conn.executescript("""
        DROP TABLE IF EXISTS alumnos;
        DROP TABLE IF EXISTS materias;
        DROP TABLE IF EXISTS inscripciones;
    """)
    conn.close()
    init_db()
    session.clear()
    flash("Simulación reiniciada correctamente. Inicia sesión con tu número de control.", "ok")
    return redirect(url_for("index"))

init_db()

if __name__ == "__main__":
    app.run(debug=True, port=5000)