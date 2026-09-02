from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import List, Optional
import psycopg2
from psycopg2.extras import RealDictCursor
from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv

load_dotenv()

# --- CONFIGURACIÓN ---
SECRET_KEY = os.getenv("SECRET_KEY", "mi_clave_super_secreta_cambia_esto_en_produccion")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

app = FastAPI()
def inicializar_bd():
    conn = get_db_connection()
    cur = conn.cursor()
    # Crear tablas si no existen
    cur.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id SERIAL PRIMARY KEY,
            nombre_usuario VARCHAR(50) UNIQUE NOT NULL,
            password_hash VARCHAR(255) NOT NULL
        );
    """)
    # Crear tabla de tareas
    cur.execute("""
        CREATE TABLE IF NOT EXISTS tareas (
            id SERIAL PRIMARY KEY,
            titulo VARCHAR(100) NOT NULL,
            descripcion TEXT,
            usuario_id INTEGER REFERENCES usuarios(id) ON DELETE CASCADE
        );
    """)
    conn.commit()
    cur.close()
    conn.close()
    print("Base de datos inicializada correctamente.")
inicializar_bd()

security = HTTPBearer()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# --- CONEXIÓN A BD ---
def get_db_connection():
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        return psycopg2.connect(database_url, sslmode='require')
    else:
        return psycopg2.connect(
            host="localhost",
            database="mi_backend_db",
            user="postgres",
            password="Coyot35Tlx",  # ¡CAMBIA ESTA CONTRASEÑA POR LA TUYA!
            port="5432"
        )

# --- FUNCIONES DE SEGURIDAD ---
def verificar_contraseña(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def encriptar_contraseña(password):
    return pwd_context.hash(password)

def crear_token_acceso(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def obtener_usuario_actual(credenciales: HTTPAuthorizationCredentials = Depends(security)):
    token = credenciales.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        usuario_id = payload.get("sub")
        if usuario_id is None:
            raise HTTPException(status_code=401, detail="Token inválido")
    except JWTError:
        raise HTTPException(status_code=401, detail="Token inválido o expirado")
    
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SELECT * FROM usuarios WHERE id = %s;", (usuario_id,))
    usuario = cur.fetchone()
    cur.close()
    conn.close()
    if not usuario:
        raise HTTPException(status_code=401, detail="Usuario no encontrado")
    return usuario

# --- MODELOS ---
class TareaCreate(BaseModel):
    titulo: str
    descripcion: Optional[str] = None

class Tarea(TareaCreate):
    id: int
    usuario_id: int

class TareaUpdate(BaseModel):
    titulo: Optional[str] = None
    descripcion: Optional[str] = None

class UsuarioCreate(BaseModel):
    nombre_usuario: str
    password: str

class UsuarioLogin(BaseModel):
    nombre_usuario: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

# --- ENDPOINTS ---
@app.post("/registro", response_model=Token)
def registrar_usuario(usuario: UsuarioCreate):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM usuarios WHERE nombre_usuario = %s;", (usuario.nombre_usuario,))
    if cur.fetchone():
        cur.close()
        conn.close()
        raise HTTPException(status_code=400, detail="El usuario ya existe")
    hashed = encriptar_contraseña(usuario.password)
    cur.execute("INSERT INTO usuarios (nombre_usuario, password_hash) VALUES (%s, %s) RETURNING id;", (usuario.nombre_usuario, hashed))
    nuevo_id = cur.fetchone()[0]
    conn.commit()
    cur.close()
    conn.close()
    token = crear_token_acceso({"sub": str(nuevo_id)})
    return {"access_token": token, "token_type": "bearer"}

@app.post("/login", response_model=Token)
def login(usuario: UsuarioLogin):
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SELECT * FROM usuarios WHERE nombre_usuario = %s;", (usuario.nombre_usuario,))
    usuario_db = cur.fetchone()
    cur.close()
    conn.close()
    if not usuario_db or not verificar_contraseña(usuario.password, usuario_db["password_hash"]):
        raise HTTPException(status_code=401, detail="Credenciales incorrectas")
    token = crear_token_acceso({"sub": str(usuario_db["id"])})
    return {"access_token": token, "token_type": "bearer"}

@app.post("/tareas/", response_model=Tarea)
def crear_tarea(tarea: TareaCreate, usuario_actual: dict = Depends(obtener_usuario_actual)):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("INSERT INTO tareas (titulo, descripcion, usuario_id) VALUES (%s, %s, %s) RETURNING id;", (tarea.titulo, tarea.descripcion, usuario_actual["id"]))
    nuevo_id = cur.fetchone()[0]
    conn.commit()
    cur.close()
    conn.close()
    return Tarea(id=nuevo_id, titulo=tarea.titulo, descripcion=tarea.descripcion, usuario_id=usuario_actual["id"])

@app.get("/tareas/", response_model=List[Tarea])
def listar_tareas(usuario_actual: dict = Depends(obtener_usuario_actual)):
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SELECT * FROM tareas WHERE usuario_id = %s ORDER BY id;", (usuario_actual["id"],))
    tareas = cur.fetchall()
    cur.close()
    conn.close()
    return tareas

@app.get("/tareas/{tarea_id}", response_model=Tarea)
def obtener_tarea(tarea_id: int, usuario_actual: dict = Depends(obtener_usuario_actual)):
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SELECT * FROM tareas WHERE id = %s AND usuario_id = %s;", (tarea_id, usuario_actual["id"]))
    tarea = cur.fetchone()
    cur.close()
    conn.close()
    if not tarea:
        raise HTTPException(status_code=404, detail="Tarea no encontrada o no te pertenece")
    return tarea

@app.put("/tareas/{tarea_id}", response_model=Tarea)
def actualizar_tarea(tarea_id: int, tarea_actualizada: TareaUpdate, usuario_actual: dict = Depends(obtener_usuario_actual)):
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SELECT * FROM tareas WHERE id = %s AND usuario_id = %s;", (tarea_id, usuario_actual["id"]))
    tarea_existente = cur.fetchone()
    if not tarea_existente:
        cur.close()
        conn.close()
        raise HTTPException(status_code=404, detail="Tarea no encontrada o no te pertenece")
    campos = []
    valores = []
    if tarea_actualizada.titulo is not None:
        campos.append("titulo = %s")
        valores.append(tarea_actualizada.titulo)
    if tarea_actualizada.descripcion is not None:
        campos.append("descripcion = %s")
        valores.append(tarea_actualizada.descripcion)
    if not campos:
        cur.close()
        conn.close()
        return tarea_existente
    valores.append(tarea_id)
    query = f"UPDATE tareas SET {', '.join(campos)} WHERE id = %s RETURNING *;"
    cur.execute(query, tuple(valores))
    tarea_actualizada_db = cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()
    return tarea_actualizada_db

@app.delete("/tareas/{tarea_id}")
def eliminar_tarea(tarea_id: int, usuario_actual: dict = Depends(obtener_usuario_actual)):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM tareas WHERE id = %s AND usuario_id = %s;", (tarea_id, usuario_actual["id"]))
    if not cur.fetchone():
        cur.close()
        conn.close()
        raise HTTPException(status_code=404, detail="Tarea no encontrada o no te pertenece")
    cur.execute("DELETE FROM tareas WHERE id = %s;", (tarea_id,))
    conn.commit()
    cur.close()
    conn.close()
    return {"mensaje": f"Tarea {tarea_id} eliminada"}