"""The submitted Personal Details Form as a PDF, laid out like BUP's paper form, for HR's file."""

import os
from io import BytesIO
from xml.sax.saxutils import escape

from django.conf import settings
from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import HRFlowable, Image, KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

NAVY = HexColor('#1B2A6B')
GREY = HexColor('#5A6385')
LINE = HexColor('#B9C1DE')
SHADE = HexColor('#EEF1FA')


def _d(value, fmt='%d %B %Y'):
    return value.strftime(fmt) if value else ''


def generate_personal_details_pdf(req):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=14 * mm, bottomMargin=16 * mm,
                            title=f"Personal Details - {req.recipient_name}")
    base = ParagraphStyle('base', fontName='Times-Roman', fontSize=10.5, leading=14)
    small = ParagraphStyle('small', parent=base, fontSize=9, leading=12, textColor=GREY)
    bold = ParagraphStyle('bold', parent=base, fontName='Times-Bold')
    head = ParagraphStyle('head', parent=base, fontName='Times-Bold', fontSize=12, leading=16, textColor=NAVY, spaceBefore=10, spaceAfter=4, keepWithNext=1)
    title = ParagraphStyle('title', parent=base, fontName='Times-Bold', fontSize=16, leading=20, textColor=NAVY, spaceAfter=2)

    def P(text, style=base):
        text = escape((text or '').strip()) or '&nbsp;'
        return Paragraph(text.replace('\n', '<br/>'), style)

    def table(pairs):
        t = Table([[P(k, bold), P(v)] for k, v in pairs], colWidths=[62 * mm, 112 * mm])
        t.setStyle(TableStyle([('GRID', (0, 0), (-1, -1), 0.5, LINE), ('VALIGN', (0, 0), (-1, -1), 'TOP'), ('BACKGROUND', (0, 0), (0, -1), SHADE),
                               ('LEFTPADDING', (0, 0), (-1, -1), 5), ('RIGHTPADDING', (0, 0), (-1, -1), 5),
                               ('TOPPADDING', (0, 0), (-1, -1), 4), ('BOTTOMPADDING', (0, 0), (-1, -1), 4)]))
        return t

    story = []
    logo = os.path.join(settings.BASE_DIR, 'static', 'images', 'logo.png')
    if os.path.exists(logo):
        img = Image(logo, width=40 * mm, height=20 * mm); img.hAlign = 'LEFT'; story.append(img)
    else:
        story.append(Paragraph('<b>BOTSWANA-UPENN PARTNERSHIP</b>', base))
    story.append(HRFlowable(width='100%', thickness=1.5, color=NAVY, spaceAfter=4 * mm, spaceBefore=2 * mm))
    story.append(Paragraph('Personal Details', title))

    gender = req.get_gender_display() if hasattr(req, 'get_gender_display') else req.gender
    marital = req.get_marital_status_display() if hasattr(req, 'get_marital_status_display') else req.marital_status
    idline = req.id_number + (f"   (expires {_d(req.id_expiry)})" if req.id_expiry else '')
    story.append(table([('Names', req.full_names), ('Date of Birth', _d(req.date_of_birth)), ('Gender', gender), ('Marital Status', marital),
                        ('ID no / Passport and Expiry', idline), ('Address: Postal', req.postal_address), ('Address: Physical', req.physical_address),
                        ('Telephone No.', req.telephone), ('Date of assumption of duty', _d(req.assumption_date)),
                        ('Position title', req.position_title), ('E-mail address', req.email_address), ('Program', req.program)]))
    story.append(Paragraph('NEXT OF KIN DETAILS', head))
    story.append(table([('Next of kin names', req.kin_name), ('Relationship', req.kin_relationship), ('Telephone Numbers', req.kin_telephone)]))
    story.append(Paragraph('EMERGENCY CONTACT PERSON DETAILS', head))
    story.append(table([('Contact Names', req.emergency_name), ('Telephone Numbers', req.emergency_telephone), ('Relationship', req.emergency_relationship)]))
    story.append(Paragraph('ACADEMIC QUALIFICATIONS', head))
    story.append(P(req.qualifications or '\u2014'))
    story.append(Paragraph('BANK DETAILS', head))
    story.append(table([('Bank Name', req.bank_name), ('Branch Code', req.bank_branch_code), ('Branch Name', req.bank_branch_name),
                        ('Account Number', req.bank_account_number), ('Names appearing on the account', req.bank_account_name)]))

    story.append(Paragraph('DOCUMENTS RECEIVED', head))
    docs = list(req.documents.all())
    if docs:
        for d in docs:
            label = d.get_kind_display() if hasattr(d, 'get_kind_display') else d.kind
            story.append(P(f"\u2022 {label}: {d.original_name}"))
    else:
        story.append(P('None attached.', small))

    signed = f"Signed electronically by {req.declaration_name}" if req.declaration_name else 'Not signed'
    when = req.submitted_at.strftime('%d %B %Y at %H:%M') if req.submitted_at else ''
    story.append(KeepTogether([Paragraph('Declaration', head),
                               P('I confirm that the above information is a correct record of my personal details.'), Spacer(1, 2 * mm),
                               Paragraph(f"<b>{escape(signed)}</b>", base), P(when, small), Spacer(1, 3 * mm),
                               P(f"Reference {req.pk}. Submitted through the BUP operations system. Confidential: for HR use only.", small)]))
    doc.build(story)
    buffer.seek(0)
    return buffer
