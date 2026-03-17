"""
Blueprint pro lokální generátor faktur.
Prefix: /faktury
"""
from flask import Blueprint, render_template, redirect, url_for, request, flash, Response, jsonify
from flask_login import login_required, current_user
from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta
from sqlalchemy import func, text
from models import db, Zakazka, Projekt, LogEntry
from models_invoice import (
    SupplierProfile, Customer, LocalInvoice, LocalInvoiceItem,
    InvoiceTemplate, InvoiceCounter, InvoiceSettings,
    get_next_invoice_number
)
import json

bp = Blueprint('faktury', __name__, url_prefix='/faktury')


# ============================================================
#  Profil dodavatele
# ============================================================

@bp.route('/dodavatel', methods=['GET', 'POST'])
@login_required
def supplier_profile():
    profile = SupplierProfile.query.filter_by(user_id=current_user.id).first()
    if request.method == 'POST':
        if not profile:
            profile = SupplierProfile(user_id=current_user.id)
            db.session.add(profile)
        profile.company_name = request.form.get('company_name', '').strip()
        profile.street = request.form.get('street', '').strip()
        profile.city = request.form.get('city', '').strip()
        profile.zip_code = request.form.get('zip_code', '').strip()
        profile.country = request.form.get('country', 'Česká republika').strip()
        profile.ic = request.form.get('ic', '').strip()
        profile.dic = request.form.get('dic', '').strip()
        profile.is_vat_payer = request.form.get('is_vat_payer') == 'on'
        profile.email = request.form.get('email', '').strip()
        profile.phone = request.form.get('phone', '').strip()
        profile.bank_account = request.form.get('bank_account', '').strip()
        profile.iban = request.form.get('iban', '').strip()
        profile.swift_bic = request.form.get('swift_bic', '').strip()
        profile.constant_symbol = request.form.get('constant_symbol', '0308').strip()
        profile.payment_method = request.form.get('payment_method', 'Převodem').strip()
        profile.late_payment_text = request.form.get('late_payment_text', '').strip()
        db.session.commit()
        flash('Profil dodavatele uložen.')
        return redirect(url_for('faktury.supplier_profile'))

    return render_template('supplier_profile.html', profile=profile)


# ============================================================
#  Správa odběratelů
# ============================================================

@bp.route('/odberatele')
@login_required
def customers():
    all_customers = Customer.query.filter_by(user_id=current_user.id)\
        .order_by(Customer.company_name).all()
    return render_template('customers.html', customers=all_customers)


@bp.route('/odberatele/novy', methods=['GET', 'POST'])
@login_required
def customer_create():
    if request.method == 'POST':
        c = Customer(user_id=current_user.id)
        _fill_customer(c, request.form)
        db.session.add(c)
        db.session.commit()
        flash('Odběratel vytvořen.')
        return redirect(url_for('faktury.customers'))
    return render_template('customer_form.html', customer=None)


@bp.route('/odberatele/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def customer_edit(id):
    c = Customer.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    if request.method == 'POST':
        _fill_customer(c, request.form)
        db.session.commit()
        flash('Odběratel upraven.')
        return redirect(url_for('faktury.customers'))
    return render_template('customer_form.html', customer=c)


@bp.route('/odberatele/<int:id>/smazat', methods=['POST'])
@login_required
def customer_delete(id):
    c = Customer.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    if c.invoices:
        flash('Nelze smazat odběratele s existujícími fakturami.')
        return redirect(url_for('faktury.customers'))
    db.session.delete(c)
    db.session.commit()
    flash('Odběratel smazán.')
    return redirect(url_for('faktury.customers'))


def _fill_customer(c, form):
    c.company_name = form.get('company_name', '').strip()
    c.street = form.get('street', '').strip()
    c.city = form.get('city', '').strip()
    c.zip_code = form.get('zip_code', '').strip()
    c.country = form.get('country', 'Česká republika').strip()
    c.ic = form.get('ic', '').strip()
    c.dic = form.get('dic', '').strip()
    c.email = form.get('email', '').strip()
    c.phone = form.get('phone', '').strip()
    c.note = form.get('note', '').strip()


# ============================================================
#  Seznam faktur
# ============================================================

@bp.route('/')
@login_required
def invoice_list():
    status_filter = request.args.get('status', '')
    q = LocalInvoice.query.filter_by(user_id=current_user.id)
    if status_filter:
        q = q.filter_by(status=status_filter)
    invoices = q.order_by(LocalInvoice.date_issued.desc()).all()
    return render_template('local_invoices.html', invoices=invoices, status_filter=status_filter)


# ============================================================
#  Vytvoření / editace faktury
# ============================================================

@bp.route('/nova', methods=['GET', 'POST'])
@login_required
def invoice_create():
    supplier = SupplierProfile.query.filter_by(user_id=current_user.id).first()
    if not supplier:
        flash('Nejprve vyplňte profil dodavatele.')
        return redirect(url_for('faktury.supplier_profile'))

    customers_list = Customer.query.filter_by(user_id=current_user.id)\
        .order_by(Customer.company_name).all()

    if request.method == 'POST':
        return _save_invoice(None, supplier, request.form)

    # Předvyplnění z query parametrů (šablona / docházka)
    prefill = _get_prefill_data()

    return render_template('local_invoice_form.html',
                           invoice=None,
                           supplier=supplier,
                           customers=customers_list,
                           prefill=prefill)


@bp.route('/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def invoice_edit(id):
    inv = LocalInvoice.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    if inv.status != 'draft':
        flash('Lze editovat pouze koncepty.')
        return redirect(url_for('faktury.invoice_detail', id=id))

    supplier = SupplierProfile.query.filter_by(user_id=current_user.id).first()
    customers_list = Customer.query.filter_by(user_id=current_user.id)\
        .order_by(Customer.company_name).all()

    if request.method == 'POST':
        return _save_invoice(inv, supplier, request.form)

    return render_template('local_invoice_form.html',
                           invoice=inv,
                           supplier=supplier,
                           customers=customers_list,
                           prefill=None)


@bp.route('/<int:id>')
@login_required
def invoice_detail(id):
    inv = LocalInvoice.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    supplier = SupplierProfile.query.filter_by(user_id=current_user.id).first()
    return render_template('local_invoice_detail.html', invoice=inv, supplier=supplier)


@bp.route('/<int:id>/smazat', methods=['POST'])
@login_required
def invoice_delete(id):
    inv = LocalInvoice.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    if inv.status != 'draft':
        flash('Lze smazat pouze koncepty.')
        return redirect(url_for('faktury.invoice_list'))
    db.session.delete(inv)
    db.session.commit()
    flash('Faktura smazána.')
    return redirect(url_for('faktury.invoice_list'))


@bp.route('/<int:id>/stav', methods=['POST'])
@login_required
def invoice_status(id):
    inv = LocalInvoice.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    new_status = request.form.get('status')
    allowed_transitions = {
        'draft': ['issued', 'cancelled'],
        'issued': ['paid', 'cancelled'],
        'paid': [],
        'cancelled': ['draft']
    }
    if new_status in allowed_transitions.get(inv.status, []):
        inv.status = new_status
        db.session.commit()
        flash(f'Stav faktury změněn na: {inv.status_label}')
    else:
        flash('Neplatný přechod stavu.')
    return redirect(url_for('faktury.invoice_detail', id=id))


# ============================================================
#  PDF generování
# ============================================================

@bp.route('/<int:id>/pdf')
@login_required
def invoice_pdf(id):
    inv = LocalInvoice.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    supplier = SupplierProfile.query.filter_by(user_id=current_user.id).first()

    from pdf_generator import generate_invoice_pdf
    pdf_bytes = generate_invoice_pdf(inv, supplier)

    return Response(
        pdf_bytes,
        mimetype='application/pdf',
        headers={'Content-Disposition': f'attachment; filename=faktura_{inv.invoice_number}.pdf'}
    )


# ============================================================
#  Šablony faktur
# ============================================================

@bp.route('/sablony')
@login_required
def template_list():
    templates = InvoiceTemplate.query.filter_by(user_id=current_user.id)\
        .order_by(InvoiceTemplate.name).all()
    return render_template('invoice_templates.html', templates=templates)


@bp.route('/sablony/nova', methods=['GET', 'POST'])
@login_required
def template_create():
    customers_list = Customer.query.filter_by(user_id=current_user.id)\
        .order_by(Customer.company_name).all()
    if request.method == 'POST':
        t = InvoiceTemplate(user_id=current_user.id)
        _fill_template(t, request.form)
        db.session.add(t)
        db.session.commit()
        flash('Šablona vytvořena.')
        return redirect(url_for('faktury.template_list'))
    return render_template('invoice_template_form.html', template=None, customers=customers_list)


@bp.route('/sablony/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def template_edit(id):
    t = InvoiceTemplate.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    customers_list = Customer.query.filter_by(user_id=current_user.id)\
        .order_by(Customer.company_name).all()
    if request.method == 'POST':
        _fill_template(t, request.form)
        db.session.commit()
        flash('Šablona upravena.')
        return redirect(url_for('faktury.template_list'))
    return render_template('invoice_template_form.html', template=t, customers=customers_list)


@bp.route('/sablony/<int:id>/smazat', methods=['POST'])
@login_required
def template_delete(id):
    t = InvoiceTemplate.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    db.session.delete(t)
    db.session.commit()
    flash('Šablona smazána.')
    return redirect(url_for('faktury.template_list'))


@bp.route('/sablony/<int:id>/pouzit')
@login_required
def template_use(id):
    t = InvoiceTemplate.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    return redirect(url_for('faktury.invoice_create', template_id=t.id))


def _fill_template(t, form):
    t.name = form.get('name', '').strip()
    cid = form.get('customer_id', '')
    t.customer_id = int(cid) if cid else None
    days = form.get('default_due_days', '14')
    t.default_due_days = int(days) if days else 14
    t.default_payment_method = form.get('default_payment_method', 'Převodem').strip()
    t.default_constant_symbol = form.get('default_constant_symbol', '0308').strip()
    t.note = form.get('note', '').strip()

    # Položky šablony
    items = []
    descriptions = form.getlist('item_description[]')
    quantities = form.getlist('item_quantity[]')
    units = form.getlist('item_unit[]')
    prices = form.getlist('item_unit_price[]')
    for i, desc in enumerate(descriptions):
        if desc.strip():
            qty = quantities[i].strip() if i < len(quantities) else ''
            items.append({
                'description': desc.strip(),
                'quantity': float(qty) if qty else None,
                'unit': units[i].strip() if i < len(units) else 'hod',
                'unit_price': float(prices[i]) if i < len(prices) and prices[i].strip() else 0
            })
    t.items_json = json.dumps(items, ensure_ascii=False)


# ============================================================
#  Integrace s docházkou
# ============================================================

@bp.route('/z-dochazky')
@login_required
def from_timesheet():
    """Předvyplní fakturu z docházkových dat."""
    month = request.args.get('month')
    zakazka_id = request.args.get('zakazka_id', type=int)
    if not month or not zakazka_id:
        flash('Chybí parametry měsíce nebo zakázky.')
        return redirect(url_for('faktury.invoice_create'))

    return redirect(url_for('faktury.invoice_create', month=month, zakazka_id=zakazka_id))


# ============================================================
#  Pomocné funkce
# ============================================================

def _get_prefill_data():
    """Získá data pro předvyplnění z query parametrů."""
    prefill = {}

    # Z šablony
    template_id = request.args.get('template_id', type=int)
    if template_id:
        t = InvoiceTemplate.query.filter_by(id=template_id, user_id=current_user.id).first()
        if t:
            prefill['customer_id'] = t.customer_id
            prefill['due_days'] = t.default_due_days
            prefill['payment_method'] = t.default_payment_method
            prefill['constant_symbol'] = t.default_constant_symbol
            prefill['note'] = t.note or ''
            prefill['template_id'] = t.id
            if t.items_json:
                prefill['items'] = json.loads(t.items_json)

    # Z docházky
    month = request.args.get('month')
    zakazka_id = request.args.get('zakazka_id', type=int)
    if month and zakazka_id:
        start_date = datetime.strptime(f"{month}-01", '%Y-%m-%d')
        end_date = start_date + relativedelta(months=1)

        total_minutes = db.session.query(
            func.sum(
                func.timestampdiff(text('MINUTE'), LogEntry.start_time, LogEntry.end_time)
            )
        ).join(Projekt).filter(
            Projekt.zakazka_id == zakazka_id,
            LogEntry.user_id == current_user.id,
            LogEntry.start_time >= start_date,
            LogEntry.start_time < end_date
        ).scalar() or 0

        hours = round(float(total_minutes) / 60.0, 2)
        zakazka = Zakazka.query.get(zakazka_id)
        settings = InvoiceSettings.query.filter_by(zakazka_id=zakazka_id).first()

        item_name = 'Softwarový vývoj'
        unit_price = 0
        if settings:
            item_name = settings.idoklad_item_name or item_name
            unit_price = settings.hourly_rate or 0

        if zakazka:
            prefill['items'] = [{
                'description': f'{item_name} za {month}, zakázka {zakazka.name}',
                'quantity': hours,
                'unit': 'hod',
                'unit_price': unit_price
            }]
            prefill['source_month'] = month
            prefill['source_zakazka_id'] = zakazka_id
            # Najdi odběratele podle zakázky (pokud existuje)
            if settings and settings.idoklad_contact_id:
                # Zkusíme najít odběratele podle IČ nebo názvu
                pass

    return prefill


def _save_invoice(existing_inv, supplier, form):
    """Uloží nebo vytvoří fakturu z formuláře."""
    if existing_inv:
        inv = existing_inv
        # Smazat staré položky
        LocalInvoiceItem.query.filter_by(invoice_id=inv.id).delete()
    else:
        inv = LocalInvoice(user_id=current_user.id)
        inv.invoice_number = get_next_invoice_number(current_user.id)
        inv.variable_symbol = inv.invoice_number
        db.session.add(inv)

    customer_id = form.get('customer_id', '')
    inv.customer_id = int(customer_id) if customer_id else None
    inv.date_issued = datetime.strptime(form.get('date_issued'), '%Y-%m-%d').date() \
        if form.get('date_issued') else date.today()
    inv.date_due = datetime.strptime(form.get('date_due'), '%Y-%m-%d').date() \
        if form.get('date_due') else (date.today() + timedelta(days=14))
    inv.constant_symbol = form.get('constant_symbol', '0308').strip()
    inv.payment_method = form.get('payment_method', 'Převodem').strip()
    inv.note = form.get('note', '').strip()
    inv.source_month = form.get('source_month', '').strip() or None
    source_z = form.get('source_zakazka_id', '')
    inv.source_zakazka_id = int(source_z) if source_z else None
    template_id = form.get('template_id', '')
    inv.template_id = int(template_id) if template_id else None

    # Stav
    if form.get('action') == 'issue':
        inv.status = 'issued'
    else:
        inv.status = 'draft'

    # Položky
    descriptions = form.getlist('item_description[]')
    quantities = form.getlist('item_quantity[]')
    units = form.getlist('item_unit[]')
    prices = form.getlist('item_unit_price[]')

    total = 0
    for i, desc in enumerate(descriptions):
        if desc.strip():
            qty = float(quantities[i]) if i < len(quantities) and quantities[i].strip() else 0
            price = float(prices[i]) if i < len(prices) and prices[i].strip() else 0
            item_total = round(qty * price, 2)
            total += item_total
            item = LocalInvoiceItem(
                description=desc.strip(),
                quantity=qty,
                unit=units[i].strip() if i < len(units) else 'hod',
                unit_price=price,
                total=item_total,
                sort_order=i
            )
            inv.items.append(item)

    inv.total_amount = total
    db.session.commit()
    flash(f'Faktura {inv.invoice_number} {"vystavena" if inv.status == "issued" else "uložena jako koncept"}.')
    return redirect(url_for('faktury.invoice_detail', id=inv.id))
