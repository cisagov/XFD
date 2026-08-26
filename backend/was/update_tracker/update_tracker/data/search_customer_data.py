import json
from set_up import CUSTOMER_DATA
from typing import Any

# SLTT = ["State", "Local", "Tribal", "Territorial"]


def get_customer_data(tag: str) -> tuple:
    """
    gets customer data from dynamodb

    Parameters
    ----------
    tag : str
        stakeholder tag

    Returns
    -------
    poc : str
        the name of the WAS poc
    poc_email : str
        the email(s) for the WAS poc
    notes : str
        notes about the stakeholder
    csa : str
        the regional csa email if the stakeholder is SLTT
    """
    try:
        stakeholder = CUSTOMER_DATA.get_item({"Tag": {"S": tag}})
    except KeyError:
        tag_split = tag.split('_')[0]
        stakeholder = CUSTOMER_DATA.get_item({"Tag": {"S": tag_split}})

    # poc = get_dynamo_value(stakeholder, "WAS Report POC")
    # poc_email = get_dynamo_value(stakeholder, "WAS Report Email")
    # notes = get_dynamo_value(stakeholder, "Comments")
    # sector = get_dynamo_value(stakeholder, "Testing Sector")
    # state = get_dynamo_value(stakeholder, "State")
    # # print(tag, poc, poc_email, notes, sector, state)
    # if any(x in sector for x in SLTT):
    #     csa = get_csa_email(state)
    # else:
    #     csa = ""
    # return poc, poc_email, notes, csa
    ############### above comment block is for Bcc of regional CSAs
    return stakeholder


def get_dynamo_value(stakeholder: dict, key: str) -> Any:
    """
    gets specific dynamo values

    Parameters
    ----------
    stakeholder : dict
        stakeholder dynamo db dict
    key : str
        stakeholder attribute

    Returns
    -------
    value
        value of field
    """
    if key in stakeholder:
        return list(stakeholder[key].values())[0]
    return None


# def get_csa_email(state_abbr):
#     """
#     gets regional csa email from csa json

#     Parameters
#     ----------
#     state_abbr : str
#         the state the stakeholder is located in

#     Returns
#     -------
#     email : str
#         the regional csa email if the stakeholder is SLTT
#     """
#     with open(CSA_JSON_PATH, 'r') as file:
##         region = json.load(file)
#         for email, states in region.items():
#             if state_abbr in states:
#                 return email
#         return None


# def get_customer_data(tag):
#     """
#     Retrieve stakeholder details from customer data sheet

#     Parameters
#     ----------
#     tag : str
#         the stakeholder tag (shortname)

#     Returns
#     -------
#     poc : str
#         the name of the WAS poc
#     poc_email : str
#         the email(s) for the WAS poc
#     notes : str
#         notes about the stakeholder
#     csa : str
#         the regional csa email if the stakeholder is SLTT

#     Raises
#     ------
#     Exception
#         if the stakeholder tag is not present in the customer data sheet
#     """
#     for row in CUSTOMER_DATA.iter_rows(min_row=2, max_row=CUSTOMER_DATA.max_row, min_col=1, max_col=1):
#         if row[0].value == tag:
#             poc = row[0].offset(column=9).value  # Assuming name is in column J (column index 9)
#             poc_email = row[0].offset(column=10).value  # Assuming email is in column K (column index 10)
#             notes = row[0].offset(column=8).value  # Assuming notes is in column I (column index 8)
#             sector = row[0].offset(column=2).value
#             state = row[0].offset(column=16).value  # Assuming state is in column Q (column index 16)
#             if "State" in sector or "Local" in sector or "Tribal" in sector or "Territorial" in sector:
#                 csa = get_csa_email(state)
#             else: csa  = ""
#             return poc, poc_email, notes, csa
#     raise Exception("Tag not found... attempt parent tag")
