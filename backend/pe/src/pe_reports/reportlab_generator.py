"""Generate a P&E report using a passed data dictionary."""
# Standard Python Libraries
from hashlib import sha256
import logging
import os

# Third-Party Libraries
import demoji
import numpy as np
from reportlab.lib import utils
from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    HRFlowable,
    Image,
    KeepTogether,
    ListFlowable,
    ListItem,
    PageBreak,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)
from reportlab.platypus.doctemplate import (
    BaseDocTemplate,
    NextPageTemplate,
    PageTemplate,
)
from reportlab.platypus.flowables import BalancedColumns
from reportlab.platypus.frames import Frame
from reportlab.platypus.tableofcontents import TableOfContents

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
LOGGER = logging.getLogger(__name__)

pdfmetrics.registerFont(
    TTFont(
        "Franklin_Gothic_Book_Italic", BASE_DIR + "/fonts/FranklinGothicBookItalic.ttf"
    )
)
pdfmetrics.registerFont(
    TTFont("Franklin_Gothic_Book", BASE_DIR + "/fonts/FranklinGothicBook.ttf")
)
pdfmetrics.registerFont(
    TTFont(
        "Franklin_Gothic_Demi_Regular",
        BASE_DIR + "/fonts/FranklinGothicDemiRegular.ttf",
    )
)
pdfmetrics.registerFont(
    TTFont(
        "Franklin_Gothic_Medium_Italic",
        BASE_DIR + "/fonts/FranklinGothicMediumItalic.ttf",
    )
)
pdfmetrics.registerFont(
    TTFont(
        "Franklin_Gothic_Medium_Regular",
        BASE_DIR + "/fonts/FranklinGothicMediumRegular.ttf",
    )
)

defaultPageSize = letter
PAGE_HEIGHT = defaultPageSize[1]
PAGE_WIDTH = defaultPageSize[0]


def sha_hash(s: str):
    """Hash a given string."""
    return sha256(s.encode("utf-8")).hexdigest()


# Extend Table of contents to create a List of Figures Class
class ListOfFigures(TableOfContents):
    """Class extention to build a Table of Figures."""

    def notify(self, kind, stuff):
        """
        Call he notification hook to register all kinds of events.

        Here we are interested in 'Figure' events only.
        """
        if kind == "TOCFigure":
            self.addEntry(*stuff)


# Extend Table of contents to create a List of Tables Class
class ListOfTables(TableOfContents):
    """Class extention to build a Table of Tables."""

    def notify(self, kind, stuff):
        """Call the notification hook to register all kinds of events.

        Here we are interested in 'Table' events only.
        """
        if kind == "TOCTable":
            self.addEntry(*stuff)


class MyDocTemplate(BaseDocTemplate):
    """Extend the BaseDocTemplate to adjust Template."""

    def __init__(self, filename, **kw):
        """Initialize MyDocTemplate."""
        self.allowSplitting = 0
        BaseDocTemplate.__init__(self, filename, **kw)
        self.pagesize = defaultPageSize

    def afterFlowable(self, flowable):
        """Register TOC, TOT, and TOF entries."""
        if flowable.__class__.__name__ == "Paragraph":
            text = flowable.getPlainText()
            style = flowable.style.name
            if style == "Heading1":
                level = 0
                notification = "TOCEntry"
            elif style == "Heading2":
                level = 1
                notification = "TOCEntry"
            elif style == "figure":
                level = 0
                notification = "TOCFigure"
            elif style == "table":
                level = 0
                notification = "TOCTable"
            else:
                return
            E = [level, text, self.page]
            # if we have a bookmark name, append that to our notify data
            bn = getattr(flowable, "_bookmarkName", None)
            if bn is not None:
                E.append(bn)
            self.notify(notification, tuple(E))


class ConditionalSpacer(Spacer):
    """Extend spacer to conditionaly shrink if near the end of the page."""

    def wrap(self, availWidth, availHeight):
        """Change hight of spacer based on available height."""
        height = min(self.height, availHeight - 1e-8)
        return (availWidth, height)


def get_image(path, width=1 * inch):
    """Read in an image and scale it based on the width argument."""
    img = utils.ImageReader(path)
    iw, ih = img.getSize()
    aspect = ih / float(iw)
    return Image(path, width=width, height=(width * aspect))


def format_table(
    df, header_style, column_widths, column_style_list, remove_symbols=False
):
    """Read in a dataframe and convert it to a table and format it with a provided style list."""
    header_row = [
        [Paragraph(str(cell), header_style) for cell in row] for row in [df.columns]
    ]
    data = []
    for row in np.array(df).tolist():
        current_cell = 0
        current_row = []
        for cell in row:
            if column_style_list[current_cell] is not None:
                # Remove emojis and escape special characters b/c the report generator can't display them
                clean_txt = demoji.replace(str(cell), "").replace("&", "&amp;")
                # Don't escape special characters if string is for cred breach table which contains valid links to appendix
                if "<link href=" not in str(cell):
                    clean_txt = clean_txt.replace("<", "&lt;")
                    clean_txt = clean_txt.replace(">", "&gt;")
                # Create paragraph cell
                try:
                    cell = Paragraph(clean_txt, column_style_list[current_cell])
                except Exception as e:
                    LOGGER.warning(
                        "Issue encountered with format_table(): %s", e, exc_info=True
                    )

            current_row.append(cell)
            current_cell += 1
        data.append(current_row)

    data = header_row + data

    table = Table(
        data,
        colWidths=column_widths,
        rowHeights=None,
        style=None,
        splitByRow=1,
        repeatRows=1,
        repeatCols=0,
        rowSplitRange=(2, -1),
        spaceBefore=None,
        spaceAfter=None,
        cornerRadii=None,
    )

    style = TableStyle(
        [
            ("VALIGN", (0, 0), (-1, 0), "MIDDLE"),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 1), (-1, -1), "MIDDLE"),
            ("INNERGRID", (0, 0), (-1, -1), 1, "white"),
            ("TEXTFONT", (0, 1), (-1, -1), "Franklin_Gothic_Book"),
            ("FONTSIZE", (0, 1), (-1, -1), 12),
            (
                "ROWBACKGROUNDS",
                (0, 1),
                (-1, -1),
                [HexColor("#FFFFFF"), HexColor("#DEEBF7")],
            ),
            ("BACKGROUND", (0, 0), (-1, 0), HexColor("#1d5288")),
            ("LINEBELOW", (0, -1), (-1, -1), 1.5, HexColor("#1d5288")),
        ]
    )
    table.setStyle(style)

    if len(df) == 0:
        label = Paragraph(
            "No Data to Report",
            ParagraphStyle(
                name="centered",
                fontName="Franklin_Gothic_Medium_Regular",
                textColor=HexColor("#a7a7a6"),
                fontSize=16,
                leading=16,
                alignment=1,
                spaceAfter=10,
                spaceBefore=10,
            ),
        )
        table = KeepTogether([table, label])
    return table


def format_anchor_table(
    df, header_style, column_widths, column_style_list, remove_symbols=False
):
    """Read in a dataframe and convert/format it to a table, with link anchors."""
    header_row = [
        [Paragraph(str(cell), header_style) for cell in row] for row in [df.columns]
    ]
    data = []
    for row in np.array(df).tolist():
        current_cell = 0
        current_row = []
        for cell in row:
            if column_style_list[current_cell] is not None:
                if current_cell == 0:
                    anchor_link = sha256(str(cell).encode("utf8")).hexdigest()
                    # Add spaces to breach name for proper text wrapping
                    wrap_str = " ".join(
                        str(cell)[i : i + 20] for i in range(0, len(str(cell)), 20)
                    )
                    anchor_str = f'<a name="{anchor_link}"/>{wrap_str}'
                    cell = Paragraph(anchor_str, column_style_list[current_cell])
                else:
                    # Remove emojis from content because the report generator can't display them
                    cell = Paragraph(
                        demoji.replace(str(cell), "").replace("&", "[and]"),
                        column_style_list[current_cell],
                    )
            current_row.append(cell)
            current_cell += 1
        data.append(current_row)
    data = header_row + data

    table = Table(
        data,
        colWidths=column_widths,
        rowHeights=None,
        style=None,
        splitByRow=1,
        repeatRows=1,
        repeatCols=0,
        rowSplitRange=(2, -1),
        spaceBefore=None,
        spaceAfter=None,
        cornerRadii=None,
    )

    style = TableStyle(
        [
            ("VALIGN", (0, 0), (-1, 0), "MIDDLE"),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 1), (-1, -1), "MIDDLE"),
            ("INNERGRID", (0, 0), (-1, -1), 1, "white"),
            ("TEXTFONT", (0, 1), (-1, -1), "Franklin_Gothic_Book"),
            ("FONTSIZE", (0, 1), (-1, -1), 12),
            (
                "ROWBACKGROUNDS",
                (0, 1),
                (-1, -1),
                [HexColor("#FFFFFF"), HexColor("#DEEBF7")],
            ),
            ("BACKGROUND", (0, 0), (-1, 0), HexColor("#1d5288")),
            ("LINEBELOW", (0, -1), (-1, -1), 1.5, HexColor("#1d5288")),
        ]
    )
    table.setStyle(style)

    if len(df) == 0:
        label = Paragraph(
            "No Data to Report",
            ParagraphStyle(
                name="centered",
                fontName="Franklin_Gothic_Medium_Regular",
                textColor=HexColor("#a7a7a6"),
                fontSize=16,
                leading=16,
                alignment=1,
                spaceAfter=10,
                spaceBefore=10,
            ),
        )
        table = KeepTogether([table, label])
    return table


def build_kpi(data, width):
    """Build a KPI element."""
    table = Table(
        [[data]],
        colWidths=[width * inch],
        rowHeights=60,
        style=None,
        splitByRow=1,
        repeatRows=0,
        repeatCols=0,
        rowSplitRange=None,
        spaceBefore=None,
        spaceAfter=None,
        cornerRadii=[10, 10, 10, 10],
    )

    style = TableStyle(
        [
            ("VALIGN", (0, 0), (-1, 0), "MIDDLE"),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 1), (-1, -1), "MIDDLE"),
            ("GRID", (0, 0), (0, 0), 1, HexColor("#003e67")),
            ("BACKGROUND", (0, 0), (0, 0), HexColor("#DEEBF7")),
        ]
    )
    table.setStyle(style)
    return table


def report_gen(data_dict, soc_med_included=False):
    """Generate a P&E report with data passed in the data dictionry."""

    def titlePage(canvas, doc):
        """Build static elements of the cover page."""
        canvas.saveState()
        canvas.drawImage(BASE_DIR + "/assets/Cover.png", 0, 0, width=None, height=None)
        canvas.setFont("Franklin_Gothic_Medium_Regular", 32)
        canvas.drawString(50, 660, "Posture & Exposure Report")
        canvas.restoreState()

    def summaryPage(canvas, doc):
        """Build static elements of the summary page."""
        canvas.saveState()
        canvas.setFont("Franklin_Gothic_Book", 13)
        canvas.drawImage(
            BASE_DIR + "/assets/summary-background.png",
            0,
            0,
            width=PAGE_WIDTH,
            height=PAGE_HEIGHT,
        )
        canvas.setFillColor(HexColor("#1d5288"))
        canvas.setStrokeColor("#1d5288")
        canvas.rect(inch, 210, 3.5 * inch, 5.7 * inch, fill=1)
        canvas.restoreState()
        summary_frame = Frame(
            1.1 * inch, 224, 3.3 * inch, 5.5 * inch, id=None, showBoundary=0
        )
        summary_1_style = ParagraphStyle(
            "summary_1_style",
            fontSize=12,
            alignment=0,
            textColor="white",
            fontName="Franklin_Gothic_Book",
        )
        summary_1 = Paragraph(
            """
        <font face="Franklin_Gothic_Medium_Regular">Credential Publication & Abuse:</font><br/>
        User credentials, often including passwords, are stolen or exposed via data breaches. They are then listed for sale on forums and the dark web, which provides attackers easy access to a stakeholders' network.
        <br/><br/><br/><br/>
        <font face="Franklin_Gothic_Medium_Regular">Suspected Domain Masquerading:</font><br/>
        Registered domain names that are similar to legitimate domains which attempt to trick users into navigating to illegitimate domains.
        <br/><br/><br/><br/><br/><br/>
        <font face="Franklin_Gothic_Medium_Regular">Insecure Devices & Vulnerabilities:</font><br/>
        Open ports, risky protocols, insecure products, and externally observable vulnerabilities are potential targets for exploit.
        <br/><br/><br/><br/><br/>
        <font face="Franklin_Gothic_Medium_Regular">Dark Web Activity:</font><br/>
        Heightened public attention can indicate increased targeting and attack coordination, especially when attention is found on the dark web.
        """,
            style=summary_1_style,
        )
        summary_frame.addFromList([summary_1], canvas)

        summary_frame_2 = Frame(
            5.1 * inch, 552, 2.4 * inch, 0.7 * inch, id=None, showBoundary=0
        )
        summary_2 = Paragraph(
            str(data_dict["creds"])
            + """<br/> <font face="Franklin_Gothic_Book" size='10'>Total Credential Publications</font>""",
            style=kpi,
        )
        summary_frame_2.addFromList([summary_2], canvas)

        summary_frame_3 = Frame(
            5.1 * inch, 444, 2.4 * inch, 0.7 * inch, id=None, showBoundary=0
        )
        summary_3 = Paragraph(
            str(data_dict["suspectedDomains"])
            + """<br/> <font face="Franklin_Gothic_Book" size='10'>Suspected Domain Masquerading</font>""",
            style=kpi,
        )
        summary_frame_3.addFromList([summary_3], canvas)

        summary_frame_4 = Frame(
            5.1 * inch, 337, 2.4 * inch, 0.7 * inch, id=None, showBoundary=0
        )
        summary_4 = Paragraph(
            str(data_dict["verifVulns"])
            + """<br/> <font face="Franklin_Gothic_Book" size='10'>Shodan Verified Vulnerabilities Found</font>""",
            style=kpi,
        )
        summary_frame_4.addFromList([summary_4], canvas)

        summary_frame_5 = Frame(
            5.1 * inch, 230, 2.4 * inch, 0.7 * inch, id=None, showBoundary=0
        )
        summary_5 = Paragraph(
            str(data_dict["darkWeb"])
            + """<br/> <font face="Franklin_Gothic_Book" size='10'>Dark Web Alerts</font>""",
            style=kpi,
        )
        summary_frame_5.addFromList([summary_5], canvas)

        json_title_frame = Frame(
            3.85 * inch, 175, 1.5 * inch, 0.5 * inch, id=None, showBoundary=0
        )
        json_title = Paragraph(
            "JSON&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;EXCEL",
            style=json_excel,
        )
        json_title_frame.addFromList([json_title], canvas)

        canvas.setStrokeColor("#a7a7a6")
        canvas.setFillColor("#a7a7a6")
        canvas.drawInlineImage(
            BASE_DIR + "/assets/cisa.png", 45, 705, width=65, height=65
        )
        canvas.drawString(130, 745, "Posture and Exposure Report")
        canvas.drawString(130, 725, "Reporting Period: " + data_dict["dateRange"])
        canvas.line(130, 710, PAGE_WIDTH - inch, 710)
        canvas.drawRightString(
            PAGE_WIDTH - inch, 0.75 * inch, "P&E Report | Page %d" % (doc.page)
        )
        canvas.drawString(inch, 0.75 * inch, data_dict["endDate"])
        canvas.setFont("Franklin_Gothic_Medium_Regular", 12)
        canvas.setFillColor("#FFC000")
        canvas.drawString(6.4 * inch, 745, "TLP: AMBER")

    def contentPage(canvas, doc):
        """Build the header and footer content for the rest of the pages in the report."""
        canvas.saveState()
        canvas.setFont("Franklin_Gothic_Book", 12)
        canvas.setStrokeColor("#a7a7a6")
        canvas.setFillColor("#a7a7a6")
        canvas.drawImage(BASE_DIR + "/assets/cisa.png", 45, 705, width=65, height=65)
        canvas.drawString(130, 745, "Posture and Exposure Report")
        canvas.drawString(130, 725, "Reporting Period: " + data_dict["dateRange"])
        canvas.line(130, 710, PAGE_WIDTH - inch, 710)
        canvas.drawRightString(
            PAGE_WIDTH - inch, 0.75 * inch, "P&E Report | Page %d" % (doc.page)
        )
        canvas.drawString(inch, 0.75 * inch, data_dict["endDate"])
        canvas.setFont("Franklin_Gothic_Medium_Regular", 12)
        canvas.setFillColor("#FFC000")
        canvas.drawString(6.4 * inch, 745, "TLP: AMBER")
        canvas.restoreState()

    def doHeading(text, sty):
        """Add a bookmark to heading element to allow linking from the table of contents."""
        # create bookmarkname
        bn = sha256((text + sty.name).encode("utf8")).hexdigest()
        # modify paragraph text to include an anchor point with name bn
        h = Paragraph(text + '<a name="%s"/>' % bn, sty)
        # store the bookmark name on the flowable so afterFlowable can see this
        h._bookmarkName = bn
        return h

    # ***Document Structures***#
    """Build frames for different page structures."""
    doc = MyDocTemplate(data_dict["filename"])
    title_frame = Frame(45, 390, 530, 250, id=None, showBoundary=0)
    frameT = Frame(
        doc.leftMargin,
        doc.bottomMargin,
        PAGE_WIDTH - (2 * inch),
        PAGE_HEIGHT - (2.4 * inch),
        id="normal",
        showBoundary=0,
    )
    doc.addPageTemplates(
        [
            PageTemplate(id="TitlePage", frames=title_frame, onPage=titlePage),
            PageTemplate(id="SummaryPage", frames=frameT, onPage=summaryPage),
            PageTemplate(id="ContentPage", frames=frameT, onPage=contentPage),
        ]
    )
    Story = []
    """Build table of contents."""
    toc = TableOfContents()
    tof = ListOfFigures()
    tot = ListOfTables()

    """Create font and formatting styles."""
    PS = ParagraphStyle

    centered = PS(
        name="centered",
        fontName="Franklin_Gothic_Medium_Regular",
        fontSize=20,
        leading=16,
        alignment=1,
        spaceAfter=10,
        spaceBefore=10,
    )

    indented = PS(
        name="indented",
        fontName="Franklin_Gothic_Book",
        fontSize=12,
        leading=14,
        leftIndent=30,
        spaceAfter=20,
    )

    h1 = PS(
        fontName="Franklin_Gothic_Medium_Regular",
        name="Heading1",
        fontSize=16,
        leading=18,
        textColor=HexColor("#003e67"),
    )

    h2 = PS(
        name="Heading2",
        fontName="Franklin_Gothic_Medium_Regular",
        fontSize=14,
        leading=10,
        textColor=HexColor("#003e67"),
        spaceAfter=12,
    )

    h3 = PS(
        name="Heading3",
        fontName="Franklin_Gothic_Medium_Regular",
        fontSize=14,
        leading=10,
        textColor=HexColor("#003e67"),
        spaceAfter=10,
    )

    body = PS(
        name="body",
        leading=14,
        fontName="Franklin_Gothic_Book",
        fontSize=12,
    )

    kpi = PS(
        name="kpi",
        fontName="Franklin_Gothic_Medium_Regular",
        fontSize=14,
        leading=16,
        alignment=1,
        spaceAfter=20,
    )

    json_excel = PS(
        name="json_excel",
        fontName="Franklin_Gothic_Medium_Regular",
        fontSize=10,
        alignment=1,
    )

    figure = PS(
        name="figure",
        fontName="Franklin_Gothic_Medium_Regular",
        fontSize=12,
        leading=16,
        alignment=1,
    )

    table = PS(
        name="table",
        fontName="Franklin_Gothic_Medium_Regular",
        fontSize=12,
        leading=16,
        alignment=1,
        spaceAfter=12,
    )

    table_header = PS(
        name="table_header",
        fontName="Franklin_Gothic_Medium_Regular",
        fontSize=12,
        leading=16,
        alignment=1,
        spaceAfter=12,
        textColor=HexColor("#FFFFFF"),
    )

    title_data = PS(
        fontName="Franklin_Gothic_Medium_Regular", name="Title", fontSize=18, leading=20
    )

    """Stream all the dynamic content to the report."""

    # *************************#
    # Create repeated elements
    point12_spacer = ConditionalSpacer(1, 12)
    horizontal_line = HRFlowable(
        width="100%",
        thickness=1.5,
        lineCap="round",
        color=HexColor("#003e67"),
        spaceBefore=0,
        spaceAfter=1,
        hAlign="LEFT",
        vAlign="TOP",
        dash=None,
    )
    # ***Title Page***#
    Story.append(Paragraph("Prepared for: " + data_dict["department"], title_data))
    Story.append(point12_spacer)
    Story.append(Paragraph("Reporting Period: " + data_dict["dateRange"], title_data))
    Story.append(NextPageTemplate("ContentPage"))
    Story.append(PageBreak())

    # ***Table of Contents***#
    Story.append(Paragraph("<b>Table of Contents</b>", centered))
    # Set styles for levels in Table of contents
    toc_styles = [
        PS(
            fontName="Franklin_Gothic_Medium_Regular",
            fontSize=14,
            name="TOCHeading1",
            leftIndent=20,
            firstLineIndent=-20,
            spaceBefore=1,
            leading=14,
        ),
        PS(
            fontSize=12,
            name="TOCHeading2",
            leftIndent=40,
            firstLineIndent=-20,
            spaceBefore=0,
            leading=12,
        ),
        PS(
            fontSize=10,
            name="TOCHeading3",
            leftIndent=60,
            firstLineIndent=-20,
            spaceBefore=0,
            leading=12,
        ),
        PS(
            fontSize=10,
            name="TOCHeading4",
            leftIndent=100,
            firstLineIndent=-20,
            spaceBefore=0,
            leading=12,
        ),
    ]
    toc.levelStyles = toc_styles
    Story.append(toc)
    Story.append(PageBreak())

    # ***Table of Figures and Table of Contents***#
    tot.levelStyles = toc_styles
    tof.levelStyles = toc_styles
    Story.append(Paragraph("<b>Table of Figures</b>", centered))
    Story.append(tof)
    Story.append(Paragraph("<b>Table of Tables</b>", centered))
    Story.append(tot)
    Story.append(PageBreak())

    # ***Content Pages***#
    # ***Start Introduction Page***#
    Story.append(doHeading("1. Introduction", h1))
    Story.append(horizontal_line)
    Story.append(point12_spacer)
    Story.append(doHeading("1.1 Overview", h2))
    Story.append(
        Paragraph(
            """Posture and Exposure (P&amp;E) offers stakeholders an opportunity to view their organizational
                risk from the viewpoint of the adversary. We utilize passive reconnaissance services,
                dark web analysis, and open-source tools to identify spoofing in order to generate a risk
                    profile report that is delivered on a regular basis.<br/><br/>
                As a customer of P&amp;E you are receiving our regularly scheduled report which contains a
                summary of the activity we have been tracking on your behalf for the following services:
                <br/><br/>""",
            body,
        )
    )

    Story.append(
        ListFlowable(
            [
                ListItem(
                    Paragraph("Credentials Leaked/Exposed", body),
                    leftIndent=35,
                    value="bulletchar",
                ),
                ListItem(
                    Paragraph("Domain Masquerading and Monitoring", body),
                    leftIndent=35,
                    value="bulletchar",
                ),
                ListItem(
                    Paragraph("Vulnerabilities & Malware Associations", body),
                    leftIndent=35,
                    value="bulletchar",
                ),
                ListItem(
                    Paragraph("Dark Web Monitoring", body),
                    leftIndent=35,
                    value="bulletchar",
                ),
                ListItem(
                    Paragraph("Hidden Assets and Risky Services", body),
                    leftIndent=35,
                    value="bulletchar",
                ),
            ],
            bulletType="bullet",
            start="bulletchar",
            leftIndent=10,
        )
    )

    Story.append(
        Paragraph(
            """<br/>It is important to note that these findings have not been verified; everything is
                            gathered via passive analysis of publicly available sources. As such there may be false
                            positive findings, however, these findings should be treated as information that your
                            organization is leaking out to the internet for adversaries to notice.<br/><br/>""",
            body,
        )
    )

    Story.append(doHeading("1.2 How to Use This Report", h2))
    Story.append(
        Paragraph(
            """While it is not our intent to prescribe to you a particular process for remediating
                            vulnerabilities, we hope you will use this report to strengthen your security posture.
                            Here is a recommended workflow:<br/><br/>""",
            body,
        )
    )
    Story.append(
        ListFlowable(
            [
                ListItem(
                    Paragraph(
                        """Review the Summary of Findings on page 5. This section gives a quick overview of key
                            results including the number of credential exposures, domain masquerading alerts, Shodan
                            verified vulnerabilites, and dark web alerts.""",
                        body,
                    ),
                    leftIndent=35,
                ),
                ListItem(
                    Paragraph(
                        """Dive deeper into those key findings by investigating the detailed results starting on
                            page 6.""",
                        body,
                    ),
                    leftIndent=35,
                ),
                ListItem(
                    Paragraph(
                        """View the raw data used to generate this report by navigating to page 5 where you can open the embedded Excel
                            files. If you are having trouble opening these files, make sure to use Adobe Acrobat.""",
                        body,
                    ),
                    leftIndent=35,
                ),
                ListItem(
                    Paragraph(
                        """If you have any questions regarding your report, please refer to the Frequently Asked Questions found on page 19. Please
                            feel free to contact us at vulnerability@cisa.gov with any further questions or concerns.<br/><br/>""",
                        body,
                    ),
                    leftIndent=35,
                ),
            ],
            bulletType="1",
            bulletFormat="%s.",
            leftIndent=10,
            bulletFontSize=12,
        )
    )

    Story.append(doHeading("1.3 Contact Information", h2))
    Story.append(
        Paragraph("Posture and Exposure Team Email: vulnerability@cisa.dhs.gov", body)
    )

    Story.append(NextPageTemplate("SummaryPage"))
    Story.append(PageBreak())

    # ***Start Generating Summary Page***#
    Story.append(doHeading("2. Summary of Findings", h1))
    Story.append(horizontal_line)
    Story.append(point12_spacer)
    Story.append(doHeading("2.1 Summary of Tracked Data & Key Metrics", h2))
    Story.append(Spacer(1, 425))
    Story.append(doHeading("2.2 Raw Data Links", h2))
    Story.append(
        Paragraph(
            "Exposed Credentials<br/><br/>Domain Masquerading and Monitoring<br/><br/>Vulnerabilities and Malware Associations<br/><br/>Dark Web Activity",
            body,
        )
    )

    Story.append(NextPageTemplate("ContentPage"))
    Story.append(PageBreak())

    # ***Start Generating Creds Page***#
    Story.append(doHeading("3. Detailed Results", h1))
    Story.append(horizontal_line)
    Story.append(point12_spacer)
    Story.append(doHeading("3.1 Credential Publication and Abuse", h2))
    Story.append(
        Paragraph(
            """Credential leakage occurs when user credentials, often including passwords, are stolen via phishing
        campaigns, network compromise, or database misconfigurations leading to public exposure. This leaked data is
        then listed for sale on numerous forums and sites on the dark web which provides attackers easy access to a
        stakeholder's networks. Detailed results are presented below.
        """,
            body,
        )
    )

    # Build row of kpi cells
    row = [
        build_kpi(
            Paragraph(
                str(data_dict["breach"])
                + """<br/> <font face="Franklin_Gothic_Book" size='10'>Distinct Breaches</font>""",
                style=kpi,
            ),
            2,
        ),
        build_kpi(
            Paragraph(
                str(data_dict["creds"])
                + """<br/> <font face="Franklin_Gothic_Book" size='10'>Credentials Exposed</font>""",
                style=kpi,
            ),
            2,
        ),
        build_kpi(
            Paragraph(
                str(data_dict["pw_creds"])
                + """<br/> <font face="Franklin_Gothic_Book" size='10'>Credentials with Password</font>""",
                style=kpi,
            ),
            2,
        ),
    ]
    Story.append(
        BalancedColumns(
            row,  # the flowables we are balancing
            nCols=3,  # the number of columns
            needed=55,  # the minimum space needed by the flowable
            spaceBefore=0,
            spaceAfter=12,
            showBoundary=False,  # optional boundary showing
            leftPadding=4,  # these override the created frame
            rightPadding=0,  # paddings if specified else the
            topPadding=None,  # default frame paddings
            bottomPadding=None,  # are used
            innerPadding=8,  # the gap between frames if specified else
            # use max(leftPadding,rightPadding)
            name="creds_kpis",  # for identification purposes when stuff goes awry
            endSlack=0.1,  # height disparity allowance ie 10% of available height
        )
    )

    Story.append(
        Paragraph(
            """
            <font face="Franklin_Gothic_Medium_Regular">Figure 1</font> shows the number of credentials that were exposed each week for the past 4 weeks. Credentials that
            were exposed with an accompanying password are shown in red. Exposed credentials that did not include a corresponding password
            are shown in blue.
            """,
            body,
        )
    )
    Story.append(point12_spacer)

    # Figure 1:
    Story.append(
        KeepTogether(
            [
                doHeading(
                    """
                        Figure 1. Credentials Exposed.
                    """,
                    figure,
                ),
                get_image(BASE_DIR + "/assets/inc_date_df.png", width=6.5 * inch),
            ]
        )
    )
    Story.append(PageBreak())

    # Table 1:
    # add link to appendix to breach names
    data_dict["breach_table"]["Breach Name"] = (
        '<link href="#'
        + data_dict["breach_table"]["Breach Name"].apply(sha_hash)
        + '" color="#003e67">'
        + data_dict["breach_table"]["Breach Name"].astype(str)
        + "</link>"
    )
    Story.append(
        KeepTogether(
            [
                Paragraph(
                    """
                    <font face="Franklin_Gothic_Medium_Regular">Table 1</font>  provides breach details. Breach descriptions can be found in Appendix A.
                    """,
                    body,
                ),
                point12_spacer,
                doHeading(
                    """
                    Table 1. Breach Details.
                    """,
                    table,
                ),
                format_table(
                    data_dict["breach_table"],
                    table_header,
                    [2.5 * inch, inch, inch, inch, inch],
                    [body, None, None, None, None],
                ),
            ]
        )
    )
    Story.append(point12_spacer)
    Story.append(PageBreak())

    # ***Start Generating Domain Masquerading Page***#
    Story.append(
        KeepTogether(
            [
                doHeading("3.2 Domain Alerts and Suspected Masquerading", h2),
                Paragraph(
                    """Spoofed or typo-squatting domains can be used to host fake web pages for malicious purposes,
            such as imitating landing pages for spear phishing campaigns. Below are alerts of domains that appear
            to mimic a stakeholder's actual domain.
            """,
                    body,
                ),
                point12_spacer,
            ]
        )
    )

    row = [
        build_kpi(
            Paragraph(
                str(data_dict["domain_alerts"])
                + """<br/> <font face="Franklin_Gothic_Book" size='10'>Domain Alert(s)</font>""",
                style=kpi,
            ),
            2,
        ),
        build_kpi(
            Paragraph(
                str(data_dict["suspectedDomains"])
                + """<br/> <font face="Franklin_Gothic_Book" size='10'>Suspected Domain(s)</font>""",
                style=kpi,
            ),
            2,
        ),
    ]

    Story.append(
        BalancedColumns(
            row,  # the flowables we are balancing
            nCols=2,  # the number of columns
            needed=55,  # the minimum space needed by the flowable
            spaceBefore=0,
            spaceAfter=12,
            showBoundary=False,  # optional boundary showing
            leftPadding=65,  # these override the created frame
            rightPadding=0,  # paddings if specified else the
            topPadding=None,  # default frame paddings
            bottomPadding=None,  # are used
            innerPadding=35,  # the gap between frames if specified else
            # use max(leftPadding,rightPadding)
            name="domain_masq_kpis",  # for identification purposes when stuff goes awry
            endSlack=0.1,  # height disparity allowance ie 10% of available height
        )
    )

    # Table 2
    Story.append(Paragraph("3.2.1 Domain Monitoring Alerts", h3))
    Story.append(
        Paragraph(
            """
            <font face="Franklin_Gothic_Medium_Regular">Table 2</font> shows alerts of newly registered or updated
            domains that appear to mimic a stakeholder's actual domain.
        """,
            body,
        )
    )
    Story.append(point12_spacer)
    Story.append(
        doHeading(
            """
                    Table 2. Domain Monitoring Alerts Results.
                """,
            table,
        )
    )
    Story.append(
        format_table(
            data_dict["domain_alerts_table"],
            table_header,
            [5.5 * inch, 1 * inch],
            [body, None],
        )
    )
    Story.append(point12_spacer)

    # Table 3:
    Story.append(
        KeepTogether(
            [
                Paragraph("3.2.2 Suspected Domain Masquerading", h3),
                Paragraph(
                    """
                    <font face="Franklin_Gothic_Medium_Regular">Table 3</font> shows registered or updated domains that were
                    flagged by a blocklist service.
                """,
                    body,
                ),
                point12_spacer,
                doHeading(
                    """
                    Table 3. Suspected Domain Masquerading Results.
                """,
                    table,
                ),
            ]
        )
    )
    Story.append(
        format_table(
            data_dict["domain_table"],
            table_header,
            [1.5 * inch, 1.5 * inch, 3.5 * inch / 3, 3.5 * inch / 3, 3.5 * inch / 3],
            [body, body, body, body, body],
        )
    )
    Story.append(point12_spacer)
    Story.append(PageBreak())

    # ***Start Generating Vulnerabilities Page***#
    Story.append(
        KeepTogether(
            [
                doHeading("3.3 Insecure Devices & Suspected Vulnerabilities", h2),
                Paragraph(
                    """This category includes insecure ports, protocols, and services; Shodan-verified vulnerabilities;
                and suspected vulnerabilities. Detailed results are presented below and discussed in the sections that follow.
                """,
                    body,
                ),
                point12_spacer,
            ]
        )
    )
    row = [
        build_kpi(
            Paragraph(
                str(data_dict["riskyPorts"])
                + """<br/> <font face="Franklin_Gothic_Book" size='10'>Total Open Ports with <br/>Insecure Protocols</font>""",
                style=kpi,
            ),
            2,
        ),
        build_kpi(
            Paragraph(
                str(data_dict["verifVulns"])
                + """<br/> <font face="Franklin_Gothic_Book" size='10'>Total Shodan-Verified Vulnerabilities</font>""",
                style=kpi,
            ),
            2,
        ),
        build_kpi(
            Paragraph(
                str(data_dict["unverifVulns"])
                + """<br/> <font face="Franklin_Gothic_Book" size='10'>Assets with Suspected Vulnerabilities</font>""",
                style=kpi,
            ),
            2,
        ),
    ]
    Story.append(
        BalancedColumns(
            row,  # the flowables we are balancing
            nCols=3,  # the number of columns
            needed=55,  # the minimum space needed by the flowable
            spaceBefore=0,
            spaceAfter=12,
            showBoundary=False,  # optional boundary showing
            leftPadding=4,  # these override the created frame
            rightPadding=0,  # paddings if specified else the
            topPadding=None,  # default frame paddings
            bottomPadding=None,  # are used
            innerPadding=8,  # the gap between frames if specified else
            # use max(leftPadding,rightPadding)
            name="vulns_kpis",  # for identification purposes when stuff goes awry
            endSlack=0.1,  # height disparity allowance ie 10% of available height
        )
    )

    Story.append(Paragraph("3.3.1 Insecure Ports, Protocols, and Services", h3))
    Story.append(
        Paragraph(
            """
            Insecure protocols are those protocols which lack proper encryption allowing threat actors to access
            data that is being transmitted and even to potentially, to control systems.
            <font face="Franklin_Gothic_Medium_Regular">Figure 2</font> and
            <font face="Franklin_Gothic_Medium_Regular">Table 4</font> provide detailed information for the Remote
            Desktop Protocol (RDP), Server Message Block (SMB) protocol, and the Telnet application protocol.
        """,
            body,
        )
    )
    Story.append(point12_spacer)

    # Figure 2:
    Story.append(
        KeepTogether(
            [
                doHeading(
                    """
                        Figure 2. Insecure Protocols.
                    """,
                    figure,
                ),
                get_image(BASE_DIR + "/assets/pro_count.png", width=6.5 * inch),
            ]
        )
    )
    # Table 4:
    Story.append(
        doHeading(
            """
                Table 4. Insecure Protocols.
            """,
            table,
        )
    )
    Story.append(
        format_table(
            data_dict["risky_assets"],
            table_header,
            [1.5 * inch, 3.5 * inch, 1.5 * inch],
            [None, body, None],
        )
    )
    Story.append(point12_spacer)

    # Table 5:
    # add link to appendix for CVE string
    data_dict["verif_vulns"]["CVE"] = (
        '<link href="#'
        + data_dict["verif_vulns"]["CVE"].str.replace("-", "_")
        + '" color="#003e67">'
        + data_dict["verif_vulns"]["CVE"].astype(str)
        + "</link>"
    )
    Story.append(
        KeepTogether(
            [
                Paragraph("3.3.2 Shodan-Verified Vulnerabilities", h3),
                Paragraph(
                    """
                    Verified vulnerabilities, shown in <font face="Franklin_Gothic_Medium_Regular">Table 5</font>, are those that are flagged by P&amp;E vendors that have gone
                    through extra checks to validate the finding. Refer to Appendix A for summary data.
                """,
                    body,
                ),
                doHeading(
                    """
                    Table 5. Shodan-Verified Vulnerabilities.
                """,
                    table,
                ),
                format_table(
                    data_dict["verif_vulns"],
                    table_header,
                    [6.5 * inch / 3, 6.5 * inch / 3, 6.5 * inch / 3],
                    [body, None, None],
                ),
            ]
        )
    )
    Story.append(point12_spacer)

    # Figure 3:
    Story.append(
        KeepTogether(
            [
                Paragraph("3.3.3 Suspected Vulnerabilities", h3),
                Paragraph(
                    """
                        Suspected vulnerabilities are determined by the software and version an asset is running and can be used
                        to understand what vulnerabilities an asset may be exposed to.
                        <font face="Franklin_Gothic_Medium_Regular">Figure 3</font> identifies suspected vulnerabilities.
                    """,
                    body,
                ),
                point12_spacer,
                doHeading(
                    """
                        Figure 3. Suspected Vulnerabilities.
                    """,
                    figure,
                ),
                get_image(
                    BASE_DIR + "/assets/unverif_vuln_count.png", width=6.5 * inch
                ),
            ]
        )
    )
    # Story.append(NextPageTemplate('ContentPage'))
    Story.append(PageBreak())

    # ***Start Generating Dark Web Page***#
    Story.append(KeepTogether([doHeading("3.4 Dark Web Activity", h2), Spacer(1, 6)]))

    row = [
        build_kpi(
            Paragraph(
                str(data_dict["mentions_count"])
                + """<br/> <font face="Franklin_Gothic_Book" size='10'>Dark Web Mentions</font>""",
                style=kpi,
            ),
            2,
        ),
        build_kpi(
            Paragraph(
                str(data_dict["darkWeb"])
                + """<br/> <font face="Franklin_Gothic_Book" size='10'>Dark Web Alerts</font>""",
                style=kpi,
            ),
            2,
        ),
    ]

    Story.append(
        BalancedColumns(
            row,  # the flowables we are balancing
            nCols=2,  # the number of columns
            needed=55,  # the minimum space needed by the flowable
            spaceBefore=0,
            spaceAfter=12,
            showBoundary=False,  # optional boundary showing
            leftPadding=65,  # these override the created frame
            rightPadding=0,  # paddings if specified else the
            topPadding=None,  # default frame paddings
            bottomPadding=None,  # are used
            innerPadding=35,  # the gap between frames if specified else
            # use max(leftPadding,rightPadding)
            name="dark_web_kpis",  # for identification purposes when stuff goes awry
            endSlack=0.1,  # height disparity allowance ie 10% of available height
        )
    )

    Story.append(
        Paragraph(
            """Stakeholders and vulnerabilities are often discussed in various ways on the Dark Web. P&amp;E monitors this
                activity, as well as the source (forums, websites, tutorials), and threat actors involved. A spike in activity can
                indicate a greater likelihood of an attack, vulnerability, or data leakage. This information along with a list of the
                most active CVEs on the Dark Web may assist in prioritizing remediation activities.""",
            style=body,
        )
    )

    Story.append(point12_spacer)

    Story.append(Paragraph("3.4.1 Dark Web Mentions", h3))
    Story.append(
        Paragraph(
            """
            <font face="Franklin_Gothic_Medium_Regular">Figure 4</font> provides details on the number of mentions on the
            dark web during the reporting period.
        """,
            body,
        )
    )
    Story.append(point12_spacer)
    Story.append(
        KeepTogether(
            [
                doHeading(
                    """
                        Figure 4. Dark Web Mentions.
                    """,
                    figure,
                ),
                get_image(BASE_DIR + "/assets/web_only_df_2.png", width=6.5 * inch),
            ]
        )
    )
    sub_section = 2
    table_num = 6
    if soc_med_included:
        Story.append(
            KeepTogether(
                [
                    Paragraph("3.4.2 Most Active Social Media Posts", h3),
                    Paragraph(
                        """
                        This result includes a list of the most active social media posts associated with a stakeholder, and tallies
                        the count of “post” or “reply” actions on sites such as Telegram, Twitter, and Github.
                        <font face="Franklin_Gothic_Medium_Regular">Table 6</font> identifies the social media comments count
                        by organization.
                    """,
                        body,
                    ),
                    point12_spacer,
                    doHeading(
                        """
                        Table 6. Social Media Comments Count.
                    """,
                        table,
                    ),
                ]
            )
        )

        Story.append(
            format_table(
                data_dict["social_med_act"],
                table_header,
                [5 * inch, 1.5 * inch],
                [
                    body,
                    None,
                ],
            )
        )

        Story.append(point12_spacer)
        sub_section = 3
        table_num = 7

    Story.append(
        KeepTogether(
            [
                Paragraph(
                    "3.4." + str(sub_section) + " Most Active Dark Web Posts", h3
                ),
                Paragraph(
                    """
                    This result includes a list of the most active posts associated with a stakeholder found on the dark web,
                    and includes forum sites and invite-only marketplaces. <font face="Franklin_Gothic_Medium_Regular">Table """
                    + str(table_num)
                    + """</font>
                    identifies the dark web comments count by organization.
                """,
                    body,
                ),
                point12_spacer,
                doHeading(
                    "Table " + str(table_num) + ". Dark Web Comments Count.", table
                ),
            ]
        )
    )
    sub_section += 1
    table_num += 1
    Story.append(
        format_table(
            data_dict["dark_web_act"],
            table_header,
            [5 * inch, 1.5 * inch],
            [
                body,
                None,
            ],
        )
    )
    Story.append(point12_spacer)

    Story.append(
        KeepTogether(
            [
                Paragraph("3.4." + str(sub_section) + " Asset Alerts", h3),
                Paragraph(
                    """
                    <font face="Franklin_Gothic_Medium_Regular">Table """
                    + str(table_num)
                    + """</font> includes discussions involving stakeholder
                    assets such as domain names and IP's.
                """,
                    body,
                ),
                point12_spacer,
                doHeading("Table " + str(table_num) + ". Asset Alerts.", table),
            ]
        )
    )
    sub_section += 1
    table_num += 1
    Story.append(
        format_table(
            data_dict["asset_alerts"],
            table_header,
            [2 * inch, 3.5 * inch, 1 * inch],
            [None, body, None],
        )
    )

    Story.append(point12_spacer)
    Story.append(
        KeepTogether(
            [
                Paragraph("3.4." + str(sub_section) + " Executive Alerts", h3),
                Paragraph(
                    """
                    <font face="Franklin_Gothic_Medium_Regular">Table """
                    + str(table_num)
                    + """</font> includes discussions involving stakeholder
                    executives and upper management.
                """,
                    body,
                ),
                point12_spacer,
                doHeading("Table " + str(table_num) + ". Executive Alerts.", table),
            ]
        )
    )
    sub_section += 1
    table_num += 1
    Story.append(
        format_table(
            data_dict["alerts_exec"],
            table_header,
            [2 * inch, 3.5 * inch, 1 * inch],
            [None, body, None],
        )
    )

    Story.append(point12_spacer)

    Story.append(
        KeepTogether(
            [
                Paragraph("3.4." + str(sub_section) + " Threat Actors", h3),
                Paragraph(
                    """
                    A threat actor's score is based on the amount of activity that person has on the dark web, the types of
                    content posted, how prominent their account is on a forum, and if there is a larger circle of connections to
                    other bad actors. Threat Actors are ranked 1 to 10, with 10 being the most severe.
                    <font face="Franklin_Gothic_Medium_Regular">Table """
                    + str(table_num)
                    + """</font>
                    identifies the top actors that have mentioned stakeholder assets.
                """,
                    body,
                ),
                point12_spacer,
                doHeading("Table " + str(table_num) + ". Threat Actors.", table),
            ]
        )
    )
    sub_section += 1
    table_num += 1
    Story.append(
        format_table(
            data_dict["dark_web_actors"],
            table_header,
            [5.5 * inch, 1 * inch],
            [body, None],
        )
    )

    Story.append(point12_spacer)

    Story.append(
        KeepTogether(
            [
                Paragraph(
                    "3.4." + str(sub_section) + " Alerts of Potential Threats", h3
                ),
                Paragraph(
                    """
                    Threats are derived by scanning suspicious chatter on the dark web that may have terms related to
                    vulnerabilities. <font face="Franklin_Gothic_Medium_Regular">Table """
                    + str(table_num)
                    + """</font> identifies the most
                    common threats.
                """,
                    body,
                ),
                point12_spacer,
                doHeading(
                    "Table " + str(table_num) + ". Alerts of Potential Threats.", table
                ),
            ]
        )
    )
    sub_section += 1
    table_num += 1
    Story.append(
        format_table(
            data_dict["alerts_threats"],
            table_header,
            [2 * inch, 3.5 * inch, 1 * inch],
            [None, body, None],
        )
    )

    Story.append(point12_spacer)

    Story.append(
        KeepTogether(
            [
                Paragraph("3.4." + str(sub_section) + " Most Active Sites", h3),
                Paragraph(
                    """
                    <font face="Franklin_Gothic_Medium_Regular">Table """
                    + str(table_num)
                    + """</font> includes the most active discussion forums where the organization is the topic of discussion.
                """,
                    body,
                ),
                point12_spacer,
                doHeading("Table " + str(table_num) + ". Most Active Sites.", table),
            ]
        )
    )
    sub_section += 1
    table_num += 1
    Story.append(
        format_table(
            data_dict["dark_web_sites"],
            table_header,
            [5 * inch, 1.5 * inch],
            [body, None],
        )
    )

    Story.append(point12_spacer)

    Story.append(
        KeepTogether(
            [
                Paragraph("3.4." + str(sub_section) + " Invite-Only Market Alerts", h3),
                Paragraph(
                    """
                    <font face="Franklin_Gothic_Medium_Regular">Table """
                    + str(table_num)
                    + """</font> includes the number of alerts on each invite-only
                    market where compromised credentials were offered for sale.
                """,
                    body,
                ),
                point12_spacer,
                doHeading(
                    "Table " + str(table_num) + ". Invite-Only Market Alerts.", table
                ),
            ]
        )
    )
    sub_section += 1
    table_num += 1
    Story.append(
        format_table(
            data_dict["markets_table"],
            table_header,
            [4 * inch, 2.5 * inch],
            [None, None],
        )
    )

    Story.append(point12_spacer)
    Story.append(
        KeepTogether(
            [
                Paragraph(
                    "3.4." + str(sub_section) + " Most Active CVEs on the Dark Web", h3
                ),
                Paragraph(
                    """
                    Rated by CyberSixGill's Dynamic Vulnerability Exploit (DVE) Score, this state-of-the-art machine
                    learning model automatically predicts the probability of a CVE being exploited.
                    <font face="Franklin_Gothic_Medium_Regular">Table """
                    + str(table_num)
                    + """</font> identifies the top 10 CVEs this report period.
                """,
                    body,
                ),
                point12_spacer,
                doHeading(
                    "Table " + str(table_num) + ". Most Active CVEs on the Dark Web.",
                    table,
                ),
            ]
        )
    )
    sub_section += 1
    table_num += 1
    Story.append(
        format_table(
            data_dict["top_cves"],
            table_header,
            [1.5 * inch, 3.5 * inch, 0.75 * inch, 1.25 * inch],  # col widths
            [None, body, None, None],  # col styles
        )
    )

    Story.append(point12_spacer)

    Story.append(NextPageTemplate("ContentPage"))
    Story.append(PageBreak())

    # ***Start Generating Methodology Page***#
    Story.append(doHeading("4. Methodology", h1))
    Story.append(horizontal_line)
    Story.append(point12_spacer)
    Story.append(doHeading("4.1 Background", h2))
    Story.append(
        Paragraph(
            """Cyber Hygiene's Posture and Exposure is a service provided by the Cybersecurity
            and Infrastructure Security Agency (CISA).<br/><br/>
            Cyber Hygiene started providing Posture and Exposure reports in October 2020 to assess,
            on a recurring basis, the security posture of your organization by tracking dark web activity,
            domain alerts, vulnerabilites, and credential exposures.""",
            body,
        )
    )
    Story.append(point12_spacer)
    Story.append(doHeading("4.2 Process", h2))
    Story.append(
        Paragraph(
            """Upon submission of an Acceptance Letter, DHS provided CISA with their
            public network address information.<br/><br/>
            The Posture and Exposure team uses this information to conduct investigations
            with various open-source tools. Resulting data is then parsed for key-findings
            and alerts. Summary data and detailed overviews are organized into this report
            and packaged into an encrypted file for delivery.""",
            body,
        )
    )
    Story.append(point12_spacer)
    Story.append(doHeading("5. Conclusion", h1))
    Story.append(horizontal_line)
    Story.append(point12_spacer)
    Story.append(
        Paragraph(
            """Your organization should use the data provided in this report to correct any identified vulnerabilities,
            exposures, or posture concerns. If you have any questions, comments, or concerns about the findings or data
            contained in this report, please work with your designated technical point of contact when requesting
            assistance from CISA at vulnerability@cisa.dhs.gov.""",
            body,
        )
    )
    Story.append(NextPageTemplate("ContentPage"))
    Story.append(PageBreak())

    Story.append(doHeading("Appendix A: Additional Information", h1))
    Story.append(horizontal_line)
    Story.append(point12_spacer)
    # If there are breaches print breach descriptions
    if len(data_dict["breach_appendix"]) > 0:
        Story.append(Paragraph("Credential Breach Details: ", h2))
        Story.append(Spacer(1, 6))

        # Table ver. of Appendix A
        breach_appendix_df = data_dict["breach_appendix"]
        breach_appendix_df.sort_values(by=["breach_name"], ascending=True, inplace=True)
        breach_appendix_df = breach_appendix_df.rename(
            columns={"breach_name": "Breach Name", "description": "Description"}
        )
        Story.append(
            format_anchor_table(
                breach_appendix_df,
                table_header,
                [2 * inch, 5 * inch],  # col widths
                [table, body],  # col styles
            )
        )
        Story.append(point12_spacer)

    # If there are verified vulns print summary info table
    if len(data_dict["verif_vulns_summary"]) > 0:
        Story.append(Paragraph("Verified Vulnerability Summaries:", h2))

        Story.append(
            Paragraph(
                """Verified vulnerabilities are determined by the Shodan scanner and identify assets with active, known vulnerabilities. More information
                about CVE's can be found <link href="https://nvd.nist.gov/">here</link>.""",
                body,
            )
        )
        Story.append(point12_spacer)
        Story.append(
            doHeading(
                "Table " + str(table_num) + ". Verified Vulnerabilities Summaries.",
                table,
            )
        )
        # Add anchor points for vuln links
        data_dict["verif_vulns_summary"]["CVE"] = (
            '<a name="'
            + data_dict["verif_vulns_summary"]["CVE"].str.replace("-", "_")
            + '"/>'
            + data_dict["verif_vulns_summary"]["CVE"].astype(str)
        )
        Story.append(
            format_table(
                data_dict["verif_vulns_summary"],
                table_header,
                [1.5 * inch, 1.25 * inch, 0.75 * inch, 3 * inch],
                [body, None, None, body],
            )
        )
        Story.append(point12_spacer)

    Story.append(
        KeepTogether(
            [
                doHeading("Appendix B: Frequently Asked Questions", h1),
                horizontal_line,
                point12_spacer,
                Paragraph(
                    """<font face="Franklin_Gothic_Medium_Regular">How are P&amp;E data and reports different from other reports I receive from CISA?</font><br/>
            The Cybersecurity and Infrastructure Security Agency's (CISA) Cyber Hygiene Posture and Exposure (P&amp;E)
            analysis is a cost-free service that helps stakeholders monitor and evaluate their cyber posture for
            weaknesses found in public source information, which is readily available to an attacker to view.
            P&amp;E utilizes passive reconnaissance services, dark web analysis, and other public information
            sources to identify suspected domain masquerading, credentials that have been leaked or exposed,
            insecure devices, suspected vulnerabilities, and increased dark web activity related to their organization.
            """,
                    body,
                ),
            ]
        )
    )
    Story.append(point12_spacer)
    Story.append(
        Paragraph(
            """<font face="Franklin_Gothic_Medium_Regular">What should I expect in terms of P&amp;E's findings? </font><br/>
            The Posture and Exposure team uses numerous tools and open-source intelligence (OSINT) gathering tactics to
            identify the potential weaknesses listed below. The data is then analyzed and complied into a Posture and
            Exposure Report which provides both executive level information and detailed information for analysts that
            includes the raw findings.""",
            body,
        )
    )
    Story.append(point12_spacer)

    Story.append(
        Paragraph(
            """
            <font face="Franklin_Gothic_Medium_Regular">Suspected Domain Masquerading:</font><br/>
            Spoofed or typo-squatting domains can be used to host fake web pages for malicious purposes, such as
            imitating landing pages for spear phishing campaigns. This report shows newly registered or reactivated
            domains that appear to mimic a stakeholder's actual domain.""",
            indented,
        )
    )

    Story.append(
        Paragraph(
            """
            <font face="Franklin_Gothic_Medium_Regular">Credentials Leaked/Exposed:</font><br/>
            Credential leakage occurs when user credentials, often including passwords, are stolen via phishing campaigns,
            network compromise or misconfiguration of databases leading to public exposure. This leaked data is then listed
            for sale on numerous forums and sites on the dark web, which provides attackers easy access to a stakeholders'
            networks.
        """,
            indented,
        )
    )

    Story.append(
        Paragraph(
            """
            <font face="Franklin_Gothic_Medium_Regular">Insecure Devices & Suspected Vulnerabilities:</font><br/>
            When looking at Open-Source information gathered from tools that search the web for Internet of Things
            (IoT) devices and other external facing assets. It can then be inferred that certain systems, ports, and
            protocols associated with these assets are likely to have vulnerabilities, based on the OS or application
            version information reported when queried. When possible, our analysis also reports on potential malware
            infections for stakeholders.
        """,
            indented,
        )
    )

    Story.append(
        KeepTogether(
            Paragraph(
                """
                    <font face="Franklin_Gothic_Medium_Regular">Increased Dark Web Activity:</font><br/>
                    Stakeholders and vulnerabilities are often discussed in various ways on the dark web. P&amp;E monitors this
                    activity, as well as the source (forums, websites, tutorials), and threat actors involved. A spike in
                    activity can indicate a greater likelihood of an attack, vulnerability, or data leakage. Additionally,
                    the urgency of the threat can be evaluated based on the threat actors involved along with other thresholds.
                    Evaluating this content may also indicate if a stakeholder has been involved in a hacking incident as that data
                    will often be published or offered 'for sale'. This information along with a list of the most active CVE's on the
                    Dark Web may assist in prioritizing remediation activities.

                """,
                indented,
            )
        )
    )

    Story.append(
        Paragraph(
            """<font face="Franklin_Gothic_Medium_Regular">Do you perform scans of our networks?</font><br/>
            P&amp;E does not perform active scanning. The information we gather is through passive collection from numerous
            public and vendor data sources. As such, we collect data on a continual basis, and provide summary reports
            twice a month.
        """,
            body,
        )
    )
    Story.append(point12_spacer)

    Story.append(
        Paragraph(
            """<font face="Franklin_Gothic_Medium_Regular">How will the results be provided to me?</font><br/>
            P&amp;E will provide twice monthly P&amp;E reports as password-protected attachments to emails from
            vulnerability@cisa.dhs.gov. The attachments will contain a PDF—providing a summary of the findings,
            tables, graphs, as charts—as well as a JSON file containing the raw data used to generate the PDF
            report to facilitate your agencies own analysis.
        """,
            body,
        )
    )
    Story.append(point12_spacer)

    Story.append(
        Paragraph(
            """<font face="Franklin_Gothic_Medium_Regular">Do you offer ad-hoc analysis of source data?</font><br/>
            If you have any questions about a particular vulnerability that you believe you have mitigated, but
            which continues to show up in the reports, we can perform a detailed analysis to determine why your
            organization continues to show that vulnerability. In many cases, the issue can be tracked back to
            the fact that the mitigation has made it impossible for the reconnaissance service or tool to identify
            the configuration, and as such they may default to displaying the last collected information.
        """,
            body,
        )
    )
    Story.append(point12_spacer)

    Story.append(
        Paragraph(
            """<font face="Franklin_Gothic_Medium_Regular">Who do I contact if there are any issues or updates that need to be addressed for my reports?</font><br/>
            The general notification process is the same as all of the CyHy components. Simply send an email to
            vulnerability@cisa.dhs.gov identifying the requested changes. In this instance, make sure to identify
            “P&amp;E Report Delivery” in the subject to ensure the issue is routed to our team.
        """,
            body,
        )
    )
    Story.append(point12_spacer)
    Story.append(
        KeepTogether(
            [
                doHeading("Appendix C: Acronyms", h1),
                horizontal_line,
                point12_spacer,
                Table(
                    [
                        ["CISA", "Cybersecurity and Infrastructure Security Agency"],
                        ["CVE", "Common Vulnerabilities and Exposures"],
                        ["DHS", "Department of Homeland Security"],
                        ["DVE", "Dynamic Vulnerability Exploit"],
                        ["FTP", "File Transfer Protocol"],
                        ["HTTP", "Hypertext Transfer Protocol"],
                        ["IP", "Internet Protocol"],
                        ["P&E", "Posture and Exposure"],
                        ["RDP", "Remote Desktop Protocol"],
                        ["SIP", "Session Initiation Protocol"],
                        ["SMB", "Server Message Block"],
                    ]
                ),
            ]
        )
    )
    doc.multiBuild(Story)
