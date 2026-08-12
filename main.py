from fastapi import FastAPI  #se importa la libreria FastAPI

app=FastAPI() #Se crea una instancia de la clase FastAPI (se crea un objeto de la clase FastAPI)

@app.get("/") #Se crea la funcion para cuando se haga una peticion GET a la ruta raiz ("/")

def raiz(): #funcion que FASTAPI ejecutara cuando se haga una peticion GET a la ruta raiz ("/")
    return {"message": "Probando el reload"} #Se retorna un diccionario con un mensaje de bienvenida