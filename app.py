import sqlite3
from flask import Flask, render_template_string, request, redirect, url_for, flash
from datetime import datetime

app = Flask(__name__)
app.secret_key = "veranotec_portal_alumno_2026"
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

    c.execute('''CREATE TABLE IF NOT EXISTS materias (
        id TEXT PRIMARY KEY,
        carrera TEXT,
        clave TEXT,
        nombre TEXT,
        docente TEXT,
        horario TEXT,
        prerrequisito TEXT,
        minimo INTEGER,
        estado TEXT
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS inscripciones (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        num_control TEXT,
        nombre_alumno TEXT,
        carrera TEXT,
        materia_id TEXT,
        referencia TEXT,
        pagado INTEGER DEFAULT 0,
        fecha_registro TEXT,
        UNIQUE(num_control, materia_id)
    )''')

    if c.execute("SELECT COUNT(*) FROM materias").fetchone()[0] == 0:
        materias_init = [
            ("FIS-01", "Ing. en Sistemas Computacionales", "SCC-1007", "Fundamentos de Ingeniería de Software", "Ing. Roberto Martínez (Simulado)", "Lun-Vie 08:00 - 10:00 | Aula CC-2", "Fundamentos de Programación", 10, "En espera (Falta 1 lugar)"),
            ("MAT-02", "Ing. en Sistemas Computacionales", "ACF-0902", "Cálculo Integral", "M.C. Laura Sánchez (Simulado)", "Lun-Vie 10:00 - 12:00 | Aula B-4", "Cálculo Diferencial", 10, "En recolección de demanda"),
            ("BDD-03", "Ing. en Sistemas Computacionales", "AEF-1031", "Fundamentos de Bases de Datos", "Ing. Carlos Hernández (Simulado)", "Lun-Vie 12:00 - 14:00 | Lab. Cómputo 1", "Taller de Programación", 10, "En recolección de demanda"),
            ("IND-01", "Ing. Industrial", "INC-1009", "Estudio del Trabajo I", "Ing. Patricia Gómez (Simulado)", "Lun-Vie 08:00 - 10:00 | Aula D-1", "Probabilidad y Estadística", 10, "En recolección de demanda"),
            ("IGE-01", "Ing. en Gestión Empresarial", "GEC-0905", "Costos Empresariales", "M.A. Fernando Ruiz (Simulado)", "Lun-Vie 10:00 - 12:00 | Aula E-3", "Contabilidad Orientada a los Negocios", 10, "En recolección de demanda")
        ]
        c.executemany("INSERT INTO materias VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", materias_init)

        # Precarga de 9 alumnos simulados en SCC-1007 para demostrar el cierre de cupo al entrar el #10
        precarga_fis = [(f"2466090{i}", f"Alumno Simulado {i}", "Ing. en Sistemas Computacionales", "FIS-01", None, 0, "2026-11-25 08:00:00") for i in range(1, 10)]
        precarga_mat = [(f"2466091{i}", f"Alumno Simulado {i}", "Ing. en Sistemas Computacionales", "MAT-02", None, 0, "2026-11-25 08:00:00") for i in range(1, 6)]
        c.executemany("INSERT INTO inscripciones (num_control, nombre_alumno, carrera, materia_id, referencia, pagado, fecha_registro) VALUES (?, ?, ?, ?, ?, ?, ?)", precarga_fis + precarga_mat)

    conn.commit()
    conn.close()

# ==========================================
# INTERFAZ EXCLUSIVA DEL ALUMNO (UX)
# ==========================================
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>VeranoTec | Portal Estudiantil de Cursos de Verano</title>
    <style>
        :root {
            --azul-oscuro: #0f172a;
            --azul-primario: #0284c7;
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
            background: var(--azul-oscuro);
            color: white;
            padding: 18px 30px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 10px;
        }
        .topbar h1 { margin: 0; font-size: 21px; color: #38bdf8; }
        .topbar p { margin: 3px 0 0; font-size: 13px; color: #cbd5e1; }
        .container { max-width: 1080px; margin: 24px auto; padding: 0 20px; }

        .grid { display: grid; grid-template-columns: 1fr 1.2fr; gap: 22px; }
        .card {
            background: white;
            border: 1px solid #e2e8f0;
            border-radius: 12px;
            padding: 22px;
            box-shadow: 0 2px 8px rgba(15, 23, 42, 0.05);
            margin-bottom: 22px;
        }
        .card h2 { margin: 0 0 6px; font-size: 18px; color: var(--azul-oscuro); }
        .subtitle { margin: 0 0 18px; font-size: 13.5px; color: #64748b; }

        label { display: block; font-weight: 600; font-size: 13.5px; margin-bottom: 6px; color: #334155; }
        input[type="text"], select {
            width: 100%;
            padding: 10px 12px;
            border: 1px solid var(--borde);
            border-radius: 8px;
            font-size: 14px;
            background: #f8fafc;
            margin-bottom: 14px;
        }
        .checkbox-row {
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 13.5px;
            margin-bottom: 16px;
            background: #f8fafc;
            padding: 10px;
            border-radius: 8px;
            border: 1px solid #e2e8f0;
        }
        button.primary {
            background: var(--azul-primario);
            color: white;
            border: none;
            padding: 12px;
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
            padding: 7px 14px;
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

        .course-item {
            border: 1px solid #e2e8f0;
            border-radius: 10px;
            padding: 14px;
            margin-bottom: 12px;
            background: #f8fafc;
        }
        .course-header { display: flex; justify-content: space-between; align-items: flex-start; gap: 10px; }
        .course-title { font-weight: 700; color: var(--azul-oscuro); font-size: 15px; }
        .course-meta { font-size: 13px; color: #475569; margin-top: 6px; line-height: 1.5; }
        .progress-wrap { background: #e2e8f0; border-radius: 99px; height: 9px; overflow: hidden; margin: 8px 0 4px; }
        .progress-bar { height: 100%; background: var(--azul-primario); }
        .progress-bar.full { background: var(--rojo); }

        .pill { padding: 4px 10px; border-radius: 99px; font-size: 11.5px; font-weight: 600; white-space: nowrap; }
        .pill-wait { background: var(--ambar-claro); color: #92400e; }
        .pill-open { background: var(--verde-claro); color: #166534; }
        .pill-full { background: var(--rojo-claro); color: #991b1b; }

        table { width: 100%; border-collapse: collapse; font-size: 13.5px; }
        th { background: #f1f5f9; text-align: left; padding: 10px; border-bottom: 2px solid #e2e8f0; color: #334155; }
        td { padding: 10px; border-bottom: 1px solid #e2e8f0; }

        .alert {
            padding: 14px 18px;
            border-radius: 8px;
            margin-bottom: 18px;
            font-size: 14px;
            font-weight: 500;
        }
        .alert-ok { background: var(--verde-claro); color: #14532d; border-left: 5px solid var(--verde); }
        .alert-err { background: var(--rojo-claro); color: #7f1d1d; border-left: 5px solid var(--rojo); }

        @media (max-width: 820px) { .grid { grid-template-columns: 1fr; } }
    </style>
</head>
<body>

<div class="topbar">
    <div>
        <h1>VeranoTec · Portal del Estudiante</h1>
        <p>Solicitud de Cursos de Verano en Línea · TecNM Campus Matehuala (Datos Simulados)</p>
    </div>
    <form action="/reiniciar_demo" method="POST" style="margin:0;">
        <button type="submit" class="reset">Reiniciar Simulación</button>
    </form>
</div>

<div class="container">

    {% with messages = get_flashed_messages(with_categories=true) %}
      {% if messages %}
        {% for category, message in messages %}
          <div class="alert {{ 'alert-ok' if category == 'ok' else 'alert-err' }}">{{ message }}</div>
        {% endfor %}
      {% endif %}
    {% endwith %}

    <div class="grid">
        <!-- COLUMNA IZQUIERDA: FORMULARIO DEL ALUMNO -->
        <div class="card">
            <h2>1. Solicitar Curso de Verano</h2>
            <p class="subtitle">Ingresa tus datos escolares y selecciona la materia. El sistema validará automáticamente tu kárdex y el cupo máximo del grupo (10 lugares).</p>

            <form action="/solicitar" method="POST">
                <label for="num_control">Número de Control (8 dígitos):</label>
                <input type="text" id="num_control" name="num_control" placeholder="Ej. 24660123" pattern="[0-9]{8}" required>

                <label for="nombre_alumno">Nombre o Alias Simulado:</label>
                <input type="text" id="nombre_alumno" name="nombre_alumno" placeholder="Ej. Alumno Prueba 01" required>

                <label for="carrera">Selecciona tu Carrera:</label>
                <select id="carrera" name="carrera" onchange="filtrarMaterias()">
                    <option value="Ing. en Sistemas Computacionales">Ing. en Sistemas Computacionales</option>
                    <option value="Ing. Industrial">Ing. Industrial</option>
                    <option value="Ing. en Gestión Empresarial">Ing. en Gestión Empresarial</option>
                </select>

                <label for="materia_id">Curso de Verano Disponible:</label>
                <select id="materia_id" name="materia_id">
                    {% for m in materias %}
                    <option value="{{ m['id'] }}" data-carrera="{{ m['carrera'] }}" {{ 'disabled' if m['total_inscritos'] >= m['minimo'] else '' }}>
                        {{ m['clave'] }} · {{ m['nombre'] }} — {{ '[GRUPO LLENO 10/10]' if m['total_inscritos'] >= m['minimo'] else 'Prof: ' + m['docente'] }}
                    </option>
                    {% endfor %}
                </select>

                <div class="checkbox-row">
                    <input type="checkbox" id="cumple_kardex" name="cumple_kardex" value="si" checked>
                    <label for="cumple_kardex" style="margin:0; font-weight:normal;">
                        Simular kárdex válido (prerrequisito aprobado y materia no cursada previamente)
                    </label>
                </div>

                <button type="submit" class="primary">Registrar Solicitud de Verano</button>
            </form>
        </div>

        <!-- COLUMNA DERECHA: OFERTA DE CURSOS Y PROFESORES -->
        <div class="card">
            <h2>2. Oferta de Verano y Docentes Asignados</h2>
            <p class="subtitle">Consulta qué materias están disponibles para tu carrera, quién las imparte y el cupo del grupo (máximo 10 alumnos).</p>

            {% for m in materias %}
            {% set pct = (m['total_inscritos'] / m['minimo'] * 100)|int %}
            {% set lleno = m['total_inscritos'] >= m['minimo'] %}
            <div class="course-item" data-carrera="{{ m['carrera'] }}">
                <div class="course-header">
                    <div class="course-title">{{ m['clave'] }} · {{ m['nombre'] }}</div>
                    <span class="pill {{ 'pill-full' if lleno else 'pill-wait' }}">
                        {{ 'Grupo Lleno (Cupo Completo)' if lleno else m['estado'] }}
                    </span>
                </div>
                <div class="course-meta">
                    <strong>Carrera:</strong> {{ m['carrera'] }}<br>
                    <strong>Docente:</strong> {{ m['docente'] }}<br>
                    <strong>Horario y Aula:</strong> {{ m['horario'] }}<br>
                    <strong>Prerrequisito:</strong> {{ m['prerrequisito'] }}
                </div>
                <div class="progress-wrap">
                    <div class="progress-bar {{ 'full' if lleno else '' }}" style="width: {{ 100 if pct > 100 else pct }}%;"></div>
                </div>
                <small style="color: {{ '#991b1b' if lleno else '#334155' }};">
                    <strong>{{ m['total_inscritos'] }} de {{ m['minimo'] }} alumnos inscritos {{ '· Sin lugares disponibles' if lleno else '' }}</strong>
                </small>
            </div>
            {% endfor %}
        </div>
    </div>

    <!-- SECCIÓN INFERIOR: MIS SOLICITUDES, REFERENCIA DE PAGO Y HORARIO -->
    <div class="card">
        <h2>3. Mis Solicitudes Registradas y Referencias de Pago</h2>
        <p class="subtitle">Tu solicitud queda guardada automáticamente en la base de datos. Cuando el grupo alcanza los 10 alumnos, se abre y libera tu referencia de pago y horario oficial.</p>

        {% if mis_solicitudes %}
        <table>
            <tr>
                <th>No. Control</th>
                <th>Alumno</th>
                <th>Materia y Docente</th>
                <th>Estatus del Grupo</th>
                <th>Referencia y Pago</th>
            </tr>
            {% for s in mis_solicitudes %}
            <tr>
                <td><strong>{{ s['num_control'] }}</strong></td>
                <td>{{ s['nombre_alumno'] }}<br><small style="color:#64748b;">{{ s['carrera'] }}</small></td>
                <td><strong>{{ s['materia_nombre'] }}</strong><br><small>{{ s['docente'] }}</small></td>
                <td>
                    {% if s['total_grupo'] >= s['minimo'] %}
                        <span class="pill pill-open">Grupo Confirmado y Lleno ({{ s['total_grupo'] }}/{{ s['minimo'] }})</span>
                    {% else %}
                        <span class="pill pill-wait">En espera ({{ s['total_grupo'] }}/{{ s['minimo'] }})</span>
                    {% endif %}
                </td>
                <td>
                    {% if s['total_grupo'] < s['minimo'] %}
                        <span style="color:#64748b; font-size:12.5px;">Referencia bloqueada hasta llegar a {{ s['minimo'] }} alumnos</span>
                    {% elif s['pagado'] == 1 %}
                        <span class="pill pill-open">INSCRITO · {{ s['horario'] }}</span>
                    {% else %}
                        <code>{{ s['referencia'] }}</code>
                        <form action="/pagar" method="POST" style="display:inline; margin-left:8px;">
                            <input type="hidden" name="id" value="{{ s['id'] }}">
                            <button type="submit" class="success">Simular Pago</button>
                        </form>
                    {% endif %}
                </td>
            </tr>
            {% endfor %}
        </table>
        {% else %}
        <p style="color:#64748b; font-size:13.5px; margin:0;">Aún no has registrado ninguna solicitud con tu número de control. Completa el formulario de arriba para probar el sistema.</p>
        {% endif %}
    </div>

</div>

<script>
    function filtrarMaterias() {
        const carreraSel = document.getElementById('carrera').value;
        const selectMat = document.getElementById('materia_id');
        let primeraDisponible = null;
        let primeraDeCarrera = null;

        for (let opt of selectMat.options) {
            if (opt.dataset.carrera === carreraSel) {
                opt.style.display = 'block';
                if (!primeraDeCarrera) primeraDeCarrera = opt.value;
                if (!opt.disabled && !primeraDisponible) primeraDisponible = opt.value;
            } else {
                opt.style.display = 'none';
            }
        }
        if (primeraDisponible) {
            selectMat.value = primeraDisponible;
        } else if (primeraDeCarrera) {
            selectMat.value = primeraDeCarrera;
        }

        document.querySelectorAll('.course-item').forEach(card => {
            card.style.display = (card.dataset.carrera === carreraSel) ? 'block' : 'none';
        });
    }
    window.onload = filtrarMaterias;
</script>
</body>
</html>
"""

# ==========================================
# RUTAS Y REGLAS DE NEGOCIO DEL ALUMNO
# ==========================================
@app.route("/")
def index():
    conn = get_db()
    materias = conn.execute("""
        SELECT m.*, COUNT(i.id) as total_inscritos 
        FROM materias m LEFT JOIN inscripciones i ON m.id = i.materia_id 
        GROUP BY m.id
    """).fetchall()

    mis_solicitudes = conn.execute("""
        SELECT i.*, m.nombre as materia_nombre, m.docente, m.horario, m.minimo,
               (SELECT COUNT(*) FROM inscripciones WHERE materia_id = m.id) as total_grupo
        FROM inscripciones i JOIN materias m ON i.materia_id = m.id
        WHERE i.num_control NOT LIKE '246609%'
        ORDER BY i.id DESC
    """).fetchall()
    conn.close()
    return render_template_string(HTML_TEMPLATE, materias=materias, mis_solicitudes=mis_solicitudes)

@app.route("/solicitar", methods=["POST"])
def solicitar():
    num_control = request.form["num_control"].strip()
    nombre_alumno = request.form["nombre_alumno"].strip()
    carrera = request.form["carrera"]
    mid = request.form.get("materia_id")
    cumple_kardex = request.form.get("cumple_kardex") == "si"

    if not mid:
        flash("No hay cursos seleccionados o disponibles.", "err")
        return redirect(url_for("index"))

    conn = get_db()
    materia = conn.execute("SELECT * FROM materias WHERE id = ?", (mid,)).fetchone()
    total_actual = conn.execute("SELECT COUNT(*) FROM inscripciones WHERE materia_id = ?", (mid,)).fetchone()[0]

    # Validación 0: Bloqueo estricto si el grupo ya está lleno (10/10)
    if total_actual >= materia["minimo"]:
        conn.close()
        flash(f"Inscripción rechazada: El grupo de {materia['nombre']} ({materia['clave']}) ya está lleno ({total_actual}/{materia['minimo']}) y no admite más alumnos.", "err")
        return redirect(url_for("index"))

    # Validación 1: Prerrequisitos de kárdex
    if not cumple_kardex:
        conn.close()
        flash(f"Solicitud bloqueada: El kárdex indica que no cumples el prerrequisito ({materia['prerrequisito']}) o ya aprobaste esta materia.", "err")
        return redirect(url_for("index"))

    # Validación 2: Máximo 2 materias de verano por alumno (Lineamiento TecNM)
    materias_alumno = conn.execute("SELECT COUNT(*) FROM inscripciones WHERE num_control = ?", (num_control,)).fetchone()[0]
    if materias_alumno >= 2:
        conn.close()
        flash(f"Límite alcanzado: El alumno {num_control} ya tiene 2 materias registradas en verano (máximo permitido por reglamento).", "err")
        return redirect(url_for("index"))

    # Validación 3: Evitar registro duplicado
    existe = conn.execute("SELECT 1 FROM inscripciones WHERE num_control = ? AND materia_id = ?", (num_control, mid)).fetchone()
    if existe:
        conn.close()
        flash(f"El número de control {num_control} ya tiene registrada una solicitud para {materia['nombre']}.", "err")
        return redirect(url_for("index"))

    fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ref = f"REF-2026-{mid}-{num_control[-4:]}"
    conn.execute(
        "INSERT INTO inscripciones (num_control, nombre_alumno, carrera, materia_id, referencia, pagado, fecha_registro) VALUES (?, ?, ?, ?, ?, 0, ?)",
        (num_control, nombre_alumno, carrera, mid, ref, fecha)
    )

    total = conn.execute("SELECT COUNT(*) FROM inscripciones WHERE materia_id = ?", (mid,)).fetchone()[0]

    # Apertura y cierre de cupo al llegar a 10/10
    if total >= materia["minimo"]:
        conn.execute("UPDATE materias SET estado = 'Grupo Lleno (Cupo Completo)' WHERE id = ?", (mid,))
        conn.execute("UPDATE inscripciones SET referencia = 'REF-2026-' || materia_id || '-' || substr(num_control, -4) WHERE materia_id = ? AND referencia IS NULL", (mid,))
        flash(f"¡Solicitud registrada para {num_control}! Se completó el cupo ({total}/{materia['minimo']}), el grupo quedó lleno y tu referencia de pago ya está disponible.", "ok")
    else:
        faltan = materia["minimo"] - total
        flash(f"¡Solicitud guardada para {num_control}! Faltan {faltan} lugares para completar el grupo de {materia['nombre']}.", "ok")

    conn.commit()
    conn.close()
    return redirect(url_for("index"))

@app.route("/pagar", methods=["POST"])
def pagar():
    ins_id = request.form["id"]
    conn = get_db()
    conn.execute("UPDATE inscripciones SET pagado = 1 WHERE id = ?", (ins_id,))
    conn.commit()
    conn.close()
    flash("¡Pago confirmado por referencia! Tu horario oficial y aula han quedado asignados.", "ok")
    return redirect(url_for("index"))

@app.route("/reiniciar_demo", methods=["POST"])
def reiniciar_demo():
    conn = get_db()
    conn.executescript("""
        DROP TABLE IF EXISTS materias;
        DROP TABLE IF EXISTS inscripciones;
    """)
    conn.close()
    init_db()
    flash("Simulación reiniciada correctamente.", "ok")
    return redirect(url_for("index"))

init_db()

if __name__ == "__main__":
    app.run(debug=True, port=5000)