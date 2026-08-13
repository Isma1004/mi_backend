from fastapi import FastAPI, HTTPException #fastapi es un framework para crear APIs en Python y HTTPException es una clase que se utiliza para manejar errores HTTP en FastAPI
from pydantic import BaseModel #BaseModel es una clase de Pydantic que se utiliza para definir modelos de datos y validación en FastAPI
from typing import List, Optional

app=FastAPI()

class TareaCreate(BaseModel): #clase que contiene para crear una tarea 
    titulo: str
    descripcion: Optional[str] = None

class Tarea(TareaCreate): #clase donde la API hereda de la clase TareaCreate y agrega un atributo adicional llamado id, que es un entero que representa el identificador único de la tarea.
    id: int

tareas_db = []  #base de datos simulada para almacenar las tareas
contador_id = 1

@app.post("/tareas/", response_model=Tarea) #cuando se hace una peticion POST a la ruta "/tareas/", se espera que se reciba un objeto JSON que cumpla con el modelo TareaCreate.
def crear_tarea(tarea: TareaCreate):
    global contador_id #se modifica la variable global contador_id para poder incrementar su valor y asignar un identificador único a cada nueva tarea creada.
    nueva_tarea = Tarea(id=contador_id, titulo=tarea.titulo, descripcion=tarea.descripcion) #se crea una nueva instancia de la clase Tarea utilizando los datos proporcionados en el objeto tarea recibido en la solicitud.
    tareas_db.append(nueva_tarea) #se añade la nueva tarea a la lista tareas_db, que simula una base de datos en memoria.
    contador_id += 1 #se  incrementa el valor de contador_id para que la próxima tarea creada tenga un identificador único diferente.
    return nueva_tarea #se devuelve la nueva tarea creada como respuesta a la solicitud POST, utilizando el modelo de respuesta Tarea para garantizar que se devuelvan los datos en el formato esperado.

#aqui se definen dos rutas GET para obtener la lista de tareas y una tarea específica por su ID. La primera ruta devuelve todas las tareas almacenadas en la base de datos simulada, mientras que la segunda ruta busca una tarea por su ID y devuelve un error 404 si no se encuentra.
@app.get("/tareas/", response_model=List[Tarea])
def listar_tareas():
    return tareas_db    


@app.get("/tareas/{tarea_id}", response_model=Tarea)
def obtener_tarea(tarea_id: int):
    for tarea in tareas_db:
        if tarea.id == tarea_id:
            return tarea
    raise HTTPException(status_code=404, detail="Tarea no encontrada")

#Modelo para actualizar una tarea existente. Permite modificar el título y la descripción de la tarea, ambos campos son opcionales.

class TareaUpdate(BaseModel):
    titulo: Optional[str]= None
    descripcion: Optional[str]= None

@app.put("/tareas/{tarea_id}", response_model=Tarea) #ruta PUT para actualizar una tarea existente. Recibe el ID de la tarea a actualizar y los datos de actualización en el cuerpo de la solicitud.

def actualizar_tarea(tarea_id: int, tarea_actualizada: TareaUpdate):
    for tarea in tareas_db:
        if tarea.id == tarea_id:
            if tarea_actualizada.titulo is not None:
                tarea.titulo = tarea_actualizada.titulo
            if tarea_actualizada.descripcion is not None:
                tarea.descripcion = tarea_actualizada.descripcion
            return tarea
    raise HTTPException(status_code=404, detail="Tarea no encontrada")

@app.delete("/tareas/{tarea_id}",response_model=Tarea) #ruta DELETE para eliminar una tarea existente. Recibe el ID de la tarea a eliminar y devuelve la tarea eliminada como respuesta.

def eliminar_tarea(tarea_id: int):
    for i, tarea in enumerate(tareas_db):
        if tarea.id == tarea_id:
            tareas_db.pop(i)
            return {"mensaje": f"Tarea {tarea_id} eliminada exitosamente"}
    raise HTTPException(status_code=404, detail="Tarea no encontrada")