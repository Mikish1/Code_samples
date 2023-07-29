import html
import json
import os
import requests
from bs4 import BeautifulSoup
import pandas as pd

SERP_FILEPATH = "serp_results/"  # location to save the SERP API results
JSON_DATA_FILEPATH = "json_data/"  # location to save product JSON data
PRODUCT_DATA_FILE = "Sample_product_data.xlsx"  # Name of the Excel file containing product data, including GTIN
PRODUCT_EXCEL_OUTPUT_FILE = "product_data.xlsx"  # Name of the output Excel file containing formatted data.
SEARCH_SERP = True     # Whether to search using the SERP API
SEARCH_PRODUCT_JSON_DATA = True       # Whether to scrape websites for product data and export into json
OUTPUT_EXCEL = True     # Whether to output a formatted Excel file

API_LOGIN = {
    'Authorization': 'Basic bWlraXNoMTIzQGhvdG1haWwuY29tOjExNTRmYmU2NDMwZWUxYTk=',
    'Content-Type': 'application/json'
}


def get_serp_data(keyword: str, api_headers: dict, filepath):
    """
    Creates a json file containing the bulk search results from the SERP API
        :param keyword: Keyword for the API to search for
        :param api_headers: headers containing the API login information
    """
    payload = f"[{{\"keyword\":\"{keyword}\", " \
              "\"location_code\":2840, " \
              "\"language_code\":\"en\", " \
              "\"device\":\"desktop\", " \
              "\"os\":\"windows\"}]"

    # Send a request to the SERP API
    response = requests.request("POST",
                                "https://api.dataforseo.com/v3/serp/google/organic/live/advanced",
                                headers=api_headers,
                                data=payload)
    response.raise_for_status()

    # Dump results into a jason file
    with open(f'{filepath}{keyword}_serp.json', 'w') as data_file:
        json.dump(response.json(), data_file, indent=2)


def get_url_list(file_name: str, max_length=100):
    """
    Returns a list of website urls from an SERP results file
        :param max_length: Maximum amount of urls to be returned
        :param file_name: Name of the JSON file as a string
        :returns: A list of urls for a given product
    """
    with open(file_name, "r") as data_file:
        data = json.load(data_file)
        site_list = data["tasks"][0]["result"][0]["items"]
        url_list = [site["url"] for site in site_list if "url" in site.keys()]
        return url_list[:max_length]


def search_json_ld(json_data, tag: str):
    """
    Helper function for searching through JSON-LD data to find product tags
        :param json_data: Formatted data to be searched through
        :return: Product information if it exists, otherwise None
    """
    if "@graph" in json_data:
        for sub_element in json_data["@graph"]:
            if "@type" in sub_element and f"{tag}" == sub_element["@type"]:
                return sub_element
    elif "@type" in json_data and f"{tag}" == json_data["@type"]:
        return json_data
    else:
        return None


def get_json_ld_data(url: str, tag: str):
    """
    Searches a website for JSON-LD formatted data, returns all product information if it contains any
        :param url: url of the website to search
        :param tag: JSON-LD tag to find information for
        :return: Dictionary containing product information, None if no data exists.
    """

    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                             'AppleWebKit/537.36 (KHTML, like Gecko) '
                             'Chrome/89.0.4389.82 '
                             'Safari/537.36'}

    # Send a request to the desired url
    try:
        response = requests.get(url, headers=headers, timeout=30)
    except (requests.exceptions.SSLError, requests.exceptions.ConnectionError, requests.exceptions.ReadTimeout):
        return None

    # Parse the returned html and search for JSON-LD formatted data
    results = BeautifulSoup(response.text, 'html.parser')
    results = results.find_all("script", type="application/ld+json")

    # Search each element in the data for the desired tag
    if results is not None and len(results) != 0:
        for element in results:
            try:
                element = json.loads(''.join(element.string))
            except (TypeError, json.decoder.JSONDecodeError):
                continue

            # If the current element is a list, parse through the list elements
            if isinstance(element, list):
                for item in element:
                    result = search_json_ld(item, tag)
                    if result is not None and "@type" in result and f"{tag}" == result["@type"]:
                        return result

            # Return None if the tag was not found
            else:
                return search_json_ld(element, tag)
    else:
        return None


def get_meta_tags(url: str):
    """
    Searches for a websites metadata and returns it as a dictionary
        :param url: url of the website to search
        :return: Dictionary containing website metadata if it has any
    """
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                             'AppleWebKit/537.36 (KHTML, like Gecko) '
                             'Chrome/89.0.4389.82 '
                             'Safari/537.36'}
    try:
        response = requests.get(url, headers=headers)
    except requests.exceptions.SSLError:
        return None

    results = BeautifulSoup(response.text, 'html.parser')

    meta_property = results.select("meta[property]")
    properties = {tag["property"]: tag["content"] for tag in meta_property}
    meta_name = results.select("meta[name]")
    names = {tag["name"]: tag["content"] for tag in meta_name if tag.has_attr("content")}

    return {**properties, **names}


def get_website_product_data(url: str, tag: str, keyword_list: list):
    """
    Creates a dictionary from a website's product data using the provided keywords
        :param url: url of the website to search
        :param keyword_list: List of keywords to search for in the JSON data
        :return: A dictionary containing results matching the provided keywords
    """

    result_data = get_json_ld_data(url, tag)
    keyword_dict = {}

    if result_data is not None:
        result_data = flatten(result_data)
        for key in result_data.keys():
            new_keyword = {key: html.unescape(str(result_data[key])) for word in keyword_list if word in key.lower()}
            if new_keyword:
                keyword_dict = {**keyword_dict, **new_keyword}

    return keyword_dict


def create_formatted_product_data(json_filepath, output_filepath):
    # List of html tags that should be ignored
    unwanted_tags = ["offers_priceValidUntil", "image_width", "image_height", "offers_priceSpecification_priceCurrency",
                     "offers_priceSpecification_@type", "offers_priceSpecification_valueAddedTaxIncluded",
                     "alternateName", "image_@type", "category_name", "breadcrumbs_itemListElement_name",
                     "offers_seller_name", "offers_priceSpecification_@context", "image_name", "image_caption",
                     "brand_name", "additionalProperty_name", "manufacturer_name", "offers_availabilityStarts",
                     "offers_availabilityEnds", "offers_priceCurrency", "review_author_name", "Brand_name",
                     "review_name", "review_description", "aggregateRating_reviewCount", "review_@type",
                     "review_reviewRating_@type", "review_reviewRating_ratingValue", "review_author_@type",
                     "review_datePublished", "review_reviewBody", "review", "review_author",
                     "review_reviewRating_worstRating", "review_reviewRating_bestRating"]

    # List of html tages that will be combined into a single column
    reduced_tags = [("image", ["image_url", "image_image", "offers_image", "image_@id", "offers_image_@id",
                               "offers_itemoffered_image", "offers_image_@id"]),
                    ("description", ["offers_description"]),
                    ("price", ["offers_pricespecification_price", "offers_price", "offers_lowprice",
                               "offers_highprice", "offers_pricespecification"]),
                    ("name", ["offers_name"])]

    # Create a dataframe and read in the json files containing item information
    formatted_data = pd.DataFrame(dtype=str)
    for file in os.listdir(json_filepath):
        with open(f"{json_filepath}{file}", "r") as data_file:
            json_data = pd.read_json(data_file, orient="index")

        # Set the first column to be the items GTIN
        gtin = file.split('_')[0]
        gtin = gtin.split('.')[0]
        json_data = json_data.reset_index()
        json_data.insert(0, "GTIN", gtin)

        # Remove the columns that contain unwanted tags
        for tag in unwanted_tags:
            if tag in json_data.columns.tolist():
                json_data.drop(tag, inplace=True, axis=1)

        # Search the columns for tags in the reduced tags list, combine columns and remove the old one.
        for tag, alternate in reduced_tags:
            for column in json_data.columns.tolist():
                if tag in column.lower() and column.lower() in alternate and tag in json_data.columns.tolist():
                    json_data[tag] = json_data[tag].combine_first(json_data[column])
                    json_data.drop(column, inplace=True, axis=1)

                elif tag in column.lower() and column.lower() in alternate:
                    if tag not in json_data.columns.tolist():
                        json_data = json_data.assign(**{tag: json_data[column]})
                    else:
                        json_data[tag] = json_data[tag].combine_first(json_data[column])

                    json_data.drop(column, inplace=True, axis=1)

        formatted_data = pd.concat([formatted_data, json_data], axis=0)

    formatted_data["MPN"] = formatted_data["offers_mpn"].combine_first(formatted_data["mpn"])
    formatted_data = formatted_data.rename(columns={"index": "URL",
                                                    "offers_availability": "availability"})

    formatted_data = formatted_data.reset_index()
    formatted_data.drop(["mpn", "offers_mpn", "index"], inplace=True, axis=1)

    # Send the formatted data to an Excel file
    formatted_data.to_excel(output_filepath)


def flatten(dictionary: dict):
    """
    Flattens a dictionary with multiple nested dictionaries or lists
        :param dictionary: The dictionary to be flattened
        :returns: A flattened dictionary with all data on a single level
    """
    out = {}
    for key, val in dictionary.items():
        if isinstance(val, dict):
            val = [val]
        if isinstance(val, list):
            for subdict in val:
                try:
                    deeper = flatten(subdict).items()
                    out.update({f"{key}_{key2}": val2 for key2, val2 in deeper})
                except AttributeError:
                    continue
        else:
            out[key] = val
    return out


# Usage
keywords = ["image", "mpn", "name", "description", "availability", "price"]

# Read the product Excel file
product_data = pd.read_excel(PRODUCT_DATA_FILE, dtype=str)

# Get all the product barcodes
product_barcode_list = product_data.dropna(subset=["Variant Barcode"])["Variant Barcode"].tolist()

# Use the SERP API to get the top results for each barcode, only needs to be done once for each item
if SEARCH_SERP:
    for barcode in product_barcode_list:
        print(barcode)
        get_serp_data(barcode, API_LOGIN, SERP_FILEPATH)

print(f"{len(product_barcode_list)} GTIN numbers found")

# Get JSON data for each barcode in the list, only needs to be done once for each item
if SEARCH_PRODUCT_JSON_DATA:
    for barcode in product_barcode_list[:5]:
        print(barcode)
        products = {}
        for product_url in get_url_list(f"{SERP_FILEPATH}{barcode}_serp.json"):
            response_data = get_website_product_data(product_url, "Product", keywords)
            if response_data:
                products[product_url] = response_data

        with open(f'{JSON_DATA_FILEPATH}{barcode}.json', 'w') as product_data_file:
            json.dump(products, product_data_file, indent=2)

# Create a formatted Excel containing all the GTIN information from the JSON files.
if OUTPUT_EXCEL:
    create_formatted_product_data(JSON_DATA_FILEPATH, PRODUCT_EXCEL_OUTPUT_FILE)
