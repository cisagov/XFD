"""
This module contains the script for populating counties data.

It includes functions for pulling counties data from Wikipedia,
and writing the data to a CSV file.
"""

# Standard Python Libraries
import re
import time

# Third-Party Libraries
from bs4 import BeautifulSoup
import pandas as pd
import requests


def pull_counties():
    """
    Process and pull counties data from Wikipedia.

    This function fetches the Wikipedia page for the list of United States counties,
    parses the page to extract county, state, and URL information,
    and writes the data to a CSV file.
    """
    print("Processing Counties...")
    # get the response in the form of html
    wikiurl = "https://en.wikipedia.org/wiki/List_of_United_States_counties_and_county_equivalents"
    try:
        response = requests.get(wikiurl, timeout=5)
    except requests.exceptions.Timeout:
        print("The request timed out")

    # parse data from the html into a beautifulsoup object
    soup = BeautifulSoup(response.text, "html.parser")
    countytable = soup.find("table", {"class": "wikitable"})

    links = countytable.select("a")

    holding_pen = []

    for link in links:
        try:
            county_pieces = link.get("title").split(", ")
            # OPEN WIKIPEDIA PAGE UP
            x = requests.get("https://en.wikipedia.org/" + link.get("href"), timeout=5)

            # PULL WEBSITE FROM WIKIPEDIA PAGE
            w = re.findall(
                r"<th scope=\"row\" class=\"infobox-label\">Website</th>.+</a>", x.text
            )
            # PULL URL OUT OF FOUND TEXT
            url = re.search(r"href=\"(.+?)\"", w[0])
            url = url.group()
            url = url.replace("href=", "")

            holding_pen.append(
                {
                    "County": county_pieces[0],
                    "State": county_pieces[1],
                    "URL": url,
                }
            )
        except Exception as e:
            print(f"Error: {e}")
            pass

        time.sleep(1)

    df = pd.DataFrame(holding_pen, columns=["County", "State", "URL"])

    df.drop_duplicates(inplace=True)

    # Drop the Statistical Area Entries
    df[~df.State.str.contains("Statistical Area")]

    df.to_csv("United_States_Counties_with_URLs.csv", index=False)


if __name__ == "__main__":
    pull_counties()
