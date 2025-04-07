from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import uuid

db = SQLAlchemy()

class AspNetUsers(db.Model):
    __tablename__ = 'AspNetUsers'
    Id = db.Column(db.String(36), primary_key=True)
    UserName = db.Column(db.String(256), unique=True, nullable=False)
    Email = db.Column(db.String(256))
    PasswordHash = db.Column(db.String(256), nullable=False)
    FullName = db.Column(db.String(100))
    CreatedAt = db.Column(db.DateTime, default=datetime.utcnow)
    LastLogin = db.Column(db.DateTime)
    IsActive = db.Column(db.Boolean, default=True)

    def set_password(self, password):
        self.PasswordHash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.PasswordHash, password)

class AspNetUserRoles(db.Model):
    __tablename__ = 'AspNetUserRoles'
    UserId = db.Column(db.String(36), db.ForeignKey('AspNetUsers.Id'), primary_key=True)
    RoleId = db.Column(db.String(36), primary_key=True)

class SystemConfig(db.Model):
    __tablename__ = 'SystemConfig'
    Id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    ConfigKey = db.Column(db.String(50), unique=True, nullable=False)
    ConfigValue = db.Column(db.String(500))
    Description = db.Column(db.String(200))
    UpdatedAt = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    UpdatedBy = db.Column(db.String(36), db.ForeignKey('AspNetUsers.Id'))

class ParkingRate(db.Model):
    __tablename__ = 'ParkingRates'
    Id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    VehicleType = db.Column(db.String(50), nullable=False)
    BaseRate = db.Column(db.Numeric(10, 2), nullable=False)
    HourlyRate = db.Column(db.Numeric(10, 2), nullable=False)
    MaximumDaily = db.Column(db.Numeric(10, 2))
    IsActive = db.Column(db.Boolean, default=True)
    UpdatedAt = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    UpdatedBy = db.Column(db.String(36), db.ForeignKey('AspNetUsers.Id'))

class ActivityLog(db.Model):
    __tablename__ = 'ActivityLogs'
    Id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    UserId = db.Column(db.String(36), db.ForeignKey('AspNetUsers.Id'))
    Action = db.Column(db.String(50), nullable=False)
    Details = db.Column(db.String(500))
    IpAddress = db.Column(db.String(50))
    CreatedAt = db.Column(db.DateTime, default=datetime.utcnow)
    Status = db.Column(db.String(20))

class HardwareStatus(db.Model):
    __tablename__ = 'HardwareStatus'
    Id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    DeviceType = db.Column(db.String(50), nullable=False)
    DeviceId = db.Column(db.String(50), nullable=False)
    Status = db.Column(db.String(20), nullable=False)
    LastPing = db.Column(db.DateTime)
    Location = db.Column(db.String(100))
    Details = db.Column(db.String(500))

class Vehicles(db.Model):
    __tablename__ = 'Vehicles'
    Id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    PlateNumber = db.Column(db.String(20), unique=True, nullable=False)
    VehicleType = db.Column(db.String(50))
    IsParked = db.Column(db.Boolean, default=False)
    EntryTime = db.Column(db.DateTime)
    LastUpdated = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class ParkingTickets(db.Model):
    __tablename__ = 'ParkingTickets'
    Id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    TicketNumber = db.Column(db.String(20), unique=True, nullable=False)
    VehicleId = db.Column(db.String(36), db.ForeignKey('Vehicles.Id'))
    EntryTime = db.Column(db.DateTime, nullable=False)
    ExitTime = db.Column(db.DateTime)
    Status = db.Column(db.String(20), default='active')
    IssuedBy = db.Column(db.String(36), db.ForeignKey('AspNetUsers.Id'))

class ParkingTransactions(db.Model):
    __tablename__ = 'ParkingTransactions'
    Id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    TicketId = db.Column(db.String(36), db.ForeignKey('ParkingTickets.Id'))
    Amount = db.Column(db.Numeric(10, 2), nullable=False)
    PaymentMethod = db.Column(db.String(20))
    PaymentStatus = db.Column(db.String(20))
    ProcessedAt = db.Column(db.DateTime, default=datetime.utcnow)
    ProcessedBy = db.Column(db.String(36), db.ForeignKey('AspNetUsers.Id'))

class ParkingSpaces(db.Model):
    __tablename__ = 'ParkingSpaces'
    Id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    SpaceNumber = db.Column(db.String(10), unique=True, nullable=False)
    VehicleType = db.Column(db.String(50))
    Status = db.Column(db.String(20), default='available')
    CurrentVehicleId = db.Column(db.String(36), db.ForeignKey('Vehicles.Id'))
    LastUpdated = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class AccessTokens(db.Model):
    __tablename__ = 'AccessTokens'
    Id = db.Column(db.String(36), primary_key=True)
    Token = db.Column(db.String(500), nullable=False)
    UserId = db.Column(db.String(36), db.ForeignKey('AspNetUsers.Id'))
    CreatedAt = db.Column(db.DateTime, default=datetime.utcnow)
    ExpiresAt = db.Column(db.DateTime, nullable=False)
    IsRevoked = db.Column(db.Boolean, default=False)
