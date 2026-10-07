"""This module contains the Message class."""

# Standard Python Libraries
from email import encoders
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import logging
import os.path

LOGGER = logging.getLogger(__name__)


class Message(MIMEMultipart):
    """An email message sent from the CISA Cyber Assessments inbox.

    Static attributes
    -----------------
    DefaultFrom : str
        The default value for the address from which the message
        should be sent.

    DefaultCc : list of str
        The default value for the CC addresses to which the message
        should be sent.

    DefaultBcc : list of str
        The default value for the BCC addresses to which the message
        should be sent.

    DefaultReplyTo : str
        The default value for the address to which replies should be
        directed.

    """

    DefaultFrom = "reports@cyber.dhs.gov"
    DefaultCc = None
    DefaultBcc: list[str] = []
    DefaultReplyTo = "vulnerability@cisa.dhs.gov"

    def __init__(
        self,
        to_addrs,
        subject=None,
        text_body=None,
        html_body=None,
        from_addr=DefaultFrom,
        cc_addrs=DefaultCc,
        bcc_addrs=DefaultBcc,
        reply_to_addr=DefaultReplyTo,
    ):
        """Construct an instance.

        Parameters
        ----------
        to_addrs : array of str
            An array of string objects, each of which is an email
            address to which this message should be sent.

        subject : str
            The subject of this email message.

        text_body : str
            The plain-text version of the email body.

        html_body : str
            The HTML version of the email body.

        from_addr : str
            The email address from which this message is to be sent.

        cc_addrs : array of str
            An array of string objects, each of which is a CC email
            address to which this message should be sent.

        bcc_addrs : array of str
            An array of string objects, each of which is a BCC email
            address to which this message should be sent.

        reply_to_addr : str
            The email address to which replies should be sent.

        """
        MIMEMultipart.__init__(self, "mixed")

        self["From"] = from_addr
        LOGGER.debug("Message to be sent from: %s", self["From"])

        self["To"] = ",".join(to_addrs)
        LOGGER.debug("Message to be sent to: %s", self["To"])

        if cc_addrs:
            self["CC"] = ",".join(cc_addrs)
            LOGGER.debug("Message to be sent as CC to: %s", self["CC"])

        if bcc_addrs:
            self["BCC"] = ",".join(bcc_addrs)
            LOGGER.debug("Message to be sent as BCC to: %s", self["BCC"])

        if reply_to_addr:
            self["Reply-To"] = reply_to_addr
            LOGGER.debug("Replies to be sent to: %s", self["Reply-To"])

        if subject:
            self["Subject"] = subject
            LOGGER.debug("Message subject: %s", subject)

        if html_body or text_body:
            self.attach_text_and_html_bodies(html_body, text_body)

    def attach_text_and_html_bodies(self, html, text):
        """Attach a plain text body and/or an HTML text body to this message.

        The HTML body will be the default version that is displayed.
        The text body will be displayed only if the client does not
        support HTML.

        Parameters
        ----------
        html : str
            The HTML to attach.

        text : str
            The plain text to attach.

        """
        textBody = MIMEMultipart("alternative")

        # The order is important here.  This order makes the HTML version the
        # default version that is displayed, as long as the client supports it.
        if text:
            textBody.attach(MIMEText(text, "plain"))
            LOGGER.debug("Message plain-text body: %s", text)

        if html:
            htmlPart = MIMEText(html, "html")
            # See https://en.wikipedia.org/wiki/MIME#Content-Disposition
            htmlPart.add_header("Content-Disposition", "inline")
            textBody.attach(htmlPart)
            LOGGER.debug("Message HTML body: %s", html)

        self.attach(textBody)

    def attach_pdf(self, pdf_filename):
        """Attach a PDF file to this message.

        Parameters
        ----------
        pdf_filename : str
            The filename of the PDF file to attach.

        """
        with open(pdf_filename, "rb") as attachment:
            part = MIMEApplication(attachment.read(), "pdf")

        encoders.encode_base64(part)
        # See https://en.wikipedia.org/wiki/MIME#Content-Disposition
        _, filename = os.path.split(pdf_filename)
        part.add_header("Content-Disposition", "attachment", filename=filename)
        self.attach(part)
        LOGGER.debug("Message PDF attachment: %s", pdf_filename)

    def attach_csv(self, csv_filename):
        """Attach a CSV file to this message.

        Parameters
        ----------
        csv_filename : str
            The filename of the CSV file to attach.

        """
        with open(csv_filename) as attachment:
            part = MIMEText(attachment.read(), "csv")

        # See https://en.wikipedia.org/wiki/MIME#Content-Disposition
        _, filename = os.path.split(csv_filename)
        part.add_header("Content-Disposition", "attachment", filename=filename)
        self.attach(part)
        LOGGER.debug("Message CSV attachment: %s", csv_filename)
