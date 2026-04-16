# PriorAI

PriorAI es un agente conversacional orientado al ámbito sanitario, desarrollado para el **Dedalus Datathon Castilla-La Mancha 2026**.

Su objetivo es permitir a profesionales de la salud **identificar cohortes de pacientes crónicos mediante lenguaje natural** a partir de distintas fuentes de datos clínicas. El sistema integra información de pacientes, alergias, condiciones, procedimientos, encuentros y medicación para construir cohortes de forma progresiva, mantener el contexto conversacional y ofrecer resultados útiles para la toma de decisiones.

Además de recuperar pacientes, PriorAI puede:

- Generar **estadísticas** sobre la cohorte creada.
- Mostrar **visualizaciones** que facilitan el análisis.
- Mantener **memoria durante la conversación** para refinar cohortes paso a paso.
- Ejecutar **acciones sobre la cohorte**, orientadas al seguimiento clínico.

## Objetivo del proyecto

El proyecto busca transformar varias fuentes de datos aisladas en una experiencia conversacional útil, intuitiva y escalable, acercando la IA a un entorno clínico más realista.

## Tecnologías y enfoque

La solución está planteada con una arquitectura modular y escalable, poniendo especial foco en:

- **Precisión**, para minimizar alucinaciones.
- **Memoria conversacional**, para mantener el contexto entre consultas.
- **Visualización de resultados**, más allá de respuestas solo textuales.
- **Ejecución de acciones**, no solo análisis.
- **Escalabilidad**, para permitir incorporar nuevas fuentes de datos y funcionalidades.

## Ejecución del proyecto

Se recomienda crear primero un entorno virtual para aislar las dependencias del proyecto.

### 1. Crear entorno virtual

python -m venv .venv

### 2. Activar entorno virtual

.venv\Scripts\activate

### 3. Instalar dependencias

### 4. Acceso a la aplicación:

- **Backend:**  python -m uvicorn app.api.main:app --reload
- **Frontend:** cd .\frontend\;python -m http.server 5500
- **Acceso:** http://127.0.0.1:5500/

## Colaboradores

- **Alex** — [Linkedin](https://www.linkedin.com/in/alexortegaredondo).
- **Celia** — [Linkedin](https://www.linkedin.com/in/celia-almendros-saelices).
- **Javier** — [Linkedin](https://www.linkedin.com/in/javier-garcía-meneses-50b300366).
