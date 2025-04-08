from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from typing import Optional
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Numeric, ForeignKey, JSON
from sqlalchemy.ext.hybrid import hybrid_property

db = SQLAlchemy()

class AspNetUsers(db.Model, UserMixin):
    Id = db.Column(db.String(36), primary_key=True)
    UserName = db.Column(db.String(256))
    Email = db.Column(db.String(256))
    PasswordHash = db.Column(db.String(256))
    FullName = db.Column(db.String(256))
    CreatedAt = db.Column(db.DateTime, default=datetime.utcnow)
    IsActive = db.Column(db.Boolean, default=True)

class AccessTokens(db.Model):
    Id = db.Column(db.Integer, primary_key=True)
    Token = db.Column(db.String(500), unique=True)
    UserId = db.Column(db.String(36), db.ForeignKey('asp_net_users.Id'))
    IsRevoked = db.Column(db.Boolean, default=False)
    ExpiresAt = db.Column(db.DateTime)
    CreatedAt = db.Column(db.DateTime, default=datetime.utcnow)

class AspNetRoles(db.Model):
    Id = db.Column(db.String(36), primary_key=True)
    Name = db.Column(db.String(256))
    Description = db.Column(db.String(256))

class AspNetUserRoles(db.Model):
    UserId = db.Column(db.String(36), db.ForeignKey('asp_net_users.Id'), primary_key=True)
    RoleId = db.Column(db.String(36), db.ForeignKey('asp_net_roles.Id'), primary_key=True)

class SystemConfig(db.Model):
    Id = db.Column(db.Integer, primary_key=True)
    ConfigKey = db.Column(db.String(50), unique=True)
    ConfigValue = db.Column(db.String(500))
    Description = db.Column(db.String(500))
    UpdatedAt = db.Column(db.DateTime, default=datetime.utcnow)
    UpdatedBy = db.Column(db.String(36), db.ForeignKey('asp_net_users.Id'))

class ParkingRate(db.Model):
    __tablename__ = 'ParkingRate'
    Id = db.Column(db.Integer, primary_key=True)
    VehicleType = db.Column(db.String(50), nullable=False)
    DurationType = db.Column(db.String(50), nullable=False)
    BaseDuration = db.Column(db.Integer, nullable=False)
    BaseRate = db.Column(db.Numeric(10, 2), nullable=False)
    AdditionalRate = db.Column(db.Numeric(10, 2))
    MaxDailyRate = db.Column(db.Numeric(10, 2))
    IsActive = db.Column(db.Boolean, default=True)
    CreatedAt = db.Column(db.DateTime, default=datetime.utcnow)
    UpdatedAt = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Members(db.Model):
    Id = db.Column(db.Integer, primary_key=True)
    MemberNumber = db.Column(db.String(20), unique=True)
    FullName = db.Column(db.String(100))
    Email = db.Column(db.String(100))
    Phone = db.Column(db.String(20))
    Address = db.Column(db.String(200))
    JoinDate = db.Column(db.DateTime, default=datetime.utcnow)
    ExpiryDate = db.Column(db.DateTime)
    Status = db.Column(db.String(20))  # active, expired, suspended
    CreatedAt = db.Column(db.DateTime, default=datetime.utcnow)
    UpdatedAt = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class MemberCards(db.Model):
    Id = db.Column(db.Integer, primary_key=True)
    MemberId = db.Column(db.Integer, db.ForeignKey('members.Id'))
    CardNumber = db.Column(db.String(50), unique=True)
    IssuedDate = db.Column(db.DateTime, default=datetime.utcnow)
    ExpiryDate = db.Column(db.DateTime)
    Status = db.Column(db.String(20))  # active, expired, lost, replaced
    ReplacementReason = db.Column(db.String(200))
    CreatedAt = db.Column(db.DateTime, default=datetime.utcnow)

class MemberRates(db.Model):
    Id = db.Column(db.Integer, primary_key=True)
    MembershipType = db.Column(db.String(50))  # regular, premium, vip
    VehicleType = db.Column(db.String(50))
    DurationType = db.Column(db.String(20))
    Rate = db.Column(db.Numeric(10, 2))
    IsActive = db.Column(db.Boolean, default=True)
    CreatedAt = db.Column(db.DateTime, default=datetime.utcnow)

class Staff(db.Model):
    Id = db.Column(db.Integer, primary_key=True)
    StaffNumber = db.Column(db.String(20), unique=True)
    FullName = db.Column(db.String(100))
    Email = db.Column(db.String(100))
    Phone = db.Column(db.String(20))
    Position = db.Column(db.String(50))
    JoinDate = db.Column(db.DateTime, default=datetime.utcnow)
    Status = db.Column(db.String(20))  # active, inactive
    UserId = db.Column(db.String(36), db.ForeignKey('asp_net_users.Id'))
    CreatedAt = db.Column(db.DateTime, default=datetime.utcnow)

class StaffAttendance(db.Model):
    Id = db.Column(db.Integer, primary_key=True)
    StaffId = db.Column(db.Integer, db.ForeignKey('staff.Id'))
    CheckInTime = db.Column(db.DateTime)
    CheckOutTime = db.Column(db.DateTime)
    ShiftId = db.Column(db.Integer, db.ForeignKey('shifts.Id'))
    Status = db.Column(db.String(20))  # present, absent, late
    Notes = db.Column(db.String(200))

class Shifts(db.Model):
    Id = db.Column(db.Integer, primary_key=True)
    ShiftName = db.Column(db.String(50))
    StartTime = db.Column(db.Time)
    EndTime = db.Column(db.Time)
    Description = db.Column(db.String(200))
    IsActive = db.Column(db.Boolean, default=True)

class Vehicles(db.Model):
    __tablename__ = 'Vehicles'
    Id = db.Column(db.String(36), primary_key=True)
    plate_number = db.Column(db.String(20), unique=True, nullable=False)
    vehicle_type = db.Column(db.String(50), nullable=False)
    status = db.Column(db.String(20), default='active')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class ParkingSpaces(db.Model):
    Id = db.Column(db.Integer, primary_key=True)
    SpaceNumber = db.Column(db.String(10))
    Level = db.Column(db.String(10))
    Section = db.Column(db.String(10))
    VehicleType = db.Column(db.String(50))
    IsOccupied = db.Column(db.Boolean, default=False)
    Status = db.Column(db.String(20))  # available, maintenance, reserved

class ParkingTickets(db.Model):
    Id = db.Column(db.Integer, primary_key=True)
    TicketNumber = db.Column(db.String(20), unique=True)
    VehicleId = db.Column(db.Integer, db.ForeignKey('vehicles.Id'))
    SpaceId = db.Column(db.Integer, db.ForeignKey('parking_spaces.Id'))
    EntryTime = db.Column(db.DateTime, default=datetime.utcnow)
    ExitTime = db.Column(db.DateTime)
    Duration = db.Column(db.Integer)  # in minutes
    Amount = db.Column(db.Numeric(10, 2))
    Status = db.Column(db.String(20))  # active, completed, cancelled
    CreatedBy = db.Column(db.String(36), db.ForeignKey('asp_net_users.Id'))

class ParkingTransactions(db.Model):
    __tablename__ = 'ParkingTransactions'
    Id = db.Column(db.String(36), primary_key=True)
    ticket_id = db.Column(db.String(36), db.ForeignKey('ParkingTickets.Id'), nullable=False)
    transaction_number = db.Column(db.String(50), unique=True, nullable=False)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    payment_method = db.Column(db.String(50), nullable=False)
    status = db.Column(db.String(20), default='pending')
    processed_by = db.Column(db.String(36), db.ForeignKey('AspNetUsers.Id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class HardwareStatus(db.Model):
    Id = db.Column(db.Integer, primary_key=True)
    DeviceId = db.Column(db.String(50))
    DeviceType = db.Column(db.String(50))  # entry_gate, exit_gate, camera, sensor
    Location = db.Column(db.String(100))
    Status = db.Column(db.String(20))  # online, offline, maintenance
    LastPing = db.Column(db.DateTime)
    IpAddress = db.Column(db.String(15))
    Details = db.Column(db.JSON)

class ActivityLog(db.Model):
    __tablename__ = 'ActivityLog'
    Id = db.Column(db.Integer, primary_key=True)
    Action = db.Column(db.String(50), nullable=False)
    Details = db.Column(db.String(500))
    Status = db.Column(db.String(20), default='success')
    UserId = db.Column(db.String(36), db.ForeignKey('AspNetUsers.Id'))
    IpAddress = db.Column(db.String(15))
    IsRead = db.Column(db.Boolean, default=False)
    CreatedAt = db.Column(db.DateTime, default=datetime.utcnow)
