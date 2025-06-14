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
from models import Retailer, Job, Invoice, InvoiceLine, FileStore, InventoryItem, StockMovement

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
    """Generate invoice code in format: 2526RTHO where 2526 is tax year, RT is retailer initials, HO is homeowner initials"""
    # Get current date to determine tax year
    current_date = datetime.now()
    if current_date.month >= 4:  # Tax year starts April 1
        tax_year_start = current_date.year
    else:
        tax_year_start = current_date.year - 1
    
    # Format as YYNN where YY is last 2 digits of start year, NN is last 2 digits of end year
    tax_year = f"{str(tax_year_start)[-2:]}{str(tax_year_start + 1)[-2:]}"
    
    # Get retailer initials (first 2 letters)
    retailer_initials = ''.join(re.findall(r'[A-Za-z]', retailer_name))[:2].upper()
    if len(retailer_initials) < 2:
        retailer_initials = retailer_initials.ljust(2, 'X')  # Pad with X if less than 2 letters
    
    # Get homeowner initials (first letter of first name and first letter of last name)
    homeowner_parts = homeowner_name.strip().split()
    if len(homeowner_parts) >= 2:
        homeowner_initials = f"{homeowner_parts[0][0]}{homeowner_parts[-1][0]}".upper()
    elif len(homeowner_parts) == 1:
        homeowner_initials = f"{homeowner_parts[0][0]}X".upper()  # Pad with X if only one name
    else:
        homeowner_initials = "XX"
    
    return f"{tax_year}{retailer_initials}{homeowner_initials}"

@app.route('/')
def index():
    """Main dashboard showing recent invoices and quick actions"""
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    
    recent_invoices = db.session.query(Invoice).join(Job).join(Retailer).limit(10).all()
    total_invoices = db.session.query(Invoice).count()
    total_jobs = db.session.query(Job).count()
    total_retailers = db.session.query(Retailer).count()
    
    # Get inventory stats
    total_inventory_items = db.session.query(InventoryItem).filter_by(is_active=True).count()
    low_stock_items = db.session.query(InventoryItem).filter_by(is_active=True).filter(
        InventoryItem.current_stock <= InventoryItem.minimum_stock
    ).count()
    total_inventory_value = db.session.query(
        db.func.sum(InventoryItem.current_stock * InventoryItem.unit_cost)
    ).filter_by(is_active=True).scalar() or 0
    
    return render_template('index.html', 
                         recent_invoices=recent_invoices,
                         total_invoices=total_invoices,
                         total_jobs=total_jobs,
                         total_retailers=total_retailers,
                         total_inventory_items=total_inventory_items,
                         low_stock_items=low_stock_items,
                         total_inventory_value=total_inventory_value)

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
    
    # Get inventory items for selection
    inventory_items = db.session.query(InventoryItem).filter_by(is_active=True).all()
    
    return render_template('invoice_form.html', job=job, inventory_items=inventory_items)

@app.route('/invoice/create', methods=['POST'])
@login_required
def create_invoice():
    """Create new invoice with lines"""
    job_id = request.form.get('job_id')
    job = db.session.get(Job, job_id)
    
    if not job:
        flash('Job not found!', 'error')
        return redirect(url_for('jobs'))
    
    # Create invoice with a temporary invoice code
    temp_invoice_code = f"TEMP-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    invoice = Invoice(
        job_id=job_id,
        date_created=datetime.now().date(),
        status='draft',
        gst_percentage=15.0,
        subtotal=0.0,
        gst_amount=0.0,
        total=0.0,
        invoice_code=temp_invoice_code
    )
    db.session.add(invoice)
    db.session.flush()  # Get the ID
    
    # Generate proper invoice code
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
    
    try:
        # Render HTML for PDF
        html_content = render_template('invoice_pdf.html', invoice=invoice)
        
        # Generate PDF
        pdf = HTML(string=html_content, base_url=request.url_root).write_pdf()
        
        # Generate filename in format: InvoiceNumber - StreetNumStreetName
        street_match = re.match(r'^(\d+)\s+(.+)', invoice.job.street_address.strip())
        if street_match:
            street_part = f"{street_match.group(1)}{street_match.group(2).replace(' ', '')}"
        else:
            street_part = invoice.job.street_address.replace(' ', '')
        
        filename = f"{invoice.invoice_code} - {street_part}.pdf"
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
        
    except Exception as e:
        app.logger.error(f"PDF generation error: {str(e)}")
        flash(f'Error generating PDF: {str(e)}', 'error')
        return redirect(url_for('invoice_preview', invoice_id=invoice_id))

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

# Inventory Management Routes

@app.route('/inventory')
@login_required
def inventory():
    """List all inventory items"""
    items = db.session.query(InventoryItem).filter_by(is_active=True).all()
    
    # Calculate summary statistics
    total_items = len(items)
    low_stock_items = [item for item in items if item.stock_status == 'low_stock']
    out_of_stock_items = [item for item in items if item.stock_status == 'out_of_stock']
    total_value = sum(item.total_value for item in items)
    
    return render_template('inventory.html', 
                         items=items,
                         total_items=total_items,
                         low_stock_count=len(low_stock_items),
                         out_of_stock_count=len(out_of_stock_items),
                         total_value=total_value,
                         low_stock_items=low_stock_items[:5],  # Show first 5 for quick view
                         out_of_stock_items=out_of_stock_items[:5])

@app.route('/inventory/add', methods=['GET', 'POST'])
@login_required
def add_inventory_item():
    """Add new inventory item"""
    if request.method == 'POST':
        # Handle empty string values for numeric fields
        unit_cost = request.form.get('unit_cost', '0').strip()
        current_stock = request.form.get('current_stock', '0').strip()
        minimum_stock = request.form.get('minimum_stock', '0').strip()
        charge_price = request.form.get('charge_price', '0').strip()
        
        item = InventoryItem(
            name=request.form.get('name'),
            description=request.form.get('description'),
            category=request.form.get('category'),
            unit=request.form.get('unit'),
            unit_cost=float(unit_cost) if unit_cost else 0.0,
            current_stock=float(current_stock) if current_stock else 0.0,
            minimum_stock=float(minimum_stock) if minimum_stock else 0.0,
            charge_price=float(charge_price) if charge_price else 0.0,
            supplier=request.form.get('supplier'),
            supplier_code=request.form.get('supplier_code')
        )
        db.session.add(item)
        db.session.commit()
        flash('Inventory item added successfully!', 'success')
        return redirect(url_for('inventory'))
    
    return render_template('inventory_item_form.html')

@app.route('/inventory/import', methods=['GET', 'POST'])
@login_required
def import_inventory_csv():
    """Import inventory items from CSV"""
    if request.method == 'POST':
        if 'csv_file' not in request.files:
            flash('No file selected!', 'error')
            return redirect(request.url)
        
        file = request.files['csv_file']
        if file.filename == '':
            flash('No file selected!', 'error')
            return redirect(request.url)
        
        if file and file.filename.endswith('.csv'):
            try:
                import csv
                import io
                
                # Read CSV content
                stream = io.StringIO(file.stream.read().decode("UTF8"), newline=None)
                csv_input = csv.DictReader(stream)
                
                items_added = 0
                errors = []
                
                for row_num, row in enumerate(csv_input, start=2):
                    try:
                        # Check required fields
                        if not row.get('name') or not row.get('category') or not row.get('unit'):
                            errors.append(f"Row {row_num}: Missing required fields (name, category, unit)")
                            continue
                        
                        # Create inventory item
                        item = InventoryItem(
                            name=row.get('name', '').strip(),
                            description=row.get('description', '').strip(),
                            category=row.get('category', '').strip().lower(),
                            unit=row.get('unit', '').strip(),
                            unit_cost=float(row.get('unit_cost', 0) or 0),
                            charge_price=float(row.get('charge_price', 0) or 0),
                            current_stock=float(row.get('current_stock', 0) or 0),
                            minimum_stock=float(row.get('minimum_stock', 0) or 0),
                            supplier=row.get('supplier', '').strip() or None,
                            supplier_code=row.get('supplier_code', '').strip() or None
                        )
                        
                        db.session.add(item)
                        items_added += 1
                        
                    except ValueError as e:
                        errors.append(f"Row {row_num}: Invalid number format - {str(e)}")
                    except Exception as e:
                        errors.append(f"Row {row_num}: {str(e)}")
                
                if items_added > 0:
                    db.session.commit()
                    flash(f'Successfully imported {items_added} inventory items!', 'success')
                else:
                    db.session.rollback()
                
                if errors:
                    flash(f'Errors encountered: {"; ".join(errors[:5])}', 'warning')
                
            except Exception as e:
                db.session.rollback()
                flash(f'Error processing CSV file: {str(e)}', 'error')
        else:
            flash('Please upload a valid CSV file!', 'error')
            
        return redirect(url_for('inventory'))
    
    return render_template('inventory_import.html')

@app.route('/inventory/<int:item_id>')
@login_required
def inventory_item_detail(item_id):
    """View inventory item details and stock movements"""
    item = db.session.get(InventoryItem, item_id)
    if not item:
        flash('Inventory item not found!', 'error')
        return redirect(url_for('inventory'))
    
    # Get recent stock movements
    movements = db.session.query(StockMovement)\
        .filter_by(inventory_item_id=item_id)\
        .order_by(StockMovement.date_created.desc())\
        .limit(20).all()
    
    return render_template('inventory_item_detail.html', item=item, movements=movements)

@app.route('/inventory/<int:item_id>/movement', methods=['GET', 'POST'])
@login_required
def add_stock_movement(item_id):
    """Add stock movement (in/out/adjustment)"""
    item = db.session.get(InventoryItem, item_id)
    if not item:
        flash('Inventory item not found!', 'error')
        return redirect(url_for('inventory'))
    
    if request.method == 'POST':
        movement_type = request.form.get('movement_type')
        quantity = float(request.form.get('quantity'))
        
        # Ensure quantity is positive for calculations
        if quantity <= 0:
            flash('Quantity must be greater than 0!', 'error')
            return render_template('stock_movement_form.html', item=item)
        
        # For 'out' movements, make quantity negative
        if movement_type == 'out':
            quantity = -quantity
        
        # Check if there's enough stock for 'out' movements
        if movement_type == 'out' and (item.current_stock + quantity) < 0:
            flash('Insufficient stock for this movement!', 'error')
            return render_template('stock_movement_form.html', item=item)
        
        movement = StockMovement(
            inventory_item_id=item_id,
            movement_type=movement_type,
            quantity=quantity,
            unit_cost=float(request.form.get('unit_cost', item.unit_cost)),
            reference_type=request.form.get('reference_type', 'manual'),
            reference_id=request.form.get('reference_id') if request.form.get('reference_id') else None,
            notes=request.form.get('notes'),
            created_by='admin'
        )
        
        # Update current stock
        item.current_stock += quantity
        
        db.session.add(movement)
        db.session.commit()
        
        flash(f'Stock movement recorded successfully! New stock level: {item.current_stock} {item.unit}', 'success')
        return redirect(url_for('inventory_item_detail', item_id=item_id))
    
    return render_template('stock_movement_form.html', item=item)

@app.route('/inventory/low-stock')
@login_required
def low_stock_report():
    """Show items with low or no stock"""
    items = db.session.query(InventoryItem)\
        .filter_by(is_active=True)\
        .filter(InventoryItem.current_stock <= InventoryItem.minimum_stock)\
        .order_by(InventoryItem.current_stock.asc()).all()
    
    return render_template('low_stock_report.html', items=items)

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
