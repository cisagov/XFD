import pandas as pd
from os import environ
from set_up import specialCasesFilePath


# Load the Excel file
xls = pd.ExcelFile(specialCasesFilePath)

ASSIGNEES = [item[0] for item in xls.parse(sheet_name='Assignees').values.tolist()]
KEEP_NWS = [item[0] for item in xls.parse(sheet_name='No NWS Deletions').values.tolist()]