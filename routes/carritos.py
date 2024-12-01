from flask import Blueprint, request, jsonify, redirect, url_for
from models.db import db
from pymongo import MongoClient

carritos_bp = Blueprint('carritos', __name__)

client = MongoClient("mongodb://localhost:27017/")
db = client['TiendaAlpaca']

@carritos_bp.route('/carrito/<usuario>/crear', methods=['POST'])
def crear_carrito(usuario):
    # Verificar si ya existe un carrito para este usuario
    carrito = db.carritos.find_one({"usuario": usuario})
    if carrito:
        return jsonify({"mensaje": "El carrito ya existe"}), 400

    # Crear el carrito
    nuevo_carrito = {
        "usuario": usuario,
        "productos": [],
        "total": 0.00
    }
    db.carritos.insert_one(nuevo_carrito)

    return jsonify({"mensaje": "Carrito creado exitosamente"}), 201

@carritos_bp.route('/carrito/<usuario>/agregar', methods=['POST'])
def agregar_producto(usuario):
    # Obtener los datos del formulario
    producto_id = request.form["producto_id"]
    cantidad = int(request.form["cantidad"])

    # Obtener el producto desde la colección de productos
    producto = db.productos.find_one({"_id": producto_id})
    if not producto:
        return jsonify({"mensaje": "Producto no encontrado"}), 404

    # Buscar el carrito del usuario
    carrito = db.carritos.find_one({"usuario": usuario})
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
    db.carritos.update_one({"usuario": usuario}, {"$set": {"productos": carrito["productos"], "total": carrito["total"]}})

    return redirect(url_for('carritos.ver_carrito', usuario=usuario))

# Ver el carrito
@carritos_bp.route('/carrito/<usuario>', methods=['GET'])
def ver_carrito(usuario):
    carrito = db.carritos.find_one({"usuario": usuario})
    if not carrito:
        return jsonify({"mensaje": "El carrito no existe"}), 404

    # Convertir ObjectId a string si es necesario
    for producto in carrito["productos"]:
        if "_id" in producto:
            producto["_id"] = str(producto["_id"])  # Convertir _id de ObjectId a string

    if "_id" in carrito:
        carrito["_id"] = str(carrito["_id"])  # Si necesitas convertir el _id del carrito también

    return jsonify(carrito)


# Quitar un producto del carrito
@carritos_bp.route('/carrito/<usuario>/quitar', methods=['DELETE'])
def quitar_producto(usuario):
    datos = request.json
    producto_id = datos["producto_id"]

    # Buscar el carrito del usuario
    carrito = db.carritos.find_one({"usuario": usuario})
    if not carrito:
        return jsonify({"mensaje": "El carrito no existe"}), 404

    # Eliminar el producto del carrito
    carrito["productos"] = [p for p in carrito["productos"] if p["producto_id"] != producto_id]

    # Actualizar el total
    carrito["total"] = sum(p.get("subtotal", 0) for p in carrito["productos"])  # Usar .get() para evitar KeyError
    db.carritos.update_one({"usuario": usuario}, {"$set": carrito})
    return jsonify({"mensaje": "Producto eliminado del carrito"}), 200

# Vaciar el carrito
@carritos_bp.route('/carrito/<usuario>/vaciar', methods=['DELETE'])
def vaciar_carrito(usuario):
    db.carritos.update_one({"usuario": usuario}, {"$set": {"productos": [], "total": 0.00}})
    return jsonify({"mensaje": "Carrito vaciado"}), 200