"""
Generátor PDF faktur s QR kódem a čárovým kódem.
Používá WeasyPrint (HTML → PDF).
"""
import io
import base64
import qrcode
import barcode
from barcode.writer import ImageWriter
from flask import render_template
from weasyprint import HTML


def czech_account_to_iban(account):
    """Převede české číslo účtu (formát 'účet/kód') na IBAN CZ.
    Např. '2619529193/0800' → 'CZ4708000000002619529193'
    """
    if not account or '/' not in account:
        return None
    parts = account.strip().split('/')
    if len(parts) != 2:
        return None

    account_part = parts[0]
    bank_code = parts[1]

    # Rozdělit na předčíslí a hlavní číslo
    if '-' in account_part:
        prefix, main = account_part.split('-', 1)
    else:
        prefix = '0'
        main = account_part

    # BBAN = kód banky (4) + předčíslí (6, doplněno nulami) + číslo účtu (10, doplněno nulami)
    bban = f"{bank_code:0>4}{prefix:0>6}{main:0>10}"

    # Výpočet kontrolního čísla IBAN
    # Přesunout CZ00 na konec: BBAN + CZ00 → BBAN + 1235 + 00
    check_str = bban + '123500'
    check_num = int(check_str)
    check_digits = 98 - (check_num % 97)

    return f"CZ{check_digits:02d}{bban}"


def generate_qr_payment(iban, amount, variable_symbol, constant_symbol='0308', message=''):
    """Generuje QR kód pro českou QR Platbu (SPD standard)."""
    # Odstranit mezery z IBAN
    iban_clean = iban.replace(' ', '') if iban else ''
    if not iban_clean:
        return None

    spayd = f"SPD*1.0*ACC:{iban_clean}*AM:{amount:.2f}*CC:CZK"
    if variable_symbol:
        spayd += f"*X-VS:{variable_symbol}"
    if constant_symbol:
        spayd += f"*X-KS:{constant_symbol}"
    if message:
        spayd += f"*MSG:{message[:60]}"

    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=6,
        border=2
    )
    qr.add_data(spayd)
    qr.make(fit=True)
    img = qr.make_image(fill_color='black', back_color='white')

    buf = io.BytesIO()
    img.save(buf, format='PNG')
    return base64.b64encode(buf.getvalue()).decode('ascii')


def generate_barcode_image(invoice_number):
    """Generuje čárový kód (Code128) pro číslo faktury."""
    if not invoice_number:
        return None

    code128 = barcode.get('code128', invoice_number, writer=ImageWriter())
    buf = io.BytesIO()
    code128.write(buf, options={
        'write_text': False,
        'module_height': 8,
        'module_width': 0.25,
        'quiet_zone': 2
    })
    return base64.b64encode(buf.getvalue()).decode('ascii')


def format_czk(amount):
    """Formátuje částku v českém formátu: 14 000,00"""
    if amount is None:
        return '0,00'
    amount = float(amount)
    # Celé číslo a desetinná část
    integer_part = int(abs(amount))
    decimal_part = round((abs(amount) - integer_part) * 100)

    # Tisícové oddělovače (mezery)
    int_str = f'{integer_part:,}'.replace(',', ' ')
    result = f'{int_str},{decimal_part:02d}'
    if amount < 0:
        result = '-' + result
    return result


def generate_invoice_pdf(invoice, supplier):
    """Generuje PDF faktury jako bytes."""
    # QR kód pro platbu — preferuje IBAN, fallback na převod z čísla účtu
    qr_base64 = None
    if supplier:
        iban = supplier.iban
        if not iban and supplier.bank_account:
            iban = czech_account_to_iban(supplier.bank_account)
        if iban:
            qr_base64 = generate_qr_payment(
                iban=iban,
                amount=float(invoice.total_amount),
                variable_symbol=invoice.variable_symbol or invoice.invoice_number,
                constant_symbol=invoice.constant_symbol or '0308'
            )

    # Čárový kód
    barcode_base64 = generate_barcode_image(invoice.invoice_number)

    # Render HTML šablony
    html_content = render_template(
        'local_invoice_pdf.html',
        invoice=invoice,
        supplier=supplier,
        customer=invoice.customer,
        items=invoice.items,
        qr_base64=qr_base64,
        barcode_base64=barcode_base64,
        format_czk=format_czk,
        now=datetime.now() if True else None
    )

    # Konverze na PDF
    pdf = HTML(string=html_content).write_pdf()
    return pdf


# Import datetime pro now
from datetime import datetime
