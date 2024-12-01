from flask import Flask, render_template, jsonify, request, redirect, url_for
from pymongo import MongoClient
import uuid
from routes.productos import productos_bp
from routes.carritos import carritos_bp, crear_carrito  # Importa carritos antes de registrar el Blueprint

app = Flask(__name__)

# Conexión a MongoDB
client = MongoClient("mongodb://localhost:27017/")
db = client['TiendaAlpaca']

# Registrar los Blueprints
app.register_blueprint(productos_bp)
app.register_blueprint(carritos_bp)  # Registra carritos después de productos

# Ruta para el registro de usuario
@app.route('/registro', methods=['GET', 'POST'])
def registro():
    if request.method == 'POST':
        datos = request.form
        nombre = datos['nombre']
        email = datos['email']
        direccion = datos['direccion']
        telefono = datos['telefono']

        # Verificar si ya existe un usuario con ese email
        usuario_existente = db.usuarios.find_one({"email": email})
        if usuario_existente:
            return jsonify({"mensaje": "El usuario ya existe"}), 400

        # Crear el nuevo usuario
        nuevo_usuario = {
            "nombre": nombre,
            "email": email,
            "direccion": direccion,
            "telefono": telefono,
            "carrito_id": None  # Al principio no tendrá un carrito asociado
        }
        db.usuarios.insert_one(nuevo_usuario)

        return redirect(url_for('login'))  # Redirige a la página de login después del registro

    return render_template("registro.html")

# Ruta para login de usuario
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        datos = request.form
        email = datos['email']
        usuario = db.usuarios.find_one({"email": email})

        if not usuario:
            return jsonify({"mensaje": "Usuario no encontrado"}), 404

        # Si el usuario existe, asociamos el carrito con el usuario
        carrito = db.carritos.find_one({"usuario": usuario["_id"]})
        if not carrito:
            carrito = crear_carrito(usuario["_id"])

        # Redirigir al carrito del usuario
        return redirect(url_for('ver_carrito', usuario_id=usuario["_id"]))  # Cambié 'usuario' a 'usuario_id'

    return render_template("login.html")

@app.route("/")
def index():
    # Redirige al carrito si el usuario está logueado, de lo contrario, muestra las categorías
    usuario_id = request.cookies.get('usuario_id')  # Usando cookie, puede ser sesión también
    if usuario_id:
        return redirect(url_for('ver_carrito', usuario_id=usuario_id))

    categorias = list(db.categorias.find())
    return render_template("index.html", categorias=categorias)

@app.route("/productos/<categoria_id>")
def productos(categoria_id):
    productos = list(db.productos.find({"categoria": categoria_id}))
    return render_template("productos.html", productos=productos)

# Ruta para ver el carrito del usuario
@app.route('/carrito/<usuario_id>', methods=['GET'])
def ver_carrito(usuario_id):
    usuario = db.usuarios.find_one({"_id": usuario_id})
    if not usuario:
        return jsonify({"mensaje": "Usuario no encontrado"}), 404

    carrito = db.carritos.find_one({"usuario": usuario["_id"]})
    if not carrito:
        carrito = crear_carrito(usuario["_id"])

    return render_template("carrito.html", carrito=carrito, usuario=usuario)

@app.route('/carrito/<usuario_id>/quitar', methods=['POST'])
def quitar_producto(usuario_id):
    datos = request.form
    producto_id = datos["producto_id"]

    # Buscar el carrito del usuario
    carrito = db.carritos.find_one({"usuario": usuario_id})
    if not carrito:
        return jsonify({"mensaje": "El carrito no existe"}), 404

    # Eliminar el producto del carrito
    carrito["productos"] = [p for p in carrito["productos"] if p["producto_id"] != producto_id]

    # Actualizar el total
    carrito["total"] = sum(p.get("subtotal", 0) for p in carrito["productos"])
    db.carritos.update_one({"usuario": usuario_id}, {"$set": carrito})

    return redirect(url_for('ver_carrito', usuario_id=usuario_id))  # Redirigir al carrito actualizado

@app.route('/carrito/<usuario_id>/agregar', methods=['POST'])
def agregar_producto(usuario_id):
    # Obtener los datos del formulario
    producto_id = request.form["producto_id"]
    cantidad = int(request.form["cantidad"])

    # Obtener el producto desde la colección de productos
    producto = db.productos.find_one({"_id": producto_id})
    if not producto:
        return jsonify({"mensaje": "Producto no encontrado"}), 404

    # Buscar el carrito del usuario
    carrito = db.carritos.find_one({"usuario": usuario_id})
    if not carrito:
        return jsonify({"mensaje": "El carrito no existe"}), 404

    precio_unitario = producto.get("precio", 0)
    if precio_unitario == 0:
        return jsonify({"mensaje": "Producto sin precio disponible"}), 400

    # Verificar si el producto ya está en el carrito
    producto_en_carrito = False
    for p in carrito["productos"]:
        if p["producto_id"] == producto_id:
            # Si el producto ya está en el carrito, actualizamos la cantidad y el subtotal
            p["cantidad"] += cantidad
            p["subtotal"] = p["cantidad"] * precio_unitario
            producto_en_carrito = True
            break
    
    if not producto_en_carrito:
        # Si el producto no está en el carrito, lo añadimos
        carrito["productos"].append({
            "producto_id": producto_id,
            "nombre": producto["nombre"],
            "cantidad": cantidad,
            "precio": precio_unitario,
            "subtotal": cantidad * precio_unitario
        })

    # Actualizar el total del carrito
    carrito["total"] = sum(p.get("subtotal", 0) for p in carrito["productos"])

    # Actualizar el carrito en la base de datos
    db.carritos.update_one({"usuario": usuario_id}, {"$set": {"productos": carrito["productos"], "total": carrito["total"]}})

    return redirect(url_for('ver_carrito', usuario_id=usuario_id))

if __name__ == "__main__":
    app.run(debug=True)
