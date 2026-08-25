"""This module contains the StatsMessage class."""

# Standard Python Libraries
import datetime

# Third-Party Libraries
import chevron
from pe_mailer.message import Message


class StatsMessage(Message):
    """An email message containing summary statistics for a run.

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

    Subject = "pe-mailer summary from {{date}}"

    TextBody = """Greetings!

Here is the pe-mailer summary from the run ending at {{date}}:

{{string}}

Please direct feedback and questions to vulnerability@cisa.dhs.gov and/or the pe-reports GitHub project.

Regards,
The P&E Development Team
Cybersecurity and Infrastructure Security Agency (CISA)
vulnerability@cisa.dhs.gov
"""

    HtmlBody = """<html>
<head></head>
<body>
<div style="font-size:14.5">
<p>Greetings!</p>

<p>
Here is the pe-mailer summary from {{date}}:<br><br>
{{string}}
</p>

<p> Please direct feedback and questions to <a
href="mailto:vulnerability@cisa.dhs.gov">the P&E Development Team</a>
and/or the <a
href="https://github.com/cisagov/pe-reports">pe-mailer GitHub
project</a>.</p>

<p>
Regards,<br>
The VM Development Team<br><br>
Cybersecurity and Infrastructure Security Agency<br>
<a href="mailto:vulnerability@cisa.dhs.gov">vulnerability@cisa.dhs.gov</a>
</div>
</body>
</html>
"""

    def __init__(self, to_addrs, list_of_strings):
        """Construct an instance.

        Parameters
        ----------
        to_addrs : array of str
            An array of string objects, each of which is an email
            address to which this message should be sent.

        list_of_strings : array of str
            An array of string objects, each of which is a statement
            about the pe-mailer run.

        """
        # Grab the current date
        now = datetime.datetime.utcnow()
        # The microseconds are irrelevant and just make everything
        # look confusing
        now = now.replace(microsecond=0)
        # This is the data mustache will use to render the templates
        mustache_data = {
            "date": now.isoformat(),
            "string": list_of_strings,
        }

        # Render the templates
        subject = chevron.render(StatsMessage.Subject, mustache_data)
        text_body = chevron.render(StatsMessage.TextBody, mustache_data)
        html_body = chevron.render(StatsMessage.HtmlBody, mustache_data)

        Message.__init__(self, to_addrs, subject, text_body, html_body)
