import os
import logging
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, session, make_response, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.security import check_password_hash, generate_password_hash
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
    """Generate invoice code in format: 2526RTHO001 where 2526 is tax year, RT is retailer initials, HO is homeowner initials, 001 is sequential number"""
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

    # Generate base code without sequential number
    base_code = f"{tax_year}{retailer_initials}{homeowner_initials}"

    # Find the highest existing sequential number across ALL invoices
    existing_invoices = db.session.query(Invoice).all()

    max_seq = 0
    for invoice in existing_invoices:
        # Extract the sequential number (last 3 digits of any invoice code)
        if len(invoice.invoice_code) >= 3:
            seq_part = invoice.invoice_code[-3:]  # Get last 3 characters
            if seq_part.isdigit():
                max_seq = max(max_seq, int(seq_part))

    # Generate next sequential number (3 digits, zero-padded)
    next_seq = max_seq + 1
    sequential_number = f"{next_seq:03d}"

    return f"{base_code}{sequential_number}"

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

@app.route('/simple-home')
@login_required
def simple_home():
    """Simplified homepage designed for older users"""
    # Get recent invoices (limit to 5 for simplicity)
    recent_invoices = db.session.query(Invoice).join(Job).join(Retailer).order_by(Invoice.date_created.desc()).limit(5).all()
    
    # Get jobs that don't have invoices yet for easy invoice creation
    jobs_without_invoices = db.session.query(Job).outerjoin(Invoice).filter(Invoice.id == None).order_by(Job.date_completed.desc()).limit(5).all()
    
    return render_template('simple_home.html', 
                         recent_invoices=recent_invoices,
                         jobs_without_invoices=jobs_without_invoices)

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
        flash('Job added successfully! Now create an invoice for this job.', 'success')
        return redirect(url_for('add_invoice', job_id=job.id))

    retailers = db.session.query(Retailer).all()
    return render_template('job_form.html', retailers=retailers)

@app.route('/job/<int:job_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_job(job_id):
    """Edit existing job"""
    job = db.session.get(Job, job_id)
    if not job:
        flash('Job not found!', 'error')
        return redirect(url_for('jobs'))

    if request.method == 'POST':
        job.street_address = request.form.get('street_address')
        job.suburb = request.form.get('suburb')
        job.town_city = request.form.get('town_city')
        job.retailer_id = request.form.get('retailer_id')
        job.homeowner_name = request.form.get('homeowner_name')
        job.homeowner_phone = request.form.get('homeowner_phone')
        job.date_completed = datetime.strptime(request.form.get('date_completed'), '%Y-%m-%d').date()
        
        db.session.commit()
        flash('Job updated successfully!', 'success')
        return redirect(url_for('jobs'))

    retailers = db.session.query(Retailer).all()
    return render_template('job_form.html', job=job, retailers=retailers)

@app.route('/job/<int:job_id>/delete', methods=['POST'])
@login_required
def delete_job(job_id):
    """Delete job and associated invoices"""
    job = db.session.get(Job, job_id)
    if not job:
        flash('Job not found!', 'error')
        return redirect(url_for('jobs'))

    # Check if job has invoices
    if job.invoices:
        flash(f'Cannot delete job: {len(job.invoices)} invoice(s) are associated with this job. Delete invoices first.', 'error')
        return redirect(url_for('jobs'))

    job_address = job.street_address
    db.session.delete(job)
    db.session.commit()
    flash(f'Job at {job_address} deleted successfully!', 'success')
    return redirect(url_for('jobs'))

@app.route('/invoices')
@login_required
def invoices():
    """List all invoices with search and filtering"""
    # Get filter parameters
    search = request.args.get('search', '').strip()
    status_filter = request.args.get('status', '')
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')
    sort_by = request.args.get('sort', 'date_created')
    sort_order = request.args.get('order', 'desc')
    
    # Base query with joins for search
    query = db.session.query(Invoice).join(Job).join(Retailer)
    
    # Apply search filter
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            db.or_(
                Invoice.invoice_code.ilike(search_term),
                Job.street_address.ilike(search_term),
                Job.suburb.ilike(search_term),
                Job.town_city.ilike(search_term),
                Job.homeowner_name.ilike(search_term),
                Retailer.name.ilike(search_term)
            )
        )
    
    # Apply status filter
    if status_filter:
        query = query.filter(Invoice.status == status_filter)
    
    # Apply date range filter
    if date_from:
        try:
            from_date = datetime.strptime(date_from, '%Y-%m-%d').date()
            query = query.filter(Invoice.date_created >= from_date)
        except ValueError:
            pass
    
    if date_to:
        try:
            to_date = datetime.strptime(date_to, '%Y-%m-%d').date()
            query = query.filter(Invoice.date_created <= to_date)
        except ValueError:
            pass
    
    # Apply sorting
    if sort_by == 'invoice_code':
        sort_column = Invoice.invoice_code
    elif sort_by == 'total':
        sort_column = Invoice.total
    elif sort_by == 'status':
        sort_column = Invoice.status
    elif sort_by == 'address':
        sort_column = Job.street_address
    elif sort_by == 'homeowner':
        sort_column = Job.homeowner_name
    elif sort_by == 'retailer':
        sort_column = Retailer.name
    else:  # default to date_created
        sort_column = Invoice.date_created
    
    if sort_order == 'asc':
        query = query.order_by(sort_column.asc())
    else:
        query = query.order_by(sort_column.desc())
    
    invoices_list = query.all()
    
    return render_template('invoices.html', 
                         invoices=invoices_list,
                         search=search,
                         status_filter=status_filter,
                         date_from=date_from,
                         date_to=date_to,
                         sort_by=sort_by,
                         sort_order=sort_order)

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
    """Generate and download PDF invoice with style selection"""
    invoice = db.session.get(Invoice, invoice_id)
    if not invoice:
        flash('Invoice not found!', 'error')
        return redirect(url_for('invoices'))

    # Get style parameter (default to style1 if not specified)
    style = request.args.get('style', 'style1')
    
    # Validate style parameter
    valid_styles = ['style1', 'style2', 'style3']
    if style not in valid_styles:
        style = 'style1'

    try:
        # Import WeasyPrint only when needed
        from weasyprint import HTML
        
        # Select the appropriate template based on style
        template_name = f'invoice_pdf_{style}.html'
        
        # Render HTML for PDF
        html_content = render_template(template_name, invoice=invoice)

        # Generate PDF
        pdf = HTML(string=html_content, base_url=request.url_root).write_pdf()

        # Generate new filename structure: Address (INVOICENUM - Address - Retailer - Year)
        # Clean address for filename (remove special characters)
        clean_address = re.sub(r'[^\w\s-]', '', invoice.job.street_address).strip()
        clean_address = re.sub(r'[-\s]+', '', clean_address)
        
        # Clean retailer name
        clean_retailer = re.sub(r'[^\w\s-]', '', invoice.job.retailer.name).strip()
        clean_retailer = re.sub(r'[-\s]+', '', clean_retailer)
        
        # Get year from invoice date
        year = invoice.date_created.year
        
        # New filename structure: Address (INVOICENUM - Address - Retailer - Year)
        filename = f"{clean_address} ({invoice.invoice_code} - {clean_address} - {clean_retailer} - {year}).pdf"
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

    except ImportError as e:
        app.logger.error(f"WeasyPrint not available: {str(e)}")
        flash('PDF generation is not available. Please contact system administrator.', 'error')
        return redirect(url_for('invoice_preview', invoice_id=invoice_id))
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

@app.route('/invoice/<int:invoice_id>/delete', methods=['POST'])
@login_required
def delete_invoice(invoice_id):
    """Delete invoice and associated files"""
    invoice = db.session.get(Invoice, invoice_id)
    if not invoice:
        flash('Invoice not found!', 'error')
        return redirect(url_for('invoices'))

    invoice_code = invoice.invoice_code
    db.session.delete(invoice)
    db.session.commit()
    flash(f'Invoice {invoice_code} deleted successfully!', 'success')
    return redirect(url_for('invoices'))

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

# Reporting Routes

@app.route('/reports')
@login_required
def reports():
    """Reports dashboard"""
    from sqlalchemy import func
    from datetime import datetime, timedelta
    
    # Calculate quick stats for dashboard
    current_date = datetime.now().date()
    first_of_month = current_date.replace(day=1)
    
    # Total outstanding invoices
    total_outstanding = db.session.query(func.sum(Invoice.total))\
        .filter(Invoice.status.in_(['draft', 'sent']))\
        .scalar() or 0
    
    # Monthly revenue (paid invoices this month)
    monthly_revenue = db.session.query(func.sum(Invoice.total))\
        .filter(Invoice.status == 'paid')\
        .filter(Invoice.date_created >= first_of_month)\
        .scalar() or 0
    
    # Active retailers (retailers with jobs this year)
    year_start = current_date.replace(month=1, day=1)
    active_retailers = db.session.query(func.count(func.distinct(Job.retailer_id)))\
        .filter(Job.date_completed >= year_start)\
        .scalar() or 0
    
    # Jobs this month
    jobs_this_month = db.session.query(func.count(Job.id))\
        .filter(Job.date_completed >= first_of_month)\
        .scalar() or 0
    
    return render_template('reports.html',
                         total_outstanding=total_outstanding,
                         monthly_revenue=monthly_revenue,
                         active_retailers=active_retailers,
                         jobs_this_month=jobs_this_month)

@app.route('/reports/accounts-receivable')
@login_required
def accounts_receivable_report():
    """Accounts receivable aging report"""
    from datetime import datetime, timedelta
    
    current_date = datetime.now().date()
    
    # Get filter parameters
    retailer_filter = request.args.get('retailer_id', type=int)
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')
    aging_filter = request.args.get('aging')
    
    # Build query
    query = db.session.query(Invoice)\
        .join(Job)\
        .join(Retailer)\
        .filter(Invoice.status.in_(['draft', 'sent']))
    
    # Apply filters
    if retailer_filter:
        query = query.filter(Job.retailer_id == retailer_filter)
    
    if date_from:
        try:
            date_from_obj = datetime.strptime(date_from, '%Y-%m-%d').date()
            query = query.filter(Invoice.date_created >= date_from_obj)
        except ValueError:
            pass
    
    if date_to:
        try:
            date_to_obj = datetime.strptime(date_to, '%Y-%m-%d').date()
            query = query.filter(Invoice.date_created <= date_to_obj)
        except ValueError:
            pass
    
    outstanding_invoices = query.order_by(Retailer.name, Invoice.date_created).all()
    
    # Apply aging filter after query
    if aging_filter:
        filtered_invoices = []
        for invoice in outstanding_invoices:
            days_outstanding = (current_date - invoice.date_created).days
            if aging_filter == 'current' and days_outstanding <= 30:
                filtered_invoices.append(invoice)
            elif aging_filter == '31-60' and 31 <= days_outstanding <= 60:
                filtered_invoices.append(invoice)
            elif aging_filter == '60-plus' and days_outstanding > 60:
                filtered_invoices.append(invoice)
        outstanding_invoices = filtered_invoices
    
    # Group by retailer
    retailer_data = {}
    summary = {
        'total_outstanding': 0,
        'current': 0,      # 0-30 days
        'days_31_60': 0,   # 31-60 days
        'days_60_plus': 0  # 60+ days
    }
    
    for invoice in outstanding_invoices:
        retailer_name = invoice.job.retailer.name
        if retailer_name not in retailer_data:
            retailer_data[retailer_name] = []
        
        retailer_data[retailer_name].append(invoice)
        
        # Calculate aging
        days_outstanding = (current_date - invoice.date_created).days
        summary['total_outstanding'] += invoice.total
        
        if days_outstanding <= 30:
            summary['current'] += invoice.total
        elif days_outstanding <= 60:
            summary['days_31_60'] += invoice.total
        else:
            summary['days_60_plus'] += invoice.total
    
    # Get all retailers for filter dropdown
    all_retailers = db.session.query(Retailer).order_by(Retailer.name).all()
    
    return render_template('accounts_receivable_report.html',
                         retailer_data=retailer_data,
                         summary=summary,
                         report_date=current_date,
                         all_retailers=all_retailers,
                         filters={
                             'retailer_id': retailer_filter,
                             'date_from': date_from,
                             'date_to': date_to,
                             'aging': aging_filter
                         })

@app.route('/reports/accounts-receivable/pdf')
@login_required
def accounts_receivable_report_pdf():
    """Export accounts receivable report as PDF"""
    from datetime import datetime, timedelta
    
    current_date = datetime.now().date()
    
    # Get filter parameters (same as regular report)
    retailer_filter = request.args.get('retailer_id', type=int)
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')
    aging_filter = request.args.get('aging')
    
    # Build query (same logic as regular report)
    query = db.session.query(Invoice)\
        .join(Job)\
        .join(Retailer)\
        .filter(Invoice.status.in_(['draft', 'sent']))
    
    # Apply filters
    if retailer_filter:
        query = query.filter(Job.retailer_id == retailer_filter)
    
    if date_from:
        try:
            date_from_obj = datetime.strptime(date_from, '%Y-%m-%d').date()
            query = query.filter(Invoice.date_created >= date_from_obj)
        except ValueError:
            pass
    
    if date_to:
        try:
            date_to_obj = datetime.strptime(date_to, '%Y-%m-%d').date()
            query = query.filter(Invoice.date_created <= date_to_obj)
        except ValueError:
            pass
    
    outstanding_invoices = query.order_by(Retailer.name, Invoice.date_created).all()
    
    # Apply aging filter after query
    if aging_filter:
        filtered_invoices = []
        for invoice in outstanding_invoices:
            days_outstanding = (current_date - invoice.date_created).days
            if aging_filter == 'current' and days_outstanding <= 30:
                filtered_invoices.append(invoice)
            elif aging_filter == '31-60' and 31 <= days_outstanding <= 60:
                filtered_invoices.append(invoice)
            elif aging_filter == '60-plus' and days_outstanding > 60:
                filtered_invoices.append(invoice)
        outstanding_invoices = filtered_invoices
    
    # Group by retailer
    retailer_data = {}
    summary = {
        'total_outstanding': 0,
        'current': 0,
        'days_31_60': 0,
        'days_60_plus': 0
    }
    
    for invoice in outstanding_invoices:
        retailer_name = invoice.job.retailer.name
        if retailer_name not in retailer_data:
            retailer_data[retailer_name] = []
        
        retailer_data[retailer_name].append(invoice)
        
        # Calculate aging
        days_outstanding = (current_date - invoice.date_created).days
        summary['total_outstanding'] += invoice.total
        
        if days_outstanding <= 30:
            summary['current'] += invoice.total
        elif days_outstanding <= 60:
            summary['days_31_60'] += invoice.total
        else:
            summary['days_60_plus'] += invoice.total
    
    try:
        # Import WeasyPrint only when needed
        from weasyprint import HTML
        
        # Get retailer name for filter display
        selected_retailer_name = None
        if retailer_filter:
            selected_retailer = db.session.get(Retailer, retailer_filter)
            if selected_retailer:
                selected_retailer_name = selected_retailer.name
        
        # Render HTML for PDF
        html_content = render_template('accounts_receivable_report_pdf.html',
                                     retailer_data=retailer_data,
                                     summary=summary,
                                     report_date=current_date,
                                     filters={
                                         'retailer_name': selected_retailer_name,
                                         'date_from': date_from,
                                         'date_to': date_to,
                                         'aging': aging_filter
                                     })
        
        # Generate PDF
        pdf = HTML(string=html_content, base_url=request.url_root).write_pdf()
        
        # Return PDF response
        filename = f"accounts_receivable_report_{current_date.strftime('%Y%m%d')}.pdf"
        response = make_response(pdf)
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        return response
        
    except ImportError as e:
        app.logger.error(f"WeasyPrint not available: {str(e)}")
        flash('PDF generation is not available. Please contact system administrator.', 'error')
        return redirect(url_for('accounts_receivable_report'))
    except Exception as e:
        app.logger.error(f"PDF generation error: {str(e)}")
        flash(f'Error generating PDF: {str(e)}', 'error')
        return redirect(url_for('accounts_receivable_report'))

@app.route('/reports/sales-summary')
@login_required
def sales_summary_report():
    """Sales summary report"""
    from sqlalchemy import func, extract
    from datetime import datetime, timedelta
    
    current_date = datetime.now().date()
    current_year = current_date.year
    
    # Monthly sales for current year
    monthly_sales = db.session.query(
        extract('month', Invoice.date_created).label('month'),
        func.sum(Invoice.total).label('total'),
        func.count(Invoice.id).label('count')
    ).filter(
        extract('year', Invoice.date_created) == current_year,
        Invoice.status == 'paid'
    ).group_by(extract('month', Invoice.date_created)).all()
    
    # Sales by retailer
    retailer_sales = db.session.query(
        Retailer.name,
        func.sum(Invoice.total).label('total'),
        func.count(Invoice.id).label('count')
    ).join(Job).join(Invoice)\
    .filter(
        extract('year', Invoice.date_created) == current_year,
        Invoice.status == 'paid'
    ).group_by(Retailer.name).all()
    
    # Year over year comparison
    previous_year_total = db.session.query(func.sum(Invoice.total))\
        .filter(
            extract('year', Invoice.date_created) == current_year - 1,
            Invoice.status == 'paid'
        ).scalar() or 0
    
    current_year_total = db.session.query(func.sum(Invoice.total))\
        .filter(
            extract('year', Invoice.date_created) == current_year,
            Invoice.status == 'paid'
        ).scalar() or 0
    
    return render_template('sales_summary_report.html',
                         monthly_sales=monthly_sales,
                         retailer_sales=retailer_sales,
                         current_year=current_year,
                         current_year_total=current_year_total,
                         previous_year_total=previous_year_total)

@app.route('/reports/retailer-performance')
@login_required
def retailer_performance_report():
    """Retailer performance report"""
    from sqlalchemy import func
    from datetime import datetime
    
    current_year = datetime.now().year
    
    # Performance by retailer
    retailer_performance = db.session.query(
        Retailer.name,
        Retailer.email,
        func.count(Job.id).label('total_jobs'),
        func.count(Invoice.id).label('total_invoices'),
        func.sum(Invoice.total).label('total_revenue'),
        func.avg(Invoice.total).label('avg_invoice_value')
    ).outerjoin(Job).outerjoin(Invoice)\
    .filter(func.extract('year', Job.date_completed) == current_year)\
    .group_by(Retailer.id, Retailer.name, Retailer.email)\
    .order_by(func.sum(Invoice.total).desc())\
    .all()
    
    return render_template('retailer_performance_report.html',
                         retailer_performance=retailer_performance,
                         current_year=current_year)

@app.route('/reports/gst-summary')
@login_required
def gst_summary_report():
    """GST summary report"""
    from sqlalchemy import func, extract
    from datetime import datetime
    
    current_date = datetime.now().date()
    current_year = current_date.year
    
    # Quarterly GST summary
    quarterly_gst = db.session.query(
        func.floor((extract('month', Invoice.date_created) - 1) / 3 + 1).label('quarter'),
        func.sum(Invoice.subtotal).label('total_sales'),
        func.sum(Invoice.gst_amount).label('total_gst'),
        func.count(Invoice.id).label('invoice_count')
    ).filter(
        extract('year', Invoice.date_created) == current_year
    ).group_by(func.floor((extract('month', Invoice.date_created) - 1) / 3 + 1)).all()
    
    # Monthly GST breakdown
    monthly_gst = db.session.query(
        extract('month', Invoice.date_created).label('month'),
        func.sum(Invoice.subtotal).label('subtotal'),
        func.sum(Invoice.gst_amount).label('gst_amount'),
        func.sum(Invoice.total).label('total')
    ).filter(
        extract('year', Invoice.date_created) == current_year
    ).group_by(extract('month', Invoice.date_created)).all()
    
    return render_template('gst_summary_report.html',
                         quarterly_gst=quarterly_gst,
                         monthly_gst=monthly_gst,
                         current_year=current_year)

@app.route('/reports/job-analysis')
@login_required
def job_analysis_report():
    """Job analysis report"""
    from sqlalchemy import func
    from datetime import datetime
    
    current_year = datetime.now().year
    
    # Jobs by location
    jobs_by_suburb = db.session.query(
        Job.suburb,
        Job.town_city,
        func.count(Job.id).label('job_count'),
        func.sum(Invoice.total).label('total_value')
    ).outerjoin(Invoice)\
    .filter(func.extract('year', Job.date_completed) == current_year)\
    .group_by(Job.suburb, Job.town_city)\
    .order_by(func.count(Job.id).desc())\
    .all()
    
    # Monthly job completion trends
    monthly_jobs = db.session.query(
        extract('month', Job.date_completed).label('month'),
        func.count(Job.id).label('job_count'),
        func.avg(Invoice.total).label('avg_value')
    ).outerjoin(Invoice)\
    .filter(func.extract('year', Job.date_completed) == current_year)\
    .group_by(extract('month', Job.date_completed)).all()
    
    return render_template('job_analysis_report.html',
                         jobs_by_suburb=jobs_by_suburb,
                         monthly_jobs=monthly_jobs,
                         current_year=current_year)

@app.route('/reports/inventory-valuation')
@login_required
def inventory_valuation_report():
    """Inventory valuation report"""
    from sqlalchemy import func
    
    # Inventory by category
    inventory_by_category = db.session.query(
        InventoryItem.category,
        func.count(InventoryItem.id).label('item_count'),
        func.sum(InventoryItem.current_stock * InventoryItem.unit_cost).label('total_value'),
        func.sum(InventoryItem.current_stock).label('total_stock')
    ).filter(InventoryItem.is_active == True)\
    .group_by(InventoryItem.category)\
    .order_by(func.sum(InventoryItem.current_stock * InventoryItem.unit_cost).desc())\
    .all()
    
    # Low stock items
    low_stock_items = db.session.query(InventoryItem)\
        .filter(InventoryItem.is_active == True)\
        .filter(InventoryItem.current_stock <= InventoryItem.minimum_stock)\
        .order_by(InventoryItem.current_stock.asc()).all()
    
    # Total inventory value
    total_value = db.session.query(
        func.sum(InventoryItem.current_stock * InventoryItem.unit_cost)
    ).filter(InventoryItem.is_active == True).scalar() or 0
    
    return render_template('inventory_valuation_report.html',
                         inventory_by_category=inventory_by_category,
                         low_stock_items=low_stock_items,
                         total_value=total_value)

@app.route('/admin')
@login_required
def admin_panel():
    """Admin control panel for database management"""
    # Get current database statistics
    total_retailers = db.session.query(Retailer).count()
    total_jobs = db.session.query(Job).count()
    total_invoices = db.session.query(Invoice).count()
    total_inventory_items = db.session.query(InventoryItem).filter_by(is_active=True).count()
    
    return render_template('admin_panel.html',
                         total_retailers=total_retailers,
                         total_jobs=total_jobs,
                         total_invoices=total_invoices,
                         total_inventory_items=total_inventory_items)

@app.route('/admin/cleanse-database', methods=['POST'])
@login_required
def cleanse_database():
    """Cleanse all data from the database (keep tables structure)"""
    try:
        # Delete all records in order to respect foreign key constraints
        db.session.query(StockMovement).delete()
        db.session.query(InventoryItem).delete()
        db.session.query(FileStore).delete()
        db.session.query(InvoiceLine).delete()
        db.session.query(Invoice).delete()
        db.session.query(Job).delete()
        db.session.query(Retailer).delete()
        
        db.session.commit()
        flash('Database cleansed successfully! All data has been removed.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error cleansing database: {str(e)}', 'error')
    
    return redirect(url_for('admin_panel'))

@app.route('/admin/reset-database', methods=['POST'])
@login_required
def reset_database():
    """Reset database with sample data"""
    try:
        # First cleanse all data
        db.session.query(StockMovement).delete()
        db.session.query(InventoryItem).delete()
        db.session.query(FileStore).delete()
        db.session.query(InvoiceLine).delete()
        db.session.query(Invoice).delete()
        db.session.query(Job).delete()
        db.session.query(Retailer).delete()
        
        # Add sample retailers
        retailers = [
            Retailer(name="Carpet Plus", email="admin@carpetplus.co.nz", phone="09-123-4567"),
            Retailer(name="Auckland Carpet Co", email="info@aucklandcarpet.co.nz", phone="09-987-6543"),
            Retailer(name="Flooring World", email="sales@flooringworld.co.nz", phone="09-555-0123"),
            Retailer(name="Premium Carpets Ltd", email="orders@premiumcarpets.co.nz", phone="09-444-5678")
        ]
        
        for retailer in retailers:
            db.session.add(retailer)
        db.session.flush()
        
        # Add sample inventory items
        inventory_items = [
            InventoryItem(name="Premium Wool Carpet", description="High-quality wool carpet for living areas", category="carpet", unit="m²", unit_cost=45.50, charge_price=89.99, current_stock=250.0, minimum_stock=50.0, supplier="Wool Masters NZ", supplier_code="WM-PREM-001"),
            InventoryItem(name="Standard Nylon Carpet", description="Durable nylon carpet for high traffic areas", category="carpet", unit="m²", unit_cost=28.75, charge_price=54.99, current_stock=180.0, minimum_stock=40.0, supplier="Synthetic Solutions", supplier_code="SS-NYL-STD"),
            InventoryItem(name="Luxury Berber Carpet", description="Textured berber carpet for modern homes", category="carpet", unit="m²", unit_cost=38.20, charge_price=72.50, current_stock=120.0, minimum_stock=30.0, supplier="Berber Direct", supplier_code="BD-LUX-002"),
            InventoryItem(name="Premium Underlay", description="High-density underlay for comfort and insulation", category="underlay", unit="m²", unit_cost=12.50, charge_price=24.99, current_stock=300.0, minimum_stock=75.0, supplier="Comfort Base Ltd", supplier_code="CB-PREM-UL"),
            InventoryItem(name="Standard Underlay", description="Standard density underlay for general use", category="underlay", unit="m²", unit_cost=8.25, charge_price=16.99, current_stock=220.0, minimum_stock=50.0, supplier="Comfort Base Ltd", supplier_code="CB-STD-UL"),
            InventoryItem(name="Carpet Adhesive", description="Professional grade carpet adhesive", category="adhesive", unit="litres", unit_cost=15.80, charge_price=32.50, current_stock=45.0, minimum_stock=10.0, supplier="Bond Strong", supplier_code="BS-ADH-001"),
            InventoryItem(name="Tack Strips", description="Wooden tack strips for carpet installation", category="tools", unit="pieces", unit_cost=2.40, charge_price=4.99, current_stock=150.0, minimum_stock=25.0, supplier="Install Pro", supplier_code="IP-TACK-24"),
            InventoryItem(name="Seaming Tape", description="Heat-activated seaming tape for joins", category="tools", unit="metres", unit_cost=3.20, charge_price=6.50, current_stock=80.0, minimum_stock=20.0, supplier="Join Perfect", supplier_code="JP-SEAM-H20"),
            InventoryItem(name="Carpet Tucker", description="Professional carpet tucker tool", category="tools", unit="pieces", unit_cost=18.50, charge_price=35.00, current_stock=12.0, minimum_stock=3.0, supplier="Tool Masters", supplier_code="TM-TUCKER-PRO"),
            InventoryItem(name="Knee Kicker", description="Carpet stretching knee kicker", category="tools", unit="pieces", unit_cost=45.00, charge_price=0.00, current_stock=8.0, minimum_stock=2.0, supplier="Stretch Pro", supplier_code="SP-KNEE-K01")
        ]
        
        for item in inventory_items:
            db.session.add(item)
        db.session.flush()
        
        # Add sample jobs
        from datetime import date, timedelta
        
        jobs = [
            Job(street_address="123 Queen Street", suburb="Auckland Central", town_city="Auckland", retailer_id=retailers[0].id, homeowner_name="John Smith", homeowner_phone="021-123-4567", date_completed=date.today() - timedelta(days=5)),
            Job(street_address="456 Ponsonby Road", suburb="Ponsonby", town_city="Auckland", retailer_id=retailers[0].id, homeowner_name="Sarah Johnson", homeowner_phone="021-987-6543", date_completed=date.today() - timedelta(days=3)),
            Job(street_address="789 Dominion Road", suburb="Mount Eden", town_city="Auckland", retailer_id=retailers[1].id, homeowner_name="Mike Wilson", homeowner_phone="021-555-0123", date_completed=date.today() - timedelta(days=7)),
            Job(street_address="321 Remuera Road", suburb="Remuera", town_city="Auckland", retailer_id=retailers[1].id, homeowner_name="Emma Brown", homeowner_phone="021-444-5678", date_completed=date.today() - timedelta(days=2)),
            Job(street_address="654 Great North Road", suburb="Grey Lynn", town_city="Auckland", retailer_id=retailers[2].id, homeowner_name="David Lee", homeowner_phone="021-333-7890", date_completed=date.today() - timedelta(days=1)),
            Job(street_address="987 New North Road", suburb="Kingsland", town_city="Auckland", retailer_id=retailers[2].id, homeowner_name="Lisa Chen", homeowner_phone="021-222-9876", date_completed=date.today() - timedelta(days=4)),
            Job(street_address="147 Manukau Road", suburb="Epsom", town_city="Auckland", retailer_id=retailers[3].id, homeowner_name="Robert Taylor", homeowner_phone="021-111-2345", date_completed=date.today() - timedelta(days=6)),
            Job(street_address="258 Mt Eden Road", suburb="Mount Eden", town_city="Auckland", retailer_id=retailers[3].id, homeowner_name="Amanda White", homeowner_phone="021-888-3456", date_completed=date.today() - timedelta(days=8))
        ]
        
        for job in jobs:
            db.session.add(job)
        db.session.flush()
        
        # Add sample invoices with line items
        invoice_data = [
            {
                "job": jobs[0],
                "status": "paid",
                "lines": [
                    {"description": "Premium Wool Carpet - Living Room", "unit_price": 89.99, "quantity": 35},
                    {"description": "Premium Underlay", "unit_price": 24.99, "quantity": 35},
                    {"description": "Installation Labour", "unit_price": 25.00, "quantity": 35}
                ]
            },
            {
                "job": jobs[1],
                "status": "sent",
                "lines": [
                    {"description": "Standard Nylon Carpet - Bedrooms", "unit_price": 54.99, "quantity": 28},
                    {"description": "Standard Underlay", "unit_price": 16.99, "quantity": 28},
                    {"description": "Installation Labour", "unit_price": 20.00, "quantity": 28}
                ]
            },
            {
                "job": jobs[2],
                "status": "paid",
                "lines": [
                    {"description": "Luxury Berber Carpet - Lounge & Dining", "unit_price": 72.50, "quantity": 42},
                    {"description": "Premium Underlay", "unit_price": 24.99, "quantity": 42},
                    {"description": "Installation Labour", "unit_price": 30.00, "quantity": 42}
                ]
            },
            {
                "job": jobs[3],
                "status": "draft",
                "lines": [
                    {"description": "Premium Wool Carpet - Master Bedroom", "unit_price": 89.99, "quantity": 18},
                    {"description": "Premium Underlay", "unit_price": 24.99, "quantity": 18},
                    {"description": "Installation Labour", "unit_price": 25.00, "quantity": 18}
                ]
            },
            {
                "job": jobs[4],
                "status": "sent",
                "lines": [
                    {"description": "Standard Nylon Carpet - Office", "unit_price": 54.99, "quantity": 22},
                    {"description": "Standard Underlay", "unit_price": 16.99, "quantity": 22},
                    {"description": "Tack Strips", "unit_price": 4.99, "quantity": 15},
                    {"description": "Installation Labour", "unit_price": 20.00, "quantity": 22}
                ]
            },
            {
                "job": jobs[5],
                "status": "paid",
                "lines": [
                    {"description": "Luxury Berber Carpet - Living Areas", "unit_price": 72.50, "quantity": 38},
                    {"description": "Premium Underlay", "unit_price": 24.99, "quantity": 38},
                    {"description": "Installation Labour", "unit_price": 30.00, "quantity": 38}
                ]
            }
        ]
        
        for inv_data in invoice_data:
            # Create invoice with temporary code
            temp_code = f"TEMP-{datetime.now().strftime('%Y%m%d%H%M%S')}-{inv_data['job'].id}"
            invoice = Invoice(
                job_id=inv_data['job'].id,
                date_created=inv_data['job'].date_completed,
                status=inv_data['status'],
                gst_percentage=15.0,
                subtotal=0.0,
                gst_amount=0.0,
                total=0.0,
                invoice_code=temp_code
            )
            db.session.add(invoice)
            db.session.flush()
            
            # Generate proper invoice code
            invoice.invoice_code = generate_invoice_code(
                invoice.id, inv_data['job'].street_address, inv_data['job'].retailer.name, inv_data['job'].homeowner_name
            )
            
            # Add invoice lines
            subtotal = 0.0
            for line_data in inv_data['lines']:
                line_total = line_data['unit_price'] * line_data['quantity']
                line = InvoiceLine(
                    invoice_id=invoice.id,
                    description=line_data['description'],
                    unit_price=line_data['unit_price'],
                    quantity=line_data['quantity'],
                    line_total=line_total
                )
                db.session.add(line)
                subtotal += line_total
            
            # Update invoice totals
            invoice.subtotal = subtotal
            invoice.gst_amount = subtotal * (invoice.gst_percentage / 100)
            invoice.total = subtotal + invoice.gst_amount
        
        # Add some stock movements
        stock_movements = [
            StockMovement(inventory_item_id=inventory_items[0].id, movement_type="in", quantity=50.0, unit_cost=45.50, reference_type="purchase", notes="Initial stock purchase", created_by="admin"),
            StockMovement(inventory_item_id=inventory_items[1].id, movement_type="in", quantity=75.0, unit_cost=28.75, reference_type="purchase", notes="Weekly delivery", created_by="admin"),
            StockMovement(inventory_item_id=inventory_items[0].id, movement_type="out", quantity=-35.0, reference_type="job", reference_id=jobs[0].id, notes="Used for Queen Street installation", created_by="admin"),
            StockMovement(inventory_item_id=inventory_items[1].id, movement_type="out", quantity=-28.0, reference_type="job", reference_id=jobs[1].id, notes="Used for Ponsonby Road installation", created_by="admin"),
            StockMovement(inventory_item_id=inventory_items[5].id, movement_type="in", quantity=20.0, unit_cost=15.80, reference_type="purchase", notes="Adhesive restock", created_by="admin")
        ]
        
        for movement in stock_movements:
            db.session.add(movement)
        
        db.session.commit()
        
        flash('Database reset successfully! Comprehensive sample data has been restored including 4 retailers, 8 jobs, 6 invoices, 10 inventory items, and stock movements.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error resetting database: {str(e)}', 'error')
    
    return redirect(url_for('admin_panel'))

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