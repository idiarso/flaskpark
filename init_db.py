from parking_gateout_app.models import db, AspNetRoles, AspNetUsers, AspNetUserRoles, ParkingSpaces, ParkingTickets
from datetime import datetime
from parking_gateout_app.app import create_app

def init_db():
    # Drop and create all tables
    db.drop_all()
    db.create_all()

    # Insert roles
    role_admin = AspNetRoles()
    role_admin.Id = '1'
    role_admin.Name = 'Admin'
    role_admin.Description = 'Administrator role'

    role_staff = AspNetRoles()
    role_staff.Id = '2'
    role_staff.Name = 'Staff'
    role_staff.Description = 'Staff role'

    # Insert users
    admin_user = AspNetUsers()
    admin_user.Id = '1'
    admin_user.UserName = 'admin'
    admin_user.Email = 'admin@example.com'
    admin_user.PasswordHash = 'hashed_password'  # Replace with actual hash
    admin_user.FullName = 'Administrator'
    admin_user.IsActive = True

    # Insert user roles
    admin_role = AspNetUserRoles()
    admin_role.UserId = '1'
    admin_role.RoleId = '1'

    # Insert staff user
    staff_user = AspNetUsers()
    staff_user.Id = '2'
    staff_user.UserName = 'staff'
    staff_user.Email = 'staff@example.com'
    staff_user.PasswordHash = 'hashed_password'  # Replace with actual hash
    staff_user.FullName = 'Staff Member'
    staff_user.IsActive = True

    staff_role = AspNetUserRoles()
    staff_role.UserId = '2'
    staff_role.RoleId = '2'

    # Insert parking spaces
    space1 = ParkingSpaces()
    space1.SpaceNumber = 'A1'
    space1.Level = '1'
    space1.Section = 'A'
    space1.VehicleType = 'Car'
    space1.IsOccupied = False
    space1.Status = 'available'

    # Insert parking ticket
    ticket1 = ParkingTickets()
    ticket1.TicketNumber = 'TICKET001'
    ticket1.VehicleId = '1'
    ticket1.SpaceId = '1'
    ticket1.EntryTime = datetime.utcnow()
    ticket1.Status = 'active'
    ticket1.CreatedBy = '1'

    # Add all to session and commit
    db.session.add_all([role_admin, role_staff, admin_user, admin_role, 
                        staff_user, staff_role, space1, ticket1])
    db.session.commit()

if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        init_db() 