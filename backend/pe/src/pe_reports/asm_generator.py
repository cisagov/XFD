"""Generate a stakeholders ASM summary based on a data dictionary."""

# Standard Python Libraries
import datetime
import io
import json
import logging
import os

# Third-Party Libraries
from PyPDF2 import PdfReader, PdfWriter
import fitz
import pandas as pd
from pe_reports.data.db_query import (
    get_subs_origin_ip,
    query_cidrs_by_org,
    query_extra_ips,
    query_foreign_IPs,
    query_ports_protocols,
    query_roots,
    query_software,
    query_subs,
)
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from reportlab.platypus import Frame, Paragraph

# Setup logging to central file
LOGGER = logging.getLogger(__name__)

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
ON_PAGE_INDEX = 0
UNDERNEATH = (
    False  # if True, new content will be placed underneath page (painted first)
)

pdfmetrics.registerFont(TTFont("Frank_Goth", BASE_DIR + "/fonts/FranklinGothic.ttf"))
pdfmetrics.registerFont(
    TTFont("Frank_Goth_Book", BASE_DIR + "/fonts/Franklin_Gothic_Book_Regular.ttf")
)


def build_kpi_string(value, last_value):
    """Build a string to show kpi and change since the last period."""
    if not last_value:
        last_value = 0
    value_diff = value - last_value
    if value_diff > 0:
        string = f" <font size=18> {value}</font><br></br> Increase of {value_diff}"
    elif value_diff < 0:
        string = f" <font size=18> {value}</font><br></br> Decrease of {abs(value_diff)}"  # added abs() to remove sign
    else:
        string = f" <font size=18> {value}</font><br></br> No Change"
    return string


def determine_arrow(value, last_value, color=False):
    """Determine the arrow color and direction based on current and previous values."""
    if not last_value:
        last_value = 0
    value_diff = value - last_value
    if color:
        if value_diff > 0:
            return BASE_DIR + "/assets_asm/up_red.png"
        elif value_diff < 0:
            return BASE_DIR + "/assets_asm/down_green.png"
        else:
            return BASE_DIR + "/assets_asm/no_change.png"
    else:
        if value_diff > 0:
            return BASE_DIR + "/assets_asm/up_black.png"
        elif value_diff < 0:
            return BASE_DIR + "/assets_asm/down_black.png"
        else:
            return BASE_DIR + "/assets_asm/no_change.png"


def add_stat_frame(current_value, last_value, x, y, width, height, style, can):
    """Add data point frame."""
    show_border = False
    image_size = 22
    frame = Frame(x, y, width, height, showBoundary=show_border)
    ip_address_paragraph = Paragraph(
        f"{build_kpi_string(current_value, last_value)}",
        style=style,
    )
    frame.addFromList([ip_address_paragraph], can)
    can.drawImage(
        determine_arrow(current_value, last_value, False),
        x + 110,
        y + 16,
        image_size,
        image_size,
        mask="auto",
    )
    return can


def add_attachment(
    org_uid, final_output, pdf_file, asm_json, asm_xlsx, start_date, end_date
):
    """Create and add JSON attachment."""
    LOGGER.info("Creating ASM attachments")
    # Create ASM Excel file
    asmWriter = pd.ExcelWriter(asm_xlsx, engine="xlsxwriter")

    # CIDRs
    cidr_df = query_cidrs_by_org(org_uid)
    cidr_df = cidr_df[["network"]]
    cidr_df.to_excel(asmWriter, sheet_name="CIDRs", index=False)
    cidr_dict = cidr_df["network"].to_list()

    # Extra IPs
    ip_lst = query_extra_ips(org_uid)
    ips_df = pd.DataFrame(ip_lst, columns=["ip"])
    ips_df.to_excel(asmWriter, sheet_name="Extra IPs", index=False)
    ips_dict = ips_df["ip"].to_list()

    # Ports/protocols
    ports_protocols_df = query_ports_protocols(org_uid, start_date, end_date)
    ports_protocols_df.to_excel(asmWriter, sheet_name="Ports Protocols", index=False)
    ports_protocols_dict = ports_protocols_df.to_dict(orient="records")

    # Root domains
    rd_df = query_roots(org_uid)
    rd_df = rd_df[["root_domain"]]
    rd_df.to_excel(asmWriter, sheet_name="Root Domains", index=False)
    rd_dict = rd_df["root_domain"].to_list()

    # Sub-domains
    sd_df = query_subs(org_uid)
    sd_df_cols = [
        "sub_domain",
        "from_root_domain",
        "origin_root_domain",
        "from_ip",
        "origin_ip",
        "origin_cidr",
    ]
    # Isolate subdomains that come from a stakeholder root domain
    root_sub_df = sd_df.loc[~sd_df["pe_discovered_asset"]].reset_index(drop=True)
    if not root_sub_df.empty:
        root_sub_df = root_sub_df.assign(
            from_root_domain=True, from_ip=False, origin_ip="N/A", origin_cidr="N/A"
        )
        root_sub_df = root_sub_df[sd_df_cols]
    else:
        root_sub_df = pd.DataFrame(columns=sd_df_cols)
    # Isolate subdomains that did not come from a stakeholder root domain (from IP)
    ident_sub_df = sd_df.loc[sd_df["pe_discovered_asset"]].reset_index(drop=True)
    if not ident_sub_df.empty:
        # Retrieve the IPs that these identified subdomains came from
        ident_sub_df = get_subs_origin_ip(ident_sub_df, org_uid)
        ident_sub_df = ident_sub_df.assign(
            from_root_domain=False, from_ip=True, origin_root_domain="N/A"
        )
        ident_sub_df = ident_sub_df[sd_df_cols]
        # non-root domains can sometimes resolve back to multiple IPs
        ident_sub_df = ident_sub_df.drop_duplicates(subset=["sub_domain"])
    else:
        ident_sub_df = pd.DataFrame(columns=sd_df_cols)
    # Combine root and non-root subdomains
    sd_df = pd.concat([root_sub_df, ident_sub_df]).reset_index(drop=True)
    # sd_df = sd_df[["sub_domain", "origin_root_domain"]]
    sd_df.to_excel(asmWriter, sheet_name="Subdomains", index=False)
    sd_dict = sd_df.to_dict(orient="records")

    # Software
    soft_df = query_software(org_uid, start_date, end_date)
    soft_df.to_excel(asmWriter, sheet_name="Software", index=False)
    soft_dict = soft_df["product"].to_list()

    # Foreign Ips
    for_ips_df = query_foreign_IPs(org_uid)
    for_ips_df["timestamp"] = pd.to_datetime(for_ips_df["timestamp"])
    for_ips_df = for_ips_df.loc[
        (for_ips_df["timestamp"] >= start_date) & (for_ips_df["timestamp"] <= end_date)
    ].reset_index(drop=True)
    for_ips_df = for_ips_df[
        [
            "organization",
            "ip",
            "port",
            "protocol",
            "product",
            "country_code",
            "location",
        ]
    ]
    for_ips_df.to_excel(asmWriter, sheet_name="Foreign IPs", index=False)
    for_ips_dict = for_ips_df.to_dict(orient="records")

    asmWriter.close()

    # Write to a JSON file
    final_dict = {
        "cidrs": cidr_dict,
        "extra_ips": ips_dict,
        "ports_protocols": ports_protocols_dict,
        "root_domains": rd_dict,
        "sub_domains": sd_dict,
        "software": soft_dict,
        "foreign_ips": for_ips_dict,
    }
    with open(asm_json, "w") as outfile:
        json.dump(final_dict, outfile, default=str)

    # Attach to PDF
    doc = fitz.open(pdf_file)

    # Get the summary page of the PDF on page 4
    page = doc[0]

    # Open CSV data as binary
    sheet = open(asm_json, "rb").read()
    excel_sheet = open(asm_xlsx, "rb").read()
    p1 = fitz.Point(455, 635)
    p2 = fitz.Point(495, 635)
    page.add_file_annot(
        p1, sheet, "ASM_Summary.json", desc="Open JSON", icon="Paperclip"
    )
    page.add_file_annot(
        p2, excel_sheet, "ASM_Summary.xlsx", desc="Open Excel", icon="Graph"
    )
    temp_output = f"{final_output}.embed.tmp"
    doc.save(
        temp_output,
        garbage=4,
        deflate=True,
    )
    doc.close()
    os.replace(temp_output, final_output)

    return asm_xlsx


def create_summary(
    org_uid,
    final_output,
    data_dict,
    file_name,
    json_filename,
    excel_filename,
    datestring,
):
    """Create ASM summary PDF."""
    # Calculate start/end dates
    end_date = datetime.datetime.strptime(datestring, "%Y-%m-%d")
    if end_date.day == 15:
        start_date = datetime.datetime(end_date.year, end_date.month, 1)
    else:
        start_date = datetime.datetime(end_date.year, end_date.month, 16)

    packet = io.BytesIO()
    # Create a new PDF with Reportlab
    can = canvas.Canvas(packet, pagesize=letter)
    can.setFillColorRGB(0, 0, 0)  # choose your font color
    can.setFont("Frank_Goth", 20)

    org_name_style = ParagraphStyle(
        "org_name_style",
        fontName="Frank_Goth",
        fontSize=14,
        textColor="black",
        splitLongWords=1,
    )
    date_frame = Frame(73, 662, 310, 35)
    date = Paragraph(data_dict["date"], style=org_name_style)
    date_frame.addFromList([date], can)

    org_name_len = len(data_dict["org_name"])
    if org_name_len > 66:
        org_name_style.fontSize = 9
    org_name_frame = Frame(155, 635, 420, 35)
    org_name = Paragraph(data_dict["org_name"], style=org_name_style)
    org_name_frame.addFromList([org_name], can)

    stat_style = ParagraphStyle(
        "date_style", fontName="Frank_Goth_Book", fontSize=12, alignment=0
    )

    json_excel = ParagraphStyle(
        name="json_excel",
        fontName="Franklin_Gothic_Medium_Regular",
        fontSize=10,
        alignment=1,
    )

    # Add all the data points to the correct frame
    can = add_stat_frame(
        int(data_dict["ip_address"]),
        data_dict["last_ip_address"],
        25,
        353,
        180,
        50,
        stat_style,
        can,
    )
    can = add_stat_frame(
        data_dict["cidrs"], data_dict["last_cidrs"], 220, 353, 180, 50, stat_style, can
    )
    can = add_stat_frame(
        data_dict["ports_and_protocols"],
        data_dict["last_ports_and_protocols"],
        410,
        353,
        180,
        50,
        stat_style,
        can,
    )
    can = add_stat_frame(
        data_dict["root_domains"],
        data_dict["last_root_domains"],
        25,
        279,
        180,
        50,
        stat_style,
        can,
    )
    can = add_stat_frame(
        data_dict["sub_domains"],
        data_dict["last_sub_domains"],
        220,
        279,
        180,
        50,
        stat_style,
        can,
    )
    can = add_stat_frame(
        data_dict["software"],
        data_dict["last_software"],
        410,
        279,
        180,
        50,
        stat_style,
        can,
    )
    can = add_stat_frame(
        data_dict["foreign_ips"],
        data_dict["last_foreign_ips"],
        25,
        207,
        180,
        50,
        stat_style,
        can,
    )
    json_title_frame = Frame(
        6 * inch, 100, 1.5 * inch, 0.5 * inch, id=None, showBoundary=0
    )
    json_title = Paragraph(
        "JSON&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;EXCEL",
        style=json_excel,
    )
    json_title_frame.addFromList([json_title], can)
    can.save()

    # Move to the beginning of the StringIO buffer
    packet.seek(0)
    new_pdf = PdfReader(packet)

    # Read existing PDF template and merge overlay
    with open(BASE_DIR + "/assets_asm/empty_asm_2024-11-19.pdf", "rb") as template_file:
        existing_pdf = PdfReader(template_file)
        page = existing_pdf.pages[0]
        page.merge_page(new_pdf.pages[0])
        output = PdfWriter()
        output.add_page(page)
        with open(file_name, "wb") as output_stream:
            output.write(output_stream)

    asm_xlsx = add_attachment(
        org_uid,
        final_output,
        file_name,
        json_filename,
        excel_filename,
        start_date,
        end_date,
    )

    return asm_xlsx
