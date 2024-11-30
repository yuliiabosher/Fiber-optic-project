from string import Template
import argparse
import sys
import logging
from typing import List
import folium

logging.basicConfig(level=logging.INFO)

try:
    from search_europe import *
except ModuleNotFoundError:
    logging.error("This file must be ran from the same folder as search_europe.py")
    sys.exit(0)

parser = argparse.ArgumentParser(
    description="Download json data for a specific place or country"
)

parser.add_argument(
    "--api_key",
    required=True,
    help="An api_key (only 1 can be used at a time)",
)

parser.add_argument(
    "--place",
    required=True,
    help="City or Country to be searched.",
)

parser.add_argument(
    "--tags",
    required=False,
    help="Tags to be searched, default is `man_made=street_cabinet` , multiple tags should be separated with a comma.",
    default="man_made=street_cabinet",
)

parser.add_argument(
    "--file",
    required=True,
    help="file name to save json data as",
    default="$data.json",
)

parser.add_argument(
    "--map_name",
    required=False,
    help="Name of map file that shows search coverage. Default `cabinets.html`",
    default="cabinets.html",
)


def main(api_key: List, place: str, tags: str, file: str, map_name: str) -> None:
    tags = tags.split(",")
    if len(tags) == 1:
        tags = tags[0]

    logging.info("Searching for tags %s" % tags)
    logging.info("Using Api Key %s" % api_key)
    logging.info("\n\nSearching for %s" % place)
    # Get countries coordinates
    min_lon, max_lon, min_lat, max_lat = get_coords(place)
    logging.info(
        "Using bbox %s, %s, %s, %s for %s" % (min_lon, min_lat, max_lon, max_lat, place)
    )
    mean_lat = (min_lat + max_lat) / 2
    mean_lon = (min_lon + max_lon) / 2

    m = folium.Map(
        location=[mean_lat, mean_lon],
        tiles="Cartodb Positron",
        zoom_start=10,
    )

    logging.info("Instantiated Map, centered on %s" % place)
    logging.info(
        "Splitting place into two boxes just in case it is too big, splitting bbox horizontally"
    )
    top_box, bottom_box, median_coords = split_box(min_lon, min_lat, max_lon, max_lat)

    tbox_min_lon, tbox_min_lat, tbox_max_lon, tbox_max_lat = top_box
    bbox_min_lon, bbox_min_lat, bbox_max_lon, bbox_max_lat = bottom_box

    logging.info("Searching for %s for %s" % (tags, place))
    tbox_json_data, tbox_errors = download_geojson(
        place, tbox_min_lon, tbox_min_lat, tbox_max_lon, tbox_max_lat, tags, api_key
    )
    if tbox_json_data and not tbox_errors:
        logging.info("Downloading Bottom box for %s" % place)
        bbox_json_data, errors = download_geojson(
            place,
            bbox_min_lon,
            bbox_min_lat,
            bbox_max_lon,
            bbox_max_lat,
            tags,
            api_key,
        )
        if not errors:
            tbox_json_data["features"].append(bbox_json_data["features"])
            logging.info("Retrieved Bottom box, joining data for both boxes")
            write_to_file(file, tbox_json_data)
        else:
            logging.info("Could not retrieve Bottom box, writing out data for top box")
            write_to_file(file, tbox_json_data)
    else:
        logging.error("Error: %s with Top box for %s" % (tbox_errors, place))
        logging.info(
            "Coordinates of Top Box for %s (%s,%s,%s,%s)"
            % (place, tbox_min_lon, tbox_max_lon, tbox_min_lat, tbox_max_lat)
        )
        sys.exit(0)
    if not errors:
        logging.info("Wrote search results for %s to file %s" % (place, file))
        top_box, bottom_box, median_coords = split_box(
            min_lon, min_lat, max_lon, max_lat
        )
        draw_box(*top_box, m)
        draw_box(*bottom_box, m)
        folium.PolyLine(
            locations=[median_coords], color="green", weight=3, opacity=1
        ).add_to(m)
        logging.info("Plotted box around %s to show search area" % place)
        logging.info("Drew line through the middle to show how the box was split")

        m.save(map_name)
        logging.info("Created map %s" % map_name)


if __name__ == "__main__":
    args = vars(parser.parse_args())
    main(**args)
