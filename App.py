from flask import Flask, render_template, redirect, url_for, flash, request, session
import mysql.connector
from flask_bcrypt import Bcrypt

app = Flask(__name__)
app.secret_key = 'your_secret_key'
bcrypt = Bcrypt(app)

# Database configuration
db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': 'pritsql',
    'database': 'myapp'
}

def get_db_connection():
    return mysql.connector.connect(**db_config)

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        role = request.form['role']
        name = request.form['name']
        password = request.form['password']
        address = request.form['address']
        phone_number = request.form['phone_number']
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')

        connection = get_db_connection()
        cursor = connection.cursor()

        if role == 'user':
            # User signup
            query = "INSERT INTO users (name, password, address, phone_number) VALUES (%s, %s, %s, %s)"
            try:
                cursor.execute(query, (name, hashed_password, address, phone_number))
                connection.commit()
                flash("User account created successfully! Please log in.")
            except mysql.connector.IntegrityError:
                flash("Username already exists, please choose a different one.")
                return redirect(url_for('signup'))

        elif role == 'admin':
            # Admin signup with restaurant details
            restaurant_name = request.form['restaurant_name']
            restaurant_location = request.form['restaurant_location']
            restaurant_description = request.form['restaurant_description']
            restaurant_category = request.form['restaurant_category']

            # Insert admin details into the admins table
            query = """INSERT INTO admins (name, password, address, phone_number, restaurant_name, restaurant_location,
                       restaurant_description, restaurant_category) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"""
            try:
                cursor.execute(query, (name, hashed_password, address, phone_number, restaurant_name,
                                       restaurant_location, restaurant_description, restaurant_category))
                admin_id = cursor.lastrowid
                connection.commit()
                
                # Insert restaurant details into the restaurants table
                restaurant_query = """INSERT INTO restaurants (admin_id, restaurant_name, restaurant_location, 
                                       restaurant_description, restaurant_category) VALUES (%s, %s, %s, %s, %s)"""
                cursor.execute(restaurant_query, (admin_id, restaurant_name, restaurant_location,
                                                  restaurant_description, restaurant_category))
                connection.commit()

                # Dynamically create a table for the restaurant to store food items
                create_table_query = f"""
                CREATE TABLE `{restaurant_name}` (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    food_item_name VARCHAR(100) NOT NULL,
                    cuisine VARCHAR(50),
                    price FLOAT(7,2) NOT NULL,
                    description VARCHAR(200)
                )"""
                cursor.execute(create_table_query)
                connection.commit()
                
                flash("Admin account and restaurant created successfully! Please log in.")
                
            except mysql.connector.IntegrityError:
                flash("Username or restaurant name already exists, please choose a different one.")
                return redirect(url_for('signup'))
        
        cursor.close()
        connection.close()
        return redirect(url_for('login'))

    return render_template('signup.html')


@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        role = request.form['role']
        name = request.form['name']
        password = request.form['password']

        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        if role == 'user':
            query = "SELECT * FROM users WHERE name = %s"
        elif role == 'admin':
            query = "SELECT * FROM admins WHERE name = %s"
        else:
            flash("Invalid role selected")
            return redirect(url_for('login'))

        cursor.execute(query, (name,))
        user = cursor.fetchone()
        cursor.close()
        connection.close()

        if user and bcrypt.check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['user_role'] = role
            session['username'] = user['name']
            session['restaurant_name'] = user.get('restaurant_name') if role == 'admin' else None

            flash(f"Logged in as {role.capitalize()} successfully!")
            if role == 'admin':
                return redirect(url_for('admin_dashboard'))
            else:
                return redirect(url_for('user_dashboard'))
        else:
            flash("Invalid username or password")
            return redirect(url_for('login'))

    return render_template('login.html')

@app.route('/user_dashboard')
def user_dashboard():
    if 'user_id' not in session or session.get('user_role') != 'user':
        flash("Access denied. Users only.")
        return redirect(url_for('login'))

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    # Fetch all restaurants from the restaurants table
    query = "SELECT * FROM restaurants"
    cursor.execute(query)
    restaurants = cursor.fetchall()

    cursor.close()
    connection.close()

    return render_template('user_dashboard.html', restaurants=restaurants)

@app.route('/view_restaurant/<string:restaurant_name>')
def view_restaurant(restaurant_name):
    if 'user_id' not in session or session.get('user_role') != 'user':
        flash("Access denied. Users only.")
        return redirect(url_for('login'))

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    # Fetch all food items from the specified restaurant's table
    query = f"SELECT * FROM `{restaurant_name}`"
    cursor.execute(query)
    food_items = cursor.fetchall()

    cursor.close()
    connection.close()

    return render_template('restaurant_menu.html', restaurant_name=restaurant_name, food_items=food_items)

@app.route('/add_to_cart', methods=['POST'])
def add_to_cart():
    if 'user_id' not in session or session.get('user_role') != 'user':
        flash("Access denied. Users only.")
        return redirect(url_for('login'))

    user_id = session['user_id']
    user_name = session['username']
    food_item = request.form['food_item']
    quantity = int(request.form.get('quantity', 1))
    price = float(request.form['price'])

    connection = get_db_connection()
    cursor = connection.cursor()

    # Check if cart table exists, if not, create it
    cursor.execute("SHOW TABLES LIKE 'cart'")
    result = cursor.fetchone()
    if not result:
        create_cart_table = """
        CREATE TABLE cart (
            order_id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT NOT NULL,
            user_name VARCHAR(100) NOT NULL,
            food_item VARCHAR(100) NOT NULL,
            quantity INT NOT NULL,
            price FLOAT(7,2) NOT NULL
        )
        """
        cursor.execute(create_cart_table)

    # Check if the food item is already in the cart
    check_item_query = "SELECT * FROM cart WHERE user_id = %s AND food_item = %s"
    cursor.execute(check_item_query, (user_id, food_item))
    item = cursor.fetchone()

    if item:
        # If item exists, update quantity
        new_quantity = item[4] + quantity
        update_query = "UPDATE cart SET quantity = %s WHERE user_id = %s AND food_item = %s"
        cursor.execute(update_query, (new_quantity, user_id, food_item))
    else:
        # Insert new item into the cart
        insert_query = "INSERT INTO cart (user_id, user_name, food_item, quantity, price) VALUES (%s, %s, %s, %s, %s)"
        cursor.execute(insert_query, (user_id, user_name, food_item, quantity, price))

    connection.commit()
    cursor.close()
    connection.close()

    flash(f"{food_item} added to cart.")
    return redirect(url_for('view_restaurant', restaurant_name=request.form['restaurant_name']))

@app.route('/remove_from_cart', methods=['POST'])
def remove_from_cart():
    if 'user_id' not in session or session.get('user_role') != 'user':
        flash("Access denied. Users only.")
        return redirect(url_for('login'))

    user_id = session['user_id']
    food_item = request.form['food_item']

    connection = get_db_connection()
    cursor = connection.cursor()

    # Remove the item from the cart
    delete_query = "DELETE FROM cart WHERE user_id = %s AND food_item = %s"
    cursor.execute(delete_query, (user_id, food_item))

    connection.commit()

    # Check if the cart is empty after removing the item
    check_cart_empty_query = "SELECT COUNT(*) FROM cart WHERE user_id = %s"
    cursor.execute(check_cart_empty_query, (user_id,))
    cart_empty = cursor.fetchone()[0] == 0

    # If cart is empty, drop the cart table
    if cart_empty:
        cursor.execute("DROP TABLE IF EXISTS cart")

    cursor.close()
    connection.close()

    flash(f"{food_item} removed from cart.")
    return redirect(url_for('view_cart'))

@app.route('/view_cart')
def view_cart():
    if 'user_id' not in session or session.get('user_role') != 'user':
        flash("Access denied. Users only.")
        return redirect(url_for('login'))

    user_id = session['user_id']

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    # Fetch items from the cart for the logged-in user
    cursor.execute("SELECT * FROM cart WHERE user_id = %s", (user_id,))
    cart_items = cursor.fetchall()

    # Calculate total price
    total_price = sum(item['quantity'] * item['price'] for item in cart_items)

    cursor.close()
    connection.close()

    return render_template('cart.html', cart_items=cart_items, total_price=total_price)


@app.route('/admin_dashboard', methods=['GET', 'POST'])
def admin_dashboard():
    if 'user_id' not in session or session.get('user_role') != 'admin':
        flash("Access denied. Admins only.")
        return redirect(url_for('login'))

    restaurant_name = session.get('restaurant_name')  # Retrieve restaurant name from session
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    # Handle form submission for adding a new food item
    if request.method == 'POST':
        food_item_name = request.form['food_item_name']
        cuisine = request.form['cuisine']
        price = request.form['price']
        description = request.form['description']

        add_food_query = f"""INSERT INTO `{restaurant_name}` (food_item_name, cuisine, price, description)
                             VALUES (%s, %s, %s, %s)"""
        cursor.execute(add_food_query, (food_item_name, cuisine, price, description))
        connection.commit()
        flash("Food item added successfully!")

    # Fetch all food items from the restaurant's table
    fetch_food_query = f"SELECT * FROM `{restaurant_name}`"
    cursor.execute(fetch_food_query)
    food_items = cursor.fetchall()

    cursor.close()
    connection.close()

    return render_template('admin_dashboard.html', food_items=food_items, restaurant_name=restaurant_name)

@app.route('/delete_food/<int:food_id>', methods=['POST'])
def delete_food(food_id):
    if 'user_id' not in session or session.get('user_role') != 'admin':
        flash("Access denied. Admins only.")
        return redirect(url_for('login'))

    restaurant_name = session.get('restaurant_name')  # Retrieve restaurant name from session
    connection = get_db_connection()
    cursor = connection.cursor()

    # Delete the food item by ID
    delete_query = f"DELETE FROM `{restaurant_name}` WHERE id = %s"
    cursor.execute(delete_query, (food_id,))
    connection.commit()

    cursor.close()
    connection.close()

    flash("Food item deleted successfully!")
    return redirect(url_for('admin_dashboard'))

@app.route('/dashboard')
def dashboard():
    # Regular user dashboard logic (not for admins)
    if 'user_id' not in session:
        flash("Please log in first.")
        return redirect(url_for('login'))
    return render_template('dashboard.html', username=session.get('username'), role=session.get('user_role'))

@app.route('/logout')
def logout():
    session.clear()
    flash("You have been logged out.")
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
