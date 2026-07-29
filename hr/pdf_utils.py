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