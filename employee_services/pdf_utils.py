from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle, HRFlowable
from reportlab.lib.colors import HexColor
from io import BytesIO
import os
from django.conf import settings

# Same identity as hr/pdf_utils.py — one visual language across every
# generated BUP document.
NAVY = HexColor('#003087')
GOLD = HexColor('#C9A84C')
BLACK = HexColor('#000000')
GREY = HexColor('#666666')


def _dash_if_blank(value, formatter=None):
    if value is None or value == '':
        return '—'
    return formatter(value) if formatter else str(value)


def generate_study_bond_pdf(application):
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        rightMargin=20 * mm, leftMargin=20 * mm,
        topMargin=10 * mm, bottomMargin=40 * mm,
    )

    styles = getSampleStyleSheet()
    normal = ParagraphStyle('N', fontName='Times-Roman', fontSize=11, leading=16, textColor=BLACK)
    bold = ParagraphStyle('B', fontName='Times-Bold', fontSize=11, leading=16, textColor=BLACK)
    small = ParagraphStyle('S', fontName='Times-Roman', fontSize=9, leading=13, textColor=BLACK)
    section_heading = ParagraphStyle('SH', fontName='Times-Bold', fontSize=11, leading=16, textColor=NAVY, alignment=TA_CENTER)
    label = ParagraphStyle('L', fontName='Times-Bold', fontSize=10, leading=14, textColor=BLACK)

    story = []

    # ── LOGO (same path/fallback as hr/pdf_utils.py) ────────────────
    logo_path = os.path.join(settings.BASE_DIR, 'static', 'images', 'logo.png')
    if os.path.exists(logo_path):
        logo = Image(logo_path, width=50 * mm, height=25 * mm)
        logo.hAlign = 'LEFT'
        story.append(logo)
    else:
        story.append(Paragraph("<b>BOTSWANA-UPENN PARTNERSHIP</b>", bold))

    story.append(Spacer(1, 3 * mm))
    story.append(HRFlowable(width="100%", thickness=1.5, color=NAVY, spaceAfter=5 * mm))

    # ── TITLE + application type ─────────────────────────────────────
    type_label = "CONTINUATION" if application.is_continuation() else "FRESH APPLICATION"
    story.append(Paragraph(f"SELF STUDY BOND — {type_label}", ParagraphStyle(
        'Title', fontName='Times-Bold', fontSize=13, leading=18, textColor=NAVY,
    )))
    story.append(Spacer(1, 4 * mm))

    if application.is_continuation() and application.previous_application:
        story.append(Paragraph(
            f"Continuation of Application #{application.previous_application.pk}", small,
        ))
        story.append(Spacer(1, 3 * mm))

    # ── EMPLOYEE DECLARATION ─────────────────────────────────────────
    full_name = application.employee.get_full_name() or application.employee.username
    story.append(Paragraph(f"I, {full_name}", normal))

    profile = getattr(application.employee, 'employee_profile', None)
    if profile and profile.signature_image:
        sig_path = os.path.join(settings.MEDIA_ROOT, str(profile.signature_image))
        if os.path.exists(sig_path):
            sig = Image(sig_path, width=40 * mm, height=16 * mm)
            sig.hAlign = 'LEFT'
            story.append(sig)
        else:
            story.append(Spacer(1, 10 * mm))
    else:
        story.append(Spacer(1, 10 * mm))
    story.append(Paragraph("[Signature]", small))
    story.append(Spacer(1, 3 * mm))

    story.append(Paragraph("Agree to be bound by the terms contained in the BUP Education Policy.", normal))
    story.append(Paragraph(f"Date: {application.submitted_at.strftime('%d %B %Y')}", normal))
    story.append(Spacer(1, 5 * mm))

    # ── PROGRAM DETAILS TABLE ─────────────────────────────────────────
    program_rows = [
        ["Period of study:", f"{application.period_start.strftime('%d %b %Y')} – {application.period_end.strftime('%d %b %Y')}"],
        ["Title of the program:", application.program_title],
        ["Institution:", application.institution],
        ["Total cost of course:", f"BWP {application.total_cost:,.2f}"],
        ["Cost of subjects:", _dash_if_blank(application.cost_of_subjects, lambda v: f"BWP {v:,.2f}")],
        ["Amount paid by BUP:", _dash_if_blank(application.amount_paid_by_bup, lambda v: f"BWP {v:,.2f}")],
        ["Date of payment:", _dash_if_blank(application.date_of_payment, lambda v: v.strftime('%d %b %Y'))],
        ["Payment receipt:", "Attached" if application.payment_receipt else "No receipt attached"],
    ]
    table = Table(
        [[Paragraph(f"<b>{r[0]}</b>", normal), Paragraph(r[1], normal)] for r in program_rows],
        colWidths=[55 * mm, 105 * mm],
    )
    table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(table)
    story.append(Spacer(1, 3 * mm))
    story.append(Paragraph(
        "10% of the employee's base pay or BWP 3000 per fiscal year (or equivalent), whichever is less.",
        small,
    ))
    story.append(Spacer(1, 5 * mm))
    story.append(HRFlowable(width="100%", thickness=1, color=GOLD, spaceAfter=4 * mm))

    # ── OFFICIAL USE ───────────────────────────────────────────────────
    story.append(Paragraph("OFFICIAL USE", section_heading))
    story.append(Spacer(1, 4 * mm))

    # HR verification (costs only — the checklist below belongs to the approver)
    story.append(Paragraph("HR Verification", label))
    story.append(Paragraph(f"Verified base pay: {_dash_if_blank(application.verified_base_pay, lambda v: f'BWP {v:,.2f}')}", normal))
    cap = application.max_allowed_bup_amount()
    story.append(Paragraph(f"Confirmed cap amount: {_dash_if_blank(cap, lambda v: f'BWP {v:,.2f}')}", normal))
    if application.hr_notes:
        story.append(Paragraph(f"Notes: {application.hr_notes}", normal))
    if application.hr_reviewed_by:
        story.append(Paragraph(
            f"Reviewed by {application.hr_reviewed_by.get_full_name()} on "
            f"{application.hr_reviewed_at.strftime('%d %b %Y') if application.hr_reviewed_at else '—'}",
            small,
        ))
    else:
        story.append(Paragraph("Pending HR review.", small))
    story.append(Spacer(1, 5 * mm))

    # Approval to Register (approver's full checklist + decision)
    story.append(Paragraph("Approval to Register for Course", label))
    checklist = [
        ("Program relevant to BUP's work / employee's development plan", application.program_relevant),
        ("Accredited / recognised institution", application.accredited_institution),
        ("Employee in good standing, 6+ months with BUP", application.good_standing_6_months),
        ("Tuition cap balance for the fiscal year not exhausted", application.tuition_cap_balance_ok),
        ("Supervisor notified (if leave requested)", application.supervisor_notified),
    ]
    for item_label, value in checklist:
        mark = "☑" if value is True else ("☒" if value is False else "☐")
        story.append(Paragraph(f"{mark} {item_label}", small))
    story.append(Spacer(1, 2 * mm))

    if application.status in ('APPROVED', 'PENDING_PAYMENT', 'COMPLETED'):
        decision_text = "Approved"
    elif application.status == 'DECLINED':
        decision_text = "Not Approved"
    else:
        decision_text = "Pending"
    story.append(Paragraph(f"<b>Status:</b> {decision_text}", normal))
    if application.status == 'DECLINED' and application.decline_reason:
        story.append(Paragraph(f"Reason: {application.decline_reason}", normal))
    story.append(Paragraph(f"Name of Approver: {application.approver.get_full_name() if application.approver else '—'}", normal))

    approver_profile = getattr(application.approver, 'employee_profile', None) if application.approver else None
    if approver_profile and approver_profile.signature_image and application.decision_date:
        sig_path = os.path.join(settings.MEDIA_ROOT, str(approver_profile.signature_image))
        if os.path.exists(sig_path):
            sig = Image(sig_path, width=40 * mm, height=16 * mm)
            sig.hAlign = 'LEFT'
            story.append(sig)
    story.append(Paragraph("Approver Signature", small))
    if application.decision_date:
        story.append(Paragraph(f"Date: {application.decision_date.strftime('%d %b %Y')}", small))
    story.append(Spacer(1, 5 * mm))

    # Grade Verification (HR's job; exists on every application)
    story.append(Paragraph("Grade Verification following Completion of Course", label))
    story.append(Paragraph(application.get_grade_status_display(), normal))
    if application.grade_status != 'PENDING' and application.grade_verified_by:
        story.append(Paragraph(
            f"Verified by {application.grade_verified_by.get_full_name()} on "
            f"{application.grade_verified_at.strftime('%d %b %Y') if application.grade_verified_at else '—'}",
            small,
        ))
    if application.grade_notes:
        story.append(Paragraph(f"Notes: {application.grade_notes}", small))

    # ── FOOTER (identical to hr/pdf_utils.py) ─────────────────────────
    def draw_footer(canvas, doc):
        canvas.saveState()
        canvas.setStrokeColor(GOLD)
        canvas.setLineWidth(1.5)
        canvas.line(20 * mm, 28 * mm, A4[0] - 20 * mm, 28 * mm)

        footer_left = (
            "Botswana-UPenn Partnership  Botswana Headquarters\n"
            "University of Botswana Main Campus\n"
            "244G - Room 103\n"
            "(Postal Address: PO Box AC 157 ACH)\n"
            "Gaborone\nBotswana\nTel: +267.355.4855\nFax: +267.393.2267"
        )
        footer_right = (
            "Botswana-UPenn Partnership  United States Headquarters\n"
            "University of Pennsylvania\n"
            "240 John Morgan Building, 3620 Hamilton Walk\n"
            "Philadelphia, PA 19104-6073\nUnited States\n"
            "Tel: +1 215.898.0848\nFax: +1 215.573.2158\n"
            "website: http://www.upenn.edu/botswana/"
        )
        canvas.setFont('Times-Roman', 7)
        canvas.setFillColor(GREY)
        t1 = canvas.beginText(20 * mm, 25 * mm)
        for line in footer_left.split('\n'):
            t1.textLine(line)
        canvas.drawText(t1)
        t2 = canvas.beginText(A4[0] / 2, 25 * mm)
        for line in footer_right.split('\n'):
            t2.textLine(line)
        canvas.drawText(t2)
        canvas.restoreState()

    doc.build(story, onFirstPage=draw_footer, onLaterPages=draw_footer)
    buffer.seek(0)
    return buffer
