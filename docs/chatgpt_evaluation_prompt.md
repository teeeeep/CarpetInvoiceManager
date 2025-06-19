
# ChatGPT Tech Stack Evaluation Prompt

Please evaluate the current technology stack for "Carpet Invoices" - a Progressive Web App for carpet installation businesses in New Zealand. Analyze the pros/cons and recommend optimizations or alternatives.

## Current Stack Analysis Required:

### Backend
- **Framework**: Flask 3.0 + Python 3.12
- **Database**: SQLite (development) → PostgreSQL (production)
- **ORM**: SQLAlchemy
- **PDF Generation**: WeasyPrint
- **Authentication**: Session-based with Flask sessions
- **Deployment**: Replit (current requirement)

### Frontend
- **UI Framework**: HTMX for dynamic interactions
- **Styling**: Tailwind CSS (CDN)
- **Icons**: Feather Icons (CDN)
- **PWA**: Service Worker + Web App Manifest
- **Forms**: Flask-WTF + WTForms

### Key Requirements to Consider:
1. **Offline-first capability** - Must work without internet
2. **Mobile-optimized** - Touch-friendly interface for tablets/phones
3. **NZ localization** - NZD currency, 15% GST, DD/MM/YYYY dates
4. **Professional PDF invoices** - A4 format with proper formatting
5. **Simple deployment** - Must work on Replit platform
6. **Small business focus** - Easy to use, not over-engineered
7. **Data integrity** - Invoice codes, calculations, audit trails

### Evaluation Criteria:
- Performance and scalability for 100-500 invoices/month
- Development speed and maintainability
- Offline functionality reliability
- Mobile experience quality
- PDF generation quality and speed
- Security considerations for business data
- Cost effectiveness (mostly open-source preferred)
- Learning curve for potential team expansion

### Specific Questions:
1. Is Flask + HTMX optimal for this use case vs. React/Vue SPA?
2. Should we consider FastAPI instead of Flask?
3. Is WeasyPrint the best choice for PDF generation?
4. How can we improve the offline-sync architecture?
5. Are there better alternatives to SQLite for this scale?
6. What are the security implications of the current session approach?
7. How future-proof is this stack for 3-5 years?

Please provide:
- Detailed analysis of current stack strengths/weaknesses
- Alternative technology recommendations with rationale
- Migration strategy if changes are recommended
- Risk assessment for any proposed changes
- Cost-benefit analysis focusing on small business needs
