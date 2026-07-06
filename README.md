# Gestor de Proyectos — producto white-label

Tablero de seguimiento a proyectos con **login, usuarios y roles**, listo para
**venderse a distintos clientes**. Cada cliente se rebrandea (nombre, colores,
logo) cambiando unas variables — sin tocar el código.

Backend Flask + SQLAlchemy. Corre en SQLite (local) o PostgreSQL (nube) con la
misma base de código.

> Marca demo por defecto: **Star Médica**. Es solo el ejemplo; se cambia con variables.

---

## Rebrandear para un cliente (lo que lo hace vendible)

No edites el código. Define estas variables de entorno por cliente:

| Variable             | Ejemplo                        | Qué controla              |
|----------------------|--------------------------------|---------------------------|
| `MARCA_NOMBRE`       | `Clínica del Valle`            | Nombre del cliente        |
| `MARCA_PRODUCTO`     | `Gestor de Proyectos`         | Nombre del producto       |
| `MARCA_TAGLINE`      | `SEGUIMIENTO A PROYECTOS`      | Subtítulo del header      |
| `MARCA_COLOR`        | `#7A1FA2`                      | Color primario            |
| `MARCA_COLOR_OSCURO` | `#4A0F6B`                      | Color oscuro (header)     |
| `MARCA_ACENTO`       | `#00A9A5`                      | Color de acento           |
| `MARCA_HEADER`       | `#5B6169`                      | Barra superior (gris)     |
| `MARCA_HEADER_2`     | `#3C4147`                      | Barra superior (oscuro)   |
| `MARCA_LOGO`         | `/static/img/logo.png`         | Logo (fondos claros)      |
| `MARCA_LOGO_HEADER`  | `/static/img/logo-blanco.png`  | Logo blanco (barra gris)  |

Sin variables, arranca con la marca demo. El logo por defecto es una estrella
genérica en los colores de la marca; pásale el logo oficial del cliente en `MARCA_LOGO`.

---

## Roles

| Rol      | Ve | Crea/edita proyectos | Comenta | Administra usuarios |
|----------|:--:|:--------------------:|:-------:|:-------------------:|
| `lector` | ✅ |          ❌          |   ✅    |         ❌          |
| `editor` | ✅ |          ✅          |   ✅    |         ❌          |
| `admin`  | ✅ |          ✅          |   ✅    |         ✅          |

Admin inicial: `admin@starmedica.mx` / `cambia123` (o define `ADMIN_EMAIL` /
`ADMIN_PASSWORD`). Cámbialo siempre.

### Librerías JS del tablero
Copia a `static/js/`: `xlsx.full.min.js`, `pptxgen.bundle.js`, `html2canvas.min.js`.

---

## Probar en tu PC (local, SQLite)

```bash
pip install -r requirements.txt
python app.py
```
`http://localhost:5000`. Se crea `data/tablero.db` solo.

Para ver la marca de un cliente al probar (Windows):
```bash
set MARCA_NOMBRE=Clínica del Valle
set MARCA_COLOR=#7A1FA2
python app.py
```

---

## Modelo de venta recomendado: una instancia por cliente

La forma más simple de empezar a vender: **un deploy independiente por cliente**.
Cada cliente = su propia app (Render) + su propia base de datos (Neon) + sus
variables de marca. Aislado, simple y barato.

(Más adelante, si crece, se puede evolucionar a multi-tenant — una sola app para
todos los clientes. Es más trabajo; no lo necesitas para empezar.)

### Publicar GRATIS por cliente (Render + Neon)
1. **Neon** (neon.tech): crea la base, copia la connection string `postgresql://...`
2. **Render** (render.com): New → Web Service → conecta el repo
   - Build: `pip install -r requirements.txt`
   - Start: `gunicorn app:app`
   - Instance: Free
3. **Variables** en Render: `DATABASE_URL`, `SECRET_KEY`, y las `MARCA_*` del cliente.
4. Render da la URL con HTTPS. Las tablas y el admin se crean solos.

Notas del plan gratis: la app se duerme a los 15 min (arranca en ~40 s; se quita
con ~$7/mes). Usa **Neon** para la base (permanente); no el Postgres gratis de
Render (caduca ~30 días).

---

## Antes de vender (checklist)
- [ ] Ponle nombre a TU producto en `MARCA_PRODUCTO` (aquí dice "Gestor de Proyectos").
- [ ] `SECRET_KEY` única por cliente.
- [ ] Contraseña admin cambiada.
- [ ] Logo oficial del cliente en `MARCA_LOGO`.
- [ ] Nunca subas `data/` a Git (ya está en `.gitignore`).
- [ ] Si el cliente maneja datos sensibles, valida cumplimiento antes de la nube.

---

## Crear el instalador de Windows (un clic para el cliente)

El objetivo: entregarle al cliente un **GestorProyectos-Setup.exe**. Lo abre,
da "Siguiente, Siguiente, Instalar", y le queda un acceso directo en el escritorio.
Al abrirlo, arranca solo y abre el navegador. **No necesita Python ni nada.**

> Nota: el `.exe` se construye EN WINDOWS (una vez por versión). Yo te dejé todos
> los archivos listos; solo corres los comandos en tu PC Windows.

### Paso 1 — Construir el ejecutable
En tu PC con Windows (con Python instalado desde python.org):
1. Copia las 3 librerías JS a `static/js/` (`xlsx.full.min.js`, `pptxgen.bundle.js`, `html2canvas.min.js`).
2. Doble clic a **`build.bat`** (o córrelo en la terminal).
3. Cuando termine, tendrás **`dist\GestorProyectos.exe`** (ya es funcional por sí solo).

### Paso 2 — Empaquetarlo en un instalador (opcional pero recomendado)
1. Instala **Inno Setup** (gratis): https://jrsoftware.org/isinfo.php
2. Abre **`instalador.iss`** con Inno Setup y presiona **Compile**.
3. Obtienes **`GestorProyectos-Setup.exe`** — ese es el que le mandas al cliente.

### Personalizar por cliente
Antes de compilar, edita **`config.env.ejemplo`** con la marca del cliente
(nombre, colores, logo, SECRET_KEY). El instalador lo copia como `config.env`
junto al programa. Para otro cliente: cambias el `config.env` y vuelves a compilar.

### Dónde quedan los datos
La base de datos se guarda en `%LOCALAPPDATA%\GestorProyectos\tablero.db`
(persiste entre reinicios; ahí haces respaldos). El programa puede estar en
Archivos de Programa sin problema.

### Alternativa sin construir .exe
Si solo quieres probarlo rápido en una PC con Python: doble clic a **`Iniciar.bat`**.
Instala lo necesario y arranca el servidor. (Esta opción sí requiere Python en esa PC.)

### Para que otros de la red entren
Mientras el programa esté abierto, otros en la misma red entran desde su navegador
a `http://IP-DE-LA-PC:5000`. Si no cargan, abre el puerto 5000 en el Firewall de Windows.
