# FlashPark - Parking Management System

A modern parking management system built with Flask, featuring comprehensive parking management, membership system, staff management, and reporting capabilities.

## Core Features

### 1. Parking Management
- Manual entry/exit vehicle recording
- Automatic fee calculation
- Parking slot management
- Receipt printing
- Barcode membership card system
- Staff card management

### 2. Membership Management
- New member registration
- Member card printing with barcode
- Special member rates configuration
- Member parking history
- Membership renewal
- Lost card replacement

### 3. Staff Management
- Staff ID card generation with barcode
- Staff attendance system
- Shift management
- Staff performance monitoring
- Staff activity history

### 4. Admin Dashboard
- Parking occupancy monitoring
- Daily/monthly revenue reports
- User and access rights management
- Parking rate configuration

### 5. Reporting System
- Financial reports
- Usage statistics
- Data export (PDF, Excel)
- System audit logs

### 6. Security Features
- Role-based access control (Admin & Operator)
- Activity logging
- Data encryption
- Regular backup & restore

## Technical Features

- **User Management**: Secure authentication and role-based access control
- **Vehicle Tracking**: Real-time monitoring of vehicles and parking spaces
- **Payment System**: Integrated payment processing and rate management
- **Hardware Integration**: Support for parking gates, sensors, and cameras
- **Reporting**: Comprehensive reporting and analytics dashboard
- **Activity Logs**: Detailed system activity monitoring
- **API Support**: RESTful API for system integration

## Tech Stack

- Python/Flask
- SQLAlchemy ORM
- JWT Authentication
- Bootstrap 5
- Modern UI/UX

## Installation

1. Clone the repository
```bash
git clone https://github.com/idiarso/flaskpark.git
```

2. Install dependencies
```bash
pip install -r requirements.txt
```

3. Configure environment variables
```bash
cp .env.example .env
# Edit .env with your configuration
```

4. Run the application
```bash
python app.py
```

## System Requirements

### Software Requirements
- Python 3.8 or higher
- PostgreSQL 12 or higher
- Modern web browser (Chrome, Firefox, Safari)

### Hardware Requirements
- Entry/Exit gates with controllers
- Barcode scanners
- Receipt printers
- Cameras (optional)
- Parking sensors (optional)

## License

MIT License
