from models import db

class InvoiceSettings(db.Model):
    __tablename__ = 'invoice_settings'
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    idoklad_contact_id = db.Column(db.Integer)
    idoklad_item_name = db.Column(db.String(200))
    hourly_rate = db.Column(db.Float)
    hours_per_md = db.Column(db.Float, default=8)
    default_description = db.Column(db.Text)
    vat_rate = db.Column(db.Float, default=21)  # DPH
    
    project = db.relationship('Project', backref='invoice_settings')

class UserSettings(db.Model):
    __tablename__ = 'user_settings'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), unique=True)
    idoklad_api_key = db.Column(db.String(255))
    idoklad_api_secret = db.Column(db.String(255))
    
    user = db.relationship('User', backref=db.backref('settings', uselist=False))

class InvoiceHistory(db.Model):
    __tablename__ = 'invoice_history'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'))
    month = db.Column(db.String(7))  # YYYY-MM
    hours = db.Column(db.Float)
    invoice_number = db.Column(db.String(50))
    idoklad_invoice_id = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=db.func.now())
    
    user = db.relationship('User')
    project = db.relationship('Project')