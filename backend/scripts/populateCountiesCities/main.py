"""
This module contains the main script for populating counties and cities data.

It includes commands for processing cities and counties data separately or both at once.
"""

# Third-Party Libraries
import cities
import counties
import typer

app = typer.Typer()


@app.command()
def process_cities():
    """
    Process and pull cities data from Wikipedia.

    This function calls the pull_cities function from the cities module,
    which reads the Wikipedia US cities data from a JSON file, processes each entry,
    fetches the corresponding Wikipedia page, parses the page to extract city, county, and URL information,
    and writes the data to a CSV file.
    """
    cities.pull_cities()


@app.command()
def process_counties():
    """
    Process and pull counties data from Wikipedia.

    This function calls the pull_counties function from the counties module,
    which fetches the Wikipedia page for the list of United States counties,
    parses the page to extract county, state, and URL information,
    and writes the data to a CSV file.
    """
    counties.pull_counties()


@app.command()
def process_both():
    """
    Process and pull both cities and counties data from Wikipedia.

    This function calls both the pull_cities function from the cities module and the pull_counties function from the counties module,
    which fetches the Wikipedia pages for the list of United States cities and counties,
    parses the pages to extract city, county, state, and URL information,
    and writes the data to CSV files.
    """
    counties.pull_counties()
    cities.pull_cities()


if __name__ == "__main__":
    app()
