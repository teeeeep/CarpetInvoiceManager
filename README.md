# Carpet Invoices

A comprehensive offline-capable invoicing web application specifically designed for carpet installation businesses in New Zealand. Built with Flask, HTMX, and Progressive Web App (PWA) technologies.

## Features

### Core Functionality
- **CRUD Operations**: Complete management of Retailers, Jobs, Invoices, Invoice Lines, and File Storage
- **Auto-Generated Invoice Codes**: Format: `<ID>-<StreetNoStreet>-<Retailer>-<Homeowner>`
- **Touch-Friendly Interface**: Optimised for mobile and tablet use
- **Live Calculations**: Real-time subtotal → GST (15%) → total calculations
- **PDF Generation**: Professional A4 invoices using WeasyPrint
- **Email Integration**: Send invoices via default mail client using mailto links

### Offline Capabilities
- **Progressive Web App**: Works offline with service worker
- **Data Synchronisation**: Automatic sync when connection restored
- **Local Caching**: Essential resources cached for offline use
- **Background Sync**: Queue invoices for submission when offline

### New Zealand Localisation
- **NZ Dollar Formatting**: All amounts displayed in NZD
- **GST Calculations**: 15% GST automatically calculated
- **Date Formatting**: DD/MM/YYYY format
- **NZ English**: All text in New Zealand English

## Technology Stack

### Backend
- **Flask**: Python web framework
- **SQLAlchemy**: Database ORM with SQLite
- **WeasyPrint**: PDF generation
- **Werkzeug**: Security utilities

### Frontend
- **HTMX**: Dynamic UI without JavaScript frameworks
- **Tailwind CSS**: Responsive design
- **Feather Icons**: Clean, professional icons
- **Service Worker**: Offline functionality

## Installation & Setup

### Prerequisites
- Python 3.12 or higher
- pip (Python package installer)

### Local Development

1. **Clone or download the application files**

2. **Install dependencies**
   ```bash
   pip install flask flask-sqlalchemy weasyprint python-dotenv
   