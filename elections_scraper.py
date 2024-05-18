# coding=utf-8
# election_scraper.py: third project
# author: Petr Běla
# email: petr.bela@seznam.cz
# discord: Petr B. Gibon420#2267

# import argparse
import os
import sys
from pprint import pprint
from urllib.parse import parse_qs, urlparse

import pandas as pd
import requests
from bs4 import BeautifulSoup
from tqdm import tqdm
import matplotlib.pyplot as plt


def get_soup(url: str) -> BeautifulSoup:
    """
    Fetches the content of the given URL and returns it as a BeautifulSoup
     object.

    :param url: The URL of the webpage to fetch.
    :type url: str
    :return: An object containing the parsed HTML content of the webpage.
    :rtype: BeautifulSoup
    :raises SystemExit: If the HTTP request fails with a non-200 status code.
    """
    try:
        response = requests.get(url)
        response.raise_for_status()  # raise for non-200 status codes
    except requests.exceptions.RequestException as error:
        print(f"ERROR: Failed to fetch the page '{url}'\n"
              f"{type(error).__name__}: {error}")
        sys.exit(1)
    else:
        return BeautifulSoup(response.content, features="html.parser")


def extract_all_district_links(page: BeautifulSoup,
                               base_url: str = "https://volby.cz/pls/ps2017nss/",
                               container_tag: str = "td",
                               container_class: str = "cislo",
                               link_tag_name: str = "a",
                               attribute_name: str = "href") -> list[str]:
    """
    Extracts all district links from the given page content.

    :param page: A BeautifulSoup object representing the parsed HTML page.
    :type page: BeautifulSoup
    :param base_url: The base URL to prepend to relative links.
    :type base_url: str, optional
    :param container_tag: The HTML tag containing the cells with links.
    :type container_tag: str, optional
    :param container_class: The class name of the containers containing
     the links.
    :type container_class: str, optional
    :param link_tag_name: The HTML tag containing the links.
    :type link_tag_name: str, optional
    :param attribute_name: The attribute of the tag containing the link URL.
    :type attribute_name: str, optional
    :return: A list containing all extracted links to district pages.
    :rtype: list[str]
    """
    all_links = []
    for cell in page.find_all(container_tag, class_=container_class):
        link = cell.find(link_tag_name)

        complete_url = collect_url(link, attribute_name, base_url)

        if not complete_url:
            print("WARNING: Failed to obtain complete URL for a link.")
            continue

        all_links.append(complete_url)

    return all_links


def collect_url(link: BeautifulSoup,
                attribute: str,
                base_url: str) -> [str]:
    """
    Collects and completes the URL from the given link and returns a complete
     URL.

    :param link: A BeautifulSoup object representing the link.
    :type link: BeautifulSoup
    :param attribute: The attribute of the tag containing the link URL.
    :type attribute: str
    :param base_url: The base URL to prepend to relative links.
    :type base_url: str
    :return: A complete URL.
    :rtype: str, optional
    """
    if link:
        href = link.get(attribute)
        if href:
            return f"{base_url}{href}"
    return None


def extract_district_data(individual_district_soup: BeautifulSoup,
                          district: str,
                          registered_header: str,
                          envelopes_header: str,
                          valid_header: str,
                          container_tag: str,
                          class_name: str) -> [dict, None]:
    """
    Extracts all relevant data for a district.

    :param individual_district_soup: A BeautifulSoup object representing
     the district HTML content.
    :type individual_district_soup: BeautifulSoup
    :param district: CSS selector for the district name element.
    :type district: str
    :param registered_header: Header name for the "count_registered" column.
    :type registered_header: str
    :param envelopes_header: Header name for the "count_envelopes" column.
    :type envelopes_header: str
    :param valid_header: Header name for the "count_valid" column.
    :type valid_header: str
    :param container_tag: The HTML tag containing the cells with data.
    :type container_tag: str
    :param class_name: Class name of the data cells containing the values
     to be extracted.
    :type class_name: str
    :return: A dictionary containing the district data, or None
    if the district name is not found.
    :rtype: dict
    """
    district_data = {
        "location": "",
        "political_parties_votes": {},
        "count_registered": None,
        "count_envelopes": None,
        "count_valid": None
    }

    district_name = get_district_name(individual_district_soup, district)
    if not district_name:
        return None

    district_data["location"] = district_name
    district_data["political_parties_votes"] = \
        get_votes_of_parties(individual_district_soup)

    headers = {
        "count_registered": registered_header,
        "count_envelopes": envelopes_header,
        "count_valid": valid_header
    }

    extract_headers_data(district_data, individual_district_soup, headers,
                         container_tag, class_name)

    return district_data


def get_district_name(soup: BeautifulSoup,
                      district: str):
    """
    Extracts the district name from the given BeautifulSoup object.

    :param soup: A BeautifulSoup object representing the district HTML content.
    :type soup: BeautifulSoup
    :param district: CSS selector for the district name element.
    :type district: str
    :return: The district name as a string, or None if not found.
    :rtype: str or None
    """
    district_name_element = soup.select_one(district)
    if district_name_element:
        return district_name_element.text.strip().split(":")[1]
    return None


def extract_headers_data(district_data: dict,
                         soup: BeautifulSoup,
                         headers: dict,
                         container_tag: str,
                         class_name: str):
    """
    Extracts data based on specified headers and updates the district
     data dictionary.

    :param district_data: The dictionary to update with extracted data.
    :type district_data: dict
    :param soup: A BeautifulSoup object representing the district HTML content.
    :type soup: BeautifulSoup
    :param headers: A dictionary mapping data keys to their respective header
     names.
    :type headers: dict
    :param container_tag: The HTML tag containing the cells with data.
    :type container_tag: str
    :param class_name: Class name of the data cells containing the values to be
     extracted.
     :type class_name: str
    """
    for key, header in headers.items():
        try:
            cell = soup.find(container_tag, class_=class_name, headers=header)
            if cell:
                district_data[key] = int(clean_data(cell.text))
            else:
                print(f"WARNING: Data cell not found for header {header}"
                      f" in district {district_data['location']}")
        except (AttributeError, ValueError, KeyError) as error:
            print(f"ERROR: An error occurred while extracting data for header"
                  f" '{header}': {error}")


def extract_all_districts_data(soup: BeautifulSoup,
                               class_name: str = "cislo",
                               district: str = 'h3:-soup-contains("Obec:")',
                               registered_header: str = "sa2",
                               envelopes_header: str = "sa3",
                               valid_header: str = "sa6",
                               container_tag: str = "td") -> dict:
    """
    Extracts data from HTML content related to votes in each district.

    :param soup: A parsed BeautifulSoup object representing the HTML content.
    :type soup: BeautifulSoup
    :param class_name: Class name of the data cells containing the values
     to be extracted.
    :type class_name: str, optional, defaults to "cislo"
    :param district: CSS selector for the district name element.
    :type district: str, optional, defaults to 'h3:-soup-contains("Obec:")'
    :param registered_header: Header name for the "count_registered" column.
    :type registered_header: str, optional, defaults to "sa2"
    :param envelopes_header: Header name for the "count_envelopes" column.
    :type envelopes_header: str, optional, defaults to "sa3"
    :param valid_header: Header name for the "count_valid" column.
    :type valid_header: str, optional, defaults to "sa6"
    :param container_tag: The HTML tag containing the cells with data.
    :type container_tag: str, optional, defaults to "td"
    :return: A dictionary containing the extracted data.
        - code (str): The code representing the district.
        - location (str): The name of the district.
        - political_parties_votes (dict): Votes for each political party
         in the district.
        - count_registered (int): The number of registered voters
         in the district.
        - count_envelopes (int): The number of envelopes received
         in the district.
        - count_valid (int): The number of valid votes in the district.
    :rtype: dict
    """

    links = extract_all_district_links(soup)
    all_district_data = {}

    for district_link in tqdm(links,
                              desc="Scraping districts informations",
                              ncols=100, colour="#03A062",
                              bar_format='{desc}: {percentage:3.0f}% |{bar}|'
                                         ' {n_fmt}/{total_fmt} [{remaining}]'
                              ):
        try:
            individual_district_soup = get_soup(district_link)
            code = get_code_from_url(district_link)
            if code is None:
                print(f"ERROR: District code not found for link:"
                      f" {district_link}")
                continue

            district_data = extract_district_data(individual_district_soup,
                                                  district,
                                                  registered_header,
                                                  envelopes_header,
                                                  valid_header,
                                                  container_tag,
                                                  class_name)
            if district_data:
                all_district_data[code] = district_data

        except Exception as error:
            print(f"Error: An exception occurred for district"
                  f" {district_link}: {error}")

    return all_district_data


def get_code_from_url(url: str,
                      parameter_name: str = "xobec") -> str:
    """
    Extracts the code of village from a URL query string.

    :param url: The string containing the URL query string.
    :type url: str
    :param parameter_name: The name of the parameter in the query string from
     which to extract the code.
    :type parameter_name: str, optional
    :return: The extracted code (xobec value) or None if not found.
    :rtype: str
    """
    try:
        # Parse the URL using urllib.parse
        url_parts = urlparse(url)
        query_dict = parse_qs(url_parts.query)

        return query_dict.get(parameter_name, [None])[0]

    except ValueError as parsing_error:
        # Handle potential parsing errors
        raise ValueError(f"ERROR parsing URL or parameter_name not found:"
                         f" {parsing_error}")


def get_votes_of_parties(page: BeautifulSoup,
                         party_name_class: str = "overflow_name",
                         votes_class: str = "cislo",
                         headers: list[str] = ("t1sa2 t1sb3", "t2sa2 t2sb3"),
                         container_tag: str = "td") -> [dict, None]:
    """
    Extracts the votes count for each political party from the given
     page content.

    :param page: An object representing the parsed HTML content.
    :type page: BeautifulSoup
    :param party_name_class: The class name of elements containing political
     party names.
    :type party_name_class: str, optional
    :param votes_class: The class name of elements containing votes count.
    :type votes_class: str, optional
    :param headers: A list of header values used to filter votes count elements.
    :type headers: list[str], optional
    :param container_tag: The HTML tag containing the cells with data.
    :type container_tag: str, optional
    :return: A dictionary containing the votes count for each political party.
    If no data is found, returns None.
    :rtype: dict or None
    """
    political_parties = page.find_all(container_tag, class_=party_name_class)
    if not political_parties:
        return None

    try:
        party_names = [party.text.strip() for party in political_parties]

    except Exception as error:
        print(f"ERROR occurred while extracting votes of parties: {error}")
        return {}

    else:
        political_parties_votes = page.find_all(container_tag,
                                                class_=votes_class,
                                                headers=headers)
        votes_count = [int(clean_data(votes.get_text().strip()))
                       for votes in political_parties_votes]

        return dict(zip(party_names, votes_count))


def clean_data(text: str,
               char_to_remove: str = "\xa0") -> str:
    """
    Removes the non-breaking space character (xa0) from the text.

    :param text: The input text.
    :type text: str
    :param char_to_remove: The character to be removed from the text.
    :type char_to_remove: str, optional
    :return: The text without the specified character.
    :rtype: str
    """
    return text.replace(char_to_remove, "")


def get_csv(data: dict, filename: str) -> None:
    """
    Converts a dictionary containing election data to a CSV file.

    :param data: Dictionary where keys are district codes and values are
     dictionaries with election data.
        Election data includes information like 'location',
         'count_registered' (number of registered voters),
        'count_envelopes' (number of envelopes issued),
         'count_valid' (number of valid votes),
        and 'political_parties_votes' (nested dictionary with number of votes
         for each party).
    :type data: dict
    :param filename: The name of the CSV file to be created.
    :type filename: str
    :return: None
    """
    # Create DataFrame from dictionary
    df = pd.DataFrame.from_dict(data, orient='index')

    # Reorder the columns in the DataFrame
    df = df[['location', 'count_registered', 'count_envelopes', 'count_valid',
             'political_parties_votes']]

    # Unnesting the `political_parties_votes` dictionary into separate columns:
    # 1. Drop the original `political_parties_votes` column.
    # 2. Apply `pd.Series` to each row of the `political_parties_votes` column:
    # -Split the dictionary into party names (columns) and vote counts (values).
    df = pd.concat([df.drop(['political_parties_votes'], axis=1),
                    df['political_parties_votes'].apply(pd.Series)],
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
    print(f"CSV FILE SUCCESSFULLY CREATED: '{file_path}'")

    # Debug: Print preview of the CSV file
    # print(f"\nPreview of CSV file '{filename}':")
    # with open(file_path, 'r', encoding='utf-8') as file:
    #     for row in range(5):
    #         print(file.readline().strip())


def plot_top_10_parties(data: dict,
                        filename: str) -> None:
    """
    Plots a bar chart showing the top 10 political parties based on the total
     number of votes.

    :param data: A dictionary containing data for each electoral district,
     including political party votes.
    :type data: dict
    :param filename: Name of the file to save the plot, typically includes
     the district name.
    :type filename: str
    :return: None
    """
    # Sum up the votes for each political party
    party_votes = {}
    for district in data.values():
        for party, votes in district["political_parties_votes"].items():
            party_votes[party] = party_votes.get(party, 0) + votes

    # Select the top 10 parties based on the total number of votes
    top_10_parties = dict(sorted(party_votes.items(),
                                 key=lambda item: item[1],
                                 reverse=True)[:10])

    # Set up the figure with a larger size
    plt.figure(figsize=(30, 20))  # width=30 inches, height=20 inches

    # Create a bar chart
    # Plotting the bar chart
    plt.bar(list(top_10_parties.keys()), list(top_10_parties.values()))
    # Rotating x-axis labels for better readability
    plt.xticks(rotation=25, fontsize=15)
    # Setting font size for y-axis labels
    plt.yticks(fontsize=15)
    # Labeling y-axis
    plt.ylabel("Total Number of Votes", fontsize=25)
    # Adding title to the plot
    plt.title("Top 10 Political Parties by Number of Votes", fontsize=25)

    # Define the file path
    plot_filename = add_extension("Top_10_Parties_of_" +
                                  os.path.splitext(filename)[0], "png")
    file_path = os.path.join("Results", plot_filename)

    # Save the plot to a file
    plt.savefig(file_path)
    plt.close()
    print(f"BAR PLOT SUCCESSFULLY CREATED: '{file_path}'")


def add_extension(filename: str,
                  extension: str) -> str:
    """
    Adds extension to the filename.

    :param filename: The filename to which the extension will be added.
    :type filename: str
    :param extension: The extension to be added to the filename.
    :type extension: str
    :return: The filename with the added extension.
    :rtype: str
    """
    if filename.endswith(f".{extension}"):
        return filename
    else:
        return f"{filename}.{extension}"


def elections_scraper(url, filename):
    print(f"DOWNLOADING DATA FROM THE SELECTED URL: '{url}'")
    soup = get_soup(url)
    dict_of_data = extract_all_districts_data(soup)
    # pprint(dict_of_data)  # Debug: show dict of scrapped data
    get_csv(dict_of_data, filename)
    plot_top_10_parties(dict_of_data, filename)
    print(f"PROCESS SUCCESSFULLY FINISHED")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage:\n$ python election_scraper.py <district_url> <filename>")
        sys.exit(1)

    territorial_url = sys.argv[1]
    territorial_filename = sys.argv[2]

    elections_scraper(territorial_url, territorial_filename)

    # # Create argument parser
    # parser = argparse.ArgumentParser(
    #     description="Scrape election data for a district.")
    # parser.add_argument("url",
    #                     help="The complete URL of the webpage containing"
    #                          " election data for a specific district.",
    #                     metavar="\"url\"")
    # parser.add_argument("filename",
    #                     help="The name of the files to be created."
    #                          " It's recommended to enter the name of"
    #                          " the district. "
    #                          "The file extension (.csv for CSV file,"
    #                          " .png for plot) "
    #                          "will be automatically added by the script.")
    # # Parse arguments
    # args = parser.parse_args()
