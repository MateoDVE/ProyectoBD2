from flask import Flask, request, jsonify, Response, render_template, redirect, url_for, session
from flask_pymongo import PyMongo
from bson import json_util
from bson.objectid import ObjectId
import random

app = Flask(__name__)
app.config['MONGO_URI'] = "mongodb://localhost:27017/TiendaAlpaca"
mongo = PyMongo(app)

app.secret_key = '123'

# Ruta principal
@app.route('/')
def index():
    products = mongo.db.Products.find()
    return render_template('index.html', products=products)

@app.route('/pago_exitoso')
def pago_exitoso():
    return render_template('pago_exitoso.html')

@app.route('/viewProducts')
def viewProducts():
    products = mongo.db.Products.find()
    return render_template('productos.html', products=products)

# CLIENTES (CRUD)
@app.route('/Clients', methods=['POST'])
def create_client():
    try:
        username = request.json['username']
        email = request.json['email']
        address = request.json['address']
        credit_card = request.json['credit_card']

        if username and email and address and credit_card:
            id = mongo.db.Clients.insert_one(
                {'username': username, 'email': email, 'address': address, 'credit_card': credit_card}
            )
            response = {
                'id': str(id),
                'username': username,
                'email': email,
                'address': address,
                'credit_card': credit_card
            }
            return response
        else:
            return not_found()
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/Clients', methods=['GET'])
def get_clients():
    try:
        clients = mongo.db.Clients.find()
        response = json_util.dumps(clients)
        return Response(response, mimetype="application/json")
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/Clients/<id>', methods=['GET'])
def get_client(id):
    try:
        client = mongo.db.Clients.find_one({'_id': ObjectId(id)})
        response = json_util.dumps(client)
        return Response(response, mimetype="application/json")
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# CATEGORÍAS
@app.route('/Category', methods=['POST'])
def create_category():
    try:
        name = request.json['name']
        description = request.json['description']

        if name and description:
            id = mongo.db.Category.insert_one({'name': name, 'description': description})
            response = {
                'id': str(id),
                'name': name,
                'description': description
            }
            return response
        else:
            return not_found()
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/Category', methods=['GET'])
def get_categories():
    try:
        categories = mongo.db.Category.find()
        response = json_util.dumps(categories)
        return Response(response, mimetype="application/json")
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# PRODUCTOS
@app.route('/Product', methods=['POST'])
def create_product():
    try:
        name = request.json['name']
        description = request.json['description']
        category_id = request.json['category_id']
        price = request.json['price']
        material = request.json['material']
        gender = request.json['gender']
        sizes = request.json['sizes']
        colors = request.json['colors']
        stock = request.json['stock']

        category_id = ObjectId(category_id)

        if name and description and price and category_id and material:
            id = mongo.db.Products.insert_one(
                {
                    'name': name, 'description': description, 'category_id': category_id,
                    'price': price, 'material': material, 'gender': gender, 'sizes': sizes,
                    'colors': colors, 'stock': stock
                }
            )
            response = {
                'id': str(id),
                'name': name,
                'description': description,
                'category_id': str(category_id),
                'price': price,
                'material': material,
                'gender': gender,
                'sizes': sizes,
                'colors': colors,
                'stock': stock
            }
            return response
        else:
            return not_found()
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/Products', methods=['GET'])
def get_products():
    try:
        products = mongo.db.Products.aggregate(
            [
                {
                    '$lookup': {
                        'from': 'Category',
                        'localField': 'category_id',
                        'foreignField': '_id',
                        'as': 'category'
                    }
                },
                {
                    '$unwind': '$category'
                }
            ]
        )
        response = json_util.dumps(products)
        return Response(response, mimetype="application/json")
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# CARRITO
@app.route('/add_to_cart/<product_id>', methods=['POST'])
def add_to_cart(product_id):
    product = mongo.db.Products.find_one({"_id": ObjectId(product_id)})
    cart_item = {
        'id': str(product['_id']),
        'name': product['name'],
        'price': float(product['price']),
        'image': product.get('image', '')  # Imagen opcional
    }

    if 'cart' not in session:
        session['cart'] = []

    session['cart'].append(cart_item)
    session.modified = True
    return redirect(url_for('view_cart'))

@app.route('/cart')
def view_cart():
    cart = session.get('cart', [])
    total = sum(item['price'] for item in cart)
    return render_template('carrito.html', cart=cart, total=total)

@app.route('/remove_from_cart/<product_id>', methods=['POST'])
def remove_from_cart(product_id):
    cart = session.get('cart', [])
    cart = [item for item in cart if item['id'] != product_id]
    session['cart'] = cart
    session.modified = True
    return redirect(url_for('view_cart'))
@app.route('/checkout', methods=['GET', 'POST'])
def checkout():
    # Si el método es POST, procesamos el pago
    if request.method == 'POST':
        # Simulamos la aprobación o rechazo del pago
        payment_successful = random.random() < 0.8  # 80% de probabilidad de que el pago sea exitoso
        
        # Obtener los detalles del pago
        payment_method = request.form['payment_method']
        address = request.form['address']

        if payment_method == 'credit_card':
            card_number = request.form['card_number']
        else:
            paypal_email = request.form['paypal_email']

        # Obtener el carrito y el total
        cart = session.get('cart', [])
        total = sum(item['price'] for item in cart)

        # Si el pago fue exitoso, guardamos el pedido en la base de datos
        if payment_successful:
            # Simulación de guardar el pedido en la base de datos
            order = {
                'client_id': session.get('client_id'),  # Suponemos que el client_id está en la sesión
                'items': cart,
                'total': total,
                'payment_status': 'Aprobado',
                'payment_method': payment_method,
                'shipping_address': address,
            }
            mongo.db.Orders.insert_one(order)
            session['cart'] = []  # Vaciar el carrito después de la compra exitosa
            return render_template('pago_exitoso.html', total=total)
        else:
            return render_template('pago_fallido.html', total=total)

    # Si es GET, mostramos el formulario de checkout
    cart = session.get('cart', [])
    total = sum(item['price'] for item in cart)
    return render_template('checkout.html', total=total)
# Error 404
@app.errorhandler(404)
def not_found(error=None):
    response = jsonify({
        'message': 'Resource Not Found: ' + request.url,
        'status': 404
    })
    response.status_code = 404
    return response

if __name__ == "__main__":
    app.run(debug=True)

