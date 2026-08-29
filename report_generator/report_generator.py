from datetime import datetime
from html import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle
)


def generate_report(data):
    # ---------------------------------
    # REPORT DATE AND REPORT ID
    # ---------------------------------

    report_date = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
    report_id = "LM-" + datetime.now().strftime("%Y%m%d-%H%M%S")

    # PDF file name
    pdf_file = "compliance_report.pdf"

    # ---------------------------------
    # CREATE PDF DOCUMENT
    # ---------------------------------

    doc = SimpleDocTemplate(
        pdf_file,
        pagesize=A4,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40
    )

    # ---------------------------------
    # PDF STYLES
    # ---------------------------------

    styles = getSampleStyleSheet()

    # Main title
    title_style = ParagraphStyle(
        "TitleStyle",
        parent=styles["Title"],
        alignment=TA_CENTER,
        fontName="Helvetica-Bold",
        fontSize=18,
        leading=22,
        spaceAfter=12
    )

    # Section headings
    heading_style = ParagraphStyle(
        "HeadingStyle",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=14,
        leading=17,
        spaceBefore=10,
        spaceAfter=7
    )

    # Report date and ID
    metadata_style = ParagraphStyle(
        "MetadataStyle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=11,
        leading=14,
        spaceAfter=6
    )

    # Status
    status_style = ParagraphStyle(
        "StatusStyle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=13,
        leading=16,
        spaceAfter=0
    )

    # Product details
    product_style = ParagraphStyle(
        "ProductStyle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=11,
        leading=15,
        spaceAfter=0
    )

    # Normal text
    normal_style = ParagraphStyle(
        "NormalStyle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10.5,
        leading=14,
        spaceAfter=5
    )

    # Rule status
    rule_style = ParagraphStyle(
        "RuleStyle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10.5,
        leading=13,
        spaceAfter=0
    )

    story = []

    # ---------------------------------
    # REPORT HEADER
    # ---------------------------------

    story.append(
        Paragraph(
            "LEGAL METROLOGY COMPLIANCE REPORT",
            title_style
        )
    )

    story.append(
        Paragraph(
            f"<b>Report Date:</b> "
            f"{escape(str(report_date))}",
            metadata_style
        )
    )

    story.append(
        Paragraph(
            f"<b>Report ID:</b> "
            f"{escape(str(report_id))}",
            metadata_style
        )
    )

    story.append(Spacer(1, 8))

    # ---------------------------------
    # PRODUCT DETAILS
    # ---------------------------------

    story.append(
        Paragraph(
            "PRODUCT DETAILS",
            heading_style
        )
    )

    product = data["product"]

    product_details = [
        [
            Paragraph(
                f"<b>Product Name:</b> "
                f"{escape(str(product["product_name"]))}",
                product_style
            )
        ],
        [
            Paragraph(
                f"<b>Brand Name:</b> "
                f"{escape(str(product["brand_name"]))}",
                product_style
            )
        ],
        [
            Paragraph(
                f"<b>Common/Generic Name:</b> "
                f"{escape(str(product["common_generic_name"]))}",
                product_style
            )
        ],
        [
            Paragraph(
                f"<b>Product Category:</b> "
                f"{escape(str(product["product_category"]))}",
                product_style
            )
        ],
        [
            Paragraph(
                f"<b>Product Subcategory:</b> "
                f"{escape(str(product["product_subcategory"]))}",
                product_style
            )
        ]
    ]

    product_table = Table(
        product_details,
        colWidths=[500]
    )

    product_table.setStyle(
        TableStyle([
            ("BOX", (0, 0), (-1, -1), 1, colors.black),

            ("LEFTPADDING", (0, 0), (-1, -1), 10),
            ("RIGHTPADDING", (0, 0), (-1, -1), 10),

            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6)
        ])
    )

    story.append(product_table)

    story.append(Spacer(1, 10))

    # ---------------------------------
    # COMPLIANCE RESULT
    # ---------------------------------

    story.append(
        Paragraph(
            "COMPLIANCE RESULT",
            heading_style
        )
    )

    status = data["status"]

    if status == "COMPLIANT":
        status_text = "COMPLIANT"
        status_color = colors.green
        status_symbol = "[OK]"
    else:
        status_text = "NON_COMPLIANT"
        status_color = colors.red
        status_symbol = "[X]"

    status_content = [
        [
            Paragraph(
                f"<b>Status:</b> "
                f"<font color='{status_color}' "
                f"name='Helvetica-Bold' size='13'>"
                f"{status_symbol} {escape(str(status_text))}"
                f"</font>",
                status_style
            )
        ]
    ]

    status_table = Table(
        status_content,
        colWidths=[500]
    )

    status_table.setStyle(
        TableStyle([
            ("BOX", (0, 0), (-1, -1), 1, colors.black),

            ("LEFTPADDING", (0, 0), (-1, -1), 10),
            ("RIGHTPADDING", (0, 0), (-1, -1), 10),

            ("TOPPADDING", (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8)
        ])
    )

    story.append(status_table)

    # ---------------------------------
    # VIOLATIONS
    # ---------------------------------

    if status == "NON_COMPLIANT":

        story.append(
            Paragraph(
                "VIOLATIONS",
                heading_style
            )
        )

        for violation in data.get("violations", []):

            field = escape(str(violation.get("field", "")))
            message = escape(str(violation.get("message", "")))

            violation_text = (
                f"<font color='red' size='12'>[X]</font> "
                f"<b>{field}:</b> "
                f"{message}"
            )

            story.append(
                Paragraph(
                    violation_text,
                    normal_style
                )
            )

        story.append(Spacer(1, 6))

        story.append(
            Paragraph(
                "RECOMMENDED ACTION",
                heading_style
            )
        )

        story.append(
            Paragraph(
                "Correct the above violations before proceeding.",
                normal_style
            )
        )

    else:

        story.append(
            Paragraph(
                "COMPLIANCE MESSAGE",
                heading_style
            )
        )

        story.append(
            Paragraph(
                "<font color='green' size='12'>[OK]</font> "
                "<b>Product is compliant.</b>",
                normal_style
            )
        )

        story.append(
            Paragraph(
                "No violations detected.",
                normal_style
            )
        )

    story.append(Spacer(1, 8))

    # ---------------------------------
    # CHECKED RULES
    # ---------------------------------

    story.append(
        Paragraph(
            "CHECKED RULES",
            heading_style
        )
    )

    rule_rows = []

    # Table header
    rule_rows.append(
        [
            Paragraph(
                "<b>RULE</b>",
                rule_style
            ),
            Paragraph(
                "<b>STATUS</b>",
                rule_style
            )
        ]
    )

    for rule in data.get("checked_rules", []):

        # A rule is failed if it appears in violations
        rule_failed = any(
            violation.get("field") == rule
            for violation in data.get("violations", [])
        )

        if rule_failed:
            status_symbol = "[X]"
            status_text = "FAILED"
            status_color = colors.red
        else:
            status_symbol = "[OK]"
            status_text = "PASSED"
            status_color = colors.green

        rule_name = escape(str(rule))

        rule_rows.append(
            [
                Paragraph(
                    f"<b>{rule_name}</b>",
                    rule_style
                ),
                Paragraph(
                    f"<font color='{status_color}' "
                    f"name='Helvetica-Bold' size='11'>"
                    f"{status_symbol} {status_text}"
                    f"</font>",
                    rule_style
                )
            ]
        )

    rules_table = Table(
        rule_rows,
        colWidths=[350, 150],
        repeatRows=1
    )

    rules_table.setStyle(
        TableStyle([
            # Outer border
            ("BOX", (0, 0), (-1, -1), 1, colors.black),

            # Inner grid
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),

            # Header alignment
            ("ALIGN", (0, 0), (-1, 0), "CENTER"),

            # Status alignment
            ("ALIGN", (1, 1), (1, -1), "LEFT"),

            # Cell padding
            ("LEFTPADDING", (0, 0), (-1, -1), 10),
            ("RIGHTPADDING", (0, 0), (-1, -1), 10),

            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5)
        ])
    )

    story.append(rules_table)

    # ---------------------------------
    # CREATE PDF
    # ---------------------------------

    doc.build(story)

    print()
    print("PDF report saved as compliance_report.pdf")

    return pdf_file