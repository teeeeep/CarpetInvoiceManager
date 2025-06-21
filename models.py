from app import db
from datetime import datetime
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship

class Retailer(db.Model):
    """Retailer model for carpet installation businesses"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    
    # Relationships
    jobs = relationship("Job", back_populates="retailer")
    
    def __repr__(self):
        return f'<Retailer {self.name}>'

class Job(db.Model):
    """Job model for carpet installation jobs"""
    id = db.Column(db.Integer, primary_key=True)
    street_address = db.Column(db.String(200), nullable=False)
    suburb = db.Column(db.String(100), nullable=False)
    town_city = db.Column(db.String(100), nullable=False)
    retailer_id = db.Column(db.Integer, ForeignKey('retailer.id'), nullable=False)
    homeowner_name = db.Column(db.String(100), nullable=False)
    homeowner_phone = db.Column(db.String(20), nullable=False)
    date_completed = db.Column(db.Date, nullable=False)
    
    # Relationships
    retailer = relationship("Retailer", back_populates="jobs")
    invoices = relationship("Invoice", back_populates="job")
    
    @property
    def full_address(self):
        return f"{self.street_address}, {self.suburb}, {self.town_city}"
    
    def __repr__(self):
        return f'<Job {self.street_address} for {self.homeowner_name}>'

class Invoice(db.Model):
    """Invoice model for carpet installation invoices"""
    id = db.Column(db.Integer, primary_key=True)
    invoice_code = db.Column(db.String(100), unique=True, nullable=False, index=True)
    job_id = db.Column(db.Integer, ForeignKey('job.id'), nullable=False, index=True)
    date_created = db.Column(db.Date, nullable=False, default=datetime.now().date, index=True)
    status = db.Column(db.String(20), nullable=False, default='draft', index=True)  # draft, sent, paid
    gst_percentage = db.Column(db.Float, nullable=False, default=15.0)
    subtotal = db.Column(db.Float, nullable=False, default=0.0)
    gst_amount = db.Column(db.Float, nullable=False, default=0.0)
    total = db.Column(db.Float, nullable=False, default=0.0, index=True)
    
    # Relationships
    job = relationship("Job", back_populates="invoices")
    lines = relationship("InvoiceLine", back_populates="invoice", cascade="all, delete-orphan")
    files = relationship("FileStore", back_populates="invoice", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f'<Invoice {self.invoice_code}>'

class InvoiceLine(db.Model):
    """Invoice line item model"""
    id = db.Column(db.Integer, primary_key=True)
    invoice_id = db.Column(db.Integer, ForeignKey('invoice.id'), nullable=False)
    description = db.Column(db.String(500), nullable=False)
    unit_price = db.Column(db.Float, nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    line_total = db.Column(db.Float, nullable=False)
    
    # Relationships
    invoice = relationship("Invoice", back_populates="lines")
    
    def __repr__(self):
        return f'<InvoiceLine {self.description}>'

class FileStore(db.Model):
    """File storage model for generated PDFs and documents"""
    id = db.Column(db.Integer, primary_key=True)
    invoice_id = db.Column(db.Integer, ForeignKey('invoice.id'), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    date_generated = db.Column(db.DateTime, nullable=False, default=datetime.now)
    
    # Relationships
    invoice = relationship("Invoice", back_populates="files")
    
    def __repr__(self):
        return f'<FileStore {self.file_path}>'

class InventoryItem(db.Model):
    """Inventory item model for carpet materials and supplies"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.String(500))
    category = db.Column(db.String(100), nullable=False)  # carpet, underlay, tools, adhesive, etc.
    unit = db.Column(db.String(50), nullable=False)  # m², linear metres, pieces, litres, etc.
    unit_cost = db.Column(db.Float, nullable=False, default=0.0)  # What you pay for the item
    charge_price = db.Column(db.Float, nullable=False, default=0.0)  # What you charge customers
    current_stock = db.Column(db.Float, nullable=False, default=0.0)
    minimum_stock = db.Column(db.Float, nullable=False, default=0.0)
    supplier = db.Column(db.String(200))
    supplier_code = db.Column(db.String(100))
    date_created = db.Column(db.Date, nullable=False, default=datetime.now().date)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    
    # Relationships
    stock_movements = relationship("StockMovement", back_populates="inventory_item", cascade="all, delete-orphan")
    
    @property
    def stock_status(self):
        """Return stock status based on current stock vs minimum stock"""
        if self.current_stock <= 0:
            return 'out_of_stock'
        elif self.current_stock <= self.minimum_stock:
            return 'low_stock'
        else:
            return 'in_stock'
    
    @property
    def total_value(self):
        """Calculate total value of current stock"""
        return self.current_stock * self.unit_cost
    
    def __repr__(self):
        return f'<InventoryItem {self.name}>'

class StockMovement(db.Model):
    """Stock movement model for tracking inventory changes"""
    id = db.Column(db.Integer, primary_key=True)
    inventory_item_id = db.Column(db.Integer, ForeignKey('inventory_item.id'), nullable=False)
    movement_type = db.Column(db.String(20), nullable=False)  # 'in', 'out', 'adjustment'
    quantity = db.Column(db.Float, nullable=False)
    unit_cost = db.Column(db.Float)  # Cost at time of movement
    reference_type = db.Column(db.String(50))  # 'job', 'purchase', 'adjustment', 'waste'
    reference_id = db.Column(db.Integer)  # ID of related job, purchase order, etc.
    notes = db.Column(db.String(500))
    date_created = db.Column(db.DateTime, nullable=False, default=datetime.now)
    created_by = db.Column(db.String(100))  # User who made the movement
    
    # Relationships
    inventory_item = relationship("InventoryItem", back_populates="stock_movements")
    
    @property
    def movement_value(self):
        """Calculate value of this movement"""
        if self.unit_cost:
            return abs(self.quantity) * self.unit_cost
        return 0.0
    
    def __repr__(self):
        return f'<StockMovement {self.movement_type} {self.quantity} of {self.inventory_item.name}>'
