import base64
import csv
import datetime
import hashlib
import json
import logging
import os
import time
import xml.etree.ElementTree as ElementTree
from xml.dom import minidom

from utils import config_utils

logger = logging.getLogger("Utils")


def generate_event(title, content, content_paragraphs_list, source, created_datetime, probable_event_date_list, country, lat, lng, category_list, author_list,
                   hit_list=None):
    event = {
        "title": title,
        "content": content,
        "source": source,
        "content_paragraphs": content_paragraphs_list,
        "created_datetime": created_datetime,
        "probable_event_dates" : probable_event_date_list,
        "country": country,
        "lat": lat,
        "lng": lng,
        "categories": category_list,
        "authors": author_list,
        "hit_list": hit_list
    }
    return event


def get_xml_tree(list_of_events):
    logger.info("GENERATING TREE ...")
    config = config_utils.get_app_config()

    root_element = ElementTree.Element('ns2:opsdashboard')
    root_element.set("xmlns:ns2", "http://www.asd.qwe.rt/sdf")

    routing_info = ElementTree.SubElement(root_element, 'routinginfo')
    sender = ElementTree.SubElement(routing_info, 'sender')
    sender.text = 'OA_FS_SENDER'

    recipient = ElementTree.SubElement(routing_info, 'recipient')
    recipient.text = 'FN_FS_Receiver_1'

    priority = ElementTree.SubElement(routing_info, 'priority')
    priority.text = 'normal'

    template = ElementTree.SubElement(routing_info, 'template')
    template.text = 'Events.xsd'

    # checksum = ET.SubElement(root_element, 'checksum')

    ts = time.time()
    created_datetime = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')
    timestamp = ElementTree.SubElement(root_element, 'timestamp')
    timestamp.text = created_datetime

    count = ElementTree.SubElement(root_element, 'count')
    count.text = str(len(list_of_events))

    keywords = ElementTree.SubElement(root_element, 'keywords')
    keyword = ElementTree.SubElement(keywords, 'keyword')
    keyword.text = '*'

    events = ElementTree.SubElement(root_element, 'events')
    for event_object in list_of_events:
        event_node = ElementTree.SubElement(events, 'event')

        title = ElementTree.SubElement(event_node, 'title')
        title.text = event_object["title"]

        the_content = " "
        if len(event_object["content"]) > 0:
            the_content = event_object["content"]
        content = ElementTree.SubElement(event_node, 'content')
        content.text = the_content

        if event_object["content_paragraphs"] is not None:
            keywords_of_event = ElementTree.SubElement(event_node, 'content_paragraphs')
            for paragraph in event_object["content_paragraphs"]:
                keyword_of_event = ElementTree.SubElement(keywords_of_event, 'paragraph')
                keyword_of_event.text = paragraph

        if event_object["hit_list"] is not None:
            keywords_of_event = ElementTree.SubElement(event_node, 'keywords')
            for word in event_object["hit_list"]:
                keyword_of_event = ElementTree.SubElement(keywords_of_event, 'keyword')
                keyword_of_event.text = word

        if event_object["probable_event_dates"] is not None:
            keywords_of_event = ElementTree.SubElement(event_node, 'probable_event_dates')
            for word in event_object["probable_event_dates"]:
                keyword_of_event = ElementTree.SubElement(keywords_of_event, 'probable_event_date')
                keyword_of_event.text = word

        country = ElementTree.SubElement(event_node, 'country')
        country.text = event_object["country"]

        lat = ElementTree.SubElement(event_node, 'lat')
        lat.text = event_object["lat"]

        lng = ElementTree.SubElement(event_node, 'lng')
        lng.text = event_object["lng"]

        source = ElementTree.SubElement(event_node, 'source')
        source.text = event_object["source"]
        created_datetime = ElementTree.SubElement(event_node, 'created_datetime')
        created_datetime.text = event_object["created_datetime"]

        categories = ElementTree.SubElement(event_node, 'categories')
        for category_object in event_object["categories"]:
            category_node = ElementTree.SubElement(categories, 'category')
            category_node.text = category_object["category"]

        authors = ElementTree.SubElement(event_node, 'authors')
        for author_object in event_object["authors"]:
            author_node = ElementTree.SubElement(authors, 'author')
            author_node.text = author_object["author"]

    ts = time.time()
    created_datetime = datetime.datetime.fromtimestamp(ts).strftime('%Y_%m_%d_%H%M%S')

    xml_str = minidom.parseString(ElementTree.tostring(root_element)).toprettyxml()
    with open(config["app"]["xml_directory"] + os.sep + created_datetime + "_for_ib.xml", "wb") as f:
        f.write(xml_str.encode('utf-8'))

    logger.info("DONE: GENERATING TREE ...")


def get_json(list_of_events):
    logger.info("Generating Elasticsearch JSON for bulk indexing...")

    es_json_list = list()

    ts = time.time()
    config = config_utils.get_app_config()
    index_name = config["elasticsearch"]["events_index_name"]
    created_datetime = datetime.datetime.fromtimestamp(ts).strftime('%Y_%m_%d_%H%M%S')
    filename = config["app"]["json_directory"] + os.sep + created_datetime + "_for_es.json"
    ib_filename = config["app"]["ib_directory"] + os.sep + created_datetime + "_for_ib.csv"

    logger.info(filename)
    logger.info(ib_filename)  # csv file to carry the json across the ib

    for event_object in list_of_events:

        categories = list()
        for c in event_object["categories"]:
            categories.append(c["category"])

        if event_object["hit_list"] is not None:
            for c in event_object["hit_list"]:
                categories.append(c)

        lng_lat = [event_object["lng"], event_object[
            "lat"]]  # each event should hold only 1 location, create multiple events if the same event is held at
        # other places at the same time

        countries_list = list()
        countries_list.append(event_object["country"])

        new_event_object = {
            "created_date_time": event_object["created_datetime"],
            "location": lng_lat,
            "source": event_object["source"],
            "probable_event_dates": event_object["probable_event_dates"],
            "categories": categories,
            "countries": countries_list,
            "title": event_object["title"],
            "content": event_object["content"],
            "content_paragraphs": event_object["content_paragraphs"],
            "authors": event_object["authors"]
        }
        es_json_list.append(new_event_object)

        # By default json is the output
        with open(filename, 'a') as outfile:
            json.dump({"index": {"_index": index_name, "_type": "_doc", "_id": generate_id(event_object["title"])}},
                      outfile)
            outfile.write("\n")
            json.dump(new_event_object, outfile)
            outfile.write("\n\n")

        with open(ib_filename, 'a') as the_base64_file:
            with open(filename) as the_file:
                encoded = base64.b64encode(the_file.read().encode('utf-8'))
                the_base64_file.write(encoded.decode('utf-8'))

    logger.info("Completed generating Elasticsearch JSON for bulk indexing")


def generate_id(text):
    """
    always generate the same id from text string
    :param text: string to hash
    :return: unique id
    """
    hash_object = hashlib.sha256(text.encode())
    hex_dig = hash_object.hexdigest()
    return hex_dig


# TODO to deprecate
class EventsParser(object):
    """
    THIS GENERATES MACHINE-READABLE CSV, NOT BASE64 CSV!
    """

    @staticmethod
    def get_csv(list_of_events):

        logger.info("GENERATING CSV...")

        ts = time.time()
        created_datetime = datetime.datetime.fromtimestamp(ts).strftime('%Y%m%d%H%M')
        with open('config/app.json') as json_config_file:
            config = json.load(json_config_file)

        filename = config["app"]["xml_directory"] + "\\" + created_datetime + "_friendly.csv"

        with open(filename, 'a') as outfile:
            fieldnames = ["created_date_time", "location", "source", "categories", "countries", "title", "content",
                          "authors"]
            writer = csv.DictWriter(outfile, fieldnames=fieldnames)
            writer.writeheader()

        for event_object in list_of_events:

            categories = list()
            for c in event_object["categories"]:
                categories.append(c["category"])

            for w in event_object["hit_list"]:
                categories.append(w)

            latlng = [event_object["lat"], event_object["lng"]]

            new_event_object = {"created_date_time": event_object["created_datetime"], "location": latlng,
                                "source": event_object["source"],
                                "categories": categories, "countries": event_object["country"],
                                "title": event_object["title"].encode('utf8'),
                                "content": event_object["content"].encode('utf8'),
                                "authors": ["OPEN-SOURCE INTERNET"]}

            with open(filename, 'a') as outfile:
                fieldnames = ["created_date_time", "location", "source", "categories", "countries", "title", "content",
                              "authors"]
                writer = csv.DictWriter(outfile, fieldnames=fieldnames)
                writer.writerow(new_event_object)

        logger.info("DONE: GENERATING CSV...")
