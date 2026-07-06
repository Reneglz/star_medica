"""
════════════════════════════════════════════════════════════════════════
  TABLERO DE PROYECTOS · Star Médica  —  backend Flask (SQLAlchemy)
  Login + usuarios + roles (RBAC) + API de proyectos.

  ► Un solo código, dos bases de datos:
      · Local  -> SQLite  (no defines nada, usa data/tablero.db)
      · Nube   -> PostgreSQL (defines la variable DATABASE_URL, ej. Neon)
    SQLAlchemy se encarga de las diferencias entre ambas.

  Roles:  admin > editor > lector
════════════════════════════════════════════════════════════════════════
"""
import os, sys, json
from datetime import datetime
from functools import wraps

from flask import (Flask, request, jsonify, render_template, redirect,
                   url_for, flash, abort)
from flask_login import (LoginManager, UserMixin, login_user, logout_user,
                         login_required, current_user)
from werkzeug.security import generate_password_hash, check_password_hash

from sqlalchemy import (create_engine, Column, Integer, String, Text, Boolean,
                        DateTime, select)
from sqlalchemy.orm import declarative_base, sessionmaker, scoped_session

# ── Rutas (funciona igual como script o como .exe empaquetado) ─────────────
CONGELADO = getattr(sys, "frozen", False)   # True cuando corre como .exe (PyInstaller)


def app_home():
    """Carpeta donde vive la app (junto al .exe, o la del código fuente)."""
    if CONGELADO:
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def recurso(rel):
    """Ruta a archivos empaquetados (templates/static). PyInstaller los extrae a _MEIPASS."""
    base = getattr(sys, "_MEIPASS", app_home())
    return os.path.join(base, rel)


def data_dir():
    """Carpeta ESCRIBIBLE para la base de datos (persiste entre reinicios)."""
    if CONGELADO and os.name == "nt":
        # En Windows instalado: %LOCALAPPDATA%\GestorProyectos
        base = os.path.join(os.environ.get("LOCALAPPDATA", app_home()), "GestorProyectos")
    else:
        base = os.path.join(app_home(), "data")
    os.makedirs(base, exist_ok=True)
    return base


def cargar_config_env():
    """Lee un archivo config.env (KEY=VALUE) junto a la app, sin dependencias externas.
       Las variables del sistema tienen prioridad sobre el archivo."""
    ruta = os.path.join(app_home(), "config.env")
    if not os.path.exists(ruta):
        return
    for linea in open(ruta, encoding="utf-8"):
        linea = linea.strip()
        if not linea or linea.startswith("#") or "=" not in linea:
            continue
        clave, valor = linea.split("=", 1)
        os.environ.setdefault(clave.strip(), valor.strip())


cargar_config_env()   # cargar marca/secretos del cliente antes de todo

# ── Configuración ───────────────────────────────────────────────────────
app = Flask(__name__,
            template_folder=recurso("templates"),
            static_folder=recurso("static"))
app.secret_key = os.environ.get("SECRET_KEY", "dev-cambia-esto-en-produccion")

# ── Marca (white-label) ───────────────────────────────────────────────────
# Cada cliente al que le vendas define estas variables de entorno.
# Sin variables, arranca con la marca demo (Star Médica).
def get_marca():
    primario = os.environ.get("MARCA_COLOR", "#059CDB")          # cyan de la presentación
    oscuro   = os.environ.get("MARCA_COLOR_OSCURO", "#0479A8")   # cyan oscuro
    acento   = os.environ.get("MARCA_ACENTO", "#00B050")         # verde de la presentación
    return {
        "nombre":          os.environ.get("MARCA_NOMBRE", "Star Médica"),
        "producto":        os.environ.get("MARCA_PRODUCTO", "Gestor de Proyectos"),
        "tagline":         os.environ.get("MARCA_TAGLINE", "SEGUIMIENTO A PROYECTOS"),
        "primario":        primario,
        "primario_oscuro": oscuro,
        "acento":          acento,
        "header":          os.environ.get("MARCA_HEADER", "#6C7075"),    # barra superior (gris)
        "header2":         os.environ.get("MARCA_HEADER_2", "#484B4F"),  # gris oscuro
        # Logo para fondos claros (login) y versión blanca para la barra gris (header)
        "logo":            os.environ.get("MARCA_LOGO", "/static/img/logo_star_medica.png"),
        "logo_header":    (os.environ.get("MARCA_LOGO_HEADER")
                           or os.environ.get("MARCA_LOGO")
                           or "/static/img/logo_star_medica_blanco.png"),
        # Imagen difuminada en la parte superior del login (vacío = sin imagen)
        "banner":          os.environ.get("MARCA_BANNER", "/static/img/hospital.jpg"),
    }


@app.context_processor
def _inyectar_marca():
    """Deja 'marca' y 'marca_json' disponibles en todas las plantillas."""
    m = get_marca()
    return {"marca": m, "marca_json": json.dumps(m)}

# ── Conexión a la base de datos (SQLite local / PostgreSQL en la nube) ────
DATABASE_URL = os.environ.get("DATABASE_URL", "").strip()
# Algunos proveedores dan el esquema viejo "postgres://"; SQLAlchemy quiere "postgresql://"
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

if DATABASE_URL:                                   # → PostgreSQL (Neon, Render, etc.)
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)
else:                                              # → SQLite local
    engine = create_engine(
        "sqlite:///" + os.path.join(data_dir(), "tablero.db"),
        connect_args={"check_same_thread": False})

Base    = declarative_base()
Session = scoped_session(sessionmaker(bind=engine, expire_on_commit=False))


@app.teardown_appcontext
def _limpiar_sesion(exc=None):
    Session.remove()


# ════════════════════════════════════════════════════════════════════════
#  MODELOS
# ════════════════════════════════════════════════════════════════════════
class Usuario(Base, UserMixin):
    __tablename__ = "usuarios"
    id            = Column(Integer, primary_key=True)
    nombre        = Column(String(120), nullable=False)
    email         = Column(String(160), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    rol           = Column(String(20), default="lector")
    area          = Column(String(80), default="")
    activo        = Column(Boolean, default=True)
    creado        = Column(DateTime, default=datetime.now)

    @property                       # Flask-Login: usuarios desactivados no entran
    def is_active(self):
        return bool(self.activo)


class Proyecto(Base):
    __tablename__ = "proyectos"
    id           = Column(Integer, primary_key=True)
    nombre       = Column(String(200), nullable=False)
    tipo         = Column(String(60), default="")
    prioridad    = Column(String(20), default="media")
    fecha_inicio = Column(String(10))
    fecha_fin    = Column(String(10))
    avance       = Column(Integer, default=0)
    estado       = Column(String(30), default="planeado")
    color        = Column(String(20), default="#0B7FC4")
    descripcion  = Column(Text, default="")
    depende_de   = Column(Integer)
    responsables = Column(Text, default="[]")   # JSON
    tareas       = Column(Text, default="[]")   # JSON
    comentarios  = Column(Text, default="[]")   # JSON
    owner_id     = Column(Integer)
    area         = Column(String(80), default="")
    creado       = Column(DateTime, default=datetime.now)
    actualizado  = Column(DateTime, default=datetime.now)

    def to_dict(self):
        """Devuelve el proyecto con el shape que espera el front (JSON ya parseado)."""
        return {
            "id": self.id, "nombre": self.nombre, "tipo": self.tipo,
            "prioridad": self.prioridad, "fecha_inicio": self.fecha_inicio,
            "fecha_fin": self.fecha_fin, "avance": self.avance,
            "estado": self.estado, "color": self.color,
            "descripcion": self.descripcion, "depende_de": self.depende_de,
            "responsables": json.loads(self.responsables or "[]"),
            "tareas": json.loads(self.tareas or "[]"),
            "comentarios": json.loads(self.comentarios or "[]"),
            "area": self.area, "owner_id": self.owner_id,
        }


class Notificacion(Base):
    __tablename__ = "notificaciones"
    id      = Column(Integer, primary_key=True)
    para_id = Column(Integer, nullable=False)
    de      = Column(String(120), default="")
    asunto  = Column(String(200), default="")
    mensaje = Column(Text, default="")
    leida   = Column(Boolean, default=False)
    creada  = Column(DateTime, default=datetime.now)

    def to_dict(self):
        return {"id": self.id, "de": self.de, "asunto": self.asunto,
                "mensaje": self.mensaje, "leida": self.leida,
                "creada": self.creada.isoformat() if self.creada else None}


class Contador(Base):
    """Genera IDs enteros para tareas/subtareas (que viven dentro de JSON)."""
    __tablename__ = "contador"
    nombre = Column(String(30), primary_key=True)
    valor  = Column(Integer, default=0)


def siguiente_id(nombre):
    c = Session.get(Contador, nombre)
    if c is None:
        c = Contador(nombre=nombre, valor=0)
        Session.add(c)
    c.valor += 1
    Session.commit()
    return c.valor


# ════════════════════════════════════════════════════════════════════════
#  INICIALIZACIÓN  (crea tablas + admin inicial)
# ════════════════════════════════════════════════════════════════════════
def init_db():
    Base.metadata.create_all(engine)
    if Session.scalar(select(Usuario).limit(1)) is None:
        email = os.environ.get("ADMIN_EMAIL", "admin@starmedica.mx")
        pwd   = os.environ.get("ADMIN_PASSWORD", "cambia123")
        Session.add(Usuario(nombre="Administrador", email=email,
                            password_hash=generate_password_hash(pwd),
                            rol="admin", area="Dirección", activo=True))
        Session.commit()
        print("\n" + "═" * 58)
        print("  Usuario admin creado:")
        print(f"    email:    {email}")
        print(f"    password: {pwd}   (CÁMBIALO al entrar)")
        print("═" * 58 + "\n")
    Session.remove()


# ════════════════════════════════════════════════════════════════════════
#  AUTENTICACIÓN
# ════════════════════════════════════════════════════════════════════════
login_manager = LoginManager(app)
login_manager.login_view = "login"
login_manager.login_message = "Inicia sesión para continuar."
RANGO = {"lector": 1, "editor": 2, "admin": 3}


@login_manager.user_loader
def cargar_usuario(uid):
    return Session.get(Usuario, int(uid))


def rol_minimo(rol):
    """Decorador RBAC: exige al menos cierto nivel de rol."""
    def deco(fn):
        @wraps(fn)
        @login_required
        def wrapper(*a, **kw):
            if RANGO.get(current_user.rol, 0) < RANGO[rol]:
                if request.path.startswith("/api/"):
                    return jsonify(error="No tienes permiso para esta acción"), 403
                abort(403)
            return fn(*a, **kw)
        return wrapper
    return deco


@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        pwd   = request.form.get("password", "")
        u = Session.scalar(select(Usuario).where(Usuario.email == email))
        if u and u.activo and check_password_hash(u.password_hash, pwd):
            login_user(u, remember=True)
            return redirect(request.args.get("next") or url_for("dashboard"))
        flash("Correo o contraseña incorrectos (o usuario desactivado).")
    return render_template("login.html")


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))


# ════════════════════════════════════════════════════════════════════════
#  PÁGINAS
# ════════════════════════════════════════════════════════════════════════
@app.route("/")
@login_required
def dashboard():
    return render_template("proyectos.html",
                           rol=current_user.rol, nombre=current_user.nombre)


@app.route("/menu")
@login_required
def menu():
    return redirect(url_for("dashboard"))


@app.route("/usuarios")
@rol_minimo("admin")
def usuarios():
    filas = Session.scalars(select(Usuario).order_by(Usuario.creado.desc())).all()
    return render_template("usuarios.html", usuarios=filas, nombre=current_user.nombre)


@app.route("/usuarios/crear", methods=["POST"])
@rol_minimo("admin")
def crear_usuario():
    f = request.form
    nombre = f.get("nombre", "").strip()
    email  = f.get("email", "").strip().lower()
    pwd    = f.get("password", "")
    rol    = f.get("rol", "lector")
    if not (nombre and email and pwd):
        flash("Nombre, correo y contraseña son obligatorios.")
    elif rol not in RANGO:
        flash("Rol inválido.")
    elif Session.scalar(select(Usuario).where(Usuario.email == email)):
        flash("Ese correo ya está registrado.")
    else:
        Session.add(Usuario(nombre=nombre, email=email,
                            password_hash=generate_password_hash(pwd),
                            rol=rol, area=f.get("area", "").strip(), activo=True))
        Session.commit()
        flash(f"Usuario «{nombre}» creado como {rol}.")
    return redirect(url_for("usuarios"))


@app.route("/usuarios/<int:uid>/rol", methods=["POST"])
@rol_minimo("admin")
def cambiar_rol(uid):
    rol = request.form.get("rol", "lector")
    u = Session.get(Usuario, uid)
    if u and rol in RANGO:
        u.rol = rol
        Session.commit()
    return redirect(url_for("usuarios"))


@app.route("/usuarios/<int:uid>/activo", methods=["POST"])
@rol_minimo("admin")
def toggle_activo(uid):
    if uid == current_user.id:
        flash("No puedes desactivarte a ti mismo.")
        return redirect(url_for("usuarios"))
    u = Session.get(Usuario, uid)
    if u:
        u.activo = not u.activo
        Session.commit()
    return redirect(url_for("usuarios"))


@app.route("/usuarios/<int:uid>/password", methods=["POST"])
@rol_minimo("admin")
def resetear_password(uid):
    nueva = request.form.get("password", "")
    u = Session.get(Usuario, uid)
    if u and len(nueva) >= 4:
        u.password_hash = generate_password_hash(nueva)
        Session.commit()
        flash("Contraseña actualizada.")
    else:
        flash("La contraseña debe tener al menos 4 caracteres.")
    return redirect(url_for("usuarios"))


@app.route("/admin/cargar-checklist")
@rol_minimo("admin")
def cargar_checklist_route():
    """Carga única del Checklist 200 (15 proyectos con sus tareas).
       Inserta proyecto por proyecto y hace commit en cada uno, para no
       agotar la memoria del plan gratis (512 MB). Es idempotente."""
    try:
        from seed_checklist import CHECKLIST
    except Exception as e:
        return f"No encontré seed_checklist.py: {e}", 500
    creados = tareas_tot = saltados = 0
    for area in CHECKLIST:
        try:
            if Session.scalar(select(Proyecto.id).where(Proyecto.nombre == area["nombre"]).limit(1)):
                saltados += 1
                continue
            tareas = [{
                "id": siguiente_id("tarea"), "nombre": nt, "descripcion": "",
                "responsables": [], "fecha_inicio": area["fecha_inicio"],
                "fecha_fin": area["fecha_fin"], "avance": 0, "estado": "planeado",
                "prioridad": "media", "subtareas": []} for nt in area["tareas"]]
            Session.add(Proyecto(
                nombre=area["nombre"], tipo="general", prioridad="alta", estado="en_curso",
                color=area["color"], descripcion=area.get("descripcion", ""),
                fecha_inicio=area["fecha_inicio"], fecha_fin=area["fecha_fin"],
                responsables="[]", tareas=json.dumps(tareas), comentarios="[]",
                owner_id=current_user.id, area=area["nombre"]))
            Session.commit()          # commit por proyecto (libera memoria)
            Session.expunge_all()     # suelta objetos de la memoria de sesión
            creados += 1
            tareas_tot += len(tareas)
        except Exception:
            Session.rollback()        # si uno falla, sigue con los demás
    return (
        "<div style='font-family:sans-serif;max-width:480px;margin:60px auto;text-align:center'>"
        "<h2 style='color:#059CDB'>✅ Checklist 200 cargado</h2>"
        f"<p style='font-size:16px'>Proyectos creados: <b>{creados}</b><br>"
        f"Tareas creadas: <b>{tareas_tot}</b>"
        + (f"<br>Ya existían (saltados): <b>{saltados}</b>" if saltados else "")
        + "</p><a href='/' style='display:inline-block;margin-top:16px;padding:12px 24px;"
        "background:#059CDB;color:#fff;text-decoration:none;border-radius:8px;font-weight:700'>"
        "← Ir al tablero</a></div>")


# ════════════════════════════════════════════════════════════════════════
#  API DE PROYECTOS
# ════════════════════════════════════════════════════════════════════════
def _filtrar_visibles(proyectos):
    """Hook de visibilidad por área (row-level security). v1: todos ven todo.
       Para restringir por área, descomenta:
         if current_user.rol != 'admin':
             return [p for p in proyectos if p.area == current_user.area]
    """
    return proyectos


@app.get("/api/proyectos")
@login_required
def api_listar():
    ps = Session.scalars(select(Proyecto).order_by(Proyecto.id.desc())).all()
    return jsonify([p.to_dict() for p in _filtrar_visibles(ps)])


@app.get("/api/proyectos/usuarios")
@login_required
def api_usuarios():
    us = Session.scalars(
        select(Usuario).where(Usuario.activo == True).order_by(Usuario.nombre)).all()
    return jsonify([{"id": u.id, "nombre": u.nombre, "email": u.email,
                     "rol": u.rol, "area": u.area} for u in us])


@app.post("/api/proyectos")
@rol_minimo("editor")
def api_crear():
    d = request.get_json(force=True) or {}
    if not d.get("nombre"):
        return jsonify(error="El nombre es obligatorio"), 400
    p = Proyecto(
        nombre=d.get("nombre"), tipo=d.get("tipo", ""),
        prioridad=d.get("prioridad", "media"), fecha_inicio=d.get("fecha_inicio"),
        fecha_fin=d.get("fecha_fin"), avance=int(d.get("avance") or 0),
        estado=d.get("estado", "planeado"), color=d.get("color", "#0B7FC4"),
        descripcion=d.get("descripcion", ""), depende_de=d.get("depende_de"),
        responsables=json.dumps(d.get("responsables", [])),
        tareas="[]", comentarios="[]",
        owner_id=current_user.id, area=current_user.area)
    Session.add(p)
    Session.commit()
    return jsonify(p.to_dict())


@app.put("/api/proyectos/<int:pid>")
@rol_minimo("editor")
def api_editar(pid):
    p = Session.get(Proyecto, pid)
    if not p:
        return jsonify(error="Proyecto no encontrado"), 404
    d = request.get_json(force=True) or {}
    p.nombre       = d.get("nombre", p.nombre)
    p.tipo         = d.get("tipo", "")
    p.prioridad    = d.get("prioridad", "media")
    p.fecha_inicio = d.get("fecha_inicio")
    p.fecha_fin    = d.get("fecha_fin")
    p.avance       = int(d.get("avance") or 0)
    p.estado       = d.get("estado", "planeado")
    p.color        = d.get("color", "#0B7FC4")
    p.descripcion  = d.get("descripcion", "")
    p.depende_de   = d.get("depende_de")
    p.responsables = json.dumps(d.get("responsables", []))
    p.actualizado  = datetime.now()
    Session.commit()
    return jsonify(p.to_dict())


@app.delete("/api/proyectos/<int:pid>")
@rol_minimo("editor")
def api_borrar(pid):
    p = Session.get(Proyecto, pid)
    if p:
        Session.delete(p)
        Session.commit()
    return jsonify(ok=True)


# ── Tareas y subtareas (viven como JSON dentro del proyecto) ──────────────
def _guardar_tareas(p, tareas):
    p.tareas = json.dumps(tareas)
    p.actualizado = datetime.now()
    Session.commit()


def _localizar_tarea(tid):
    """Devuelve (proyecto, lista_tareas, indice) o (None, None, None)."""
    for p in Session.scalars(select(Proyecto)).all():
        tareas = json.loads(p.tareas or "[]")
        for i, t in enumerate(tareas):
            if t.get("id") == tid:
                return p, tareas, i
    return None, None, None


def _localizar_subtarea(sid):
    for p in Session.scalars(select(Proyecto)).all():
        tareas = json.loads(p.tareas or "[]")
        for t in tareas:
            for j, s in enumerate(t.get("subtareas", [])):
                if s.get("id") == sid:
                    return p, tareas, t, j
    return None, None, None, None


@app.post("/api/proyectos/<int:pid>/tareas")
@rol_minimo("editor")
def api_crear_tarea(pid):
    p = Session.get(Proyecto, pid)
    if not p:
        return jsonify(error="Proyecto no encontrado"), 404
    d = request.get_json(force=True) or {}
    tareas = json.loads(p.tareas or "[]")
    tareas.append({
        "id": siguiente_id("tarea"),
        "nombre": d.get("nombre", ""), "descripcion": d.get("descripcion", ""),
        "responsables": d.get("responsables", []),
        "fecha_inicio": d.get("fecha_inicio"), "fecha_fin": d.get("fecha_fin"),
        "avance": int(d.get("avance") or 0), "estado": d.get("estado", "planeado"),
        "prioridad": d.get("prioridad", "media"), "subtareas": []})
    _guardar_tareas(p, tareas)
    return jsonify(p.to_dict())


@app.put("/api/proyectos/tareas/<int:tid>")
@rol_minimo("editor")
def api_editar_tarea(tid):
    p, tareas, i = _localizar_tarea(tid)
    if p is None:
        return jsonify(error="Tarea no encontrada"), 404
    d = request.get_json(force=True) or {}
    tareas[i].update({k: d[k] for k in
                      ("nombre", "descripcion", "responsables", "fecha_inicio",
                       "fecha_fin", "avance", "estado", "prioridad") if k in d})
    _guardar_tareas(p, tareas)
    return jsonify(p.to_dict())


@app.delete("/api/proyectos/tareas/<int:tid>")
@rol_minimo("editor")
def api_borrar_tarea(tid):
    p, tareas, i = _localizar_tarea(tid)
    if p is None:
        return jsonify(error="Tarea no encontrada"), 404
    tareas.pop(i)
    _guardar_tareas(p, tareas)
    return jsonify(p.to_dict())


@app.post("/api/proyectos/tareas/<int:tid>/subtareas")
@rol_minimo("editor")
def api_crear_subtarea(tid):
    p, tareas, i = _localizar_tarea(tid)
    if p is None:
        return jsonify(error="Tarea no encontrada"), 404
    d = request.get_json(force=True) or {}
    tareas[i].setdefault("subtareas", []).append({
        "id": siguiente_id("subtarea"),
        "nombre": d.get("nombre", ""), "descripcion": d.get("descripcion", ""),
        "responsables": d.get("responsables", []),
        "fecha_inicio": d.get("fecha_inicio"), "fecha_fin": d.get("fecha_fin"),
        "avance": int(d.get("avance") or 0), "estado": d.get("estado", "planeado"),
        "prioridad": d.get("prioridad", "media")})
    _guardar_tareas(p, tareas)
    return jsonify(p.to_dict())


@app.put("/api/proyectos/subtareas/<int:sid>")
@rol_minimo("editor")
def api_editar_subtarea(sid):
    p, tareas, t, j = _localizar_subtarea(sid)
    if p is None:
        return jsonify(error="Subtarea no encontrada"), 404
    d = request.get_json(force=True) or {}
    t["subtareas"][j].update({k: d[k] for k in
                              ("nombre", "descripcion", "responsables", "fecha_inicio",
                               "fecha_fin", "avance", "estado", "prioridad") if k in d})
    _guardar_tareas(p, tareas)
    return jsonify(p.to_dict())


@app.delete("/api/proyectos/subtareas/<int:sid>")
@rol_minimo("editor")
def api_borrar_subtarea(sid):
    p, tareas, t, j = _localizar_subtarea(sid)
    if p is None:
        return jsonify(error="Subtarea no encontrada"), 404
    t["subtareas"].pop(j)
    _guardar_tareas(p, tareas)
    return jsonify(p.to_dict())


# ── Comentarios ───────────────────────────────────────────────────────────
@app.post("/api/proyectos/<int:pid>/comentarios")
@login_required
def api_comentar(pid):
    p = Session.get(Proyecto, pid)
    if not p:
        return jsonify(error="Proyecto no encontrado"), 404
    texto = (request.get_json(force=True) or {}).get("texto", "").strip()
    if not texto:
        return jsonify(error="Comentario vacío"), 400
    coms = json.loads(p.comentarios or "[]")
    coms.append({"id": siguiente_id("comentario"),
                 "autor": current_user.nombre, "autor_id": current_user.id,
                 "texto": texto, "fecha": datetime.now().isoformat()})
    p.comentarios = json.dumps(coms)
    Session.commit()
    return jsonify(p.to_dict())


# ── Notificaciones ─────────────────────────────────────────────────────────
@app.get("/api/proyectos/notificaciones")
@login_required
def api_notif_listar():
    ns = Session.scalars(
        select(Notificacion).where(Notificacion.para_id == current_user.id)
        .order_by(Notificacion.id.desc())).all()
    return jsonify([n.to_dict() for n in ns])


@app.post("/api/proyectos/notificaciones")
@login_required
def api_notif_crear():
    d = request.get_json(force=True) or {}
    destinos = d.get("destinatarios") or d.get("para") or []
    if isinstance(destinos, int):
        destinos = [destinos]
    for uid in destinos:
        Session.add(Notificacion(para_id=uid, de=current_user.nombre,
                                asunto=d.get("asunto", ""), mensaje=d.get("mensaje", "")))
    Session.commit()
    return jsonify(ok=True, enviadas=len(destinos))


@app.post("/api/proyectos/notificaciones/leer")
@login_required
def api_notif_leer():
    ids = (request.get_json(force=True) or {}).get("ids")
    q = select(Notificacion).where(Notificacion.para_id == current_user.id)
    if ids:
        q = q.where(Notificacion.id.in_(ids))
    for n in Session.scalars(q).all():
        n.leida = True
    Session.commit()
    return jsonify(ok=True)


# ════════════════════════════════════════════════════════════════════════
init_db()   # crea tablas y admin al arrancar (sirve para gunicorn y flask run)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
