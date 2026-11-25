# VeranoTec — Sistema Automatizado de Cursos de Verano (SCC-1007)

**Consultoría:** VeranoTec (*Gestión académica ágil, grupos confirmados a tiempo*)  
**Cliente:** Tecnológico Nacional de México, Campus Matehuala — División de Estudios Profesionales y Jefaturas Académicas  
**Consultor / Alumno:** Cristofer Yahir Herrera Rodríguez | **No. de Control:** `24660462`  
**Asignatura:** Fundamentos de Ingeniería de Software (SCC-1007)  

---

## 🚀 Acceso en Línea y Documentación Ejecutiva
* **🌐 Abrir Aplicación Web en Vivo (Render):** [https://veranotec-automatizacion.onrender.com/](https://veranotec-automatizacion.onrender.com/) *(Disponible 24/7 desde cualquier computadora o teléfono)*
* **📘 Libro Final de Consultoría Completo (PDF):** [Abrir / Descargar `Libro_Final_Consultoria_VeranoTec.pdf`](./Libro_Final_Consultoria_VeranoTec.pdf)

---

## 📌 Resumen Ejecutivo del Proyecto
* **Problema (AS-IS):** En el TecNM Campus Matehuala, la demanda de cursos de verano se organiza mediante listas informales en papel o grupos de mensajería. El **22 %** de las solicitudes presentan alumnos sin prerrequisitos de kárdex, existe una espera de **4 a 6 días hábiles** de incertidumbre y el **15.4 %** (4 de 26 encuestados) pagaron grupos que terminaron cancelándose.
* **Solución (TO-BE):** Plataforma web desplegada en la nube con base de datos relacional (`veranotec.db` en SQLite) donde el alumno solicita su materia, el sistema valida automáticamente su kárdex, contabiliza la demanda en tiempo real, cambia el estado a **«Por abrir»** al alcanzar el mínimo reglamentario, permite a la Jefatura asignar docente con un clic y emite referencias de pago únicamente cuando el grupo está confirmado.
* **Resultados Medidos:** Reducción del tiempo de confirmación de grupo de **4–6 días a 12 minutos operativos**, **0 %** de pagos anticipados en grupos cancelados y puntaje promedio de usabilidad **SUS de 84.5 / 100** (evaluado con 5 usuarios reales).

---

## 📋 Especificación de Requerimientos (IEEE/ISO/IEC 29148)
* **RF-01 (Solicitud y Kárdex):** Valida automáticamente que el alumno no haya aprobado la materia y cumpla sus prerrequisitos.
* **RF-02 (Conteo y Apertura):** Contabiliza solicitudes válidas en tiempo real y abre el grupo automáticamente al llegar al cupo mínimo.
* **RF-03 (Asignación Docente):** Permite a la Jefatura Académica asignar un profesor disponible con un clic.
* **RF-04 (Referencias y Pagos):** Genera referencias únicas de pago exclusivamente en grupos confirmados con docente.
* **RF-05 / RF-06 (Listas y Cancelación):** Genera horarios/listas oficiales al confirmar pagos y notifica cierres preventivos sin cobro si no se alcanza el mínimo.
* **RF-07 (Reportes División):** Tablero consolidado de demanda, grupos abiertos, pagos y atención de excepciones.
* **RN-01 / RN-02 (Reglas de Negocio):** Prohibición de emitir referencias sin cupo mínimo ni docente asignado; límite máximo de 2 materias simultáneas por alumno en verano.

---

## 🛡️ Aseguramiento de Calidad (Unidad 5) y Métricas
* **Estándares aplicados:** `ISO/IEC/IEEE 29148` (Requerimientos), `ISO/IEC 25010` y factores de **McCall** (Adecuación funcional, Usabilidad, Fiabilidad, Seguridad y Mantenibilidad), e `ISO/IEC/IEEE 29119-3` (Casos de prueba `CP-01` a `CP-05`).
* **Madurez y PSP:** Diagnóstico **CMMI** (proceso actual en Nivel 1 → propuesta en Nivel 2; desarrollo personal en Nivel 2) y bitácora **PSP** con **19.5 horas reales** invertidas y **5 defectos** corregidos antes de liberación.

---

## 💻 Ejecución Local Opcional (Python + Flask + SQLite)
Si se desea ejecutar en un entorno local aislado:
1. Instalar dependencias:
   ```bash
   pip install -r requirements.txt
