# coding=utf-8
# election_scraper.py: third project
# author: Petr Běla
# email: petr.bela@seznam.cz
# discord: Petr B. Gibon420#2267

import argparse
import os
import pandas as pd
import requests
import sys
from bs4 import BeautifulSoup
from urllib.parse import parse_qs, urlparse
from tqdm import tqdm
import matplotlib.pyplot as plt
from pprint import pprint


def get_soup(url: str) -> BeautifulSoup:
    """
    Fetches the content of the given URL and returns it as a BeautifulSoup object.

    :param url: The URL of the webpage to fetch.
    :return: BeautifulSoup: A BeautifulSoup object containing the parsed HTML content of the webpage.
    :raise SystemExit: If the HTTP request fails with a non-200 status code.
    """
    try:
        response = requests.get(url)
        response.raise_for_status()  # raise for non-200 status codes
    except requests.exceptions.RequestException as e:
        print(f"ERROR: Failed to fetch the page '{url}'\n"
              f"{type(e).__name__}: {e}")
        sys.exit(1)
    else:
        return BeautifulSoup(response.content, features="html.parser")


def all_district_links(
        page: BeautifulSoup,
        base_url: str = "https://volby.cz/pls/ps2017nss/",
        container_tag: str = "td",
        container_class: str = "cislo",
        link_tag_name: str = "a",
        attribute_name: str = "href"
) -> list[str]:
    """
    Extracts all district links from the given page content.

    :param page: A BeautifulSoup object representing the parsed HTML page.
    :param base_url: The base URL to prepend to relative links.
    :param container_tag: The HTML tag containing the cells with links.
    :param container_class: The class name of the containers containing the links.
    :param link_tag_name: The HTML tag containing the links.
    :param attribute_name: The attribute of the tag containing the link URL.
    :return: A list containing all extracted links to district pages.
    """
    all_links = []
    for cell in page.find_all(container_tag, class_=container_class):
        link = cell.find(link_tag_name)
        try:
            href = link.get(attribute_name)
            if not href:
                raise ValueError(f"Link or attribute '{attribute_name}' not found in cell: {cell}")
            all_links.append(f"{base_url}{href}")
        except (TypeError, KeyError):
            print(f"WARNING: Link or attribute '{attribute_name}' not found in cell: {cell}")
            continue  # Skip to next cell

    return all_links


def global_data(
        soup: BeautifulSoup,
        class_name: str = "cislo",
        district: str = 'h3:-soup-contains("Obec:")',
        registered_header: str = "sa2",
        envelopes_header: str = "sa3",
        valid_header: str = "sa6",
        container_tag: str = "td"
) -> dict:
    """
    Extracts data from HTML content related to votes in each district.

    :param soup: A parsed BeautifulSoup object representing the HTML content.
    :param class_name: Class name of the data cells containing the values to be extracted.
    :param district: CSS selector for the district name element.
    :param registered_header: Header name for the "count_registered" column.
    :param envelopes_header: Header name for the "count_envelopes" column.
    :param valid_header: Header name for the "count_valid" column.
    :param container_tag: The HTML tag containing the cells with data.
    :return: A dictionary containing the extracted data.
        - code (str): The code representing the district.
        - count_registered (str): The number of registered voters in the district.
        - count_envelopes (str): The number of envelopes received in the district.
        - count_valid (str): The number of valid votes in the district.
    """
    links = all_district_links(soup)
    all_global = {}

    for district_link in tqdm(links, desc="Scraping districts informations", ncols=100, colour="#03A062",
                              bar_format='{desc}: {percentage:3.0f}% |{bar}| {n_fmt}/{total_fmt} [{remaining}]'):
        district_name = ""
        try:
            district_data = {
                "location": "",
                "political_parties_votes": {},
                "count_registered": None,
                "count_envelopes": None,
                "count_valid": None
            }

            individual_district_soup = get_soup(district_link)
            district_name_element = individual_district_soup.select_one(district)
            if district_name_element:
                district_name = district_name_element.text.strip().split(":")[1]
                district_data["location"] = district_name
            else:
                print(f"ERROR: District name not found for link: {district_link}")
                continue

            code = get_code_from_url(district_link)
            if code is None:
                print(f"ERROR: District code not found for link: {district_link}")
                continue

            district_data["political_parties_votes"] = get_votes_of_parties(individual_district_soup)

            headers = {
                "count_registered": registered_header,
                "count_envelopes": envelopes_header,
                "count_valid": valid_header
            }

            for key, header in headers.items():
                try:
                    cell = individual_district_soup.find(container_tag, class_=class_name, headers=header)
                    if cell:
                        district_data[key] = int(clean_data(cell.text))
                    else:
                        print(f"ERROR: Data cell not found for header {header} in district {district_name}")
                except (AttributeError, ValueError, KeyError) as e:
                    print(f"ERROR: An error occurred while extracting data for header '{header}': {e}")

            all_global[code] = district_data

        except Exception as e:
            print(f"Error: An exception occurred for district {district_name}: {e}")

    return all_global


def get_code_from_url(
        url: str,
        parameter_name: str = "xobec"
) -> str:
    """
    Extracts the code of village from a URL query string.

    :param url: The string containing the URL query string.
    :param parameter_name: The name of the parameter in the query string from which to extract the code.
    :return: The extracted code (xobec value) or None if not found.
    """
    try:
        # Parse the URL using urllib.parse
        url_parts = urlparse(url)
        query_dict = parse_qs(url_parts.query)

        return query_dict.get(parameter_name, [None])[0]

    except ValueError as ve:
        # Handle potential parsing errors
        raise ValueError(f"ERROR parsing URL or parameter_name not found: {ve}")


def get_votes_of_parties(
        page: BeautifulSoup,
        party_name_class: str = "overflow_name",
        votes_class: str = "cislo",
        headers: list[str] = ("t1sa2 t1sb3", "t2sa2 t2sb3"),
        container_tag: str = "td"
) -> dict:
    """
    Extracts the votes count for each political party from the given page content.

    :param page: A BeautifulSoup object representing the parsed HTML content.
    :param party_name_class: The class name of elements containing political party names.
    :param votes_class: The class name of elements containing votes count.
    :param headers: A list of header values used to filter votes count elements.
    :param container_tag: The HTML tag containing the cells with data.
    :return: A dictionary containing the votes count for each political party.
    """
    try:
        political_parties = page.find_all(container_tag, class_=party_name_class)
        party_names = [party.text.strip() for party in political_parties]

        political_parties_votes = page.find_all(container_tag, class_=votes_class, headers=headers)
        votes_count = [int(clean_data(votes.get_text().strip())) for votes in political_parties_votes]

        return dict(zip(party_names, votes_count))

    except Exception as e:
        print(f"ERROR occurred while extracting votes of parties: {e}")
        return {}


def clean_data(text: str, char_to_remove: str = "\xa0") -> str:
    """
    Removes the non-breaking space character (xa0) from the text.

    :param text: The input text.
    :param char_to_remove: The character to be removed from the text.
    :return: The text without the specified character.
    """
    return text.replace(char_to_remove, "")


def get_csv(data: dict, filename: str) -> None:
    """
    Converts a dictionary containing election data to a CSV file.

    :param data: Dictionary where keys are district codes and values are dictionaries with election data.
        Election data includes information like 'location', 'count_registered' (number of registered voters),
        'count_envelopes' (number of envelopes issued), 'count_valid' (number of valid votes),
        and 'political_parties_votes' (nested dictionary with number of votes for each party).
    :param filename: The name of the CSV file to be created.
    :return: None
    """
    # Create DataFrame from dictionary
    df = pd.DataFrame.from_dict(data, orient='index')

    # Reorder the columns in the DataFrame
    df = df[['location', 'count_registered', 'count_envelopes', 'count_valid', 'political_parties_votes']]

    # Unnesting the `political_parties_votes` dictionary into separate columns:
    # 1. Drop the original `political_parties_votes` column.
    # 2. Apply `pd.Series` to each row of the `political_parties_votes` column:
    #    - Split the dictionary into party names (columns) and vote counts (values).
    df = pd.concat([df.drop(['political_parties_votes'], axis=1), df['political_parties_votes'].apply(pd.Series)],
                   axis=1)

    # Create directory if it doesn't exist
    os.makedirs("Results", exist_ok=True)

    # Define the file path
    file_path = os.path.join("Results", add_extension(filename, "csv"))

    # Check if the file already exists
    if os.path.exists(file_path):
        raise FileExistsError(f"File {filename} already exists.")

    # Save DataFrame to CSV file
    df.to_csv(file_path, index_label='code', encoding="utf-8-sig", sep=",")
    print(f"CSV FILE SUCCESSFULLY CREATED: '{filename}.csv'")

    # Debug: Print preview of the CSV file
    # print(f"\nPreview of CSV file '{filename}':")
    # with open(file_path, 'r', encoding='utf-8') as file:
    #     for row in range(5):
    #         print(file.readline().strip())


def plot_top_10_parties(data: dict, filename: str) -> None:
    """
    Plots a bar chart showing the top 10 political parties based on the total number of votes.

    :param data: A dictionary containing data for each electoral district, including political party votes.
    :param filename: Name of the file to save the plot, typically includes the district name.
    :return: None
    """
    # Sum up the votes for each political party
    party_votes = {}
    for district in data.values():
        for party, votes in district["political_parties_votes"].items():
            party_votes[party] = party_votes.get(party, 0) + votes

    # Select the top 10 parties based on the total number of votes
    top_10_parties = dict(sorted(party_votes.items(), key=lambda item: item[1], reverse=True)[:10])

    # Set up the figure with a larger size
    plt.figure(figsize=(30, 20))  # width=30 inches, height=20 inches

    # Create a bar chart
    plt.bar(list(top_10_parties.keys()), list(top_10_parties.values()))  # Plotting the bar chart
    plt.xticks(rotation=25, fontsize=15)  # Rotating x-axis labels for better readability
    plt.yticks(fontsize=15)  # Setting font size for y-axis labels
    plt.ylabel("Total Number of Votes", fontsize=25)  # Labeling y-axis
    plt.title("Top 10 Political Parties by Number of Votes", fontsize=25)  # Adding title to the plot

    # Define the file path
    file_path = os.path.join("Results", add_extension("Top_10_Parties_of_" + filename, "png"))

    # Save the plot to a file
    plt.savefig(file_path)
    plt.close()
    print(f"BAR PLOT SUCCESSFULLY CREATED: 'Top_10_Parties_of_{filename}.png'")


def add_extension(filename: str, extension: str) -> str:
    """Adds extension to the filename."""
    return f"{filename}.{extension}"


def elections_scraper(url, filename):
    print(f"DOWNLOADING DATA FROM THE SELECTED URL: '{url}'")
    soup = get_soup(url)
    dict_of_data = global_data(soup)
    # pprint(dict_of_data)  # Debug: show dict of scrapped data
    get_csv(dict_of_data, filename)
    plot_top_10_parties(dict_of_data, filename)
    print(f"PROCESS SUCCESSFULLY FINISHED")


if __name__ == "__main__":
    # Create argument parser
    parser = argparse.ArgumentParser(description="Scrape election data for a district.")
    parser.add_argument("url",
                        help="The complete URL of the webpage containing election data for a specific district.",
                        metavar="\"url\"")
    parser.add_argument("filename",
                        help="The name of the files to be created. It's recommended to enter the name of the district. "
                             "The appropriate file extension (.csv for CSV file, .png for plot) "
                             "will be automatically added by the script.")
    # Parse arguments
    args = parser.parse_args()

    elections_scraper(args.url, args.filename)
