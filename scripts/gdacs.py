import datetime
import logging
import time
import urllib
import urllib.request
import feedparser

import App
from gdacs_event_codes_mapping import event_codes_mapping
from gdacs_event_types import event_types
from utils import config_utils, events_utils

logger = logging.getLogger("GDACS")


def run():
    logger.info("Running GDACS script")
    config = config_utils.get_app_config()
    rss_24h_feed_url = config["gdacs"]["rss_24h_feed_url"]

    if config["proxy"]["enabled"].lower() == "true":
        proxy_handler = urllib.request.ProxyHandler(
            {
                "http": config["proxy"]["http_ip_port"],
                "https": config["proxy"]["https_ip_port"]
            }
        )
        logger.info("Added proxy handler")
        gdacs_feed = feedparser.parse(rss_24h_feed_url, handlers=[proxy_handler])
    else:
        gdacs_feed = feedparser.parse(rss_24h_feed_url)

    logger.info('Getting disasters from GDACS ...')
    items = gdacs_feed['entries']
    events_list = list()

    logger.info("Number of disasters(s) from GDACS 24 hours rss feed to process: {}".format(len(items)))
    num_errors = 0

    for i in range(len(items)):
        try:
            logger.info("Processing #{} disaster fromm GDACS feed ...".format(i + 1))
            item = items[i]
            event_date = item["published"]
            logger.debug(event_date)

            # Mon, 26 Nov 2018 01:19:41 GMT
            event_date = datetime.datetime.strptime(event_date, '%a, %d %b %Y %H:%M:%S %Z').strftime('%Y%m%d')
            logger.debug(event_date)
            title = item["title"]
            description = item["description"]
            lat = item["geo_lat"]
            lng = item["geo_long"]
            country = item["gdacs_country"]
            event_type = item["gdacs_eventtype"]
            if event_type in event_types:
                event_type = event_types[event_type]
            else:
                event_type = "445"
            source = item["link"]

            ts = time.time()
            created_datetime = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')

            category_list = list()
            event_str = event_codes_mapping[event_type]
            category_list.append({"category": event_str})
            author_list = list()
            author_list.append({"author": "OPEN-SOURCE INTERNET"})
            event_object = events_utils.generate_event(title, description, source, created_datetime, country, str(lat),
                                                       str(lng), category_list, author_list)
            logger.info("Completed processing #{} disaster fromm GDACS feed".format(i + 1))
            events_list.append(event_object)
            logger.info('Currently {} event(s) built'.format(len(events_list)))
        except Exception:
            logger.exception("Failed to process #{} disaster fromm GDACS feed ...".format(i + 1))
            num_errors += 1
            continue

    events_utils.get_xml_tree(events_list)
    events_utils.get_json(events_list)

    logger.info('\n\n#### Summary of GDACS events ###')
    logger.info('Number of disasters from GDACS = {}'.format(len(items)))
    logger.info('Number of events generated from GDACS = {}'.format(len(events_list)))
    logger.info('Number of erroneous disasters= {}'.format(num_errors))


if __name__ == '__main__':
    App.setup_directories()
    App.setup_logging()
    run()
