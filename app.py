from flask import Flask, request, jsonify, render_template, send_file
from fpdf import FPDF
import sqlite3
from datetime import datetime

app = Flask(__name__)

# Create a connection to the database
def get_db_connection():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn

# Initialize the database with customers and transactions
def init_db():
    conn = get_db_connection()
    conn.execute('''CREATE TABLE IF NOT EXISTS customers (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT NOT NULL,
                        total_balance REAL DEFAULT 0
                    )''')
    conn.execute('''CREATE TABLE IF NOT EXISTS transactions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        customer_id INTEGER,
                        item_name TEXT,
                        weight REAL,
                        percentage REAL,
                        amount REAL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY(customer_id) REFERENCES customers(id)
                    )''')
    conn.commit()
    conn.close()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/search-customer', methods=['GET'])
def search_customer():
    customer_name = request.args.get('customerName')
    
    conn = get_db_connection()
    customer = conn.execute('SELECT * FROM customers WHERE name = ?', (customer_name,)).fetchone()
    
    if customer is None:
        return jsonify({"error": "Customer not found"}), 404
    
    transactions = conn.execute('SELECT * FROM transactions WHERE customer_id = ?', (customer['id'],)).fetchall()
    conn.close()

    past_balance = customer['total_balance']
    
    return jsonify({
        'customer': {
            'id': customer['id'],
            'name': customer['name'],
            'past_balance': past_balance,
            'transactions': [dict(transaction) for transaction in transactions]
        }
    })

@app.route('/add-purchase', methods=['POST'])
def add_purchase():
    data = request.json
    customer_id = data['customerId']
    item_name = data['itemName']
    weight = data['weight']
    percentage = data['percentage']

    # Example price per gram
    price_per_gram = 5000
    calculated_amount = weight * (percentage / 100) * price_per_gram

    conn = get_db_connection()

    # Add the transaction
    conn.execute('INSERT INTO transactions (customer_id, item_name, weight, percentage, amount) VALUES (?, ?, ?, ?, ?)',
                 (customer_id, item_name, weight, percentage, calculated_amount))
    
    # Update the total balance
    conn.execute('UPDATE customers SET total_balance = total_balance + ? WHERE id = ?', (calculated_amount, customer_id))
    conn.commit()

    customer = conn.execute('SELECT * FROM customers WHERE id = ?', (customer_id,)).fetchone()
    conn.close()

    return jsonify({
        'customerName': customer['name'],
        'newBalance': customer['total_balance'],
        'amountAdded': calculated_amount
    })

@app.route('/generate-invoice/<customer_id>', methods=['GET'])
def generate_invoice(customer_id):
    conn = get_db_connection()
    customer = conn.execute('SELECT * FROM customers WHERE id = ?', (customer_id,)).fetchone()
    transactions = conn.execute('SELECT * FROM transactions WHERE customer_id = ?', (customer_id,)).fetchall()
    conn.close()

    past_balance = customer['total_balance'] - transactions[-1]['amount']
    current_purchase = transactions[-1]

    pdf = FPDF()
    pdf.add_page()

    # Professional Invoice Content
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(200, 10, txt="S.K Ornaments", ln=True, align='C')
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt="Professional Gold Jewellery Merchant", ln=True, align='C')

    pdf.cell(200, 10, txt=f"Customer: {customer['name']}", ln=True)
    pdf.cell(200, 10, txt=f"Invoice Date: {current_purchase['created_at']}", ln=True)
    pdf.cell(200, 10, txt=f"Past Balance: ₹{past_balance:.2f}", ln=True)

    pdf.cell(200, 10, txt="Purchase Details:", ln=True)
    pdf.cell(200, 10, txt=f"Item: {current_purchase['item_name']} - Weight: {current_purchase['weight']}g", ln=True)
    pdf.cell(200, 10, txt=f"Percentage of Gold: {current_purchase['percentage']}%", ln=True)
    pdf.cell(200, 10, txt=f"Amount: ₹{current_purchase['amount']:.2f}", ln=True)

    pdf.cell(200, 10, txt=f"Total Balance: ₹{customer['total_balance']:.2f}", ln=True)

    pdf.cell(200, 10, txt="Thank you for your business!", ln=True, align='C')

    invoice_file = f"invoices/invoice_{customer_id}.pdf"
    pdf.output(invoice_file)

    return send_file(invoice_file, as_attachment=True)

if __name__ == "__main__":
    init_db()
    app.run(debug=True)
