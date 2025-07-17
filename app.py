from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from flask_mail import Mail, Message
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
from flask_migrate import Migrate

import os
from PIL import Image
import pytesseract
import requests

# Flask app configuration
app = Flask(__name__)
app.secret_key = 'secretkey'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'uploads'
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# OpenFDA API URL
OPENFDA_URL = "https://api.fda.gov/drug/label.json"

# Initialize database
db = SQLAlchemy(app)
migrate = Migrate(app, db)

# Email configuration
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 465
app.config['MAIL_USE_SSL'] = True
app.config['MAIL_USERNAME'] = 'roshinirgowda@gmail.com'
app.config['MAIL_PASSWORD'] = 'gnqk yvlf qbsb xgkz'
app.config['MAIL_DEFAULT_SENDER'] = 'roshinirgowda@gmail.com'

# Initialize Flask-Mail
mail = Mail(app)

# Models
class Drug(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Float, nullable=False)
    expiry_date = db.Column(db.String(20), nullable=False)

class Invoice(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(100), nullable=False)
    extracted_text = db.Column(db.Text, nullable=False)

class Customer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    phone_number = db.Column(db.String(15), nullable=False)
    email = db.Column(db.String(100), nullable=False)
    medicines = db.Column(db.String(200), nullable=True)  # Store medicine names as a comma-separated string

# Initialize database
with app.app_context():
    db.create_all()

# Routes
@app.route('/')
def home():
    return render_template('home.html')

# Search medicines from OpenFDA API
@app.route('/search_medicine', methods=['GET'])
def search_medicine():
    query = request.args.get('query', '').strip()
    if not query:
        return jsonify([])
    try:
        response = requests.get(OPENFDA_URL, params={'search': f'openfda.brand_name:{query}', 'limit': 10})
        if response.status_code == 200:
            results = response.json()
            medicines = [
                item['openfda']['brand_name'][0]
                for item in results.get('results', [])
                if 'openfda' in item and 'brand_name' in item['openfda']
            ]
            return jsonify(medicines)
        else:
            return jsonify({'error': 'Failed to fetch medicines from OpenFDA.'})
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({'error': 'An error occurred while fetching medicines.'})

# Add new stock
@app.route('/add_stock', methods=['GET', 'POST'])
def add_stock():
    if request.method == 'POST':
        name = request.form['medicine']
        quantity = request.form['quantity']
        price = request.form['price']
        expiry_date = request.form['expiry_date']
        new_drug = Drug(name=name, quantity=quantity, price=price, expiry_date=expiry_date)
        db.session.add(new_drug)
        db.session.commit()
        flash('Stock added successfully!', 'success')
        return redirect(url_for('view_stock'))
    return render_template('add_stock.html')

# Update stock
@app.route('/update_stock/<int:id>', methods=['GET', 'POST'])
def update_stock(id):
    drug = Drug.query.get_or_404(id)
    if request.method == 'POST':
        try:
            drug.name = request.form['medicine']
            drug.quantity = int(request.form['quantity'])
            drug.price = float(request.form['price'])
            drug.expiry_date = request.form['expiry_date']
            db.session.commit()
            flash('Stock updated successfully!', 'success')
            return redirect(url_for('view_stock'))
        except Exception as e:
            flash(f'Error updating stock: {e}', 'danger')
    return render_template('update_stock.html', drug=drug)

# View stock
@app.route('/view_stock', methods=['GET'])
def view_stock():
    drugs = Drug.query.all()
    return render_template('view_stock.html', drugs=drugs)
# Delete stock
@app.route('/delete_stock/<int:id>', methods=['GET'])
def delete_stock(id):
    drug = Drug.query.get_or_404(id)  # Fetch the drug by ID or return a 404 error if not found
    db.session.delete(drug)  # Delete the drug from the database
    db.session.commit()  # Commit the changes to the database
    flash('Stock deleted successfully!', 'success')  # Flash a success message
    return redirect(url_for('view_stock'))  # Redirect to the view stock page

# Add customer
@app.route('/add_customer', methods=['GET', 'POST'])
def add_customer():
    if request.method == 'POST':
        name = request.form['name']
        phone_number = request.form['phone_number']
        email = request.form['email']
        medicines = request.form.getlist('medicines')  # Assuming you have a form to select medicines
        new_customer = Customer(name=name, phone_number=phone_number, email=email, medicines=', '.join(medicines))
        db.session.add(new_customer)
        db.session.commit()
        flash('Customer added successfully!', 'success')
        return redirect(url_for('view_customers'))
    return render_template('add_customer.html')

# View customers
@app.route('/view_customers', methods=['GET'])
def view_customers():
    customers = Customer.query.all()
    return render_template('view_customers.html', customers=customers)

# Update customer
@app.route('/update_customer/<int:id>', methods=['GET', 'POST'])
def update_customer(id):
    customer = Customer.query.get_or_404(id)
    if request.method == 'POST':
        customer.name = request.form['name']
        customer.phone_number = request.form['phone_number']
        customer.email = request.form['email']
        medicines = request.form.getlist('medicines')  # Assuming you have a form to select medicines
        customer.medicines = ', '.join(medicines)
        db.session.commit()
        flash('Customer updated successfully!', 'success')
        return redirect(url_for('view_customers'))
    return render_template('update_customer.html', customer=customer)

# Delete customer
@app.route('/delete_customer/<int:id>', methods=['GET'])
def delete_customer(id):
    customer = Customer.query.get_or_404(id)
    db.session.delete(customer)
    db.session.commit()
    flash('Customer deleted successfully!', 'success')
    return redirect(url_for('view_customers'))
# Scan invoice
@app.route('/scan_invoice', methods=['GET', 'POST'])
def scan_invoice():
    if request.method == 'POST' and 'invoice' in request.files:
        invoice = request.files['invoice']
        filename = secure_filename(invoice.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        invoice.save(filepath)
        extracted_text = pytesseract.image_to_string(Image.open(filepath))
        new_invoice = Invoice(filename=filename, extracted_text=extracted_text)
        db.session.add(new_invoice)
        db.session.commit()
        flash('Invoice scanned successfully!', 'info')
        return render_template('scan_invoice.html', extracted_text=extracted_text)
    return render_template('scan_invoice.html')

# View invoices
@app.route('/view_invoices', methods=['GET'])
def view_invoices():
    invoices = Invoice.query.all()
    return render_template('view_invoices.html', invoices=invoices)

# Contact Us
@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        message = request.form['message']
        msg = Message(subject='Contact Us Form Submission', sender=email, recipients=[app.config['MAIL_DEFAULT_SENDER']])
        msg.body = f"Name: {name}\nEmail: {email}\nMessage: {message}"
        mail.send(msg)
        flash('Your message has been sent successfully!', 'success')
        return redirect(url_for('home'))
    return render_template('contact.html')

# Run the app
if __name__ == '__main__':
    app.run(debug=True)