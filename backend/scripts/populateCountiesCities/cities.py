"""
This module contains the script for populating cities data.

It includes functions for parsing titles, pulling cities data from Wikipedia,
and writing the data to a CSV file.
"""

# Standard Python Libraries
import json
import re
import time
from urllib.parse import unquote

# Third-Party Libraries
from bs4 import BeautifulSoup
import pandas as pd
import requests


def title_parse(title):
    """
    Parse the title by unquoting it.

    Args:
        title (str): The title to be parsed.

    Returns:
        str: The parsed title.
    """
    title = unquote(title)
    return title


def pull_cities():
    """
    Process and pull cities data from Wikipedia.

    This function reads the Wikipedia US cities data from a JSON file, processes each entry,
    fetches the corresponding Wikipedia page, parses the page to extract city, county, and URL information,
    and writes the data to a CSV file.
    """
    print("Processing Cities...")
    with open("wikipedia_US_cities.json") as f:
        wikipedia_us_city_data = json.load(f)

    holding_pen = []

    for entry in wikipedia_us_city_data:
        print(entry["name"])
        # get the response in the form of html
        wikiurl = "https://en.wikipedia.org/wiki/" + entry["url"]
        try:
            response = requests.get(wikiurl, timeout=5)
        except requests.exceptions.Timeout:
            print("The request timed out")

        # parse data from the html into a beautifulsoup object
        soup = BeautifulSoup(response.text, "html.parser")

        # DEAL WITH VERMONT'S NON-COMPLIANT WIKIPEDIA PAGE
        if entry["name"] == "Vermont":
            countytable = soup.find_all(
                "table",
                {"class": entry["table_type"]},
            )
            vermont_special = ""
            for thing in countytable:
                vermont_special = vermont_special + "\n" + str(thing)
            soup_special = BeautifulSoup(vermont_special, "html.parser")
            countytable = soup_special
        else:
            countytable = soup.find(
                "table",
                {"class": entry["table_type"]},
            )

        links = countytable.select("a")
        for link in links:
            if "County" or "Parish" not in link.get("title"):
                try:
                    if "," in link.get("title"):
                        county_pieces = link.get("title").split(",")
                        # OPEN WIKIPEDIA PAGE UP
                        x = requests.get(
                            "https://en.wikipedia.org/" + link.get("href"), timeout=5
                        )

                        # PULL COUNTY OR PARISH FROM WIKIPEDIA PAGE
                        county_parish_matches = re.findall(
                            r"<td class=\"infobox-data\"><a href=\"/wiki/(.+?)\"",
                            x.text,
                        )

                        for match in county_parish_matches:
                            if ("County" or "Parish") in match:
                                county_value = match
                                county_value = county_value.split(",")
                                county_value = county_value[0].replace("_", " ")

                        # PULL WEBSITE FROM WIKIPEDIA PAGE
                        w = re.findall(
                            r"<th scope=\"row\" class=\"infobox-label\">Website</th>.+</a>",
                            x.text,
                        )
                        # PULL URL OUT OF FOUND TEXT
                        url = re.search(r"href=\"(.+?)\"", w[0])
                        url = url.group()
                        url = url.replace("href=", "").replace('"', "")

                        holding_pen.append(
                            {
                                "City": county_pieces[0],
                                "State": entry["name"],
                                "URL": url,
                                "County": county_value,
                            }
                        )
                    time.sleep(1)
                except Exception as e:
                    print(f"Error: {e}")
                    pass

        df = pd.DataFrame(holding_pen, columns=["State", "County", "City", "URL"])

        df.drop_duplicates(inplace=True)

        # DROP COUNTIES FROM CITY ENTRIES
        df = df[~df.City.str.contains(" County", na=False)]

        # REMOVE HTML ENTITIES (LIKE %27)
        df["State"] = df.State.apply(title_parse)
        df["City"] = df.City.apply(title_parse)
        df["County"] = df.County.apply(title_parse)

        df.to_csv("United_States_Cities_with_URLs.csv", index=False, encoding="utf-8")


if __name__ == "__main__":
    pull_cities()
