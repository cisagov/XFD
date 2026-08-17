"""This module contains the PandEMessage class."""

# Third-Party Libraries
import chevron
from pe_mailer.message import Message
from pe_mailer.report_message import ReportMessage


class PEMessage(ReportMessage):
    """An email message with the Posture and Exposure Report attachment.

    Static attributes
    -----------------
    Subject : str
        The mustache template to use when constructing the message
        subject.

    TextBody : str
        The mustache template to use when constructing the plain text
        message body.

    HtmlBody : str
        The mustache template to use when constructing the HTML
        message body.

    """

    Subject = (
        "Posture and Exposure (P&E) Report - {{cyhy_id}} - {{report_date}} (TLP:AMBER)"
    )

    TextBody = """Greetings,

The attached Posture and Exposure (P&E) report is the result of a CISA Cyber Assessments service that provides actionable information about public exposures and security posture weaknesses.

All of the findings and information are derived from public information that is currently available. No scanning has occurred for this service.

The report will initially be delivered twice per month, but it will be updated and enhanced to integrate more data sources and be sent with greater frequency in the future. The P&E report is for your situational awareness as a supplement to other threat reports you may have internally or externally. No action is required, but your feedback and questions are more than welcome.

Note: The report is encrypted with your Cyber Hygiene password.

Thank you,
CISA Cyber Assessments - Posture and Exposure
Cybersecurity and Infrastructure Security Agency
vulnerability@cisa.dhs.gov

WARNING: This document is FOR OFFICIAL USE ONLY (FOUO). It contains information that may be exempt from public release under the Freedom of Information Act (5 U.S.G. 552). It is to be controlled, stored, handled, transmitted, distributed, and disposed of in accordance with CISA policy relating to FOUO information and is not to be released to the public or other personnel who do not have a valid 'need-to-know' without prior approval of an authorized CISA official.
"""

    HtmlBody = """<html>
<head></head>
<body style="font-family: 'Times New Roman'">
<p style="color:#FFC000">TLP:AMBER</p>

<p>Good afternoon,</p>

<p>Posture and Exposure (P&E) offers stakeholders an opportunity
to view their organizational risk from the viewpoint of the adversary.
We utilize passive reconnaissance services, dark web analysis, and open-source
tools to identify spoofing in order to generate a risk profile report that is
delivered on a regular basis.</p>

<p>As a customer of P&E you are receiving our regularly scheduled report
which contains a summary of the activity we have been tracking on your behalf
for the following services:</p>

<ul>
<li>Domain Masquerading and Monitoring</li>
<li>Credentials Leaked/Exposed</li>
<li>Insecure Devices & Suspected Vulnerabilities</li>
<li>Dark Web Monitoring</li>
<li>Hidden Assets and Risky Services</li>
</ul>

<p>In the attached document you will find a Summary Report with the findings
based on what we identified above. On page 4 of the report, you will
find links to the JSON raw data as it was discovered by us. For the protection of
your organization, we have encrypted the document with the password that was
shared when the agreement was signed for Cyber Hygiene Services. <strong>For
the best results, we recommend using Adobe Acrobat.</strong></p>

<p>Finally, it is important to note that these findings have not been verified;
everything is gathered via passive analysis of publicly available sources.  As
such there may be false positive findings, however these findings should be
treated as information that your organization is leaking out to the internet
for adversaries to notice.</p>

<p style="display:inline;">Thank you,<br></p>
<p style="display:inline;font-size:12pt;"><strong>The Posture and Exposure (P&E) Team</strong><br></p>
<p style="display:inline;">Cybersecurity and Infrastructure Security Agency (CISA)<br>Email:
<a href="mailto:vulnerability@cisa.dhs.gov">vulnerability@cisa.dhs.gov</a></p>

<p>WARNING: This document is FOR OFFICIAL USE ONLY (FOUO). It contains information
that may be exempt from public release under the Freedom of Information Act
(5 U.S.G. 552). It is to be controlled, stored, handled, transmitted, distributed,
and disposed of in accordance with CISA policy relating to FOUO information and
is not to be released to the public or other personnel who do not have a valid
'need-to-know' without prior approval of an authorized CISA official.</p>
</body>
</html>
"""

    def __init__(
        self,
        pdf_filename,
        pdf_asm_filename,
        report_date,
        id,
        to_addrs,
        from_addr=Message.DefaultFrom,
        cc_addrs=Message.DefaultCc,
        bcc_addrs=Message.DefaultBcc,
    ):
        """Construct an instance.

        Parameters
        ----------
        pdf_filename : str
            The filename of the PDF file that is the Posture and
            Exposure report corresponding to this message.

        report_date : str
            The date corresponding to the Posture and Exposure
            report attachment. We have been using dates of the
            form December 12, 2017.

        to_addrs : array of str
            An array of string objects, each of which is an email
            address to which this message should be sent.

        from_addr : str
            The email address from which this message is to be sent.

        cc_addrs : array of str
            An array of string objects, each of which is a CC email
            address to which this message should be sent.

        bcc_addrs : array of str
            An array of string objects, each of which is a BCC email
            address to which this message should be sent.

        """
        # This is the data mustache will use to render the templates
        mustache_data = {"report_date": report_date, "cyhy_id": id}

        # Render the templates
        subject = chevron.render(PEMessage.Subject, mustache_data)
        text_body = chevron.render(PEMessage.TextBody, mustache_data)
        html_body = chevron.render(PEMessage.HtmlBody, mustache_data)

        ReportMessage.__init__(
            self,
            to_addrs,
            subject,
            text_body,
            html_body,
            pdf_filename,
            pdf_asm_filename,
            from_addr,
            cc_addrs,
            bcc_addrs,
        )


class ScorecardMessage(ReportMessage):
    """An email message with the Posture and Exposure Report attachment.

    Static attributes
    -----------------
    Subject : str
        The mustache template to use when constructing the message
        subject.

    TextBody : str
        The mustache template to use when constructing the plain text
        message body.

    HtmlBody : str
        The mustache template to use when constructing the HTML
        message body.

    """

    Subject = "CyHy Scorecard Report - {{cyhy_id}} - {{report_date}} (TLP:AMBER)"

    TextBody = """Greetings,
                This is a test of the text body.

                """

    HtmlBody = """<html>
<head></head>
<body style="font-family: 'Times New Roman'">
<p style="color:#FFC000">TLP:AMBER</p>

<p>Good afternoon,</p>

<p>Posture and Exposure (P&E) offers stakeholders an opportunity
to view their organizational risk from the viewpoint of the adversary.
We utilize passive reconnaissance services, dark web analysis, and open-source
tools to identify spoofing in order to generate a risk profile report that is
delivered on a regular basis.</p>

<p>As a customer of P&E you are receiving our regularly scheduled Scorecard
which contains a summary of your attack surface.</p>

<p>Finally, it is important to note that these findings have not been verified;
everything is gathered via passive analysis of publicly available sources.  As
such there may be false positive findings, however these findings should be
treated as information that your organization is leaking out to the internet
for adversaries to notice.</p>

<p style="display:inline;">Thank you,<br></p>
<p style="display:inline;font-size:12pt;"><strong>The Posture and Exposure (P&E) Team</strong><br></p>
<p style="display:inline;">Cybersecurity and Infrastructure Security Agency (CISA)<br>Email:
<a href="mailto:vulnerability@cisa.dhs.gov">vulnerability@cisa.dhs.gov</a></p>

<p>WARNING: This document is FOR OFFICIAL USE ONLY (FOUO). It contains information
that may be exempt from public release under the Freedom of Information Act
(5 U.S.G. 552). It is to be controlled, stored, handled, transmitted, distributed,
and disposed of in accordance with CISA policy relating to FOUO information and
is not to be released to the public or other personnel who do not have a valid
'need-to-know' without prior approval of an authorized CISA official.</p>
</body>
</html>
"""

    def __init__(
        self,
        pdf_filename,
        month,
        year,
        id,
        to_addrs,
        from_addr=Message.DefaultFrom,
        cc_addrs=Message.DefaultCc,
        bcc_addrs=Message.DefaultBcc,
    ):
        """Construct an instance.

        Parameters
        ----------
        pdf_filename : str
            The filename of the PDF file that is the Posture and
            Exposure report corresponding to this message.

        report_date : str
            The date corresponding to the Posture and Exposure
            report attachment. We have been using dates of the
            form December 12, 2017.

        to_addrs : array of str
            An array of string objects, each of which is an email
            address to which this message should be sent.

        from_addr : str
            The email address from which this message is to be sent.

        cc_addrs : array of str
            An array of string objects, each of which is a CC email
            address to which this message should be sent.

        bcc_addrs : array of str
            An array of string objects, each of which is a BCC email
            address to which this message should be sent.

        """
        # This is the data mustache will use to render the templates
        mustache_data = {"report_date": f"{month} {year}", "cyhy_id": id}

        # Render the templates
        subject = chevron.render(ScorecardMessage.Subject, mustache_data)
        text_body = chevron.render(ScorecardMessage.TextBody, mustache_data)
        html_body = chevron.render(ScorecardMessage.HtmlBody, mustache_data)

        pdf_asm_filename = None
        ReportMessage.__init__(
            self,
            to_addrs,
            subject,
            text_body,
            html_body,
            pdf_filename,
            pdf_asm_filename,
            from_addr,
            cc_addrs,
            bcc_addrs,
        )
