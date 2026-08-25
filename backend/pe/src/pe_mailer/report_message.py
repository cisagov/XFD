"""This module contains the ReportMessage class."""

# Third-Party Libraries
from pe_mailer.message import Message


class ReportMessage(Message):
    """An email message with a report PDF attachment."""

    def __init__(
        self,
        to_addrs,
        subject,
        text_body,
        html_body,
        pdf_filename,
        pdf_asm_filename,
        from_addr=Message.DefaultFrom,
        cc_addrs=Message.DefaultCc,
        bcc_addrs=Message.DefaultBcc,
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

        pdf_filename : str
            The filename of the PDF file that is the report to be
            attached to this message.

        from_addr : str
            The email address from which this message is to be sent.

        cc_addrs : array of str
            An array of string objects, each of which is a CC email
            address to which this message should be sent.

        bcc_addrs : array of str
            An array of string objects, each of which is a BCC email
            address to which this message should be sent.

        """
        Message.__init__(
            self,
            to_addrs,
            subject,
            text_body,
            html_body,
            from_addr,
            cc_addrs,
            bcc_addrs,
        )

        self.attach_pdf(pdf_filename)
        if pdf_asm_filename:
            self.attach_pdf(pdf_asm_filename)
