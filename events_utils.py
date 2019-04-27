import base64
import csv
import datetime
import json
import time
import xml.etree.ElementTree as ET
import os

from numpy.core import unicode


class EventsParser(object):

    @staticmethod
    def generate_events(title, content, source, created_datetime, country, lat, lng, category_list, author_list,
                        hit_list=None):
        event = {"title": title, "content": content, "source": source,
                 "created_datetime": created_datetime, "country": country, "lat": lat, "lng": lng,
                 "categories": category_list,
                 "authors": author_list, "hit_list": hit_list}
        return event

    def indent(self, elem, level=0):
        i = "\n" + level * "  "
        if len(elem):
            if not elem.text or not elem.text.strip():
                elem.text = i + "  "
            if not elem.tail or not elem.tail.strip():
                elem.tail = i
            for elem in elem:
                self.indent(elem, level + 1)
            if not elem.tail or not elem.tail.strip():
                elem.tail = i
        else:
            if level and (not elem.tail or not elem.tail.strip()):
                elem.tail = i

    def get_tree(self, list_of_events):

        print("GENERATING TREE...")

        root_element = ET.Element('ns2:opsdashboard')
        root_element.set("xmlns:ns2", "http://www.asd.qwe.rt/sdf")

        routing_info = ET.SubElement(root_element, 'routinginfo')
        sender = ET.SubElement(routing_info, 'sender')
        sender.text = 'OA_FS_SENDER'

        recipient = ET.SubElement(routing_info, 'recipient')
        recipient.text = 'FN_FS_Receiver_1'

        priority = ET.SubElement(routing_info, 'priority')
        priority.text = 'normal'

        template = ET.SubElement(routing_info, 'template')
        template.text = 'Events.xsd'

        # checksum = ET.SubElement(root_element, 'checksum')

        ts = time.time()
        created_datetime = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')
        timestamp = ET.SubElement(root_element, 'timestamp')
        timestamp.text = created_datetime

        count = ET.SubElement(root_element, 'count')
        count.text = str(len(list_of_events))

        keywords = ET.SubElement(root_element, 'keywords')
        keyword = ET.SubElement(keywords, 'keyword')
        keyword.text = '*'

        events = ET.SubElement(root_element, 'events')
        for event_object in list_of_events:
            event_node = ET.SubElement(events, 'event')

            title = ET.SubElement(event_node, 'title')
            title.text = event_object["title"]

            the_content = " "
            if len(event_object["content"]) > 0:
                the_content = event_object["content"]
            content = ET.SubElement(event_node, 'content')
            content.text = the_content

            if event_object["hit_list"] is not None:
                keywords_of_event = ET.SubElement(event_node, 'keywords')
                for word in event_object["hit_list"]:
                    keyword_of_event = ET.SubElement(keywords_of_event, 'keyword')
                    keyword_of_event.text = word

            country = ET.SubElement(event_node, 'country')
            country.text = event_object["country"]

            lat = ET.SubElement(event_node, 'lat')
            lat.text = event_object["lat"]

            lng = ET.SubElement(event_node, 'lng')
            lng.text = event_object["lng"]

            source = ET.SubElement(event_node, 'source')
            source.text = event_object["source"]
            created_datetime = ET.SubElement(event_node, 'created_datetime')
            created_datetime.text = event_object["created_datetime"]

            categories = ET.SubElement(event_node, 'categories')
            for category_object in event_object["categories"]:
                category_node = ET.SubElement(categories, 'category')
                category_node.text = category_object["category"]

            authors = ET.SubElement(event_node, 'authors')
            for author_object in event_object["authors"]:
                author_node = ET.SubElement(authors, 'author')
                author_node.text = author_object["author"]

        self.indent(root_element)
        tree = ET.ElementTree(root_element)
        # ET.dump(tree)
        ts = time.time()
        created_datetime = datetime.datetime.fromtimestamp(ts).strftime('%Y%m%d%H%M')
        with open('config/app.json') as json_config_file:
            config = json.load(json_config_file)
        tree.write(config["app"]["xml_directory"] + "\\" + created_datetime + "_for_ib.xml", xml_declaration=True,
                   encoding='utf-8', method="html")

        print("DONE: GENERATING TREE...")

    @staticmethod
    def get_json(list_of_events):

        print("GENERATING ELASTICSEARCH JSON...")

        es_json_list = list()

        ts = time.time()
        with open('config/app.json') as json_config_file:
            config = json.load(json_config_file)

        if not os.path.exists(config["app"]["json_directory"]):
            os.makedirs(config["app"]["json_directory"])

        created_datetime = datetime.datetime.fromtimestamp(ts).strftime('%Y%m%d%H%M')
        filename = config["app"]["json_directory"] + "\\" + created_datetime + "_for_es.json"
        ib_filename = config["app"]["ib_directory"] + "\\" + created_datetime + "_for_ib.csv"
        print(filename)
        print(ib_filename)

        for event_object in list_of_events:

            categories = list()
            for c in event_object["categories"]:
                categories.append(c["category"])

            if event_object["hit_list"] is not None:
                for w in event_object["hit_list"]:
                    categories.append(w)

            latlng = [[event_object["lat"], event_object["lng"]]]

            countries_list = list()
            countries_list.append(event_object["country"])

            new_event_object = {"created_date_time": event_object["created_datetime"], "location": latlng,
                                "source": event_object["source"],
                                "categories": categories, "countries": countries_list, "title": event_object["title"],
                                "content": event_object["content"],
                                "authors": ["OPEN-SOURCE INTERNET"]}
            es_json_list.append(new_event_object)

            index_name = config["app"]["es_index_name"]
            with open(filename, 'a') as outfile:
                json.dump({"index": {"_index": index_name, "_type": "doc"}}, outfile)
                outfile.write("\n")
                json.dump(new_event_object, outfile)
                outfile.write("\n\n")

            with open(ib_filename, 'a') as the_base64_file:
                with open(filename) as the_file:
                    encoded = base64.b64encode(the_file.read().encode('utf-8'))
                    the_base64_file.write(encoded.decode('utf-8'))

        print("DONE: GENERATING JSON...")

    '''
    THIS GENERATES MACHINE-READABLE CSV, NOT BASE64 CSV!
    '''

    @staticmethod
    def get_csv(list_of_events):

        print("GENERATING CSV...")

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

        print("DONE: GENERATING CSV...")


def py2_unicode_to_str(u):
    # unicode is only exist in python2
    assert isinstance(u, unicode)
    return u.encode('utf-8')
