from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle, HRFlowable
from reportlab.lib import colors
from reportlab.lib.colors import HexColor
from io import BytesIO
import os
from django.conf import settings
from django.utils import timezone


NAVY = HexColor('#003087')
GOLD = HexColor('#C9A84C')
BLACK = HexColor('#000000')
GREY = HexColor('#666666')


def generate_confirmation_letter_pdf(letter, hr_profile, request):
    buffer = BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=20*mm,
        leftMargin=20*mm,
        topMargin=10*mm,
        bottomMargin=40*mm,
    )

    styles = getSampleStyleSheet()

    # Custom styles
    normal = ParagraphStyle(
        'CustomNormal',
        fontName='Times-Roman',
        fontSize=11,
        leading=16,
        textColor=BLACK,
        alignment=TA_LEFT,
    )
    justified = ParagraphStyle(
        'Justified',
        fontName='Times-Roman',
        fontSize=11,
        leading=16,
        textColor=BLACK,
        alignment=TA_JUSTIFY,
    )
    bold_style = ParagraphStyle(
        'Bold',
        fontName='Times-Bold',
        fontSize=11,
        leading=16,
        textColor=BLACK,
    )
    heading = ParagraphStyle(
        'Heading',
        fontName='Times-Bold',
        fontSize=11,
        leading=16,
        textColor=BLACK,
        alignment=TA_CENTER,
        underline=True,
    )
    footer_style = ParagraphStyle(
        'Footer',
        fontName='Times-Roman',
        fontSize=7,
        leading=10,
        textColor=GREY,
    )

    story = []

    # ── LOGO ──────────────────────────────────────────────────────
    logo_path = os.path.join(settings.BASE_DIR, 'static', 'images', 'logo.png')
    if os.path.exists(logo_path):
        logo = Image(logo_path, width=50*mm, height=25*mm)
        logo.hAlign = 'LEFT'
        story.append(logo)
    else:
        story.append(Paragraph("<b>BOTSWANA-UPENN PARTNERSHIP</b>", bold_style))

    # ── HORIZONTAL LINE ───────────────────────────────────────────
    story.append(Spacer(1, 3*mm))
    story.append(HRFlowable(
        width="100%",
        thickness=1.5,
        color=NAVY,
        spaceAfter=5*mm,
    ))

    # ── DATE ──────────────────────────────────────────────────────
    date_str = letter.date_issued.strftime("%d %B %Y")
    story.append(Paragraph(date_str, normal))
    story.append(Spacer(1, 5*mm))

    # ── SALUTATION ────────────────────────────────────────────────
    story.append(Paragraph("To whom it may concern", normal))
    story.append(Spacer(1, 4*mm))
    story.append(Paragraph("Dear Sir/ Madam", normal))
    story.append(Spacer(1, 6*mm))

    # ── SUBJECT LINE ──────────────────────────────────────────────
    full_name = letter.employee.get_full_name() or letter.employee.username
    subject = f"<u><b>CONFIRMATION OF EMPLOYMENT FOR {letter.salutation} {full_name.upper()}</b></u>"
    story.append(Paragraph(subject, ParagraphStyle(
        'Subject',
        fontName='Times-Bold',
        fontSize=11,
        leading=16,
        alignment=TA_LEFT,
    )))
    story.append(Spacer(1, 8*mm))

    # ── BODY PARAGRAPH 1 ─────────────────────────────────────────
    story.append(Paragraph(
        "The Botswana-UPenn Partnership was formed in 2001, in association with the Ministry of Health, "
        "the University of Botswana, and the University of Pennsylvania.",
        justified
    ))
    story.append(Spacer(1, 5*mm))

    # ── BODY PARAGRAPH 2 ─────────────────────────────────────────
    salary_text = f"BWP {letter.annual_salary:,.2f}" if letter.annual_salary else "BWP ……"
    id_text = letter.employee_id_number if letter.employee_id_number else "……"

    body2 = (
        f"This letter serves to confirm the employment of {letter.salutation} {full_name} "
        f"of (ID# {id_text}) with the University of Pennsylvania o/a Botswana-UPenn Partnership "
        f"as a {letter.job_title}. "
        f"{'His' if letter.salutation in ['Mr.', 'Dr.'] else 'Her'} annual salary is {salary_text}."
    )
    story.append(Paragraph(body2, justified))
    story.append(Spacer(1, 5*mm))

    # ── ADDRESS SECTION ───────────────────────────────────────────
    pronoun = 'His' if letter.salutation in ['Mr.', 'Dr.'] else 'Her'
    story.append(Paragraph(f"{pronoun} physical and postal addresses are:", normal))
    story.append(Spacer(1, 4*mm))

    # Address table (two columns: physical | postal)
    plot_text = f"Plot {letter.plot_number}," if letter.plot_number else "Plot ……,"
    ward_text = f"{letter.ward} Ward" if letter.ward else "…… Ward"
    po_text = letter.po_box if letter.po_box else "P O Box ……"
    city_text = letter.postal_city or "Gaborone"

    addr_data = [
        [
            Paragraph(f"{plot_text} {ward_text}", normal),
            Paragraph("and", normal),
            Paragraph(po_text, normal),
        ],
        [
            Paragraph("Tlokweng", normal),
            Paragraph("", normal),
            Paragraph(city_text, normal),
        ],
    ]
    addr_table = Table(addr_data, colWidths=[70*mm, 15*mm, 75*mm])
    addr_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
    ]))
    story.append(addr_table)
    story.append(Spacer(1, 6*mm))

    # ── CLOSING ───────────────────────────────────────────────────
    story.append(Paragraph(
        "For any additional information or clarity you may contact the undersigned.",
        normal
    ))
    story.append(Spacer(1, 5*mm))
    story.append(Paragraph("Yours sincerely,", normal))
    story.append(Spacer(1, 5*mm))

    # ── SIGNATURE IMAGE ───────────────────────────────────────────
    if hr_profile.signature_image:
        sig_path = os.path.join(settings.MEDIA_ROOT, str(hr_profile.signature_image))
        if os.path.exists(sig_path):
            sig_img = Image(sig_path, width=40*mm, height=18*mm)
            sig_img.hAlign = 'LEFT'
            story.append(sig_img)
        else:
            story.append(Spacer(1, 15*mm))
    else:
        story.append(Spacer(1, 15*mm))

    # ── HR SIGN-OFF ───────────────────────────────────────────────
    story.append(Paragraph(f"<b>{hr_profile.full_name}</b>", normal))
    story.append(Paragraph(hr_profile.job_title, normal))
    story.append(Paragraph(hr_profile.organisation, normal))
    if hr_profile.telephone:
        story.append(Paragraph(f"Tel: {hr_profile.telephone}", normal))

    # ── FOOTER ────────────────────────────────────────────────────
    def draw_footer(canvas, doc):
        canvas.saveState()
        canvas.setStrokeColor(GOLD)
        canvas.setLineWidth(1.5)
        canvas.line(
            20*mm,
            28*mm,
            A4[0] - 20*mm,
            28*mm
        )

        footer_left = (
            "Botswana-UPenn Partnership  Botswana Headquarters\n"
            "University of Botswana Main Campus\n"
            "244G - Room 103\n"
            "(Postal Address: PO Box AC 157 ACH)\n"
            "Gaborone\n"
            "Botswana\n"
            "Tel: +267.355.4855\n"
            "Fax: +267.393.2267"
        )
        footer_right = (
            "Botswana-UPenn Partnership  United States Headquarters\n"
            "University of Pennsylvania\n"
            "240 John Morgan Building, 3620 Hamilton Walk\n"
            "Philadelphia, PA 19104-6073\n"
            "United States\n"
            "Tel: +1 215.898.0848\n"
            "Fax: +1 215.573.2158\n"
            "website: http://www.upenn.edu/botswana/"
        )

        canvas.setFont('Times-Roman', 7)
        canvas.setFillColor(GREY)

        # Left column
        text_obj = canvas.beginText(20*mm, 25*mm)
        for line in footer_left.split('\n'):
            text_obj.textLine(line)
        canvas.drawText(text_obj)

        # Right column
        text_obj2 = canvas.beginText(A4[0]/2, 25*mm)
        for line in footer_right.split('\n'):
            text_obj2.textLine(line)
        canvas.drawText(text_obj2)

        canvas.restoreState()

    doc.build(story, onFirstPage=draw_footer, onLaterPages=draw_footer)
    buffer.seek(0)
    return buffer



# SECTION 1 — add to hr/pdf_utils.py
# ----------------------------------------------------------------
# Reuses the same NAVY/GOLD styling and footer as
# generate_confirmation_letter_pdf, already in this file. Add this
# function alongside it:
 
def generate_study_bond_pdf(sb, request):
    """
    sb: a StudyBondRequest instance.
    Renders the Self Study Bond form, including whatever has been
    filled in for the OFFICIAL USE section so far — a bond that's
    still PENDING will show blank/"Pending" approval fields, and one
    that's REGISTERED but not yet graded will show the registration
    signature but blank grade fields.
    """
    buffer = BytesIO()
 
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=20*mm,
        leftMargin=20*mm,
        topMargin=10*mm,
        bottomMargin=40*mm,
    )
 
    normal = ParagraphStyle('SBNormal', fontName='Times-Roman', fontSize=11, leading=16, textColor=BLACK)
    label = ParagraphStyle('SBLabel', fontName='Times-Bold', fontSize=10, leading=14, textColor=BLACK)
    heading = ParagraphStyle('SBHeading', fontName='Times-Bold', fontSize=13, leading=18,
                              textColor=NAVY, alignment=TA_LEFT)
    section = ParagraphStyle('SBSection', fontName='Times-Bold', fontSize=10, leading=14, textColor=NAVY)
    small = ParagraphStyle('SBSmall', fontName='Times-Roman', fontSize=9, leading=12, textColor=GREY)
 
    story = []
 
    logo_path = os.path.join(settings.BASE_DIR, 'static', 'images', 'logo.png')
    if os.path.exists(logo_path):
        logo = Image(logo_path, width=50*mm, height=25*mm)
        logo.hAlign = 'LEFT'
        story.append(logo)
    story.append(Spacer(1, 3*mm))
    story.append(HRFlowable(width="100%", thickness=1.5, color=NAVY, spaceAfter=5*mm))
 
    story.append(Paragraph("SELF STUDY BOND", heading))
    story.append(Spacer(1, 6*mm))
 
    full_name = sb.requested_by.get_full_name() or sb.requested_by.username
 
    story.append(Paragraph("I", normal))
    story.append(Spacer(1, 1*mm))
    # Print Name is filled from data we already have. Signature is left as
    # a blank ruled line — there's no employee signature capture anywhere
    # in the system yet, so this prints for a wet-ink signature, same as
    # the original paper form.
    sig_block = Table(
        [
            [Paragraph(f"<u>{full_name}</u>", normal), Paragraph("[Print Name]", small)],
            [Paragraph("&nbsp;", normal), Paragraph("[Signature]", small)],
        ],
        colWidths=[110*mm, 55*mm]
    )
    sig_block.setStyle(TableStyle([
        ('LINEBELOW', (0, 0), (0, 0), 0.6, BLACK),
        ('LINEBELOW', (0, 1), (0, 1), 0.6, BLACK),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('VALIGN', (0, 0), (-1, -1), 'BOTTOM'),
    ]))
    story.append(sig_block)
    story.append(Spacer(1, 4*mm))
    story.append(Paragraph(
        "Agree to be bound by the terms contained in the BUP Education Policy.", normal))
    story.append(Spacer(1, 3*mm))
    story.append(Paragraph(f"Date: {sb.submitted_at.strftime('%d %B %Y')}", normal))
    story.append(Spacer(1, 6*mm))
 
    def field_row(rows):
        t = Table(rows, colWidths=[65*mm, 105*mm])
        t.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ]))
        return t
 
    receipt_note = "Receipt attached" if sb.payment_receipt else "No receipt attached"
    story.append(field_row([
        [Paragraph("Period of study:", label), Paragraph(
            f"{sb.period_start.strftime('%d %b %Y')} – {sb.period_end.strftime('%d %b %Y')}", normal)],
        [Paragraph("Title of the program:", label), Paragraph(sb.program_title, normal)],
        [Paragraph("Institution:", label), Paragraph(sb.institution, normal)],
        [Paragraph("Total cost of course:", label), Paragraph(f"{sb.total_cost:,.2f}", normal)],
        [Paragraph("Cost of subjects:", label), Paragraph(f"{sb.subject_costs:,.2f}", normal)],
        [Paragraph("Amount paid by BUP:", label), Paragraph(f"{sb.amount_paid_by_bup:,.2f}", normal)],
        [Paragraph("Date of payment:", label), Paragraph(
            sb.payment_date.strftime('%d %b %Y') if sb.payment_date else "—", normal)],
        [Paragraph("Payment receipt:", label), Paragraph(receipt_note, normal)],
    ]))
    story.append(Spacer(1, 4*mm))
    story.append(Paragraph(
        "10% of the employee's base pay or BWP 3000 per fiscal year (or equivalent), whichever is less.",
        small
    ))
    story.append(Spacer(1, 8*mm))
 
    # ── OFFICIAL USE BOX ────────────────────────────────────────
    story.append(HRFlowable(width="100%", thickness=1, color=GOLD, spaceAfter=3*mm))
    story.append(Paragraph("OFFICIAL USE", ParagraphStyle(
        'OfficialUse', fontName='Times-Bold', fontSize=11, alignment=TA_CENTER, textColor=NAVY)))
    story.append(Spacer(1, 5*mm))
 
    # Stage 1: Approval to Register
    story.append(Paragraph("Approval to Register", section))
    story.append(Spacer(1, 2*mm))
 
    if sb.status == 'PENDING':
        story.append(Paragraph("Status: Pending", normal))
    elif sb.status == 'DECLINED' and not sb.approved_by:
        story.append(Paragraph("Status: Not Approved", normal))
        if sb.decline_reason:
            story.append(Paragraph(f"Reason: {sb.decline_reason}", normal))
    else:
        story.append(Paragraph("Status: Approved", normal))
        story.append(Paragraph(
            f"Date: {sb.approved_at.strftime('%d %b %Y') if sb.approved_at else '—'}", normal))
        story.append(Spacer(1, 3*mm))
        if sb.approver_signature:
            sig_path = os.path.join(settings.MEDIA_ROOT, str(sb.approver_signature))
            if os.path.exists(sig_path):
                sig_img = Image(sig_path, width=40*mm, height=18*mm)
                sig_img.hAlign = 'LEFT'
                story.append(sig_img)
        story.append(Paragraph(f"<b>{sb.approver_name}</b>", normal))
        story.append(Paragraph(sb.approver_job_title, normal))
 
    story.append(Spacer(1, 6*mm))
 
    # Stage 2: HR Verification — the final step; only reached once the
    # Director/PI has already approved.
    story.append(Paragraph("HR Verification", section))
    story.append(Spacer(1, 2*mm))
 
    if sb.hr_reviewed_by:
        story.append(Paragraph(f"Verified base pay: {sb.hr_verified_salary:,.2f}", normal))
        story.append(Paragraph(f"Confirmed cap amount: {sb.hr_cap_amount:,.2f}", normal))
        if sb.hr_notes:
            story.append(Paragraph(f"Notes: {sb.hr_notes}", normal))
        story.append(Paragraph(
            f"Reviewed by {sb.hr_reviewed_by.get_full_name()} on "
            f"{sb.hr_reviewed_at.strftime('%d %b %Y') if sb.hr_reviewed_at else '—'}", normal))
    elif sb.status == 'PENDING_HR_REVIEW':
        story.append(Paragraph("Status: Pending", normal))
    else:
        story.append(Paragraph("Not yet reached", normal))
 
    story.append(Spacer(1, 6*mm))
 
    # Stage 3: Grade Verification
    story.append(Paragraph("Grade Verification following Completion of Course", section))
    story.append(Spacer(1, 2*mm))
 
    if sb.status == 'COMPLETED':
        story.append(Paragraph(f"Grade received: <b>{sb.grade_received}</b>", normal))
        story.append(Paragraph(
            f"Verified: {sb.verified_at.strftime('%d %b %Y') if sb.verified_at else '—'}", normal))
        story.append(Spacer(1, 3*mm))
        if sb.verifier_signature:
            sig_path = os.path.join(settings.MEDIA_ROOT, str(sb.verifier_signature))
            if os.path.exists(sig_path):
                sig_img = Image(sig_path, width=40*mm, height=18*mm)
                sig_img.hAlign = 'LEFT'
                story.append(sig_img)
        story.append(Paragraph(f"<b>{sb.verifier_name}</b>", normal))
        story.append(Paragraph(sb.verifier_job_title, normal))
    else:
        story.append(Paragraph("Pending", normal))
 
    # ── FOOTER (same as confirmation letters) ───────────────────
    def draw_footer(canvas, doc_):
        canvas.saveState()
        canvas.setStrokeColor(GOLD)
        canvas.setLineWidth(1.5)
        canvas.line(20*mm, 28*mm, A4[0] - 20*mm, 28*mm)
        footer_left = (
            "Botswana-UPenn Partnership  Botswana Headquarters\n"
            "University of Botswana Main Campus\n244G - Room 103\n"
            "(Postal Address: PO Box AC 157 ACH)\nGaborone\nBotswana\n"
            "Tel: +267.355.4855\nFax: +267.393.2267"
        )
        footer_right = (
            "Botswana-UPenn Partnership  United States Headquarters\n"
            "University of Pennsylvania\n240 John Morgan Building, 3620 Hamilton Walk\n"
            "Philadelphia, PA 19104-6073\nUnited States\n"
            "Tel: +1 215.898.0848\nFax: +1 215.573.2158\nwebsite: http://www.upenn.edu/botswana/"
        )
        canvas.setFont('Times-Roman', 7)
        canvas.setFillColor(GREY)
        t1 = canvas.beginText(20*mm, 25*mm)
        for line in footer_left.split('\n'):
            t1.textLine(line)
        canvas.drawText(t1)
        t2 = canvas.beginText(A4[0]/2, 25*mm)
        for line in footer_right.split('\n'):
            t2.textLine(line)
        canvas.drawText(t2)
        canvas.restoreState()
 
    doc.build(story, onFirstPage=draw_footer, onLaterPages=draw_footer)
    buffer.seek(0)
    return buffer
 