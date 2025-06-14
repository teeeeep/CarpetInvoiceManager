import os
import logging
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, session, make_response, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.security import check_password_hash, generate_password_hash
from weasyprint import HTML
import re
import tempfile

# Configure logging
logging.basicConfig(level=logging.DEBUG)

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)

# Create the app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key-change-in-production")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Configure the database
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///carpet_invoices.db")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}

# Initialize the app with the extension
db.init_app(app)

# Import models after db initialization
from models import Retailer, Job, Invoice, InvoiceLine, FileStore

def login_required(f):
    """Decorator to require login for protected routes"""
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def format_nz_currency(amount):
    """Format amount as NZ currency"""
    return f"${amount:.2f} NZD"

def generate_invoice_code(invoice_id, street_address, retailer_name, homeowner_name):
    """Generate invoice code in format: <ID>-<StreetNoStreet>-<Retailer>-<Homeowner>"""
    # Extract street number and street from address
    street_match = re.match(r'^(\d+)\s+(.+)', street_address.strip())
    if street_match:
        street_no_street = f"{street_match.group(1)}{street_match.group(2).replace(' ', '')}"
    else:
        street_no_street = street_address.replace(' ', '')[:20]
    
    # Clean retailer and homeowner names
    retailer_clean = re.sub(r'[^a-zA-Z0-9]', '', retailer_name)[:10]
    homeowner_clean = re.sub(r'[^a-zA-Z0-9]', '', homeowner_name)[:10]
    
    return f"{invoice_id}-{street_no_street}-{retailer_clean}-{homeowner_clean}"

@app.route('/')
def index():
    """Main dashboard showing recent invoices and quick actions"""
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    
    recent_invoices = db.session.query(Invoice).join(Job).join(Retailer).limit(10).all()
    total_invoices = db.session.query(Invoice).count()
    total_jobs = db.session.query(Job).count()
    total_retailers = db.session.query(Retailer).count()
    
    return render_template('index.html', 
                         recent_invoices=recent_invoices,
                         total_invoices=total_invoices,
                         total_jobs=total_jobs,
                         total_retailers=total_retailers)

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Admin login"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        admin_username = os.environ.get('ADMIN_USERNAME', 'admin')
        admin_password = os.environ.get('ADMIN_PASSWORD', 'admin123')
        
        if username == admin_username and password == admin_password:
            session['logged_in'] = True
            flash('Successfully logged in!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Invalid credentials. Please try again.', 'error')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    """Admin logout"""
    session.pop('logged_in', None)
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

@app.route('/retailers')
@login_required
def retailers():
    """List all retailers"""
    retailers_list = db.session.query(Retailer).all()
    return render_template('retailers.html', retailers=retailers_list)

@app.route('/retailer/add', methods=['GET', 'POST'])
@login_required
def add_retailer():
    """Add new retailer"""
    if request.method == 'POST':
        retailer = Retailer(
            name=request.form.get('name'),
            email=request.form.get('email'),
            phone=request.form.get('phone')
        )
        db.session.add(retailer)
        db.session.commit()
        flash('Retailer added successfully!', 'success')
        return redirect(url_for('retailers'))
    
    return render_template('retailer_form.html')

@app.route('/jobs')
@login_required
def jobs():
    """List all jobs"""
    jobs_list = db.session.query(Job).join(Retailer).all()
    return render_template('jobs.html', jobs=jobs_list)

@app.route('/job/add', methods=['GET', 'POST'])
@login_required
def add_job():
    """Add new job"""
    if request.method == 'POST':
        job = Job(
            street_address=request.form.get('street_address'),
            suburb=request.form.get('suburb'),
            town_city=request.form.get('town_city'),
            retailer_id=request.form.get('retailer_id'),
            homeowner_name=request.form.get('homeowner_name'),
            homeowner_phone=request.form.get('homeowner_phone'),
            date_completed=datetime.strptime(request.form.get('date_completed'), '%Y-%m-%d').date()
        )
        db.session.add(job)
        db.session.commit()
        flash('Job added successfully!', 'success')
        return redirect(url_for('jobs'))
    
    retailers = db.session.query(Retailer).all()
    return render_template('job_form.html', retailers=retailers)

@app.route('/invoices')
@login_required
def invoices():
    """List all invoices"""
    invoices_list = db.session.query(Invoice).join(Job).join(Retailer).all()
    return render_template('invoices.html', invoices=invoices_list)

@app.route('/invoice/add/<int:job_id>')
@login_required
def add_invoice(job_id):
    """Add new invoice for a job"""
    job = db.session.get(Job, job_id)
    if not job:
        flash('Job not found!', 'error')
        return redirect(url_for('jobs'))
    
    return render_template('invoice_form.html', job=job)

@app.route('/invoice/create', methods=['POST'])
@login_required
def create_invoice():
    """Create new invoice with lines"""
    job_id = request.form.get('job_id')
    job = db.session.get(Job, job_id)
    
    if not job:
        flash('Job not found!', 'error')
        return redirect(url_for('jobs'))
    
    # Create invoice
    invoice = Invoice(
        job_id=job_id,
        date_created=datetime.now().date(),
        status='draft',
        gst_percentage=15.0,
        subtotal=0.0,
        gst_amount=0.0,
        total=0.0
    )
    db.session.add(invoice)
    db.session.flush()  # Get the ID
    
    # Generate invoice code
    invoice.invoice_code = generate_invoice_code(
        invoice.id, job.street_address, job.retailer.name, job.homeowner_name
    )
    
    # Add invoice lines
    subtotal = 0.0
    descriptions = request.form.getlist('description[]')
    unit_prices = request.form.getlist('unit_price[]')
    quantities = request.form.getlist('quantity[]')
    
    for desc, price, qty in zip(descriptions, unit_prices, quantities):
        if desc and price and qty:
            unit_price = float(price)
            quantity = int(qty)
            line_total = unit_price * quantity
            
            line = InvoiceLine(
                invoice_id=invoice.id,
                description=desc,
                unit_price=unit_price,
                quantity=quantity,
                line_total=line_total
            )
            db.session.add(line)
            subtotal += line_total
    
    # Update invoice totals
    invoice.subtotal = subtotal
    invoice.gst_amount = subtotal * (invoice.gst_percentage / 100)
    invoice.total = subtotal + invoice.gst_amount
    
    db.session.commit()
    flash('Invoice created successfully!', 'success')
    return redirect(url_for('invoice_preview', invoice_id=invoice.id))

@app.route('/invoice/<int:invoice_id>/preview')
@login_required
def invoice_preview(invoice_id):
    """Preview invoice"""
    invoice = db.session.get(Invoice, invoice_id)
    if not invoice:
        flash('Invoice not found!', 'error')
        return redirect(url_for('invoices'))
    
    return render_template('invoice_preview.html', invoice=invoice)

@app.route('/invoice/<int:invoice_id>/pdf')
@login_required
def invoice_pdf(invoice_id):
    """Generate and download PDF invoice"""
    invoice = db.session.get(Invoice, invoice_id)
    if not invoice:
        flash('Invoice not found!', 'error')
        return redirect(url_for('invoices'))
    
    # Render HTML for PDF
    html_content = render_template('invoice_preview.html', invoice=invoice, for_pdf=True)
    
    # Generate PDF
    pdf = HTML(string=html_content, base_url=request.url_root).write_pdf()
    
    # Save to FileStore
    filename = f"invoice_{invoice.invoice_code}.pdf"
    file_store = FileStore(
        invoice_id=invoice.id,
        file_path=filename,
        date_generated=datetime.now()
    )
    db.session.add(file_store)
    db.session.commit()
    
    # Return PDF response
    response = make_response(pdf)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    return response

@app.route('/invoice/<int:invoice_id>/email')
@login_required
def invoice_email(invoice_id):
    """Generate mailto link for sending invoice"""
    invoice = db.session.get(Invoice, invoice_id)
    if not invoice:
        flash('Invoice not found!', 'error')
        return redirect(url_for('invoices'))
    
    # Create mailto link
    subject = f"Invoice {invoice.invoice_code} - Carpet Installation"
    body = f"""Dear {invoice.job.homeowner_name},

Please find attached your invoice for carpet installation services.

Invoice Details:
- Invoice Number: {invoice.invoice_code}
- Property: {invoice.job.street_address}, {invoice.job.suburb}, {invoice.job.town_city}
- Total Amount: {format_nz_currency(invoice.total)}

Thank you for your business.

Best regards,
Carpet Invoices Team"""
    
    mailto_link = f"mailto:{invoice.job.retailer.email}?subject={subject}&body={body}"
    
    return redirect(mailto_link)

@app.route('/api/invoice/<int:invoice_id>/calculate', methods=['POST'])
@login_required
def calculate_invoice(invoice_id):
    """HTMX endpoint to calculate invoice totals"""
    data = request.get_json()
    lines = data.get('lines', [])
    
    subtotal = 0.0
    for line in lines:
        if line.get('unit_price') and line.get('quantity'):
            unit_price = float(line['unit_price'])
            quantity = int(line['quantity'])
            subtotal += unit_price * quantity
    
    gst_percentage = 15.0
    gst_amount = subtotal * (gst_percentage / 100)
    total = subtotal + gst_amount
    
    return jsonify({
        'subtotal': subtotal,
        'gst_amount': gst_amount,
        'total': total,
        'subtotal_formatted': format_nz_currency(subtotal),
        'gst_formatted': format_nz_currency(gst_amount),
        'total_formatted': format_nz_currency(total)
    })

@app.template_filter('nz_currency')
def nz_currency_filter(amount):
    """Template filter for NZ currency formatting"""
    return format_nz_currency(amount)

@app.template_filter('nz_date')
def nz_date_filter(date):
    """Template filter for NZ date formatting"""
    if date:
        return date.strftime('%d/%m/%Y')
    return ''

# Create tables
with app.app_context():
    db.create_all()
    
    # Create sample data if tables are empty
    if db.session.query(Retailer).count() == 0:
        sample_retailer = Retailer(
            name="Carpet Plus",
            email="admin@carpetplus.co.nz",
            phone="09-123-4567"
        )
        db.session.add(sample_retailer)
        db.session.commit()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
