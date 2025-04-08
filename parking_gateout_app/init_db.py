from parking_gateout_app.app import create_app
from parking_gateout_app.models import db, AspNetUsers, AspNetRoles, AspNetUserRoles, ParkingSpaces, Vehicles, ParkingTickets
from werkzeug.security import generate_password_hash
from datetime import datetime, timedelta
import uuid

def init_db():
    app = create_app()
    with app.app_context():
        # Create all tables
        db.create_all()

        # Create admin role if not exists
        admin_role = AspNetRoles.query.filter_by(Name='Admin').first()
        if not admin_role:
            admin_role_data = {
                'Id': str(uuid.uuid4()),
                'Name': 'Admin',
                'Description': 'Administrator'
            }
            admin_role = AspNetRoles(**admin_role_data)
            db.session.add(admin_role)

        # Create operator role if not exists
        operator_role = AspNetRoles.query.filter_by(Name='Operator').first()
        if not operator_role:
            operator_role_data = {
                'Id': str(uuid.uuid4()),
                'Name': 'Operator',
                'Description': 'Parking Operator'
            }
            operator_role = AspNetRoles(**operator_role_data)
            db.session.add(operator_role)

        # Create admin user if not exists
        admin_user = AspNetUsers.query.filter_by(Email='admin@example.com').first()
        if not admin_user:
            admin_user_data = {
                'Id': str(uuid.uuid4()),
                'UserName': 'admin',
                'Email': 'admin@example.com',
                'PasswordHash': generate_password_hash('admin123'),
                'FullName': 'Admin User',
                'IsActive': True
            }
            admin_user = AspNetUsers(**admin_user_data)
            db.session.add(admin_user)
            db.session.flush()

            # Assign admin role
            admin_user_role_data = {
                'UserId': admin_user.Id,
                'RoleId': admin_role.Id
            }
            admin_user_role = AspNetUserRoles(**admin_user_role_data)
            db.session.add(admin_user_role)

        # Create operator user if not exists
        operator_user = AspNetUsers.query.filter_by(Email='operator@example.com').first()
        if not operator_user:
            operator_user_data = {
                'Id': str(uuid.uuid4()),
                'UserName': 'operator',
                'Email': 'operator@example.com',
                'PasswordHash': generate_password_hash('operator123'),
                'FullName': 'Operator User',
                'IsActive': True
            }
            operator_user = AspNetUsers(**operator_user_data)
            db.session.add(operator_user)
            db.session.flush()

            # Assign operator role
            operator_user_role_data = {
                'UserId': operator_user.Id,
                'RoleId': operator_role.Id
            }
            operator_user_role = AspNetUserRoles(**operator_user_role_data)
            db.session.add(operator_user_role)

        # Create parking spaces if not exists
        if ParkingSpaces.query.count() == 0:
            for i in range(1, 21):  # Create 20 parking spaces
                space_data = {
                    'SpaceNumber': f'A-{i:02d}',
                    'Level': '1',
                    'Section': 'A',
                    'VehicleType': 'Car',
                    'IsOccupied': False,
                    'Status': 'available'
                }
                space = ParkingSpaces(**space_data)
                db.session.add(space)

        # Create some dummy vehicles and tickets
        if Vehicles.query.count() == 0:
            # Sample plate numbers
            plates = ['B 1234 CD', 'B 5678 EF', 'B 9012 GH']
            for plate in plates:
                vehicle_data = {
                    'Id': str(uuid.uuid4()),
                    'plate_number': plate,
                    'vehicle_type': 'Car',
                    'status': 'registered'
                }
                vehicle = Vehicles(**vehicle_data)
                db.session.add(vehicle)
                db.session.flush()

                # Create active parking ticket for first two vehicles
                if plates.index(plate) < 2:
                    space = ParkingSpaces.query.filter_by(IsOccupied=False).first()
                    if space:
                        space.IsOccupied = True
                        ticket_data = {
                            'TicketNumber': f'TKT{datetime.now().strftime("%Y%m%d%H%M%S")}{vehicle.Id}',
                            'VehicleId': vehicle.Id,
                            'SpaceId': space.Id,
                            'EntryTime': datetime.now() - timedelta(hours=2),
                            'Status': 'active',
                            'CreatedBy': operator_user.Id
                        }
                        ticket = ParkingTickets(**ticket_data)
                        db.session.add(ticket)

        # Commit all changes
        db.session.commit()

if __name__ == '__main__':
    init_db()
