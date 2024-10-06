import geopy
import folium
import json
import collections
import requests
import shapely
from typing import Optional, List, Tuple, Dict
from country_list import countries_for_language
from countrygroups import EUROPEAN_UNION
from string import Template
import argparse
import sys
import logging
import os

parser = argparse.ArgumentParser(
    description="Download json data for the UK and European countries using OpenStreetMap Tags"
)

parser.add_argument(
    "--api_keys",
    required=True,
    help="A list of API Keys separated by a comma, minimum (2)",
)

parser.add_argument(
    "--tags",
    required=False,
    help="Tags to be searched, default is `man_made=street_cabinet` , multiple tags should be separated with a comma.",
    default="man_made=street_cabinet",
)

parser.add_argument(
    "--file_format",
    required=False,
    help="Format for files to saved. Default is `${country}_cabinets.json (must have ${country} in name",
    default="${country}_cabinets.json",
)

parser.add_argument(
    "--map_name",
    required=False,
    help="Name of map file that shows search coverage. Default `cabinets.html`",
    default="cabinets.html",
)

logging.basicConfig(level=logging.INFO)
# file which hold country coordinates
# Country Code, Country Name, Longitude, Latitude
# "GB": ["United Kingdom", [-7.57, 49.96, 1.68, 58.64]],
if not os.path.exists("bbox.json"):
    logging.error("This script should be in the same folder as bbox.json")
country_bboxes = json.load(open("bbox.json"))

# countries_for_languages returns a dictionary with
# Country Abbrivation: Country Name, here we are reversing it to {country_name: country_abbrivtion}
countries = {v: k for k, v in dict(countries_for_language("en")).items()}

app = geopy.Nominatim(user_agent="app")


def download_geojson(
    country: str,
    min_lon: float,
    min_lat: float,
    max_lon: float,
    max_lat: float,
    tags: str,
    api_keys: List,
) -> Tuple[Dict, Optional[str]]:
    """rotate api_keys and get data"""
    try:
        api_keys.rotate()
        api_key = api_keys[0]
        logging.info("Using Api Key %s" % api_key)
        params = {
            "tags": tags,
            "api_key": api_key,
            "bbox": f"{min_lon},{min_lat},{max_lon},{max_lat}",
        }

        response = requests.get(
            "https://osm.buntinglabs.com/v1/osm/extract", params=params
        )
        assert "features" in response.json()
    except Exception as e:
        return dict(), e
    return response.json(), None


def write_to_file(file: str, json_data: Dict) -> bool:
    """Write json to file"""
    with open(file, "w") as f:
        f.write(json.dumps(json_data))
    return True


def split_box(
    min_lon: float, min_lat: float, max_lon: float, max_lat: float
) -> Tuple[Tuple[float], Tuple[float]]:
    """Split large countries into two boxes"""
    # find mean cordinates
    # Mean longitude will be halfway accross the box (horizontal)
    # Mean latitude will be halfway down the box (vertical)
    mean_lon = (min_lon + max_lon) / 2
    mean_lat = (min_lat + max_lat) / 2

    median_coords = (mean_lat, min_lon), (mean_lat, max_lon)

    # Therefore the top box should be from the top rleft hand corner to the top right hand corner
    # Then from the top of the box half way down on each  side
    top_box = min_lon, min_lat, max_lon, mean_lat
    # The top of the bottom box should be the bottom of the top box
    # To the bottom of the full box
    bottom_box = min_lon, mean_lat, max_lon, max_lat
    return top_box, bottom_box, median_coords


def get_coords(country: str) -> Tuple[float]:
    try:
        min_lon, min_lat, max_lon, max_lat = country_bboxes[countries[country]][1]
    except KeyError:
        query = app.geocode(country)
        min_lat, max_lat, min_lon, max_lon = [
            float(coord) for coord in query.raw["boundingbox"]
        ]
    return min_lon, max_lon, min_lat, max_lat


def draw_box(
    min_lon: float, min_lat: float, max_lon: float, max_lat: float, m=folium.Map
) -> bool:
    folium.GeoJson(shapely.box(min_lon, min_lat, max_lon, max_lat)).add_to(m)
    return True


def draw_errors(
    country,
    min_lon: float,
    min_lat: float,
    max_lon: float,
    max_lat: float,
    m=folium.Map,
) -> bool:
    # If there are errors lets drop a marker
    mean_lon = (float(min_lon) + float(max_lon)) / 2
    mean_lat = (float(min_lat) + float(max_lat)) / 2
    folium.Marker(location=(mean_lon, mean_lat), popup=country).add_to(m)
    return True


def main(api_keys: List, tags: str, file_format: str, map_name: str) -> None:

    try:
        api_keys = api_keys.split(",")
        assert len(api_keys) >= 2
        logging.info("using API Keys %s" % api_keys)
    except AssertionError:
        logging.error("To Download GeoJson for Europe, 2 or more API Keys are needed")
        sys.exit(0)
    api_keys = collections.deque(api_keys)

    tags = tags.split(",")
    if len(tags) == 1:
        tags = tags[0]

    logging.info("Searching for tags %s" % tags)

    file = Template(file_format)
    eu_countries = EUROPEAN_UNION.names
    eu_countries.append("United Kingdom")  # Lets add the UK to the list

    # Get Coordinates for Euope
    eu_bbox = [float(coord) for coord in app.geocode("europe").raw["boundingbox"]]

    # Unpack EU coordinates and workout the mean so we can center the map around Europe
    min_lon, max_lon, min_lat, max_lat = eu_bbox
    mean_lat = (min_lat + max_lat) / 2
    mean_lon = (min_lon + max_lon) / 2

    m = folium.Map(
        location=[mean_lon, mean_lat],
        tiles="Cartodb Positron",
        zoom_start=5,
    )
    logging.info("Instantiated Map, centered on Europe")
    # Some Large Countries Fail to Download, Lets note them so we can work around this
    large_countries = ["Germany", "Italy", "Latvia", "Poland", "France", "Netherlands"]

    for country in eu_countries:
        logging.info("\n\nSearching for %s" % country)
        # Get countries coordinates
        min_lon, max_lon, min_lat, max_lat = get_coords(country)
        logging.info(
            "Using bbox %s, %s, %s, %s for %s"
            % (min_lon, min_lat, max_lon, max_lat, country)
        )
        if country in large_countries:
            logging.info("Country is too big, splitting bbox horizontally")
            # if this is a large country lets split it into two bboxes and find the center line
            top_box, bottom_box, median_coords = split_box(
                min_lon, min_lat, max_lon, max_lat
            )

            # unpacking coordinates
            tbox_min_lon, tbox_min_lat, tbox_max_lon, tbox_max_lat = top_box
            bbox_min_lon, bbox_min_lat, bbox_max_lon, bbox_max_lat = bottom_box

            # results for the top box
            logging.info("Searching for %s for %s" % (tags, country))
            tbox_json_data, tbox_errors = download_geojson(
                country,
                tbox_min_lon,
                tbox_min_lat,
                tbox_max_lon,
                tbox_max_lat,
                tags,
                api_keys,
            )
            # if there are no errors with downloading the top box lets do the bottom box
            if tbox_json_data and not tbox_errors:
                logging.info("Downloading Bottom box for %s" % country)
                bbox_json_data, errors = download_geojson(
                    country,
                    bbox_min_lon,
                    bbox_min_lat,
                    bbox_max_lon,
                    bbox_max_lat,
                    tags,
                    api_keys,
                )
                # lets concatenate the json data from the top box and bottom box and write it out
                if not errors:
                    tbox_json_data["features"].append(bbox_json_data["features"])
                    logging.info("Retrieved Bottom box, joining data for both boxes")
                    write_to_file(file.substitute(country=country), tbox_json_data)
            else:
                logging.error("Error: %s with Top box for %s" % (tbox_errors, country))
                logging.info(
                    "Coordinates of Top Box for %s (%s,%s,%s,%s)"
                    % (country, tbox_min_lon, tbox_max_lon, tbox_min_lat, tbox_max_lat)
                )

        else:
            logging.info("Searching for %s for %s" % (tags, country))
            # if it is not a large country just download the whole bbox and write it out
            json_data, errors = download_geojson(
                country, min_lon, min_lat, max_lon, max_lat, tags, api_keys
            )
            write_to_file(file.substitute(country=country), json_data)

        if not errors:
            logging.info(
                "Wrote search results for %s to file %s"
                % (country, file.substitute(country=country))
            )
            # Lets display the areas we searched on a map
            if country in large_countries:
                # if it is a large country, display both boxes and draw a central line showing the split
                top_box, bottom_box, median_coords = split_box(
                    min_lon, min_lat, max_lon, max_lat
                )
                draw_box(*top_box, m)
                draw_box(*bottom_box, m)
                folium.PolyLine(
                    locations=[median_coords], color="green", weight=3, opacity=1
                ).add_to(m)
                logging.info("Plotted box around %s to show search area" % country)
                logging.info(
                    "Drew line through the middle to show how the box was split"
                )
            else:
                # else just draw the box, no need to draw a line accross the center if we never split it
                logging.info("Plotted box around %s to show search area")
                draw_box(min_lon, min_lat, max_lon, max_lat, m)
        else:
            # if it failed dont draw a box, instead just drop a marker
            draw_errors(country, min_lon, min_lat, max_lon, max_lat, m)
            logging.error("Error Downloading %s" % country)
    m.save(map_name)
    logging.info("Created map %s" % map_name)


if __name__ == "__main__":
    args = vars(parser.parse_args())
    main(**args)
