from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.exceptions import NotFound
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from flask import url_for, current_app
from flask_sqlalchemy import SQLAlchemy
from .helpers import args_from_url
from .errors import ValidationError

db = SQLAlchemy()


class Registration(db.Model):
    __tablename__ = 'registrations'
    student_id = db.Column('student_id', db.Integer,
                           db.ForeignKey('students.id'), primary_key=True)
    class_id = db.Column('class_id', db.Integer,
                         db.ForeignKey('classes.id'), primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    def get_url(self):
        return url_for('api.get_registration', student_id=self.student_id,
                       class_id=self.class_id, _external=True)

    def export_data(self):
        return {'self_url': self.get_url(),
                'student_url': url_for('api.get_student', id=self.student_id,
                                       _external=True),
                'class_url': url_for('api.get_class', id=self.class_id,
                                     _external=True),
                'timestamp': self.timestamp.isoformat() + 'Z'}

    def import_data(self, data):
        try:
            student_id = args_from_url(data['student_url'],
                                       'api.get_student')['id']
            self.student = Student.query.get_or_404(student_id)
        except (KeyError, NotFound):
            raise ValidationError('Invalid student URL')
        try:
            class_id = args_from_url(data['class_url'], 'api.get_class')['id']
            self.class_ = Class.query.get_or_404(class_id)
        except (KeyError, NotFound):
            raise ValidationError('Invalid class URL')
        return self


class Student(db.Model):
    __tablename__ = 'students'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), index=True)
    registrations = db.relationship(
        'Registration',
        backref=db.backref('student', lazy='joined'),
        lazy='dynamic', cascade='all, delete-orphan')

    def get_url(self):
        return url_for('api.get_student', id=self.id, _external=True)

    def export_data(self):
        return {'self_url': self.get_url(),
                'name': self.name,
                'registrations_url': url_for('api.get_student_registrations',
                                             id=self.id, _external=True)}

    def import_data(self, data):
        try:
            self.name = data['name']
        except KeyError as e:
            raise ValidationError('Invalid student: missing ' + e.args[0])
        return self


class Class(db.Model):
    __tablename__ = 'classes'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), index=True)
    registrations = db.relationship(
        'Registration',
        backref=db.backref('class_', lazy='joined'),
        lazy='dynamic', cascade='all, delete-orphan')

    def get_url(self):
        return url_for('api.get_class', id=self.id, _external=True)

    def export_data(self):
        return {'self_url': self.get_url(),
                'name': self.name,
                'registrations_url': url_for('api.get_class_registrations',
                                             id=self.id, _external=True)}

    def import_data(self, data):
        try:
            self.name = data['name']
        except KeyError as e:
            raise ValidationError('Invalid class: missing ' + e.args[0])
        return self


class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True)
    password_hash = db.Column(db.String(128))

    @property
    def password(self):
        raise AttributeError('password is not a readable attribute')

    @password.setter
    def password(self, password):
        self.password_hash = generate_password_hash(password)

    def verify_password(self, password):
        return check_password_hash(self.password_hash, password)

    def generate_auth_token(self, expires_in=3600):
        s = Serializer(current_app.config['SECRET_KEY'], expires_in=expires_in)
        return s.dumps({'id': self.id}).decode('utf-8')

    @staticmethod
    def verify_auth_token(token):
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token)
        except:
            return None
        return User.query.get(data['id'])

