# Backend AgroTracker · GPTI G10

API (FastAPI) del sistema de trazabilidad y gestión de cosecha para la Cooperativa Newen al Sur.

- **Fase 1:** registro de lotes/cosechas, código QR por lote, historial.
- **Fase 2:** clima del campo con la Red Agroclimática Nacional (Agromet), alertas climáticas,
  sensores de suelo, recomendaciones IA. Instacrops aún sin contrato: se prueba con `simuladores/`.

## Arquitectura

> Propuesta de arquitectura objetivo en AWS. Para el piloto ya existe un despliegue con Docker en
> un solo servidor (ver **Despliegue con Docker**). Esta arquitectura sirve de base para el
> documento de arquitectura y para estimar costos en AWS Pricing Calculator.

### Despliegue en AWS

```mermaid
flowchart LR
    subgraph Usuarios
        ADM["Administrador<br/>(directiva)"]
        PRO["Productor<br/>(socio)"]
        AUD["Comprador / auditor<br/>(escanea el QR)"]
    end

    R53["Route 53<br/>dominio .cl"]

    subgraph AWS["AWS · región sa-east-1"]
        ACM["Certificate Manager<br/>(HTTPS)"]
        ALB["Application Load Balancer"]

        subgraph VPC["VPC"]
            subgraph ECS["ECS Fargate"]
                FE["Frontend<br/>Flask (PWA)"]
                BE["Backend<br/>FastAPI"]
            end
            RDS[("RDS PostgreSQL<br/>respaldos automáticos")]
        end

        ECR["ECR<br/>imágenes Docker"]
        SM["Secrets Manager<br/>SECRET_KEY, claves API, BD"]
        CW["CloudWatch<br/>logs y alarmas"]
    end

    subgraph Externos["Servicios externos"]
        GEM["Google Gemini API<br/>recomendaciones IA"]
        BRE["Brevo<br/>SMTP de correo"]
        AGR["Agromet (RAN)<br/>estaciones agroclimáticas"]
        INS["Instacrops API<br/>clima y datos agronómicos"]
    end

    ADM & PRO & AUD --> R53 --> ALB
    ACM -.-> ALB
    ALB -- "app.dominio" --> FE
    ALB -- "api.dominio" --> BE
    FE -- "REST + JWT" --> BE
    BE --> RDS
    ECR -.-> ECS
    SM -.-> BE
    BE -.-> CW
    FE -.-> CW
    BE -- "ProveedorIA" --> GEM
    BE -- "ServicioCorreo" --> BRE
    BE -- "ProveedorClima" --> AGR
    BE --> INS
```

- **ALB + ACM**: un solo punto de entrada con HTTPS; enruta por subdominio al frontend o a la API.
- **ECS Fargate**: frontend y backend corren como contenedores sin administrar servidores; las
  imágenes se publican en ECR.
- **RDS PostgreSQL**: en subred privada, solo accesible desde el backend (`DATABASE_URL`).
- **Secrets Manager**: las variables sensibles del `.env` se inyectan a los contenedores.
- **Servicios externos** (presupuesto 2.3): Gemini para la IA y Brevo para correo. Ambos se
  usan detrás de un puerto (patrón Adapter), así cambiar de proveedor no toca los casos de uso.
- Para ajustarse a la estimación mensual del presupuesto conviene evitar un NAT Gateway:
  tareas Fargate en subred pública con security groups que solo aceptan tráfico del ALB.

### Capas del backend

```mermaid
flowchart TB
    R["routers/<br/>HTTP: validación, auth y códigos de estado"]
    A["auth.py<br/>sesión JWT y permisos por rol"]
    S["services/<br/>casos de uso y reglas de negocio"]
    M["models.py<br/>SQLAlchemy"]
    DB[("PostgreSQL / SQLite")]

    subgraph Puertos["Puertos (patrón Adapter)"]
        PIA["ProveedorIA"]
        PCO["ServicioCorreo"]
    end

    subgraph Adapters
        GEM["GeminiAdapter"]
        CLA["ClaudeAdapter"]
        SIA["ProveedorSimulado"]
        SMTP["SmtpAdapter<br/>(Brevo)"]
        SCO["CorreoSimulado"]
    end

    R --> A
    R --> S
    S --> M --> DB
    S --> PIA
    S --> PCO
    PIA -.-> GEM & CLA & SIA
    PCO -.-> SMTP & SCO
```

Los routers no contienen lógica; los servicios no conocen HTTP ni el proveedor concreto de IA o
correo. Los errores de dominio (`app/exceptions.py`) se traducen a HTTP en `main.py`.

## Estructura

```
app/
  main.py            # app FastAPI, CORS, routers
  config.py          # variables de entorno (.env)
  db.py              # SQLAlchemy (SQLite local / Postgres en AWS)
  models.py          # tablas
  schemas.py         # modelos de entrada/salida (Pydantic)
  exceptions.py      # errores de dominio (se mapean a HTTP en main.py)
  migraciones.py     # agrega columnas nuevas a bases existentes al iniciar
  routers/           # endpoints por módulo (solo HTTP)
  services/          # casos de uso y clientes externos
    ia/              # patrón Adapter: puerto ProveedorIA + adapters Gemini/Claude/simulado
    correo/          # patrón Adapter: puerto ServicioCorreo + adapters SMTP/simulado
tests/
Dockerfile         # imagen de la API
simuladores/       # APIs simuladas de Agromet e Instacrops (solo demo)
despliegue/        # docker-compose (PostgreSQL + API + frontend + Caddy HTTPS)
```

## Endpoints

| Método | Ruta | Descripción |
|---|---|---|
| POST | `/auth/login` | Inicia sesión y entrega un token (público) |
| GET | `/auth/yo` | Usuario de la sesión |
| POST | `/auth/logout` | Cierra la sesión: el token queda revocado |
| POST | `/auth/recuperar` | Envía por correo un código de 6 dígitos (público, misma respuesta exista o no el correo) |
| POST | `/auth/restablecer` | Cambia la contraseña con el código (público) |
| GET | `/publico/lotes/{codigo}` | Ficha de origen: entregas y estado, sin ventas ni precios (público, destino del QR) |
| GET/POST | `/lotes` | Listar (filtros `desde`, `hasta`, `estado`, `cultivo`, `usuario_id`) / registrar con su primera entrega |
| GET/PATCH | `/lotes/{codigo}` | Ver / editar (exige `motivo`, queda en el historial) |
| POST | `/lotes/{codigo}/anular` | Anula el lote con un motivo (no hay borrado físico) |
| POST | `/lotes/{codigo}/entregas` | Agrega una entrega de cosecha (kilos, fecha, calidad) |
| POST | `/lotes/{codigo}/entregas/{id}/anular` | Anula una entrega con un motivo |
| GET | `/lotes/{codigo}/qr` | Código QR del lote |
| GET/POST | `/lotes/{codigo}/ventas` | Ventas del lote |
| POST | `/lotes/{codigo}/ventas/{id}/anular` | Anula una venta con un motivo (sus kilos vuelven a estar disponibles) |
| GET | `/lotes/{codigo}/trazabilidad` | Lote + entregas + ventas + historial de cambios |
| GET | `/lotes/{codigo}/reporte.pdf` · `.csv` | Reporte del lote para descargar |
| GET | `/lotes/{codigo}/recomendacion` | Recomendación con IA: se guarda con los datos usados |
| GET | `/lotes/{codigo}/recomendaciones` · `/recomendaciones` | Historial de recomendaciones |
| POST | `/lotes/{codigo}/reporte` | Envía por correo el reporte (PDF y CSV adjuntos) |
| GET/PUT | `/campo` | Ubicación del campo propio (admin: `?usuario_id=` para ver otro) |
| GET | `/campos` | Campos registrados (solo admin) |
| GET | `/clima` | Clima del campo: estación Agromet más cercana, últimas 48 h y alertas |
| GET | `/clima/recomendacion` | Qué tomar en consideración según el clima y la bodega (IA) |
| GET | `/dashboard/resumen` | Indicadores con filtros `desde`, `hasta`, `cultivo` y `usuario_id` (socio, solo admin): kilos, entregas, ventas, ingresos, recomendaciones y demora de la cola |
| GET/POST | `/usuarios` | Listar / crear usuarios con RUT validado; las credenciales se envían por correo (solo admin) |
| PATCH | `/usuarios/{id}` | Editar nombre, correo, RUT, rol o acceso (solo admin) |

Salvo los marcados como públicos, los endpoints exigen `Authorization: Bearer <token>` (401 sin sesión).

**Roles** (sección 5 del documento de requerimientos):

- **Administrador** (directiva de la cooperativa): ve y gestiona todos los lotes (los anula, no los borra), filtra por socio y gestiona usuarios.
- **Productor** (socio): registra lotes a su nombre y solo ve, edita y vende sus propios lotes; el dashboard muestra solo sus cifras. Lo que no le corresponde responde **403**.

El primer administrador se crea al iniciar la API con `ADMIN_EMAIL` y `ADMIN_CLAVE` (mínimo 12
caracteres, solo en tu `.env`) si la base no tiene usuarios.

Las reglas de negocio que no se cumplen responden **409** (p. ej. vender más kilos de los disponibles).

## Entregas, anulaciones e historial

- Un lote tiene **predio**, **superficie** y una o más **entregas** (fecha, kilos y calidad:
  extra, primera, segunda o descarte). Los kilos del lote son la suma de sus entregas vigentes.
- **Nada se borra.** Lotes, entregas y ventas se **anulan** con un motivo: siguen en el historial
  y en los reportes, pero no cuentan en los saldos ni en el dashboard. No se puede anular una
  entrega si quedarían menos kilos que los vendidos, ni un lote con ventas vigentes.
- Cada creación, edición y anulación queda en la tabla `cambios` con **usuario, fecha, detalle**
  (`campo: antes → después`) y **motivo**. Editar un lote exige motivo.
- Al iniciar, `migraciones.py` agrega las columnas nuevas a una base existente y convierte los
  kilos de cada lote antiguo en su primera entrega.

## Cola sin conexión (solicitud de cambio N°2)

El frontend manda en cada registro guardado en el teléfono `X-Evento-Id` (identificador único),
`X-Evento-Creado` (cuándo se guardó) y `X-Cola: 1` si esperó sin señal. El backend:

- **No duplica**: si un `X-Evento-Id` ya llegó, devuelve el registro existente (un reintento tras
  un corte no crea otro lote ni descuenta dos veces una venta).
- **Mide la demora** entre que se guarda y que llega (`eventos_cola`). El dashboard muestra el
  promedio, cuántos esperaron señal y la demora máxima.

## Recomendaciones con IA

- Proveedores: `simulado` (por defecto, reglas fijas), `gemini` (API REST de Google Gemini,
  `GEMINI_API_KEY`) o `claude`.
- Cada recomendación se guarda con los **datos que se le entregaron** (cultivo, kilos, días desde
  la cosecha, clima, sensores…), que se muestran junto a la sugerencia.
- `IA_LIMITE_DIARIO` limita las consultas por usuario al día (429 al superarlo) e
  `IA_HABILITADA=0` las desactiva (503), sin tocar el resto del sistema.

## Clima (Agromet)

Cada usuario registra la ubicación de su campo (`PUT /campo`). `GET /clima` busca la estación más
cercana de la **Red Agroclimática Nacional** (catastro de 417 estaciones en
`app/data/estaciones_agromet.json`), trae sus lecturas horarias de las últimas 48 h y calcula:

- **Resumen de 24 h:** mínima, máxima, lluvia, humedad media y viento máximo.
- **Alertas por reglas** (`services/clima/analisis.py`): helada (≤ 0 °C) y riesgo de helada (≤ 3 °C),
  calor (≥ 32 °C), lluvia (≥ 5 mm / ≥ 20 mm), viento (≥ 40 km/h), condiciones para hongos
  (humedad ≥ 85 % con 10-25 °C), datos atrasados y estación lejana (> 30 km).
- **Sensores de suelo** (opcional): humedad y temperatura, con alertas de suelo seco (≤ 30 %) y
  saturado (≥ 90 %). Si fallan, el clima se sigue mostrando.
- `GET /clima/recomendacion` entrega todo eso, más la cosecha en bodega, al `ProveedorIA`.

La fuente de datos es un puerto (`ProveedorClima`) con dos adapters, elegidos con `CLIMA_PROVEEDOR`:

- `simulado` (por defecto): datos plausibles para la latitud y la época, sin red.
- `agromet`: usa `getGraphData.php` de agromet.cl, el servicio que alimenta los gráficos del
  portal (el mismo que usa el paquete abierto agrometR), con caché de 15 minutos.
  **Agromet no publica una API documentada y hoy su firewall bloquea clientes automáticos (HTTP
  403)**: antes de activarlo hay que pedir acceso a la red (info@agromet.cl). Si cambian el formato,
  basta ajustar `services/clima/agromet.py`.

## APIs simuladas (demo sin servicios externos)

`simuladores/` es un servicio aparte que imita Agromet e Instacrops por HTTP, así se ejecutan los
adapters reales. Pasar a las APIs verdaderas es cambiar la configuración.

- **Agromet:** mismo XML que lee el adapter. El formato sigue al paquete agrometR; no se ha podido
  comparar con una respuesta actual porque el acceso está bloqueado.
- **Instacrops:** no tenemos su especificación. **El contrato es una propuesta nuestra**
  (`services/sensores/instacrops.py`) y habrá que ajustarlo cuando exista el real.
- Con `APIS_SIMULADAS=1` la app avisa que los datos son de ejemplo.

| Escenario | Qué muestra |
|---|---|
| `normal` | Clima templado y suelo con humedad adecuada |
| `helada` | Mínimas bajo 0 °C |
| `lluvia` | Lluvia intensa, alta humedad y suelo saturado |
| `sequia` | Calor, aire seco y suelo seco |
| `sin_agromet` | Agromet caído: la pantalla muestra el campo y el error |
| `sin_instacrops` | Sensores caídos: el clima sigue funcionando |

Con Docker (desde `despliegue/`):

```bash
docker compose -f docker-compose.yml -f docker-compose.simuladores.yml up -d --build
docker compose -f docker-compose.yml -f docker-compose.simuladores.yml exec simuladores python -m simuladores.escenario helada
```

Sin Docker: `uvicorn simuladores.main:app --port 9000`, y en `.env`:

```bash
APIS_SIMULADAS=1
CLIMA_PROVEEDOR=agromet
AGROMET_URL=http://127.0.0.1:9000/agromet/getGraphData.php
AGROMET_CACHE_MINUTOS=0
SENSORES_PROVEEDOR=instacrops
INSTACROPS_API_URL=http://127.0.0.1:9000/instacrops
INSTACROPS_API_KEY=demo
INSTACROPS_CACHE_MINUTOS=0
```

## IA

`IA_PROVEEDOR=simulado` (por defecto) no usa red ni API key: aplica reglas fijas sobre clima, suelo,
cultivo y días en bodega, y su respuesta siempre se identifica como simulada. Con `IA_PROVEEDOR=claude` y
`ANTHROPIC_API_KEY` se usa Claude. Para agregar otro proveedor basta un nuevo adapter con el
método `generar(instrucciones, consulta, contexto=None)` y registrarlo en `services/ia/__init__.py`.

## Despliegue con Docker (piloto)

`despliegue/` levanta todo el sistema en un solo servidor con Docker Compose:

```mermaid
flowchart LR
    U["Navegador / PWA"] -- "HTTPS 443" --> C["Caddy<br/>certificado automático"]
    C --> F["frontend<br/>Flask + gunicorn"]
    F -- "red interna" --> B["backend<br/>FastAPI"]
    B --> D[("PostgreSQL 16<br/>volumen datos_db")]
```

- **Caddy** obtiene y renueva solo el certificado HTTPS (Let's Encrypt) y redirige HTTP a HTTPS.
  HTTPS es obligatorio: sin él no funcionan en el teléfono la PWA, la cámara del escáner ni la
  ubicación del campo.
- Solo Caddy publica puertos (80 y 443). La API y la base quedan en la red interna de Docker.
- Los datos viven en el volumen `datos_db`; `docker compose down` no los borra (`down -v` sí).

### Poner en marcha un servidor

Sirve cualquier servidor Linux con Docker (por ejemplo una instancia EC2 en `sa-east-1`, que es
el paso previo a la arquitectura objetivo con ECS y RDS descrita arriba).

1. Apuntar el dominio (registro DNS `A`) a la IP pública del servidor y abrir los puertos 80 y 443.
2. Clonar los dos repositorios uno al lado del otro:
   ```bash
   git clone https://github.com/scortes5/Backend-GPTI-G10.git
   git clone https://github.com/scortes5/Frontend-GPTI-G10.git
   ```
3. Configurar y levantar:
   ```bash
   cd Backend-GPTI-G10/despliegue
   cp .env.example .env     # DOMINIO, claves (ver comentarios), ADMIN_EMAIL y ADMIN_CLAVE
   docker compose up -d --build
   ```
4. Abrir `https://<DOMINIO>` e iniciar sesión con `ADMIN_EMAIL` y `ADMIN_CLAVE`.

**Importante:** los QR llevan la dirección `https://<DOMINIO>/Trazabilidad?codigo=...`. Define el
dominio definitivo antes de imprimir etiquetas.

Para probar en el computador basta `DOMINIO=localhost`: Caddy usa un certificado local que el
navegador marca como no confiable (se puede aceptar para la prueba).

### Operación

```bash
docker compose ps                         # estado y chequeos de salud
docker compose logs -f backend frontend   # registros
git pull && docker compose up -d --build  # actualizar a la última versión
docker compose exec -T db pg_dump -U agrotracker agrotracker > respaldo-$(date +%F).sql   # respaldo
docker compose exec -T db psql -U agrotracker agrotracker < respaldo.sql                  # restaurar
```

Las tablas se crean solas al iniciar la API. Cambios de columnas en tablas existentes requieren
una migración (pendiente: Alembic).

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS/Linux
pip install -r requirements.txt
cp .env.example .env
```

## Correr

```bash
uvicorn app.main:app --reload
```

Docs interactivas en http://localhost:8000/docs

## Tests

```bash
pytest
```

## Correo

`CORREO_PROVEEDOR=simulado` (por defecto) no envía nada: deja el correo completo en el log de la API,
incluidos los códigos de recuperación de contraseña. Sirve para desarrollo; **en producción usar `smtp`**.
Con `CORREO_PROVEEDOR=smtp` se usa cualquier servidor SMTP (`SMTP_HOST`, `SMTP_PUERTO`,
`SMTP_USUARIO`, `SMTP_CLAVE`); con Gmail se necesita una contraseña de aplicación.

## Base de datos

Local se usa SQLite. Para Postgres basta `DATABASE_URL=postgresql://usuario:clave@host/db`
(también acepta `postgres://`); se normaliza al driver `psycopg` en `app/db.py`.
