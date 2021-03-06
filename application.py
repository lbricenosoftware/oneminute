from flask import Flask, render_template, request, session, redirect
from flask_session import Session
import re
import os
from werkzeug.security import generate_password_hash, check_password_hash
import pymongo

EMAIL_REGEX = re.compile(r"[^@]+@[^@]+\.[^@]+")
ROLES = ['estudiante', 'profesor']

app = Flask(__name__)
# El nombre del usuario y la clave de la base de datos se leen del sistema operativo
dbUser = os.environ['dbUser']
dbPass = os.environ['dbPass']
# Debe escribir el link a su cluster de MongoDB Atlas
client = pymongo.MongoClient(f"mongodb+srv://{dbUser}:{dbPass}@cluster0.twnzg.mongodb.net/oneminute?retryWrites=true&w=majority")
db = client.oneminute


app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

@app.route("/")
def index():
    # Si la sesión no ha sido iniciada
    if  not session.get("correo") or not session.get("nombre"):
        return redirect("/login")
    else:
        return render_template("index.html", correo = session["correo"], nombre = session["nombre"])

@app.route("/login", methods=["POST", "GET"])
def login():
    if request.method == "GET":
        # Si la sesión ya fue iniciada
        if  session.get("correo") and session.get("nombre"):
            return redirect("/")
        else:
            return render_template("login.html")
    else:
        # Se debe validar que se hayan ingresado los datos necesarios. En caso de que haya un error se va construyendo un mensaje de error
        msgError = ""
        loginData = {}
        # con este primer if se revisa si en el formulario viene el campo email.
        if "correo" in request.form:
            #Luego se guarda en un diccionario, pero antes se le quitan los espacios del inicio y del final con el método strip
            loginData["correo"] = request.form.get("correo").strip()
        else:
            msgError = "Debe ingresar un correo"
        # Se repite lo mismo para el apellido
        if "clave" in request.form:
            loginData["clave"] = request.form.get("clave")
        else:
            msgError = "Debe ingresar la contraseña"

        if msgError != "":
            return render_template("login.html", msg = msgError)
        else:
            # Ahora debemos verificar si el usuario existe en la base de datos con la clave correspondiente
            usuario = db.usuarios.find_one({"correo":loginData["correo"]})
            # Si se obtuvo algún usurio que tenga el correo ingresado
            if usuario:
                # Se verifica si tiene el campo clave
                if "clave" in usuario:
                    # Luego se revisa si la clave coincide con la ingresada por el usuario
                    if check_password_hash(usuario["clave"], loginData["clave"]):
                        # Se guarda en la sesión el correo del usuario, eso nos permitirá ver si la sesión fue iniciada
                        session["correo"] = loginData["correo"]
                        if "nombres" in usuario:
                            session["nombre"] = usuario["nombres"].split()[0]
                        else:
                            session["nombre"] = "Anónimo"
                        return redirect("/")
            # Si se llega hasta este punto es que la autenticación falló
            msgError += "Correo o clave erradas"
            return render_template("login.html", msg = msgError)

@app.route("/logout", methods=["POST", "GET"])
def logout():
    session["correo"] = None
    session["nombre"] = None
    return redirect("/login")

@app.route("/register", methods=["POST", "GET"])
def register():
    if request.method == "GET":
        return render_template("register.html")
    else:
        # Se debe validar que se hayan ingresado los datos necesarios. En caso de que haya un error se va construyendo un mensaje de error
        msgError = ""
        nuevoUsuario = {}
        print(request.form)
        # con este primer if se revisa si en el formulario viene el campo nombres.
        if "nombres" in request.form:
            #Luego se guarda en un diccionario, pero antes se le quitan los espacios del inicio y del final con el método strip
            nuevoUsuario["nombres"] = request.form.get("nombres").strip()
            # Ahora se revisa si el nombre es vacío ""
            if not nuevoUsuario["nombres"]:
                msgError += "Debe ingresar un nombre válido. "
        # Se repite lo mismo para el apellido
        if "apellidos" in request.form:
            nuevoUsuario["apellidos"] = request.form.get("apellidos").strip()
            if not nuevoUsuario["apellidos"]:
                msgError += "Debe ingresar un apellido válido. "
        # Se repite para el correo
        if "correo" in request.form:
            nuevoUsuario["correo"] = request.form.get("correo").strip()
            if not nuevoUsuario["correo"]:
                # Si el correo es vacío
                msgError += "Debe ingresar un correo válido. "
            elif not EMAIL_REGEX.match(nuevoUsuario["correo"]):
                # Si el correo no tiene un arroba y un punto
                msgError += "Debe ingresar un correo válido. "
        # Se obtienen los roles
        if "rol" in request.form:
            nuevoUsuario["roles"] = [request.form.get("rol").strip()]
            if nuevoUsuario["roles"][0] not in ROLES:
                # Si el rol ingresado no hace parte de los roles
                msgError += "Debe ingresar un rol válido. "
            # Si el rol es profesor se le añade también el de estudiante automaticamente
            elif nuevoUsuario["roles"][0] == ROLES[1]:
                nuevoUsuario["roles"].append(ROLES[0])
        # Ahora para la contraseña
        if "clave" in request.form:
            nuevoUsuario["clave"] = request.form.get("clave")
            if not nuevoUsuario["clave"]:
                msgError += "Debe ingresar una contraseña válida. "
            else:
                if "confClave" in request.form:
                # Se debe revisar que coincidan
                    if nuevoUsuario["clave"] != request.form.get("confClave"):
                        msgError += "Las dos contraseñas deben coincidir. "
        # Se revisa si hubo algún error
        if msgError != "":
            return render_template("register.html", msg=msgError)
        else:
            #Ahora se debe añadir el usuario a la base de datos, pero antes de eso se debe hacer el hash de la contraseña
            nuevoUsuario["clave"] = generate_password_hash(nuevoUsuario["clave"])
            try:
                result = db.usuarios.insert_one(nuevoUsuario)
            except pymongo.errors.DuplicateKeyError:
                msgError += "El correo ingresado no está disponible"
                return render_template("register.html", msg=msgError)
            return render_template("index.html", user = nuevoUsuario, result = result)
if __name__ == '__main__':
      app.run(host='0.0.0.0', port=5500)