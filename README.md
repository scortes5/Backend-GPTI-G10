# Backend AgroTracker · GPTI G10

API (FastAPI) del sistema de trazabilidad y gestión de cosecha para la Cooperativa Newen al Sur.

- **Fase 1:** registro de lotes/cosechas, código QR por lote, historial.
- **Fase 2:** clima del campo con la Red Agroclimática Nacional (Agromet), alertas climáticas,
  recomendaciones IA. Integración Instacrops pendiente de contrato.

## Arquitectura

> Propuesta de arquitectura objetivo en AWS. Aún no está implementada; sirve de base para el
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
        GEM["GeminiAdapter<br/>(por implementar)"]
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
  routers/           # endpoints por módulo (solo HTTP)
  services/          # casos de uso y clientes externos
    ia/              # patrón Adapter: puerto ProveedorIA + adapters Claude/simulado
    correo/          # patrón Adapter: puerto ServicioCorreo + adapters SMTP/simulado
tests/
```

## Endpoints

| Método | Ruta | Descripción |
|---|---|---|
| POST | `/auth/login` | Inicia sesión y entrega un token (público) |
| GET | `/auth/yo` | Usuario de la sesión |
| POST | `/auth/logout` | Cierra la sesión: el token queda revocado |
| POST | `/auth/recuperar` | Envía por correo un código de 6 dígitos (público, misma respuesta exista o no el correo) |
| POST | `/auth/restablecer` | Cambia la contraseña con el código (público) |
| GET | `/publico/lotes/{codigo}` | Ficha de origen del lote, sin ventas (público, destino del QR) |
| GET/POST | `/lotes` | Listar / registrar lotes |
| GET/PATCH/DELETE | `/lotes/{codigo}` | Ver, editar o eliminar un lote |
| GET | `/lotes/{codigo}/qr` | Código QR del lote |
| GET/POST | `/lotes/{codigo}/ventas` | Ventas del lote |
| GET | `/lotes/{codigo}/trazabilidad` | Lote + ventas + kilos e ingresos |
| GET | `/lotes/{codigo}/recomendacion` | Recomendación agronómica con IA |
| POST | `/lotes/{codigo}/reporte` | Envía por correo el reporte de trazabilidad (CSV de ventas adjunto) |
| GET/PUT | `/campo` | Ubicación del campo propio (admin: `?usuario_id=` para ver otro) |
| GET | `/campos` | Campos registrados (solo admin) |
| GET | `/clima` | Clima del campo: estación Agromet más cercana, últimas 48 h y alertas |
| GET | `/clima/recomendacion` | Qué tomar en consideración según el clima y la bodega (IA) |
| GET | `/dashboard/resumen` | Indicadores (de la cooperativa o del productor) |
| GET/POST | `/usuarios` | Listar / crear usuarios (solo admin) |
| PATCH | `/usuarios/{id}` | Cambiar rol o activar/desactivar (solo admin) |

Salvo los marcados como públicos, los endpoints exigen `Authorization: Bearer <token>` (401 sin sesión).

**Roles** (sección 5 del documento de requerimientos):

- **Administrador** (directiva de la cooperativa): ve y gestiona todos los lotes, elimina lotes, gestiona usuarios y usa Instacrops.
- **Productor** (socio): registra lotes a su nombre y solo ve, edita y vende sus propios lotes; el dashboard muestra solo sus cifras. Lo que no le corresponde responde **403**.

El primer administrador se crea al iniciar la API con `ADMIN_EMAIL` y `ADMIN_CLAVE` (mínimo 12
caracteres, solo en tu `.env`) si la base no tiene usuarios.

Las reglas de negocio que no se cumplen responden **409** (p. ej. vender más kilos de los disponibles).

## Clima (Agromet)

Cada usuario registra la ubicación de su campo (`PUT /campo`). `GET /clima` busca la estación más
cercana de la **Red Agroclimática Nacional** (catastro de 417 estaciones en
`app/data/estaciones_agromet.json`), trae sus lecturas horarias de las últimas 48 h y calcula:

- **Resumen de 24 h:** mínima, máxima, lluvia, humedad media y viento máximo.
- **Alertas por reglas** (`services/clima/analisis.py`): helada (≤ 0 °C) y riesgo de helada (≤ 3 °C),
  calor (≥ 32 °C), lluvia (≥ 5 mm / ≥ 20 mm), viento (≥ 40 km/h), condiciones para hongos
  (humedad ≥ 85 % con 10-25 °C), datos atrasados y estación lejana (> 30 km).
- `GET /clima/recomendacion` entrega todo eso, más la cosecha en bodega, al `ProveedorIA`.

La fuente de datos es un puerto (`ProveedorClima`) con dos adapters, elegidos con `CLIMA_PROVEEDOR`:

- `simulado` (por defecto): datos plausibles para la latitud y la época, sin red.
- `agromet`: usa `getGraphData.php` de agromet.cl, el servicio que alimenta los gráficos del
  portal (el mismo que usa el paquete abierto agrometR), con caché de 15 minutos.
  **Agromet no publica una API documentada y hoy su firewall bloquea clientes automáticos (HTTP
  403)**: antes de activarlo hay que pedir acceso a la red (info@agromet.cl). Si cambian el formato,
  basta ajustar `services/clima/agromet.py`.

## IA

`IA_PROVEEDOR=simulado` (por defecto) no usa red ni API key. Con `IA_PROVEEDOR=claude` y
`ANTHROPIC_API_KEY` se usa Claude. Para agregar otro proveedor basta un nuevo adapter con el
método `generar(instrucciones, consulta)` y registrarlo en `services/ia/__init__.py`.

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
