
# Product Requirements Document: Carpet Invoices

## Executive Summary

Carpet Invoices is a Progressive Web Application designed specifically for carpet installation businesses in New Zealand. It provides a complete invoicing solution with offline capabilities, professional PDF generation, and mobile-optimized interface for field workers.

## Product Vision

To empower small carpet installation businesses with professional, reliable invoicing tools that work anywhere, anytime, without complex setup or ongoing costs.

## Target Users

### Primary Users
- **Carpet Installation Business Owners** (1-10 employees)
  - Need professional invoicing system
  - Work across multiple job sites
  - Limited technical expertise
  - Cost-conscious

### Secondary Users
- **Field Workers/Installers**
  - Use tablets/phones on job sites
  - Limited internet connectivity
  - Need simple, touch-friendly interface

### User Personas

**Persona 1: Mike - Business Owner**
- Age: 35-55
- Manages 2-5 installers
- Handles 50-200 jobs/month
- Uses tablet for on-site work
- Wants professional invoices without complexity

**Persona 2: Sarah - Field Installer**
- Age: 25-45
- Works at customer properties
- Needs to create invoices on completion
- Limited technical skills
- Uses smartphone/tablet

## Business Objectives

### Primary Goals
1. **Reduce invoicing time** from 30 minutes to 5 minutes per job
2. **Improve cash flow** with immediate invoice generation
3. **Enhance professional image** with branded PDF invoices
4. **Eliminate paper-based processes**
5. **Work reliably in areas with poor connectivity**

### Success Metrics
- Invoice creation time: <5 minutes per job
- User adoption: 90% of jobs invoiced within 24 hours
- System uptime: 99.5% including offline functionality
- User satisfaction: >4.5/5 rating
- PDF generation success rate: >99%

## Feature Requirements

### Core Features (MVP)

#### 1. Retailer Management
- **Priority**: High
- **User Story**: As a business owner, I want to manage my retailer partners so I can associate jobs with the correct retailer
- **Acceptance Criteria**:
  - Create, edit, delete retailers
  - Store name, email, phone number
  - Link multiple jobs to one retailer
  - Email integration for invoice sending

#### 2. Job Management
- **Priority**: High
- **User Story**: As a field worker, I want to record job details so I can create accurate invoices
- **Acceptance Criteria**:
  - Capture property address (street, suburb, town/city)
  - Record homeowner contact details
  - Associate with retailer
  - Set completion date
  - Support for multiple invoices per job

#### 3. Invoice Creation
- **Priority**: High
- **User Story**: As a user, I want to create professional invoices quickly with accurate calculations
- **Acceptance Criteria**:
  - Auto-generate unique invoice codes (format: 2526RTHO001)
  - Add multiple line items with descriptions, quantities, prices
  - Automatic GST calculation (15%)
  - Real-time total calculations
  - Draft/sent/paid status tracking

#### 4. PDF Generation
- **Priority**: High
- **User Story**: As a business owner, I want professional PDF invoices to send to customers
- **Acceptance Criteria**:
  - A4 format with company branding
  - All invoice details clearly formatted
  - NZ currency formatting
  - Download functionality
  - Email integration (mailto links)

#### 5. Offline Functionality
- **Priority**: High
- **User Story**: As a field worker, I want to create invoices without internet connection
- **Acceptance Criteria**:
  - Full app functionality offline
  - Data synchronization when online
  - Conflict resolution for sync issues
  - Offline indicator in UI

### Advanced Features (Phase 2)

#### 6. Inventory Management
- **Priority**: Medium
- **User Story**: As a business owner, I want to track materials used and automate pricing
- **Features**:
  - Material catalog with standard pricing
  - Stock level tracking
  - Auto-populate invoice lines from inventory
  - CSV import for bulk inventory setup
  - Low stock alerts

#### 7. Reporting & Analytics
- **Priority**: Medium
- **User Story**: As a business owner, I want insights into my business performance
- **Features**:
  - Accounts receivable aging report
  - Sales summary by period
  - Retailer performance analysis
  - GST reporting for tax compliance
  - Job location analysis

#### 8. Enhanced PDF Features
- **Priority**: Low
- **Features**:
  - Custom invoice templates
  - Company logo upload
  - Terms and conditions customization
  - Multiple currency support

## Technical Requirements

### Performance Requirements
- **Page Load Time**: <2 seconds on 3G connection
- **PDF Generation**: <5 seconds for standard invoice
- **Offline Sync**: Complete within 30 seconds when online
- **Database Queries**: <200ms for typical operations

### Scalability Requirements
- Support 1,000+ invoices per user
- Handle 100 concurrent users
- 99.5% uptime including offline capability

### Security Requirements
- Session-based authentication
- HTTPS encryption for all communications
- Data validation on all inputs
- XSS and CSRF protection
- Regular security updates

### Compatibility Requirements
- **Mobile Browsers**: Safari iOS 12+, Chrome Android 8+
- **Desktop Browsers**: Chrome 90+, Firefox 88+, Safari 14+
- **Offline Storage**: IndexedDB support required
- **PWA Features**: Service Worker support

## User Experience Requirements

### Design Principles
1. **Mobile-First**: Optimized for touch interfaces
2. **Simplicity**: Minimal clicks to complete tasks
3. **Clarity**: Clear visual hierarchy and readable text
4. **Consistency**: Uniform patterns across all features
5. **Accessibility**: Supports screen readers and keyboard navigation

### Key User Flows

#### Primary Flow: Create Invoice
1. Select job from list
2. Add invoice line items
3. Review calculated totals
4. Generate PDF
5. Send via email

**Success Criteria**: Complete flow in <5 minutes

#### Secondary Flow: Add New Job
1. Select retailer
2. Enter property details
3. Enter homeowner information
4. Set completion date
5. Save job

**Success Criteria**: Complete flow in <3 minutes

## Constraints & Assumptions

### Technical Constraints
- Must deploy on Replit platform
- Limited to open-source technologies where possible
- Must work offline (primary constraint)
- SQLite database limitations for concurrent users

### Business Constraints
- Budget for premium services: <$50/month
- Development team: 1-2 developers
- Support availability: Business hours only

### Assumptions
- Users have basic smartphone/tablet skills
- Internet connectivity available for initial setup
- Customers accept PDF invoices via email
- Business operates within New Zealand tax regulations

## Success Criteria

### Launch Criteria
- All core features tested and functional
- Offline sync working reliably
- PDF generation producing professional results
- Mobile interface passes usability testing
- Data migration tools ready if needed

### Post-Launch Success
- User adoption: 80% of target users actively using within 3 months
- User satisfaction: >4.0/5 rating
- Feature usage: Core features used by >90% of active users
- Performance: Page load times <2 seconds on mobile

## Risk Assessment

### High Risks
1. **Offline sync complexity** - Mitigation: Thorough testing, simple conflict resolution
2. **PDF quality on mobile** - Mitigation: Extensive device testing, fallback options
3. **User adoption** - Mitigation: Simple onboarding, clear value proposition

### Medium Risks
1. **Performance with large datasets** - Mitigation: Pagination, data archiving
2. **Cross-browser compatibility** - Mitigation: Progressive enhancement approach

### Low Risks
1. **Feature scope creep** - Mitigation: Strict MVP focus
2. **Third-party dependency issues** - Mitigation: Minimal external dependencies

## Timeline & Milestones

### Phase 1: MVP (4-6 weeks)
- Core CRUD operations
- Basic PDF generation
- Offline functionality
- Mobile optimization

### Phase 2: Enhanced Features (4-6 weeks)
- Advanced reporting
- Inventory management
- Performance optimization
- Enhanced PDF features

### Phase 3: Growth Features (ongoing)
- Multi-user support
- Advanced analytics
- Integration capabilities
- Custom branding options

## Appendices

### A. Competitive Analysis
- QuickBooks: Too complex, expensive
- FreshBooks: Missing offline capability
- Wave: Limited customization
- Paper-based: Unprofessional, inefficient

### B. Technical Architecture
- Frontend: HTMX + Tailwind CSS
- Backend: Flask + SQLAlchemy
- Database: SQLite → PostgreSQL
- PDF: WeasyPrint
- PWA: Service Worker + Manifest

### C. Regulatory Requirements
- GST compliance (15% NZ rate)
- Invoice numbering requirements
- Data retention policies
- Privacy considerations
