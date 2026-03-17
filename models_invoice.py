from models import db
from datetime import datetime, date
import json

class InvoiceSettings(db.Model):
    __tablename__ = 'invoice_settings'
    id = db.Column(db.Integer, primary_key=True)
    zakazka_id = db.Column(db.Integer, db.ForeignKey('zakazky.id'), nullable=False, unique=True)
    idoklad_contact_id = db.Column(db.Integer)
    idoklad_item_name = db.Column(db.String(200))
    hourly_rate = db.Column(db.Float)
    hours_per_md = db.Column(db.Float, default=8)
    default_description = db.Column(db.Text)
    vat_rate = db.Column(db.Float, default=21)  # DPH

    zakazka = db.relationship('Zakazka', backref=db.backref('invoice_settings', uselist=False))
    # Alias for backward compatibility
    @property
    def project_id(self):
        return self.zakazka_id

    @property
    def project(self):
        return self.zakazka

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
    project_id = db.Column(db.Integer, db.ForeignKey('projekty.id'))
    month = db.Column(db.String(7))  # YYYY-MM
    hours = db.Column(db.Float)
    invoice_number = db.Column(db.String(50))
    idoklad_invoice_id = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=db.func.now())

    user = db.relationship('User')
    projekt = db.relationship('Projekt')
    # Alias for backward compatibility
    @property
    def project(self):
        return self.projekt


# ============================================================
#  Lokální generátor faktur - nové modely
# ============================================================

class SupplierProfile(db.Model):
    """Profil dodavatele (1 na uživatele)"""
    __tablename__ = 'supplier_profile'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), unique=True, nullable=False)
    company_name = db.Column(db.String(200), nullable=False)
    street = db.Column(db.String(200))
    city = db.Column(db.String(100))
    zip_code = db.Column(db.String(20))
    country = db.Column(db.String(100), default='Česká republika')
    ic = db.Column(db.String(20))
    dic = db.Column(db.String(20))
    is_vat_payer = db.Column(db.Boolean, default=False)
    email = db.Column(db.String(200))
    phone = db.Column(db.String(50))
    bank_account = db.Column(db.String(50))  # formát "2619529193/0800"
    iban = db.Column(db.String(50))
    swift_bic = db.Column(db.String(20))
    constant_symbol = db.Column(db.String(10), default='0308')
    payment_method = db.Column(db.String(50), default='Převodem')
    late_payment_text = db.Column(db.Text, default='Dovolujeme si Vás upozornit, že v případě nedodržení data splatnosti uvedeného na faktuře Vám můžeme účtovat zákonný úrok z prodlení.')

    user = db.relationship('User', backref=db.backref('supplier_profile', uselist=False))


class Customer(db.Model):
    """Odběratel (více na uživatele)"""
    __tablename__ = 'customer'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    company_name = db.Column(db.String(200), nullable=False)
    street = db.Column(db.String(200))
    city = db.Column(db.String(100))
    zip_code = db.Column(db.String(20))
    country = db.Column(db.String(100), default='Česká republika')
    ic = db.Column(db.String(20))
    dic = db.Column(db.String(20))
    email = db.Column(db.String(200))
    phone = db.Column(db.String(50))
    note = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref=db.backref('customers', lazy=True))


class InvoiceCounter(db.Model):
    """Čítač faktur pro automatické číslování"""
    __tablename__ = 'invoice_counter'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    year = db.Column(db.Integer, nullable=False)
    last_number = db.Column(db.Integer, default=0)

    __table_args__ = (db.UniqueConstraint('user_id', 'year', name='uq_counter_user_year'),)

    user = db.relationship('User')


def get_next_invoice_number(user_id):
    """Vygeneruje další číslo faktury ve formátu RRRRXXXX (např. 20260001)"""
    current_year = date.today().year
    counter = InvoiceCounter.query.filter_by(user_id=user_id, year=current_year).first()
    if not counter:
        counter = InvoiceCounter(user_id=user_id, year=current_year, last_number=0)
        db.session.add(counter)
    counter.last_number += 1
    db.session.flush()
    return f"{current_year}{counter.last_number:04d}"


class LocalInvoice(db.Model):
    """Lokální faktura"""
    __tablename__ = 'local_invoice'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    invoice_number = db.Column(db.String(20), nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'), nullable=False)
    date_issued = db.Column(db.Date, nullable=False, default=date.today)
    date_due = db.Column(db.Date, nullable=False)
    variable_symbol = db.Column(db.String(20))
    constant_symbol = db.Column(db.String(10), default='0308')
    payment_method = db.Column(db.String(50), default='Převodem')
    note = db.Column(db.Text)
    status = db.Column(db.String(20), default='draft')  # draft, issued, paid, cancelled
    total_amount = db.Column(db.Numeric(12, 2), default=0)
    currency = db.Column(db.String(10), default='CZK')
    source_month = db.Column(db.String(7))  # YYYY-MM, napojení na docházku
    source_zakazka_id = db.Column(db.Integer, db.ForeignKey('zakazky.id'), nullable=True)
    template_id = db.Column(db.Integer, db.ForeignKey('invoice_template.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = db.relationship('User', backref=db.backref('local_invoices', lazy=True))
    customer = db.relationship('Customer', backref=db.backref('invoices', lazy=True))
    items = db.relationship('LocalInvoiceItem', backref='invoice', lazy=True,
                            cascade='all, delete-orphan', order_by='LocalInvoiceItem.sort_order')
    source_zakazka = db.relationship('Zakazka', backref=db.backref('local_invoices', lazy=True))
    template = db.relationship('InvoiceTemplate', backref=db.backref('invoices', lazy=True))

    STATUS_LABELS = {
        'draft': 'Koncept',
        'issued': 'Vystavena',
        'paid': 'Zaplacena',
        'cancelled': 'Stornována'
    }

    @property
    def status_label(self):
        return self.STATUS_LABELS.get(self.status, self.status)

    @property
    def status_color(self):
        colors = {'draft': 'secondary', 'issued': 'primary', 'paid': 'success', 'cancelled': 'danger'}
        return colors.get(self.status, 'secondary')

    def recalculate_total(self):
        self.total_amount = sum(item.total for item in self.items)


class LocalInvoiceItem(db.Model):
    """Položka faktury"""
    __tablename__ = 'local_invoice_item'
    id = db.Column(db.Integer, primary_key=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey('local_invoice.id', ondelete='CASCADE'), nullable=False)
    description = db.Column(db.String(500), nullable=False)
    quantity = db.Column(db.Numeric(10, 2), nullable=False, default=1)
    unit = db.Column(db.String(20), default='hod')
    unit_price = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    total = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    sort_order = db.Column(db.Integer, default=0)


class InvoiceTemplate(db.Model):
    """Šablona pro opakované faktury"""
    __tablename__ = 'invoice_template'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'), nullable=True)
    default_due_days = db.Column(db.Integer, default=14)
    default_payment_method = db.Column(db.String(50), default='Převodem')
    default_constant_symbol = db.Column(db.String(10), default='0308')
    items_json = db.Column(db.Text)  # JSON pole [{description, quantity, unit, unit_price}]
    note = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref=db.backref('invoice_templates', lazy=True))
    customer = db.relationship('Customer')

    @property
    def items_count(self):
        if not self.items_json:
            return 0
        try:
            return len(json.loads(self.items_json))
        except (json.JSONDecodeError, TypeError):
            return 0