# Carpet Invoices - Progressive Web App

## Overview

Carpet Invoices is a comprehensive offline-capable invoicing web application specifically designed for carpet installation businesses in New Zealand. The application provides complete CRUD operations for managing retailers, jobs, invoices, and file storage, with auto-generated invoice codes and professional PDF generation capabilities.

## System Architecture

### Backend Architecture
- **Framework**: Flask 3.0 with Python 3.12
- **Database**: SQLite with SQLAlchemy ORM (designed to be easily migrated to PostgreSQL)
- **PDF Generation**: WeasyPrint for professional A4 invoices
- **Authentication**: Session-based authentication with admin credentials
- **Security**: Werkzeug security utilities with configurable session settings

### Frontend Architecture
- **UI Framework**: HTMX for dynamic interactions without JavaScript frameworks
- **Styling**: Tailwind CSS for responsive design
- **Icons**: Feather Icons for clean, professional iconography
- **Progressive Web App**: Service worker implementation for offline functionality
- **Forms**: Flask-WTF with WTForms for form handling and validation

### Database Schema
The application uses four main models:
- **Retailer**: Stores carpet retailer partner information (name, email, phone)
- **Job**: Manages carpet installation jobs with property details and homeowner information
- **Invoice**: Handles invoicing with auto-generated codes, GST calculations, and status tracking
- **InvoiceLine**: Individual line items for invoices with descriptions, quantities, and pricing
- **FileStore**: Placeholder for future file upload functionality

## Key Components

### Invoice Code Generation
Auto-generated invoice codes follow the format: `<ID>-<StreetNoStreet>-<Retailer>-<Homeowner>`

### New Zealand Localization
- **Currency**: NZD formatting for all monetary values
- **GST**: 15% GST automatically calculated and displayed
- **Date Format**: DD/MM/YYYY format throughout the application
- **Timezone**: Pacific/Auckland as default

### Offline Capabilities
- **Service Worker**: Caches essential resources for offline use
- **Progressive Web App**: Full PWA implementation with manifest.json
- **Background Sync**: Queues operations when offline for later synchronization

### PDF Generation
- **WeasyPrint Integration**: Professional A4 invoice generation
- **Email Integration**: mailto links for sending invoices via default mail client
- **Print Support**: Browser-based printing with CSS print styles

## Data Flow

1. **Retailer Management**: Add and manage carpet retailer partners
2. **Job Creation**: Record carpet installation jobs with property and homeowner details
3. **Invoice Generation**: Create invoices from jobs with multiple line items
4. **PDF Export**: Generate professional invoices as downloadable PDFs
5. **Status Tracking**: Track invoice status (draft, sent, paid)

## External Dependencies

### Frontend Libraries
- **Tailwind CSS**: Via CDN for responsive styling
- **HTMX**: Via CDN for dynamic UI interactions
- **Feather Icons**: Via CDN for iconography

### Python Packages
- **Flask**: Web framework and extensions
- **SQLAlchemy**: Database ORM
- **WeasyPrint**: PDF generation
- **WTForms**: Form handling and validation
- **Werkzeug**: Security and WSGI utilities

### System Dependencies
- **wkhtmltopdf**: PDF rendering engine
- **Cairo/Pango**: Graphics libraries for WeasyPrint
- **Fonts**: Liberation and DejaVu fonts for PDF generation

## Deployment Strategy

### Development
- **Local**: Flask development server with SQLite
- **Replit**: Configured with PostgreSQL module for cloud development

### Production Options
- **Docker**: Multi-stage Dockerfile with optimized Python 3.12 slim image
- **Fly.io**: Configured for Sydney region deployment with persistent storage
- **Gunicorn**: WSGI server for production deployment

### Database Migration
- **Current**: SQLite for development and small deployments
- **Future**: PostgreSQL support configured for scaling (DATABASE_URL environment variable)

### Environment Configuration
Comprehensive environment variables for:
- Database configuration
- Flask settings
- Admin authentication
- Email configuration (future feature)
- PDF generation settings
- Security settings
- Performance tuning

## Changelog

- June 14, 2025. Initial setup

## User Preferences

Preferred communication style: Simple, everyday language.