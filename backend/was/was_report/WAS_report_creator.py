#!/usr/bin/env python3
# -*- coding: utf-8 -*-

'''Welcome to the WAS Report Tool!

Usage:
    COMMAND_NAME [-t STAKEHOLDER_TAG] [-l] [-x] [--noninteractive PASSWORD] [--encrypt PASSWORD]
    COMMAND_NAME [--reactivate WEBAPP_LIST]
    COMMAND_NAME [--delete-webapp WEBAPP_LIST]
    COMMAND_NAME [-f FALSEPOSITIVE_LIST]
    COMMAND_NAME [-d WEBAPP_LIST]
    COMMAND_NAME [--add-tag WEBAPP_LIST]
    COMMAND_NAME [--remove-tag WEBAPP_LIST]
    COMMAND_NAME [-h]
    COMMAND_NAME [--version]
    COMMAND_NAME [--dailywas]
    COMMAND_NAME [--onboard]
    COMMAND_NAME [--update-tracker]
    COMMAND_NAME [--check-dates]
    COMMAND_NAME [--mailer]
    COMMAND_NAME [--check-passwords]

Options:
-t STAKEHOLDER_TAG,--tag=STAKEHOLDER_TAG                             Use this argument to feed the appropriate stakeholder tag for the script to use to generate the report.
-l,--list                                                            Use this to output a list of current WAS stakeholders and their Web Application count
-x,--xml                                                             Use this option to geneerate an XML only report for the specified tag
-f FALSEPOSITIVE_LIST,--false-positive=FALSEPOSITIVE_LIST            Use this option to mark a list of finding IDs as false positive. FALSEPOSITIVE_LIST is a file containing the list of finding IDs to bee marked.
-d WEBAPP_LIST,--details-only=WEBAPP_LIST                            Use this option to generate detail reports for each web application in the provided list.
--add-tag WEBAPP_LIST                                                Use this to add a specified tag each web application in the list.
--remove-tag WEBAPP_LIST                                             Use this to remove a specified tag from each web application in the list.
--noninteractive TEMPLATE_FILE                                       Use this to run th e script in noninteractive mode, with agument for the completed template file for multiple reports.
--reactivate WEBAPP_LIST                                             Use this to re-add the provided list of apps to the Qualys instance.
--encrypt PASSWORD                                                   Use this to encrypt the report using the provided password.
--delete-webapp WEBAPP_LIST                                          Use this to provide alist of web applications to be removed from Qualys.
--dailywas                                                           Use this to run the dailywas tool, but please use your dailywas alias to include all functions.
--onboard                                                            NOT FUNCTIONAL - Use this to onboard a customer.
--update-tracker                                                     Use this to update the tracker each morning.
--check-dates                                                        Use this to view ALL next scan dates per day of the month.
--mailer                                                             Use this to create your email templates for the day.
--check-passwords                                                    Use this to check passwords of today's reports for tags currently in the multi_report sheet.
'''

import pystache
import csv
import json
import html
import qualysapi
import requests
import base64
import subprocess
import time
import threading
import pandas as pd
from datetime import datetime, date, timedelta
import pytz
from collections import OrderedDict, defaultdict
from lxml import etree
from lxml import objectify
import xml.etree.ElementTree as ET
#from ConfigParser import SafeConfigParser
from docopt import docopt
from configparser import ConfigParser
from pdfrw import PdfReader, PdfWriter, PageMerge
import pdfrw
from PyPDF4 import PdfFileReader, PdfFileWriter
import pypdf
from PIL import Image, ImageDraw, ImageFont
from lxml.builder import E
import os
import sys
import re
import matplotlib as mpl
if os.environ.get('DISPLAY','') == '':
    mpl.use('Agg')
import matplotlib.pyplot as plt; plt.rcdefaults()
import numpy as np
import argparse
from pikepdf import Pdf,Encryption
from fpdf import FPDF
import concurrent.futures
import multiprocessing
import docker
import random
import pathlib
from pathlib import Path
from dateutil.relativedelta import relativedelta
from math import pi
import seaborn as sns

### test comment ### 
#Sets up account connections for API calls
was_config_fp = Path('/WAS_REPORT_GENERATION/docs/was_config.txt')
qgc = qualysapi.connect(was_config_fp)
parser = ConfigParser()
parser.read(was_config_fp)
version = '2.3'

LATEX_ESCAPE_MAP = {
    '$':r'\$',
    '%':r'\%',
    '&':r'\&',
    '#':r'\#',
    '_':r'\_',
    '{':r'\{',
    '}':r'\}',
    '[':'{[}',
    ']':'{]}',
    #"'":"{'}",
    '<':'\\textless{}',
    '>':'\\textgreater{}'
}

def unspace(string):
    string = string.replace(" ","-")
    return string

def respace(string):
    string = string.replace("-"," ")
    return string

def decomma(in_string):
    in_string = re.sub(',','',in_string)

    return in_string

def quote_field(field):
    field = str(field)
    if ',' in field or '"' in field:
        field = field.replace('"', '""')
        return f'"{field}"'
    return field

def format_request(request):
    headers = request.HEADERS.HEADER    
    headers_str = ''.join([f'{header.key}: {header.value}\n' for header in headers])
    body = request.BODY if request.BODY else ''
    return f'{request.METHOD} {request.URL}\n{headers_str}\n{body}'

def remove_html_tags(text):
    """Remove html tags from a string"""
    import re
    clean = re.compile('<.*?>')
    return re.sub(clean, '', text)

def get_report(id):
    """Gets the XML output for a specified report."""
    print("Fetching report...")
    call = '/download/was/report/%s' % id

    xml_output = qgc.request(call,http_method='get')
    print("Done.")
    return xml_output

def sanitize_url(in_string):
    in_string = re.sub('https://','',in_string)
    in_string = re.sub('http://','',in_string)
    in_string = re.sub('/','',in_string)
    in_string = re.sub(':','',in_string)
    in_string = re.sub(" ",'',in_string)

    return in_string

def read_file(file):
    out_list = []
    # with open(file) as f:
    #     for line in f.readlines():
    #         u = line.decode('utf-8-sig')
    #         line = u.encode('utf-8')
    #
    #         out_list.append(line.strip())
    with open(file,encoding='utf-8-sig') as f:
        reader = csv.reader(f)
        out_list = list(reader)

    return (str(x[0]) for x in out_list)

def get_app_id(app):
    post = '''<ServiceRequest>
<filters>
 <Criteria field="url" operator="EQUALS">%s</Criteria>
</filters>
</ServiceRequest>''' % app

    call = '/search/was/webapp'

    response = qgc.request(call,post,http_method='POST')

    root = objectify.fromstring(response.encode())

    id = root.data.WebApp.id

    return id

#This is used to escape certain characters before sending them to LaTeX
def latex_string_prep(temp_string):
    for latex_key, latex_value in LATEX_ESCAPE_MAP.items():
        temp_string = temp_string.replace(latex_key, latex_value)

    return temp_string

def totalgraphgen(report):
    """Generates the image for the graph for total vulnerabilities."""

    report_str = etree.tostring(report)
    root = ET.fromstring(report_str)

    tot1 = 0
    tot2 = 0
    tot3 = 0
    tot4 = 0
    tot5 = 0

    for webapp in root.findall("./SUMMARY/SUMMARY_STATS/SUMMARY_STAT"):
        Lvl1 = int(webapp.find("./LEVEL1").text)
        tot1 += Lvl1
        Lvl2 = int(webapp.find("./LEVEL2").text)
        tot2 += Lvl2
        Lvl3 = int(webapp.find("./LEVEL3").text)
        tot3 += Lvl3
        Lvl4 = int(webapp.find("./LEVEL4").text)
        tot4 += Lvl4
        Lvl5 = int(webapp.find("./LEVEL5").text)
        tot5 += Lvl5

    #labels = ('Minimal', 'Medium', 'Serious', 'Critical', 'Urgent')
    #y_pos = np.arange(len(labels))
    #results = [tot1,tot2,tot3,tot4,tot5]
    return str(tot1),str(tot2),str(tot3),str(tot4),str(tot5)
    
    # # This sets the figure number. Otherwise, the figures get jumbled up and start to look really weird.
    # fig1 = plt.figure(1)
    # barlist = plt.bar(y_pos, results, align='center', alpha=None)

    # # This hard-codes acolor foreach bar. I tried to go with a cool, blue color scheme but the colors are easy enough to change if needed.
    # barlist[0].set_color('#eebdc5')
    # barlist[1].set_color('#e08493')
    # barlist[2].set_color('#d24b62')
    # barlist[3].set_color('#c41230')
    # barlist[4].set_color('#950e24')
    # plt.xticks(y_pos, labels)
    # plt.ylabel('Number of Results')
    # plt.title('Total Vulnerabilities by Severity')
    # legend = ('Minimal','Medium','Serious','Critical','Urgent')


    # fig1.savefig("assets/figure1.png")
    # plt.clf()

# This sets up and creates the image for the OWASP graph.

def delete_report(report_id, tag):

    call = '/delete/was/report/%s' % report_id
    xml_output = qgc.request(call)
    root = objectify.fromstring(xml_output.encode())
    if tag == None:
        if root.responseCode == 'SUCCESS':
            id = root.data.Report.id
            print("Report %s was successfully deleted." % id)
        else:
            print("Something went wrong. Here is the XML response from the server:\n")
            print(xml_output)
    else:
        if root.responseCode == 'SUCCESS':
            print("Report for %s was successfully deleted." % tag)
        else:
            print("Something went wrong. Here is the XML response from the server:\n")
            print(xml_output)

class Qid:
    def __init__(self,severity,title,group,description,impact,solution,cvss,cve,cwe):
        self.severity = severity
        self.title = title
        self.group = group
        self.description = description
        self.impact = impact
        self.solution = solution
        self.cvss = cvss
        self.cve = cve
        self.cwe =cwe

class Vulnerability:
    def __init__(self,data):
        self.id = data.ID
        self.uid = data.UNIQUE_ID
        self.qid = data.QID
        self.url = data.URL
        self.first_detect = data.FIRST_TIME_DETECTED
        self.last_detect = data.LAST_TIME_DETECTED
        self.last_test = data.LAST_TIME_TESTED
        self.potential = data.POTENTIAL
        self.status = data.STATUS
        try:
            self.response = data.PAYLOADS.PAYLOAD.RESPONSE.CONTENTS
        except AttributeError:
            # self.response = base64.b64encode("N/A".encode('ascii'))
            self.response = "Ti9B"
        try:
            self.request = format_request(data["PAYLOADS"]["PAYLOAD"]["REQUEST"])
        except AttributeError:
            if hasattr(data,'PAYLOADS.PAYLOAD'):
                self.request = data.PAYLOADS.PAYLOAD.PAYLOAD
            else:
                 self.request = 'n/a'
                 
class InfoGathered:
    def __init__(self,data):
        self.id = data.ID
        self.qid = data.QID
        self.last_detect = data.LAST_TIME_DETECTED

class WebApp:
    def __init__(self,data):
        self.id = data.ID
        self.name = data.NAME
        self.vuln_list = data.VULNERABILITY_LIST
        self.info_list = data.INFORMATION_GATHERED_LIST

def get_qid_stats(xml_data):
    # root = objectify.fromstring(xml_data.encode())
    entry_dict = {}
    if hasattr(xml_data.GLOSSARY.QID_LIST,"QID"):
        for entry in xml_data.GLOSSARY.QID_LIST.QID:
            qid = entry.QID
            severity = str(entry.SEVERITY)
            title = str(entry.TITLE)
            if hasattr(entry, "GROUP"):
                group = str(entry.GROUP)
            else:
                print("Warning: No group found for qid.  Set group to empty string")
                group = ""
            description = re.sub('\n','',remove_html_tags(str(entry.DESCRIPTION)))
            impact = re.sub('\n','',remove_html_tags(str(entry.IMPACT)))
            solution = re.sub('\n','',remove_html_tags(str(entry.SOLUTION)))
            try:
                cvss = str(entry.CVSS_BASE)
            except AttributeError:
                cvss = "None"
            try:
                cve = str(entry.CVE)
            except AttributeError:
                cve = "None"
            try:
                cwe = str(entry.CWE)
            except AttributeError:
                cwe = "None"
            entry_dict[qid] = Qid(severity,title,group,description,impact,solution,cvss,cve,cwe)
        return entry_dict
    else:
        print("No QID Glossary found. Check if Customer has findings.")
        # Code for Creating a Empty Report to kick off flow to send All NWS email
        date_setter = datetime.today()
        name_date = date_setter.strftime('%Y-%m-%d')
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        pdf.cell(200, 10, txt="EMPTY PDF!", ln=True, align='C')
        pdf.output(f"docs/{query}_report_{name_date}.pdf")
        print("Empty report generated.")
        sys.exit(-1)

def csv_genner(report,name):
    # print(report_xml)
    print('Generating findings CSV...')
    # root = objectify.fromstring(report_xml.encode())
    filename = "vulnerability-list-%s.csv" % name
    info_filename = "information-gathered-list%s.csv" % name
    info_file = open("assets/"+info_filename, "w")
    #pulg in real columns
    info_file.write("INFO_ID,NAME,QID,URL,LAST DETECTION,SEVERITY,DESCRIPTION,IMPACT,SOLUTION")
    info_file.write('\n')
    csv_file = open("assets/"+filename,"w")
    csv_file.write("VULN_ID,NAME,QID,SEVERITY,BASE CVSS,CWE,CVE,FIRST DETECTION,LAST DETECTION,GROUP,WEB APPLICATION,URL,PAYLOAD REQUEST,PAYLOAD RESPONSE,DESCRIPTION,IMPACT,SOLUTION,VULN TYPE")
    csv_file.write('\n')
    qid_dict = get_qid_stats(report)
    webapp_list = []
    severity_list = []
    age_list = []
    for webapp in report.RESULTS.WEB_APPLICATION:
        webapp_list.append(WebApp(webapp))
    for app in webapp_list:
        web_application = app.name
        for info in app.info_list.getchildren():
            temp = InfoGathered(info)
            id = temp.id
            qid = temp.qid
            url = decomma(str(web_application))
            last_detection = temp.last_detect
            severity = qid_dict[qid].severity
            title = decomma(qid_dict[qid].title)
            description = decomma(qid_dict[qid].description)
            impact = decomma(qid_dict[qid].impact)
            solution = decomma(qid_dict[qid].solution)
            info_file.write("{},{},{},{},{},{},{},{},{}".format(id,decomma(title),qid,url,last_detection,severity,decomma(description),decomma(impact),decomma(solution)))
            info_file.write("\n")

        for vuln in app.vuln_list.getchildren():
            temp = Vulnerability(vuln)
            if temp.status != 'FIXED':
                id = temp.id
                qid = temp.qid
                url = decomma(str(temp.url))
                first_detection = temp.first_detect
                last_detection = temp.last_detect
                potential = temp.potential
                if potential:
                    vuln_type = "Potential"
                else:
                    vuln_type = "Confirmed"
                severity = qid_dict[qid].severity
                
                date_time_obj = datetime.strptime(str(first_detection), '%d %b %Y %I:%M%p %Z')
                age = (pd.Timestamp.now(tz='UTC') - pd.Timestamp(date_time_obj, tz='UTC')).days
                severity_list.append(severity)
                age_list.append(age)

                title = decomma(qid_dict[qid].title)
                group = qid_dict[qid].group
                description = decomma(qid_dict[qid].description)
                impact = decomma(qid_dict[qid].impact)
                solution = decomma(qid_dict[qid].solution)
                cvss = qid_dict[qid].cvss
                cve = qid_dict[qid].cve
                cwe = qid_dict[qid].cwe
                
                response = decomma(str(base64.b64decode(str(temp.response))))
                request = quote_field(temp.request)
                csv_file.write("{},{},{},{},{},{},{},{},{},{},{},{},{},{},{},{},{},{}".format(id,decomma(title),qid,severity,cvss,decomma(cwe),decomma(cve),first_detection,last_detection,group,web_application,url,request,response,decomma(description),decomma(impact),decomma(solution),vuln_type))
                csv_file.write("\n")
    return filename, info_filename, severity_list, age_list

def owasp_graph_gen(owasp_count_dict):
    """Generates the image for the OWASP graph."""

    # owasp_graph_dict = {"":0,"Injection":0,"Broken Authentication":0,"Sensitive Data Exposure":0,"XML External Entities (XXE)":0,"Broken Access Control":0,"Security Misconfiguration":0,'Cross-Site Scripting (XSS)':0,'Insecure Deserialization':0,'Components with Known Vulnerabilities':0,'Insufficient Logging & Monitoring':0}

    owasp_graph_dict = {
        "": 0,
        "Broken Access Control": 0,                         # A01
        "Cryptographic Failures": 0,                         # A02
        "Injection": 0,                                      # A03 (includes XSS)
        "Insecure Design": 0,                                # A04
        "Security Misconfiguration": 0,                      # A05
        "Vulnerable and Outdated Components": 0,             # A06
        "Identification and Authentication Failures": 0,     # A07
        "Software and Data Integrity Failures": 0,           # A08
        "Security Logging and Monitoring Failures": 0,       # A09
        "Server-Side Request Forgery (SSRF)": 0               # A10
}

    for entry in owasp_count_dict:
        owasp_graph_dict[entry] += owasp_count_dict[entry]

    x = owasp_graph_dict.keys()
    values = owasp_graph_dict.values()

    x_pos = np.arange(len(x))

    fig2 = plt.figure(2)
    plt.barh(x_pos, values,align='center', alpha=None, color='#005288')
    plt.xlabel("Number of Vulnerabilities")
    plt.title("Number of Vulnerabilities by OWASP Category")
    plt.subplots_adjust(left=0.5)

    plt.yticks(x_pos, x)

    fig2.savefig('assets/owasp_graph.png')
    plt.clf()

def vulnsbygroupgraphgen(group_count_dict):
    """Generates the image for the vulnerabilities by group graph."""
    labels = group_count_dict.keys()
    sizes = list(group_count_dict.values())
    percents = []
    for x in sizes:
        try:
            percents.append((x/sum(sizes)*100))
        except (ZeroDivisionError,ValueError):
            print("Oops, dividing by zero...")
            percents.append(0)

    plt.figure(3)
    colors = ['#001726','#003e67','#d6e9f2','#7ab9d5','#7aa5c1', '#0078ae']
    fig1, ax1 = plt.subplots()
    try:
        patches, autotexts = ax1.pie(sizes,shadow=False, startangle=90,colors=colors,labeldistance=1.05)

        ax1.axis('equal')  # Equal aspect ratio ensures that pie is drawn as a circle.

        plt.legend(bbox_to_anchor=(-0.15,0.25), loc="upper left",labels=['%s, %1.1f %%' % (l, s) for l, s in zip(labels, percents)])
    except ValueError:
        pass
    plt.savefig("assets/figure3.png")
    plt.clf()

def percent_donut(fixed, total):
    if total == 0:
        percent = 0
    else:
        percent = int(fixed / total * 100)
    percentage = str(percent) + '%'
    fig, ax = plt.subplots(figsize=(6, 6))
    ax = plt.subplot(projection='polar')
    ax.set_facecolor('#e5eede')
    data = [100, percent]
    startangle = 90
    colors = ['#c0c2c4', '#5e9732']
    xs = [(i * pi *2)/ 100 for i in data]
    ys = [3.1, 3.1]
    left = (startangle * pi *2)/ 360 #this is to control where the bar starts
    # plot bars and points at the end to make them round
    for i, x in enumerate(xs):
        ax.barh(ys[i], x, left=left, height=2, color=colors[i])
        if i==1:
            ax.scatter(x+left, ys[i], s=1650, color=colors[i], zorder=2)

    plt.ylim(-4, 4)
    # legend
    ax.text(0.5, 0.5, percentage, transform=ax.transAxes, ha='center', va='center', fontsize=36)
    # clear ticks, grids, spines
    plt.xticks([])
    plt.yticks([])
    ax.spines.clear()
    plt.savefig('assets/donut.png', bbox_inches='tight')

def plot_histogram(ages, severities):
    f = plt.figure(figsize=(7,5))
    ax = f.add_subplot(1,1,1)

    _df = pd.DataFrame({
        "age":np.array(ages),
        "Severity":np.array(severities)
    })
    # plot
    from matplotlib.ticker import FormatStrFormatter
    if len(ages) == 0 or len(severities) == 0:
        sns.histplot(data=_df, ax=ax)
    else: 
        sns.histplot(data=_df, ax=ax, stat="count", multiple="stack",
                    x="age", bins='auto', kde=False,
                    palette=['#eebdc5', '#e08493', '#d24b62', '#c41230', '#950e24'], hue="Severity", hue_order=['1','2','3','4','5'],
                    element="bars", alpha=None, legend=True)
    ax.set_title("Vulnerability Distribution by Age and Severity")
    ax.set_xlabel("Age (Days)")
    ax.set_ylabel(None)
    ax.xaxis.set_major_formatter(FormatStrFormatter('%d'))
    plt.savefig('assets/histogram.png', bbox_inches='tight')

def format_month_year(date):
    month_date = datetime.strptime(date, '%B %Y')
    mm_yy = month_date.strftime('%-m/%y')
    return mm_yy

def monthly_trend(fixed, active_new_reo):
    # months = list(reversed(dict.keys()))
    # fixed = [dict[date]['fixed'] for date in reversed(dict)]
    # vuln = [dict[date]['vuln'] for date in reversed(dict)]
    months = list(reversed(fixed.keys()))
    fixed = dict(reversed(list(fixed.items())))
    active_new_reo = dict(reversed(list(active_new_reo.items())))
    fig, ax = plt.subplots(figsize=(7.5, 2))
    ax.stackplot(months, fixed.values(), active_new_reo.values(), colors=['#bfeca9', '#7ab9d5'],labels=['Fixed Vulnerabilities', 'Total Vulnerabilities'], alpha=None)
    ax.set_xticks(months)
    ax.set_xticklabels([format_month_year(date) for date in months], rotation=30)
    ax.legend(loc=2)
    plt.savefig('assets/monthly.png', bbox_inches='tight')

def max_age(tag):
    qgc = qualysapi.connect(was_config_fp)
    call = 'search/was/finding'
    critical_param = (
        E.ServiceRequest(
            E.filters(
                E.Criteria(tag, field='webApp.tags.name', operator='EQUALS'),
                E.Criteria('ACTIVE, NEW, REOPENED', field='status', operator='IN'),
                E.Criteria('4', field = 'severity', operator='EQUALS'),
                E.Criteria('FALSE_POSITIVE', field = 'ignoredReason', operator='NOT EQUALS')
            ),
            E.preferences(
                E.limitResults('1')
            )
        )
    )
    urgent_param = (
        E.ServiceRequest(
            E.filters(
                E.Criteria(tag, field='webApp.tags.name', operator='EQUALS'),
                E.Criteria('ACTIVE, NEW, REOPENED', field='status', operator='IN'),
                E.Criteria('5', field = 'severity', operator='EQUALS'),
                E.Criteria('FALSE_POSITIVE', field = 'ignoredReason', operator='NOT EQUALS')
            ),
            E.preferences(
                E.limitResults('1')
            )
        )
    )

    xml_critical = qgc.request(call, critical_param)
    xml_urgent = qgc.request(call, urgent_param)
    critical = objectify.fromstring(xml_critical.encode())
    urgent = objectify.fromstring(xml_urgent.encode())
    try:
        criticaldiff = pd.Timestamp.now().tz_localize('UTC') - pd.to_datetime(critical.data.Finding.firstDetectedDate.text).tz_convert('UTC')
        urgentdiff = pd.Timestamp.now().tz_localize('UTC') - pd.to_datetime(urgent.data.Finding.firstDetectedDate.text).tz_convert('UTC')
    except AttributeError:
        return '0', '0'
    return str(criticaldiff.days), str(urgentdiff.days)

# Checks the report status to see if it is running or not
def get_report_status(id):
    call = '/status/was/report/%s' % id
    xml_out = qgc.request(call,http_method='get')
    root = ET.fromstring(xml_out)
    status = root.find('./data/Report/status').text
    print("The report status is: " + status)

    return status

def qualys_redact(file,name):
    try:
        os.system("python redact_qualys.py < "+file+" > "+name)
    except pdfrw.errors.PdfParseError:
        print("DOWNLOAD FAILED")
        sys.exit()

# adds the CISA logo to bottom of details report
def watermarker(infile,wmfile):
    inputFile = infile
    outputFile = infile
    watermarkFile = wmfile

    readerInput = PdfReader(inputFile)
    writerOutput = PdfWriter()
    watermarkInput = PdfReader(watermarkFile)
    watermark = watermarkInput.pages[0]

    for currentPage in range(len(readerInput.pages)):
        merger = PageMerge(readerInput.pages[currentPage])
        merger.add(watermark).render()

    writerOutput.write(outputFile,readerInput)

# removes first page from details report
def unfirstpagify(infile, outfile):
    input_file = infile
    output_file = outfile

    pdf_file = PdfFileReader(input_file)
    writer_output = PdfFileWriter()

    for i in range(1, pdf_file.getNumPages()):
        page = pdf_file.getPage(i)
        writer_output.addPage(page)

    with open(output_file, 'wb') as out:
        writer_output.write(out)

# Downloads the details report and modifies it for attachment prep
def download_report(id,filename,fromArg=False):

    filename_path = 'assets/'+filename+'Details.pdf'
    if fromArg:
        filename_path = 'docs/'+sanitize_url(filename)+'Details.pdf'
    call = '/qps/rest/3.0/download/was/report/%s' % id

    user = parser.get('info','username')
    password = parser.get('info','password')
    hostname = parser.get('info','hostname')

    print("Checking report status...")
    status = get_report_status(id)
    while status != 'COMPLETE':
        if status == 'ERROR':
            print("Oops, it looks like the report has errored. Aborting the process.")
            sys.exit()
        else:
            print("It looks like the report is not complete, let's start the download once it is.")
            print("Waiting...")
            time.sleep(30)
            status = get_report_status(id)

    print("It looks like the report is complete! Downloading now...")
    session = requests.Session()
    session.auth = (user, password)

    r = session.get('https://'+hostname+call)

    with open(filename_path,'wb') as f:
        f.write(r.content)

    print(filename+"Details.pdf has been downloaded.")

    print("Redacting...")
    qualys_redact(filename_path,filename_path+"_redacted.pdf")

    print("Watermarking...")
    watermarker(filename_path+"_redacted.pdf","cisa_marker_new.pdf")
    #
    print("Removing first page...")
    unfirstpagify(filename_path+"_redacted.pdf",filename_path)
    #
    os.system("rm "+filename_path+"_redacted.pdf")
    print("All done! The file is "+filename+"Details.pdf")

    return filename+"Details.pdf"

def get_tag_id(query):

    tag_id = ''
    call='search/am/tag'
    param=(
        E.ServiceRequest(
            E.filters(
                E.Criteria(str(query), field='name', operator='EQUALS')
            )
        )
    )
    xml_output = qgc.request(call,param)

    # root = ET.fromstring(xml_output)
    root = objectify.fromstring(xml_output.encode())

    # if root.find('./count').text == '0':
    if root.count == 0:
        print("No Tag found with that name.")
        sys.exit()
    else:
        tag_id = root.data.Tag.id
        # print("The tag ID is: " + tag_id )
    return tag_id

def qid_counter(report):
    """Performs calculations for different statistical counts based on the found QID."""

    print("...Calculating QID stats...")
    report_str = etree.tostring(report)
    root = ET.fromstring(report_str)
    qid_count_dict = defaultdict(lambda:0)
    fixed_monthly_dict = defaultdict(lambda:0)
    vulns_monthly_dict = defaultdict(lambda:0)
    for month in range(12):
        keydate = datetime.now() - relativedelta(months=month)
        key = keydate.strftime("%B %Y")
        fixed_monthly_dict[key] = 0
        vulns_monthly_dict[key] = 0
    fixed = 0
    total = 0
    new = 0
    reopened = 0
    active = 0
    for webapp in root.findall("RESULTS/WEB_APPLICATION"):
        vuln_list = webapp.find("./VULNERABILITY_LIST")
        
        for vuln in vuln_list.findall("VULNERABILITY"):
            if vuln.find('STATUS').text == 'FIXED':
                fixed += 1
                for month in range(12):
                    keydate = datetime.now() - relativedelta(months=month)
                    if datetime.strptime(vuln.find('LAST_TIME_DETECTED').text, '%d %b %Y %I:%M%p %Z') <= keydate:
                        key = keydate.strftime("%B %Y")
                        fixed_monthly_dict[key] += 1
            else:
                if vuln.find('STATUS').text == 'NEW':
                    new += 1
                if vuln.find('STATUS').text == 'REOPENED':
                    reopened += 1
                if vuln.find('STATUS').text == 'ACTIVE':
                    active += 1
                total += 1
                for month in range(12):
                    keydate = datetime.now() - relativedelta(months=month)
                    if datetime.strptime(vuln.find('FIRST_TIME_DETECTED').text, '%d %b %Y %I:%M%p %Z') <= keydate:
                        key = keydate.strftime("%B %Y")
                        vulns_monthly_dict[key] += 1
                qid_count_dict[vuln.find("QID").text] +=1
    qid_group_dict = {}
    qid_owasp_dict = {}
    group_count_dict = defaultdict(lambda:0)
    owasp_count_dict = defaultdict(lambda:0)
    qid_list = root.findall("./GLOSSARY/QID_LIST/QID")
    for entry in qid_count_dict:
        for qid in qid_list:
            if entry == qid.find("QID").text:
                # if hasattr(qid, "GROUP"):
                #     qid_group_dict[entry] = qid.find("GROUP").text
                # else:
                #     qid_group_dict[entry] = ""
                try:
                    qid_group_dict[entry] = qid.find("GROUP").text
                except AttributeError:
                    qid_group_dict[entry] = ""
                try:
                    qid_owasp_dict[entry] = qid.find("OWASP").text
                except AttributeError:
                    # print("No OWASP for QID "+entry)
                    qid_owasp_dict[entry] = 'None'

    for qid in qid_count_dict:
        if qid_group_dict[qid] == "PATH":
            group_count_dict["Path Disclosure"] += qid_count_dict[qid]
        if qid_group_dict[qid] == "INFO":
            group_count_dict["Information Disclosure"] += qid_count_dict[qid]
        if qid_group_dict[qid] == "XSS":
            group_count_dict["Cross-Site Scripting"] += qid_count_dict[qid]
        if qid_group_dict[qid] == "BURP":
            group_count_dict["Burp"] += qid_count_dict[qid]
        if qid_group_dict[qid] == "SQL":
            group_count_dict["SQL Injection"] += qid_count_dict[qid]
        if qid_group_dict[qid] == "BUGCROWD":
            group_count_dict["Bugcrowd"] += qid_count_dict[qid]

    # for qid in qid_count_dict:
    #     if qid_owasp_dict[qid] == 'A1':
    #         owasp_count_dict['Injection'] += qid_count_dict[qid]
    #     if qid_owasp_dict[qid] == 'A2':
    #         owasp_count_dict['Broken Authentication'] += qid_count_dict[qid]
    #     if qid_owasp_dict[qid] == 'A3':
    #         owasp_count_dict['Sensitive Data Exposure'] += qid_count_dict[qid]
    #     if qid_owasp_dict[qid] == 'A4':
    #         owasp_count_dict['XML External Entities (XXE)'] += qid_count_dict[qid]
    #     if qid_owasp_dict[qid] == 'A5':
    #         owasp_count_dict['Broken Access Control'] += qid_count_dict[qid]
    #     if qid_owasp_dict[qid] == 'A6':
    #         owasp_count_dict['Security Misconfiguration'] += qid_count_dict[qid]
    #     if qid_owasp_dict[qid] == 'A7':
    #         owasp_count_dict['Cross-Site Scripting (XSS)'] += qid_count_dict[qid]
    #     if qid_owasp_dict[qid] == 'A8':
    #         owasp_count_dict['Insecure Deserialization'] += qid_count_dict[qid]
    #     if qid_owasp_dict[qid] == 'A9':
    #         owasp_count_dict['Components with Known Vulnerabilities'] += qid_count_dict[qid]
    #     if qid_owasp_dict[qid] == 'A10':
    #         owasp_count_dict['Insufficient Logging & Monitoring'] += qid_count_dict[qid]
    for qid in qid_count_dict:
        if qid_owasp_dict[qid] == 'A1':
            owasp_count_dict['Broken Access Control'] += qid_count_dict[qid]
        if qid_owasp_dict[qid] == 'A2':
            owasp_count_dict['Cryptographic Failures'] += qid_count_dict[qid]
        if qid_owasp_dict[qid] == 'A3':
            owasp_count_dict['Injection'] += qid_count_dict[qid]
        if qid_owasp_dict[qid] == 'A4':
            owasp_count_dict['Insecure Design'] += qid_count_dict[qid]
        if qid_owasp_dict[qid] == 'A5':
            owasp_count_dict['Security Misconfiguration'] += qid_count_dict[qid]
        if qid_owasp_dict[qid] == 'A6':
            owasp_count_dict['Vulnerable and Outdated Components'] += qid_count_dict[qid]
        if qid_owasp_dict[qid] == 'A7':
            owasp_count_dict['Identification and Authentication Failures'] += qid_count_dict[qid]
        if qid_owasp_dict[qid] == 'A8':
            owasp_count_dict['Software and Data Integrity Failures'] += qid_count_dict[qid]
        if qid_owasp_dict[qid] == 'A9':
            owasp_count_dict['Security Logging and Monitoring Failures'] += qid_count_dict[qid]
        if qid_owasp_dict[qid] == 'A10':
            owasp_count_dict['Server-Side Request Forgery (SSRF)'] += qid_count_dict[qid]

    print("...Done.")
    return group_count_dict, owasp_count_dict, fixed_monthly_dict, vulns_monthly_dict, fixed, total+fixed, new, reopened, active

def list_users():
    call = 'user_list.php?'
    xml_out = qgc.request(call)
    root = objectify.fromstring(xml_out.encode('utf-8'))
    user_name_dict = {}

    for user in root.USER_LIST.USER:
        user_name_dict[user.USER_LOGIN] = user.CONTACT_INFO.FIRSTNAME

    name = user_name_dict[parser.get('info','username')]

    return name

def info_dict_gen(report):
    root = objectify.fromstring(report.encode())

    info_dict = {}
    for webapp in root.SUMMARY.SUMMARY_STATS.SUMMARY_STAT:
        info_dict[webapp.WEB_APPLICATION] = webapp.INFORMATION_GATHERED
    return info_dict

def get_summary_info(report):
    # root = objectify.fromstring(report.encode())

    data = {}

    try:
        scan_start = str(report.HEADER.GENERATION_DATETIME)
    except AttributeError:
        print("There was an error. Here is the XML:\n")
        print(report)
        sys.exit()

    data['StartDate'] = scan_start[:11]

    data['SecurityRisk'] = str(report.SUMMARY.GLOBAL_SUMMARY.SECURITY_RISK)
    data['TotInfo'] = str(report.SUMMARY.GLOBAL_SUMMARY.INFORMATION_GATHERED)
    data['NumApps'] = str(report.SUMMARY.GLOBAL_SUMMARY.WEB_APPLICATIONS)
    name = str(report.HEADER.NAME)

    if data['SecurityRisk'] == 'High':
        data['RiskColor'] = 'CB0000'
    if data['SecurityRisk'] == 'Medium':
        data['RiskColor'] = 'FFC702'
    if data['SecurityRisk'] == 'Low':
        data['RiskColor'] = '32CB00'
    data['Sensitive'] = str(report.SUMMARY.GLOBAL_SUMMARY.SENSITIVE_CONTENT)
    if data['Sensitive'] == '0':
        data['SensitiveColor'] = '5e9732'
    else:
        data['SensitiveColor'] = 'c41230'
        
    data['maxurg'], data['maxctl'] = max_age(name)
    if data['maxurg'] == '0':
        data['UrgColor'] = '5e9732'
    else: data['UrgColor'] = 'c41230'
    if data['maxctl'] == '0':
        data['CtlColor'] = '5e9732'
    else: data['CtlColor'] = 'c41230'

    print("Done getting info.")
    return data

# Deletes extra files so they do not clog up space
def cleanup(file):
    extensions = [".log",".toc",".atfi",".out",".aux"]
    for ext in extensions:
        os.system("rm docs/"+file+ext)
    os.system("rm "+file+".tex")

def webapp_vuln_table(report,name):

    # root = ET.fromstring(report)
    # root = objectify.fromstring(report.encode())

    webapp_vuln_dict = {}

    total_1 = 0
    total_2 = 0
    total_3 = 0
    total_4 = 0
    total_5 = 0
    overall_total = 0

    for webapp in report.SUMMARY.SUMMARY_STATS.SUMMARY_STAT:

        lvl5 = webapp.LEVEL5
        total_5 += lvl5
        lvl4 = webapp.LEVEL4
        total_4 += lvl4
        lvl3 = webapp.LEVEL3
        total_3 += lvl3
        lvl2 = webapp.LEVEL2
        total_2 += lvl2
        lvl1 = webapp.LEVEL1
        total_1 += lvl1
        tot_vulns = lvl1+lvl2+lvl3+lvl4+lvl5

        webapp_vuln_dict[str(webapp.WEB_APPLICATION)] = [lvl1,lvl2,lvl3,lvl4,lvl5,tot_vulns]
        overall_total += tot_vulns
    filename = "vulns-by-webapp-%s.csv" % name
    vulns_by_webapp_csv = open("assets/"+filename,"w")
    vulns_by_webapp_csv.write("WEBAPP,LEVEL 1,LEVEL 2,LEVEL 3,LEVEL 4,LEVEL 5,TOTAL")
    vulns_by_webapp_csv.write('\n')
    for entry in list(webapp_vuln_dict.keys()):
        vulns_by_webapp_csv.write("{},{},{},{},{},{},{}".format(str(entry),str(webapp_vuln_dict[entry][0]),str(webapp_vuln_dict[entry][1]),str(webapp_vuln_dict[entry][2]),str(webapp_vuln_dict[entry][3]),str(webapp_vuln_dict[entry][4]),str(webapp_vuln_dict[entry][5])))
        vulns_by_webapp_csv.write('\n')
    vulns_by_webapp_csv.close()
    return filename

def app_overview_table(report,in_name):

    # root = objectify.fromstring(report.encode())
    appendix = report.APPENDIX
    webapp_table_dict = {}

    for webapp in appendix.WEB_APPLICATION:

        name = webapp.NAME
        url = webapp.URL
        try:
            os = webapp.OPERATING_SYSTEM
        except AttributeError:
            os = "N/A"
        scope = webapp.SCOPE
        webapp_table_dict[name] = [url,scope,os]

    tablethings = ""
    filename = "webapp-overview-" + in_name + ".csv"
    webapp_overview_csv = open("assets/" + filename,"w")
    webapp_overview_csv.write("WEBAPP,URL,SCOPE,DETECTED OS")
    webapp_overview_csv.write("\n")
    for entry in list(webapp_table_dict.keys()):
        webapp_overview_csv.write("{},{},{},{}".format(str(entry),str(webapp_table_dict[entry][0]),str(webapp_table_dict[entry][1]),str(webapp_table_dict[entry][2])))
        webapp_overview_csv.write("\n")
    webapp_overview_csv.close()

    return filename

def mustache_generate(mustache_file, data,filename):
    mustache_template = mustache_file.read()
    mustache_file.close()

    with open('test.txt','w') as outfile:
        json.dump(data, outfile)

    with open('test.txt') as f:
        json_data = json.load(f)

    renderer = pystache.Renderer(string_encoding='utf-8')

    r = pystache.render(mustache_template, json_data)

    r = html.unescape(r)

    filename = filename+"_report_"+str(datetime.now())[:10]+".tex"

    with open(filename,"w",encoding='utf-8') as output:
        output.write(r)

    print("Your file "+filename+" has been created!")
    return filename

def generate_pdf(file):

    print("Xelatex-ing the .tex to make the pdf...")
    subprocess.call(['xelatex',"-output-directory=docs",file],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    print("Doing it again because reasons...")
    subprocess.call(['xelatex',"-output-directory=docs",file],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    pdf_filename = file[:-4] + ".pdf"
    print("Done. The PDF %s has been generated. Cleaning up..." % pdf_filename)

    return "docs/"+pdf_filename

def encrypt_pdf(file,password,tag,args):
    base, ext = os.path.splitext(file)
    unencrypted_file = base + '_UNENCRYPTED' + ext

    # Step 2: Rename the original file
    os.rename(file, unencrypted_file)

    # Step 3: Determine encryption password
    if args['--encrypt']:
        password = args['--encrypt']
    else:
        print('empty')
        password = input("Encryption Password: ")

    # Step 4: Encrypt and save to original filename
    new_file = 'docs/' + tag + 'temp_encrypt.pdf'

    try:
        pdf_file = Pdf.open(unencrypted_file)
        pdf_file.save(new_file, encryption=Encryption(owner=password, user=password, R=4))
        pdf_file.close()

        # Step 5: Move encrypted file to original name
        os.rename(new_file, file)

        # Step 6: Delete unencrypted file
        os.remove(unencrypted_file)
        print("Encryption successful. Unencrypted file removed.")

    except Exception as e:
        print(f"Encryption failed: {e}")
        # Recover original file
        if not os.path.exists(file):
            os.rename(unencrypted_file, file)
        raise

#This generates the file for the 'links crawled' attachment
def return_links(report,name):
    # root = objectify.fromstring(report.encode())
    filename = "links-crawled-%s.csv" % name
    filename_path = "assets/"+filename
    file_csv = open(filename_path,'w')
    for webapp in report.RESULTS.WEB_APPLICATION:
        name = webapp.NAME
        file_csv.write("\nLinks for web application %s:" % name)
        file_csv.write('\n')
        for info in webapp.INFORMATION_GATHERED_LIST.INFORMATION_GATHERED:
            if info.QID == 150009:
                data = str(info.DATA)
                linklist = base64.b64decode(data).splitlines()
                for x in linklist:
                    file_csv.write(x.decode('utf-8'))
                    file_csv.write('\n')
    return filename

#This generates the file for the 'emails found' attachment
def return_emails(report,name):
    # root = objectify.fromstring(report.encode())
    filename = "emails-found-%s.csv" % name
    filename_path = "assets/"+filename
    file_csv = open(filename_path,'w')
    for webapp in report.RESULTS.WEB_APPLICATION:
        name = webapp.NAME
        file_csv.write("\nEmails found for web application %s:" % name)
        file_csv.write('\n')
        for info in webapp.INFORMATION_GATHERED_LIST.INFORMATION_GATHERED:
            if info.QID == 150054:
                data = str(info.DATA)
                linklist = base64.b64decode(data).splitlines()
                for x in linklist:
                    file_csv.write(x.decode('utf-8'))
                    file_csv.write('\n')
    return filename
# gets social and credit card data found
def get_ssn_and_cc(tag):
    print("Getting SSN and Credit Card info...")
    call = '/search/was/finding'
    ssn_post = '''<ServiceRequest>
    <preferences>
    <limitResults>1000</limitResults>
    <verbose>true</verbose>
    </preferences>
    <filters>
    <Criteria field="qid" operator="IN">150034, 150603</Criteria>
    <Criteria field="webApp.tags.name" operator="EQUALS">%s</Criteria>
    <Criteria field="ignoredReason" operator="NOT EQUALS">FALSE_POSITIVE</Criteria>
    <Criteria field="status" operator="NOT EQUALS">FIXED</Criteria>
    </filters>
    </ServiceRequest>''' % tag
    cc_post = '''<ServiceRequest>
    <preferences>
    <limitResults>1000</limitResults>
    <verbose>true</verbose>
    </preferences>
    <filters>
    <Criteria field="qid" operator="IN">150033, 150080</Criteria>
    <Criteria field="webApp.tags.name" operator="EQUALS">%s</Criteria>
    <Criteria field="ignoredReason" operator="NOT EQUALS">FALSE_POSITIVE</Criteria>
    <Criteria field="status" operator="NOT EQUALS">FIXED</Criteria>
    </filters>
    </ServiceRequest>''' % tag
    ssn_data = []
    ssn_links = []
    cc_data = []
    cc_links = []
    ssn_response = qgc.request(call,ssn_post,http_method='POST')
    ssn_root = objectify.fromstring(ssn_response.encode())
    cc_response = qgc.request(call, cc_post, http_method='POST')
    cc_root = objectify.fromstring(cc_response.encode())
    try:
        for finding in ssn_root.data.Finding:
            ssn_list = str(finding.resultList.list.Result.payloads.list.PayloadInstance.response)
            ssn_link = str(finding.resultList.list.Result.payloads.list.PayloadInstance.request.link)
            ssn_links.append(ssn_link)
            ssn_data.append(ssn_list)
    except AttributeError:
        ssn_links.append("No SSN data found.")
    try:
        for finding in cc_root.data.Finding:
            cc_list = str(finding.resultList.list.Result.payloads.list.PayloadInstance.response)
            cc_link = str(finding.resultList.list.Result.payloads.list.PayloadInstance.request.link)
            cc_links.append(cc_link)
            cc_data.append(cc_list)
    except AttributeError:
        cc_links.append("No Credit Card data found.")
    
    filename = 'assets/ssn-and-cc-found.csv'
    
    df = pd.DataFrame({'SSN URL':pd.Series(ssn_links), 'SSN FOUND':pd.Series(ssn_data),'':pd.Series(''), 'CC URL':pd.Series(cc_links), 'CREDIT CARD FOUND':pd.Series(cc_data)})
    df.to_csv(filename, index=False)
    return filename

#This generates the file for the 'links rejected' attachment
def return_rejects(report,name):
    # root = objectify.fromstring(report.encode())
    filename = "rejected-links-%s.csv" % name
    filename_path = "assets/"+filename
    file_csv = open(filename_path,'w')
    for webapp in report.RESULTS.WEB_APPLICATION:
        name = webapp.NAME
        file_csv.write("\nRejected Links found for web application "+str(name)+":")
        file_csv.write('\n')
        for info in webapp.INFORMATION_GATHERED_LIST.INFORMATION_GATHERED:
            if info.QID == 150041:
                data = str(info.DATA)
                linklist = base64.b64decode(data).splitlines()
                for x in linklist:
                    file_csv.write(x.decode('utf-8'))
                    file_csv.write('\n')
    return filename

def create_webapp_report_v2(name,tag):
    print("Creating webapp XML report for data...")
    doc = open('assets/was_report.xml',"r").read()
    root = objectify.fromstring(doc.encode())

    root.data.Report.template.id = "1994875"
    # root.data.Report.template.id = "2201149"
    root.data.Report.config.webAppReport.target.tags.included.tagList.Tag.id = tag
    root.data.Report.name = "<![CDATA[%s]]>" % name
    root.data.Report.format = "XML"

    objectify.deannotate(root, xsi_nil=True, pytype=True, xsi=True)
    etree.cleanup_namespaces(root)

    post = etree.tostring(root).decode()
    post = post.replace("&lt;", "<")
    post = post.replace("&gt;", ">")

    response = qgc.request('/create/was/report',post,http_method='post')
    root = objectify.fromstring(response.encode())
    # print(response)

    if root.responseCode == "SUCCESS":
        report_id = root.data.Report.id
        print("The report was successfully created. The report id is %s" % report_id)
    elif root.responseCode == "INVALID_REQUEST":
        print("Got the INVALID_REQUEST response. Please try running the report again.")
        sys.exit()

    else:
        print("There was an error. Here is the raw XML response from the server:")
        print(response)
        sys.exit()
    return report_id

def create_details_report(name,tag,fromArg=False):
    # print(fromArg)
    print('Creating details report...')
    if fromArg:
        doc = open('assets/was_report_details.xml',"r").read()
    else:
        doc = open('assets/was_report.xml',"r").read()
    root = objectify.fromstring(doc.encode())

    root.data.Report.template.id =  "2201149"
    if fromArg:
        root.data.Report.config.webAppReport.target.webapps.WebApp.id = tag
    else:
        root.data.Report.config.webAppReport.target.tags.included.tagList.Tag.id = tag
    root.data.Report.name = "<![CDATA[%s]]>" % name
    root.data.Report.format = "PDF"

    objectify.deannotate(root, xsi_nil=True, pytype=True, xsi=True)
    etree.cleanup_namespaces(root)

    post = etree.tostring(root).decode()
    post = post.replace("&lt;", "<")
    post = post.replace("&gt;", ">")

    response = qgc.request('/create/was/report',post,http_method='post')
    root = objectify.fromstring(response.encode())

    if root.responseCode == "SUCCESS":
        report_id = root.data.Report.id
        print("The report was successfully created. The report id is %s" % report_id)
    elif root.responseCode == "INVALID_REQUEST":
        print("Got the INVALID_REQUEST response. Please try running the report again.")
        sys.exit()

    else:
        print("There was an error. Here is the raw XML response from the server:")
        print(response)
        sys.exit()
    return report_id

#generates the dictionary for tag-to-description references
def tag_dict_v2():
    call = '/search/am/tag'
    tag_description_dict = {}

    post_root = objectify.Element("ServiceRequest")
    objectify.SubElement(post_root,"preferences")
    objectify.SubElement(post_root.preferences,"limitResults")
    post_root.preferences.limitResults = 1000
    objectify.SubElement(post_root, "filters")
    objectify.SubElement(post_root.filters, "Criteria")
    post_root.filters.Criteria = 'WAS_CUSTOMERS'
    post_root.filters.Criteria.set("field", "name")
    post_root.filters.Criteria.set("operator", "EQUALS")

    objectify.deannotate(post_root, xsi_nil=True, pytype=True, xsi=True)
    etree.cleanup_namespaces(post_root)

    post = etree.tostring(post_root).decode()
    response = qgc.request(call,post,http_method='POST')
    root = objectify.fromstring(response.encode())

    for tag in root.data.Tag.children.list.Tag:
        try:
            tag_description_dict[tag.name] = str(tag.description)
        except AttributeError:
            tag_description_dict[tag.name] = str(tag.name)

    return tag_description_dict

#returns a count of total web apps associated with a given tag
def app_count(tag):
    call = '/count/was/webapp'
    post_root = objectify.Element("ServiceRequest")
    objectify.SubElement(post_root, "filters")
    objectify.SubElement(post_root.filters, "Criteria")
    post_root.filters.Criteria = tag
    post_root.filters.Criteria.set("field", "tags.name")
    post_root.filters.Criteria.set("operator", "EQUALS")

    objectify.deannotate(post_root, xsi_nil=True, pytype=True, xsi=True)
    etree.cleanup_namespaces(post_root)

    post = etree.tostring(post_root).decode()
    response = qgc.request(call,post,http_method='POST')

    root = objectify.fromstring(response.encode())

    return root.count

def app_find(tag):
    call = '/search/am/tag'
    tag_description_dict = {}

    post_root = objectify.Element("ServiceRequest")
    objectify.SubElement(post_root,"preferences")
    objectify.SubElement(post_root.preferences,"limitResults")
    post_root.preferences.limitResults = 1000
    objectify.SubElement(post_root, "filters")
    objectify.SubElement(post_root.filters, "Criteria")
    post_root.filters.Criteria = tag
    post_root.filters.Criteria.set("field", "name")
    post_root.filters.Criteria.set("operator", "EQUALS")

    objectify.deannotate(post_root, xsi_nil=True, pytype=True, xsi=True)
    etree.cleanup_namespaces(post_root)

    post = etree.tostring(post_root).decode()
    response = qgc.request(call,post,http_method='POST')
    # print(response)
    root = objectify.fromstring(response.encode())
    if hasattr(root.data.Tag,'description'):
        desc =  str(root.data.Tag.description)
    else:
        desc = tag
    return desc

# generates a list of WAS customers (children of WAS_CUSTOMERS tag) and prints them out one by one, listing their webapp count
def app_numbering():
    from tqdm import tqdm
    call = '/count/was/webapp'
    tag_description_dict = tag_dict_v2()
    tag_list = tag_description_dict.keys()
    app_count_dict = {}
    for tag in tag_list:
        print(tag)

    with tqdm(total=len(tag_list),desc='Getting Webapp Counts...') as pbar:
        for tag in tag_list:
            post_root = objectify.Element("ServiceRequest")
            objectify.SubElement(post_root, "filters")
            objectify.SubElement(post_root.filters, "Criteria")
            post_root.filters.Criteria = tag
            post_root.filters.Criteria.set("field", "tags.name")
            post_root.filters.Criteria.set("operator", "EQUALS")

            objectify.deannotate(post_root, xsi_nil=True, pytype=True, xsi=True)
            etree.cleanup_namespaces(post_root)

            post = etree.tostring(post_root).decode()


            response = qgc.request(call,post,http_method='POST')

            root = objectify.fromstring(response.encode())
            if root.responseCode != 'SUCCESS':
                print('Oops, ERROR! The response from the server is %s' % root.responseCode)
            else:
                app_count_dict[tag] = root.count
            pbar.update(1)

    for tag in tag_list:
        print("%s (%s): %s" % (tag,tag_description_dict[tag],app_count_dict[tag]))

def add_tag(webapp_id, tag_id):
    call = 'update/was/webapp/%s' % webapp_id
    post = '''<ServiceRequest>
 <data>
 <WebApp>
 <tags>
 <add>
 <Tag>
 <id>%s</id>
 </Tag>
 </add>
 </tags>
 </WebApp>
 </data>
</ServiceRequest>''' % tag_id

    response = qgc.request(call,post,http_method='POST')
    # print(response)
    root = objectify.fromstring(response.encode())

    if str(root.responseCode) == 'SUCCESS':
        return(str(root.responseCode))
    else:
        return(response)
    # if str(root.responseCode) == 'SUCCESS':
    #     print("Successfully added tag to web applicaiton.")
    # else:
    #     print("Error. Her eis the response:\n %s" % response)

def remove_tag(webapp_id, tag_id):
    call = 'update/was/webapp/%s' % webapp_id
    post = '''<ServiceRequest>
 <data>
 <WebApp>
 <tags>
 <remove>
 <Tag>
 <id>%s</id>
 </Tag>
 </remove>
 </tags>
 </WebApp>
 </data>
</ServiceRequest>''' % tag_id

    response = qgc.request(call,post,http_method='POST')
    # print(response)
    root = objectify.fromstring(response.encode())

    if str(root.responseCode) == 'SUCCESS':
        return(str(root.responseCode))
    else:
        return(response)

def app_numbering_V2():
    call = '/search/was/webapp'
    post_root = objectify.Element("ServiceRequest")
    objectify.SubElement(post_root, "filters")
    objectify.SubElement(post_root.filters, "Criteria")
    post_root.filters.Criteria = 'WAS_CUSTOMERS'
    post_root.filters.Criteria.set("field", "tags.name")
    post_root.filters.Criteria.set("operator", "EQUALS")

    objectify.deannotate(post_root, xsi_nil=True, pytype=True, xsi=True)
    etree.cleanup_namespaces(post_root)

    post = etree.tostring(post_root).decode()

    response = qgc.request(call,post,http_method='POST')
    # print(response)

def generate_full(report,name,csv,pdf_file,count,severities,ages,info_csv):
    #This sets the mustache file for usage in the LaTex
    mustache_file = open('NEW_BIG.mustache','r',encoding='utf-8')

    data = get_summary_info(report)
    tag_description_dict = tag_dict_v2()

    #Populates various fields in the Mustache file to create the .tex for processing
    if name in tag_description_dict.keys():
        data['OrgName'] = latex_string_prep(tag_description_dict[name])
    else:
        data['OrgName'] = latex_string_prep(app_find(name))
    num = len(data['OrgName'])
    if num >= 55:
        data['NameLen'] = '18cm'
    elif num >= 45:
        data['NameLen'] = '16cm'
    elif num >= 40:
        data['NameLen'] = '13cm'
    elif num >= 35:
        data['NameLen'] = '12cm'
    elif num >= 25:
        data['NameLen'] = '10cm'
    elif num >= 14:
        data['NameLen'] = '8.5cm'
    else:
        data['NameLen'] = '6cm'

    data['OrgTag'] = latex_string_prep(name)
    webapp_csv_file = webapp_vuln_table(report,name)
    ssn_cc_file = get_ssn_and_cc(name)
    overview_csv_file = app_overview_table(report,name)
    data['DetailsCSV'] = csv
    data['InfoCSV'] = info_csv
    data['VulnCSV'] = webapp_csv_file
    data['AppOverviewCSV'] = overview_csv_file
    data['LinksCrawled'] = return_links(report,name)
    data['LinksRejected'] = return_rejects(report,name)
    data['EmailsFound'] = return_emails(report,name)

    data['DetailsCSVTex'] = latex_string_prep(data['DetailsCSV'])
    data['InfoCSVTex'] = latex_string_prep(data['InfoCSV'])
    data['VulnCSVTex'] = latex_string_prep(data['VulnCSV'])
    data['AppOverviewCSVTex'] = latex_string_prep(data['AppOverviewCSV'])
    data['LinksCrawledTex'] = latex_string_prep(data['LinksCrawled'])
    data['LinksRejectedTex'] = latex_string_prep(data['LinksRejected'])
    data['EmailsFoundTex'] = latex_string_prep(data['EmailsFound'])

    group_count_dict,owasp_count_dict,fixed_monthly_dict,vulns_monthly_dict,fixed,total,new,reopened,active = qid_counter(report)
    data['PathDisc'] = str(group_count_dict["Path Disclosure"])
    data['InfoDisc'] = str(group_count_dict["Information Disclosure"])
    data['CrossSite'] = str(group_count_dict["Cross-Site Scripting"])
    data['Burp'] = str(group_count_dict["Burp"])
    data['SqlInj'] = str(group_count_dict["SQL Injection"])
    data['Bugcrowd'] = str(group_count_dict["Bugcrowd"])
    data['Reopened'] = str(reopened)
    if data['Reopened'] == '0':
        data['ReopenedColor'] = '5e9732'
    else:
        data['ReopenedColor'] = 'c41230'
    data['NewVulns'] = str(new)
    if data['NewVulns'] == '0':
        data['NewVulnsColor'] = '5e9732'
    else:
        data['NewVulnsColor'] = 'c41230'
    data['TotVulns'] = str(active)
    if data['TotVulns'] == '0':
        data['TotVulnsColor'] = '5e9732'
    else:
        data['TotVulnsColor'] = 'c41230'
    # info_dict = info_dict_gen(report)
    
    print("Generating Graphs...")

    if count < 35:
        pdf_file_tex = latex_string_prep(pdf_file)
        data['PdfFile'] = '''\\newline

\\textbf{Attachment 9: Details PDF}
\\newline
\\attachfile[appearance=false,mimetype=application/pdf,icon=Paperclip,ucfilespec=assets/%s]{assets/%s}
%s: Detailed PDF Report of all findings.
''' % (pdf_file_tex,pdf_file,pdf_file_tex)
    else:
        data['PdfFile'] = ''
    #These generate the graph images for usage in the report.
    data['lev1'], data['lev2'], data['lev3'], data['lev4'], data['lev5'] = totalgraphgen(report) #this generates figure1.png
    # print("figure1.png saved.")
    owasp_graph_gen(owasp_count_dict) #this generates owasp_graph.png
    # print("owasp_graph.png saved.")
    vulnsbygroupgraphgen(group_count_dict) #this generates figure3.png
    # print("figure3.png saved.")
    monthly_trend(fixed_monthly_dict, vulns_monthly_dict)
    percent_donut(fixed, total)
    plot_histogram(ages, severities)
    #This uses the data generated from above to populate the fields in the mustache file to create the final result for the .tex that will be used to create the pdf.
    file = mustache_generate(mustache_file,data,name)

    #This executes Xelatex to generate the pdf from the .tex file
    pdf_filename = generate_pdf(file)

    #This removes all the additional files that are generated in the process.
    cleanup(name+"_report_"+str(datetime.now())[:10])

    return pdf_filename

def falsepos(fp_list):
    print("Marking false positives...")
    falsepos_list = read_file('docs/'+fp_list)
    # falsepos_list = []
    # with open(fp_list,'r') as f:
    #     for line in f.readlines():
    #         falsepos_list.append(line.strip())
    comment = input('Enter a comment for this False Positive marking:\n')
    for entry in falsepos_list:
        call = '/ignore/was/finding'
        post = '''<ServiceRequest>
<data>
<Finding>
<id>%s</id>
<ignoredReason>FALSE_POSITIVE</ignoredReason>
<ignoredComment>%s</ignoredComment>
</Finding>
</data>
</ServiceRequest>''' % (entry, comment)

        response = qgc.request(call,post,http_method='POST')
        root = objectify.fromstring(response.encode())
        if root.responseCode == 'SUCCESS':
            print('Finding %s successfully marked as FALSE_POSITIVE.' % entry)
        else :
            try:
                print(root.responseErrorDetails.errorMessage)
            except AttributeError:
                print('There was a problem marking %s as FALSE_POSITIVE. Here is the response from the server:\n%s' % (entry,response))

def delete_webapp(app):
    call = '/delete/was/webapp'
    post = '''<ServiceRequest>
 <filters>
 <Criteria field="url" operator="EQUALS">%s</Criteria>
</filters>
<data>
<WebApp>
<removeFromSubscription>true</removeFromSubscription>
</WebApp>
</data>
</ServiceRequest>''' %  app

    response = qgc.request(call,post,http_method='POST')
    root = objectify.fromstring(response.encode())
    print("Status on app deletion for %s: %s" % (app,root.responseCode))

def reactivate_webapp(app,org_tags):
    call = '/create/was/webapp'
    post = '''<ServiceRequest>
<data>
<WebApp>
<name><![CDATA[%s]]></name>
<url><![CDATA[%s]]></url>
<reactivateIfExists>true</reactivateIfExists>
<tags>
<set>
'''% (app,app) + org_tags + '''
</set>
</tags>
</WebApp>
</data>
</ServiceRequest>
    '''

    response = qgc.request(call,post,http_method='POST')
    root = objectify.fromstring(response.encode())

    print("Status on app activation for %s: %s" % (app,root.responseCode))
    # print(response)

# def do_report(tag,password,args):
#     print("Generating the report for " + tag)
#     count = app_count(tag)
#     print("The web application count is: %s" % count)

#     if count < 1:
#         print("No Web Applications found for tag: %s" % tag)
#         sys.exit(-1)

#     tag_id = get_tag_id(tag)

#     if count < 35:
#         pdf_id = create_details_report(tag,tag_id)
#         pdf_file = download_report(pdf_id,tag)
#     else:
#         pdf_file = None

#     report_id = create_webapp_report_v2(tag,tag_id)
#     report_xml = get_report(report_id)
#     #print(report_xml)
#     csv, info_csv, severities, ages = csv_genner(report_xml,tag)

#     pdf_filename = generate_full(report_xml,tag,csv,pdf_file,count, severities, ages, info_csv)
#     delete_report(report_id, tag)

#     encrypt_pdf(pdf_filename,password,tag,args)

# def reporting(tag, args):
#     dateSet = datetime.today()
#     pass_date = dateSet.strftime('%Y%m%d')
#     password = tag.strip() + "_WAS_" + pass_date
#     #print('Generating the report for ' + tag)
#     # Send stdout to a text file specific to the tag. Check if last line of text file says successfully deleted. If it doesn't then the report needs to be rerun.
#     #sys.stdout = open(tag + '_log', 'w')
#     #original = sys.stdout
#     #sys.stdout = open('docs/' + tag + '_reportlog.txt', 'w')
#     do_report(tag, password, args)
#     #sys.stdout = original
#     #sys.stdout.close()
#     return f'Report for {tag} done.'

def main():
    global __doc__
    __doc__ = re.sub('COMMAND_NAME', __file__, __doc__)
    args = docopt(__doc__, version='v' + version)

    #name = list_users()

    ### term_size = os.get_terminal_size()
    ### if term_size.columns < 125 or term_size.lines < 18:
    ###     print("\nYour terminal window is too small for the cool title graphic :( \n")
    ### else:
    ###     print('''
    ### ########################################################################################################################
    ### #  ____    __    ____  ___           _______.   .______       _______ .______     ______   .______     .___________.   #
    ### #  \   \  /  \  /   / /   \         /       |   |   _  \     |   ____||   _  \   /  __  \  |   _  \    |           |   #
    ### #   \   \/    \/   / /  ^  \       |   (----`   |  |_)  |    |  |__   |  |_)  | |  |  |  | |  |_)  |   `---|  |----`   #
    ### #    \            / /  /_\  \       \   \       |      /     |   __|  |   ___/  |  |  |  | |      /        |  |        #
    ### #     \    /\    / /  _____  \  .----)   |      |  |\  \----.|  |____ |  |      |  `--'  | |  |\  \----.   |  |        #
    ### #      \__/  \__/ /__/     \__\ |_______/       | _| `._____||_______|| _|       \______/  | _| `._____|   |__|        #
    ### #                                                                                                                      #
    ### #                      ______ .______       _______     ___   .___________.  ______   .______                          #
    ### #                     /      ||   _  \     |   ____|   /   \  |           | /  __  \  |   _  \                         #
    ### #                    |  ,----'|  |_)  |    |  |__     /  ^  \ `---|  |----`|  |  |  | |  |_)  |                        #
    ### #                    |  |     |      /     |   __|   /  /_\  \    |  |     |  |  |  | |      /                         #
    ### #                    |  `----.|  |\  \----.|  |____ /  _____  \   |  |     |  `--'  | |  |\  \----.                    #
    ### #                     \______|| _| `._____||_______/__/     \__\  |__|      \______/  | _| `._____|                    #
    ### #                                                                                                                      #
    ### ########################################################################################################################
    ### ''')
    print("WAS Report Generation Tool v"+version)
    #print("Welcome, "+name)

    if args['--list']:
        app_numbering()
        sys.exit(-1)

    if args['--add-tag']:
        app_list = read_file('docs/'+args['--add-tag'])
        app_id_dict = {}
        # with open('docs/'+args['--add-tag']) as f:
        #     for line in f.readlines():
        #         app_list.append(line.strip())

        for app in app_list:
            print('Getting app ID for', app)
            try:
                app_id_dict[app] = get_app_id(app)
            except AttributeError:
                print("No ID for %s." % app)
        tag = input("Which Tag should be added to this list of webapps?\n")
        tag_id = get_tag_id(tag)
        for id in app_id_dict:
            response = add_tag(app_id_dict[id],tag_id)
            if response == 'SUCCESS':
                print("Successfully added tag %s to %s" % (tag, id))
            else:
                print("There was an error with %s. Here is the response:\n %s" %(id,response))

        sys.exit(-1)

    if args['--remove-tag']:
        app_list = []
        app_id_dict = {}
        with open('docs/'+args['--remove-tag'],'r') as f:
            for line in f.readlines():
                app_list.append(line.strip())

        for app in app_list:
            try:
                app_id_dict[app] = get_app_id(app)
            except AttributeError:
                print("No ID for %s." % app)
        tag = input("Which Tag should be removed from this list of webapps?\n")
        tag_id = get_tag_id(tag)
        for id in app_id_dict:
            response = remove_tag(app_id_dict[id],tag_id)
            if response == 'SUCCESS':
                print("Successfully removed tag %s from %s" % (tag, id))
            else:
                print("There was an error with %s. Here is the response:\n %s" %(id,response))

        sys.exit(-1)

    if args['--false-positive']:
        falsepos(args['--false-positive'])
        sys.exit(-1)

    if args['--xml']:
        if not args['--tag']:
            tag = input("Which tag would you like to use?\n")
        else:
            tag = args['--tag']
        print('Generating the report for %s' % tag)
        tag_id  = get_tag_id(tag)

        report_id = create_webapp_report_v2(tag,tag_id)
        report_xml = get_report(report_id)
        report_custom_parse = objectify.fromstring(report_xml.encode(),parser=objectify.makeparser(huge_tree=True))

        # root = objectify.fromstring(report_xml.encode())

        header = report_custom_parse.HEADER
        # company_info = root.HEADER.COMPANY_INFO
        # user_info = root.HEADER.USER_INFO

        header.remove(header.COMPANY_INFO)
        header.remove(header.USER_INFO)

        filename = input("Filename: ")

        file = open('docs/'+filename, 'w')
        file.write(str(etree.tostring(report_custom_parse),'UTF-8'))
        file.close()

        sys.exit(-1)

    if args['--details-only']:
        name_list = read_file('docs/%s' % args['--details-only'])
        for name in name_list:
            fromArg = True
            id = str(get_app_id(name))
            report_id = create_details_report(name,id,fromArg)
            download_report(report_id,name,fromArg)
        print("All detail reports completed.")
        sys.exit(-1)

    # if args['--noninteractive']:
    #     panda_frame = pd.read_excel('docs/' + args['--noninteractive'])
    #     for row in panda_frame.itertuples(index=True):
    #         tag = str(row.TAG).strip()
    #         try:
    #             do_report(tag,row.PASSWORD,args)
    #         except:
    #             print("There was an error with report %s: %s" % (row.TAG, sys.exc_info()[0]))
    #     print("All reports in file complete.")
    #     sys.exit(-1)

    if args['--reactivate']:
        activate_list = read_file('docs/'+args['--reactivate'])
        added_tag = get_tag_id(input("Which tag would you like to add?\n"))
        org_tags = '''<Tag>
        <id>%s</id>
        </Tag>
        ''' % added_tag
        tag_response = input("Would you like to add another tag? (Y/N)\n")
        while tag_response.upper() == 'Y':
             tag_add = get_tag_id(input("Which tag would you like to add?\n"))
             org_tags += '''<Tag>
             <id>%s</id>
             </Tag>
             ''' % tag_add
             tag_response = input("Would you like to add another tag? (Y/N)\n")

        for app in activate_list:
            reactivate_webapp(app,org_tags)
        sys.exit(-1)

    if args['--delete-webapp']:
        delete_list = read_file('docs/'+args['--delete-webapp'])
        for app in delete_list:
            delete_webapp(app)
        print('App deletion complete.')
        sys.exit(-1)

    if args['--update-tracker']:
        import update_tracker
        sys.exit(-1)

    if not args['--tag']:
        global query
        query = input("Which tag would you like to use?\n")
    else:
        query = args['--tag']

    print("Generating the report for " + query)
    count = app_count(query)
    print("The web application count is: %s" % count)

    if count < 1:
        print("No Web Applications found for tag: %s" % query)
        sys.exit(-1)

    tag_id = get_tag_id(query)

    if count < 35:
        pdf_id = create_details_report(query,tag_id)
        pdf_file = download_report(pdf_id,query)
    else:
        pdf_file = None

    report_id = create_webapp_report_v2(query,tag_id)
    report_xml = get_report(report_id)
    report_custom_parse = objectify.fromstring(report_xml.encode(),parser=objectify.makeparser(huge_tree=True))
    csv, info_csv, severities, ages = csv_genner(report_custom_parse,query)

    pdf_filename = generate_full(report_custom_parse,query,csv,pdf_file,count, severities, ages, info_csv)
    delete_report(report_id, None)

    if args['--encrypt']:
        if str(args['--encrypt']) == 'N/A':
            sys.exit()
        encrypt_pdf(pdf_filename,str(args['--encrypt']),args['--tag'],args)

    else:
        encrypt = input("Encrypt PDF? (Y/N)\n")
        if len(encrypt) < 1:
            sys.exit()
        if encrypt.upper()[0] == 'Y':
            encrypt_pdf(pdf_filename,None,args['--tag'],args)

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\nUser has forced a close. Goodbye.")
        sys.exit()
