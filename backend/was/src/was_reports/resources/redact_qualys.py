#!/usr/bin/env python3

# Standard Python Libraries
from datetime import datetime
import re

# Third-Party Libraries
import pdf_redactor

year = datetime.now().year

options = pdf_redactor.RedactorOptions()

options.content_filters = [
    (re.compile(r"""CONFIDENTIAL AND PROPRIETARY INFORMATION."""), lambda m: ""),
    (
        re.compile(
            r"""Qualys provides the QualysGuard Service "As Is," without any warranty of any kind. Qualys makes no warranty that the information contained in this report is"""
        ),
        lambda m: "",
    ),
    (
        re.compile(
            r"""complete or error-free. Copyright """ + str(year) + """, Qualys, Inc."""
        ),
        lambda m: "",
    ),
]

pdf_redactor.redactor(options)
