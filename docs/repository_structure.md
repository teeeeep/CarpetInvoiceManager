
# Carpet Invoices - Repository Structure Documentation

## Overview
This is a Flask-based Progressive Web Application (PWA) for carpet installation businesses in New Zealand. The application provides offline-capable invoicing with auto-generated invoice codes, professional PDF generation, and comprehensive business management features.

## Technology Stack
- **Backend**: Flask 3.0 + Python 3.12
- **Database**: SQLite (development) → PostgreSQL (production ready)
- **ORM**: SQLAlchemy 2.0
- **PDF Generation**: WeasyPrint
- **Frontend**: HTMX + Tailwind CSS (CDN)
- **PWA**: Service Worker + Web App Manifest
- **Authentication**: Session-based Flask sessions
- **Deployment**: Replit (Gunicorn + PostgreSQL module)

## Directory Structure

```
carpet-invoices/
├── docs/                           # Documentation files
│   ├── chatgpt_evaluation_prompt.md # Tech stack evaluation prompt for ChatGPT
│   ├── product_requirements_document.md # Business requirements and specifications
│   └── repository_structure.md     # This file
│
├── static/                         # Static assets for PWA
│   ├── manifest.json              # PWA manifest for app installation
│   ├── sw.js                      # Service worker for offline functionality
│   └── tailwind.css               # Custom Tailwind overrides (minimal)
│
├── templates/                      # Jinja2 HTML templates
│   ├── base.html                  # Base template with PWA setup, Tailwind, HTMX
│   ├── index.html                 # Dashboard with business metrics
│   ├── login.html                 # Simple admin authentication
│   │
│   ├── retailers.html             # Retailer management list view
│   ├── retailer_form.html         # Add/edit retailer form
│   │
│   ├── jobs.html                  # Job management list view
│   ├── job_form.html              # Add/edit job form
│   │
│   ├── invoices.html              # Invoice list with status tracking
│   ├── invoice_form.html          # Invoice creation with inventory integration
│   ├── invoice_preview.html       # Invoice preview before PDF generation
│   ├── invoice_pdf.html           # PDF template for WeasyPrint
│   │
│   ├── inventory.html             # Inventory management dashboard
│   ├── inventory_item_form.html   # Add/edit inventory items
│   ├── inventory_item_detail.html # Item details with stock movements
│   ├── inventory_import.html      # CSV import interface
│   ├── stock_movement_form.html   # Record stock in/out/adjustments
│   ├── low_stock_report.html      # Low stock alerts
│   │
│   └── reports/                   # Business reporting templates
│       ├── reports.html           # Reports dashboard
│       ├── accounts_receivable_report.html # Outstanding invoices by aging
│       ├── accounts_receivable_report_pdf.html # PDF version of A/R report
│       └── sales_summary_report.html # Revenue analysis
│
├── app.py                         # Main Flask application
├── main.py                        # Entry point (imports app)
├── models.py                      # SQLAlchemy database models
├── forms.py                       # Flask-WTF form definitions (touch-optimized)
│
├── .replit                        # Replit configuration with PostgreSQL
├── pyproject.toml                 # Python dependencies
├── Dockerfile                     # Docker containerization (optional)
├── fly.toml                       # Fly.io deployment config (alternative)
│
├── README.md                      # Project overview and setup instructions
├── replit.md                      # Detailed technical documentation
└── .env.example                   # Environment variables template
```

## Core Application Components

### Database Models (`models.py`)
- **Retailer**: Carpet retailer partners (name, email, phone)
- **Job**: Installation jobs (address, homeowner, completion date)
- **Invoice**: Invoices with auto-generated codes and NZ tax compliance
- **InvoiceLine**: Line items with quantity/pricing calculations
- **FileStore**: PDF storage tracking
- **InventoryItem**: Materials and supplies with costing
- **StockMovement**: Inventory tracking (in/out/adjustments)

### Key Features

#### Invoice Code Generation
Auto-generated format: `2526RTHO001`
- `25-26`: Tax year (April 1 to March 31)
- `RT`: Retailer initials
- `HO`: Homeowner initials
- `001`: Sequential number across all invoices

#### New Zealand Localization
- **Currency**: NZD formatting (`$123.45 NZD`)
- **GST**: 15% automatically calculated
- **Date Format**: DD/MM/YYYY throughout
- **Tax Year**: April 1 - March 31 cycle

#### Offline Capabilities
- **Service Worker**: Caches essential resources
- **Background Sync**: Queues operations when offline
- **Progressive Web App**: Installable on mobile devices
- **Local Storage**: Critical data cached for offline access

#### PDF Generation
- **WeasyPrint**: Professional A4 invoices
- **Email Integration**: mailto: links for sending invoices
- **Print Styles**: Optimized for physical printing

### Business Logic

#### Invoice Workflow
1. Create Job → Link to Retailer
2. Create Invoice → Auto-generate code
3. Add Line Items → Real-time calculations
4. Preview → Generate PDF → Email/Print

#### Inventory Integration
- Pre-populated pricing from inventory
- Stock level tracking
- CSV import for bulk setup
- Low stock alerts

#### Reporting System
- Accounts Receivable (aging analysis)
- Sales summaries with GST breakdown
- Retailer performance metrics
- Inventory valuation reports

## Development Environment

### Replit Configuration
- **Platform**: Replit with PostgreSQL module
- **Runtime**: Python 3.11 + Nix packages
- **Server**: Gunicorn with auto-reload
- **Database**: PostgreSQL 16 for production scaling

### Dependencies Management
- **Core**: Flask ecosystem (SQLAlchemy, WTF, etc.)
- **PDF**: WeasyPrint with system libraries (Cairo, Pango)
- **Production**: Gunicorn + PostgreSQL drivers

### Security Considerations
- Session-based authentication (configurable admin credentials)
- CSRF protection via Flask-WTF
- SQL injection protection via SQLAlchemy ORM
- XSS prevention through Jinja2 auto-escaping

## Deployment Strategy

### Development
- **Local**: Flask dev server + SQLite
- **Replit**: PostgreSQL + Gunicorn with live reload

### Production Ready
- **Database**: PostgreSQL with connection pooling
- **Server**: Gunicorn with multiple workers
- **Static Files**: CDN for Tailwind/HTMX (replaceable with local files)
- **Environment**: Configurable via environment variables

## Business Context

### Target Users
- Small carpet installation businesses (1-10 employees)
- New Zealand market focus
- Mobile-first workflow (tablets/phones on job sites)
- Offline-required (unreliable internet at properties)

### Scale Expectations
- 100-500 invoices per month per business
- 10-50 retailers per business
- 20-100 inventory items
- Multi-year data retention

### Compliance Requirements
- NZ GST calculation and reporting
- Invoice numbering for tax purposes
- Business record retention
- Professional PDF formatting for legal/tax purposes

## Future Considerations

### Potential Enhancements
- Multi-user authentication with role-based access
- Integration with accounting systems (Xero, MYOB)
- SMS notifications for job completion
- Photo attachment for job documentation
- Advanced inventory forecasting

### Scalability Paths
- PostgreSQL clustering for high availability
- Redis for session storage and caching
- Celery for background PDF generation
- API endpoints for mobile app integration

This structure prioritizes simplicity, offline capability, and New Zealand business compliance while maintaining professional standards for small business use.
