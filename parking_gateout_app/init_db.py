from app import create_app
from models import db, AspNetUsers, AspNetUserRoles
import uuid

def init_db():
    app = create_app()
    with app.app_context():
        # Create all tables
        db.create_all()
        
        # Create test user if it doesn't exist
        test_user = AspNetUsers.query.filter_by(UserName='admin').first()
        if not test_user:
            test_user = AspNetUsers(
                Id=str(uuid.uuid4()),
                UserName='admin',
                Email='admin@test.com',
                FullName='Admin User'
            )
            test_user.set_password('admin123')
            db.session.add(test_user)
            
            # Add admin role
            admin_role = AspNetUserRoles(
                UserId=test_user.Id,
                RoleId='admin'
            )
            db.session.add(admin_role)
            
            db.session.commit()
            print("Test user 'admin' created successfully")
        else:
            print("Test user 'admin' already exists")

if __name__ == '__main__':
    init_db()
