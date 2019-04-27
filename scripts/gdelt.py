import csv
import datetime
import io
import logging.config
import os
import subprocess
import time
import traceback
import urllib
import urllib.request
import zipfile
from os.path import isfile, join

import requests
from bs4 import BeautifulSoup
from goose3 import Goose
from numpy.distutils.misc_util import Configuration

import App
import config_utils
import events_utils
from gdelt_countries_mapping import countries_mapping
from gdelt_events_mapping import event_codes_mapping
from gdelt_headers import headers
# from gdelt_keywords_we_want import keywords_we_want

browser_headers = config_utils.get_app_config()["gdelt"]["browser_headers"]
base_codes_we_want = config_utils.get_app_config()["gdelt"]["event_base_codes_we_want"]
countries_we_want = config_utils.get_app_config()["gdelt"]["countries_we_want"]
keywords_we_want = config_utils.get_app_config()["gdelt"]["keywords_we_want"]

logger = logging.getLogger("GDELT")

config = config_utils.get_app_config()


def get_article_preview(the_url):
    title = None
    try:
        logger.info('Getting preview of: ' + the_url)

        if config["proxy"]["enabled"].lower() == "true":
            proxy_handler = urllib.request.ProxyHandler(
                {"http": config["proxy"]["http_ip_port"], "https": config["proxy"]["https_ip_port"]})
            opener = urllib.request.build_opener(proxy_handler)
            urllib.request.install_opener(opener)

        article_preview_request = requests.get(the_url, headers=browser_headers, timeout=10, stream=True)

        logger.info('Opening page now...')

        page = article_preview_request.content

        logger.info('Page loaded, parsing page now')

        soup = BeautifulSoup(page, "html.parser")
        title = soup.find('title').get_text()
        # title = title.replace("\r","")
        # title = title.replace("\n","")
        # title = title.trim()
        title_tag = soup.find("meta", property="og:title")
        page_headline = None
        if title_tag is not None:
            page_headline = title_tag.get("content")
            page_headline = page_headline.replace("\r", "")
            page_headline = page_headline.replace("\n", "")
        else:
            logger.info("Page Html missing meta title tag")
        # headline = headline.trim()

        page_description = None
        description_tag = soup.find("meta", property="og:description")
        if description_tag is not None:
            page_description = description_tag.get("content")
            page_description = page_description.replace("\r", "")
            page_description = page_description.replace("\n", "")
        else:
            logger.info("Page Html missing meta description tag")
        # description = description.trim()
        # logger.info title.encode("utf-8")
        # logger.info headline.encode("utf-8")
        # logger.info description.encode("utf-8")

        # the_body = soup.find('body').get_text()
        # EventsLogging.info('<body>' + the_body + '</body>')

        logger.info('Page parsed')

        if page_headline is not None:
            return {"headline": page_headline, "description": page_description}
        else:
            return {"headline": title, "description": ""}
    except Exception as e:
        logger.error(traceback.format_exc())
        return {"headline": title, "description": None}


def get_article_content(url):
    try:
        logger.info("Getting article content of " + url + " with Goose")
        goose_config = Configuration()
        goose_config.browser_user_agent = 'Mozilla 5.0'
        goose_config.http_timeout = 10  # set http timeout in seconds

        if config["proxy"]["enabled"].lower() == "true":
            goose_config.http_proxy = config["proxy"]["http_ip_port"]
            goose_config.https_proxy = config["proxy"]["https_ip_port"]

        g = Goose(goose_config)
        article = g.extract(url=url)
        logger.debug("Extracted content of article from {}".format(url))
        content = article.cleaned_text.replace("\n", " ")
        logger.debug(content)

        return content
    except Exception as e:
        logging.exception("Error getting article's content from {}".format(url))
        return ""


def get_gdelt_export_url(url):
    r = requests.get(url, headers=browser_headers, timeout=10)
    text = r.text
    return text.split('\n')[0].split(' ')[2]


def get_gdelt_csv_files(export_url):
    logger.info('Downloading GDELT export zip file from  {} ... '.format(export_url))
    r = requests.get(export_url, headers=browser_headers, timeout=10, stream=True)
    z = zipfile.ZipFile(io.BytesIO(r.content))
    z.extractall(config["gdelt"]["in_process_csv_directory"])
    csv_files = [f for f in os.listdir(config["gdelt"]["in_process_csv_directory"]) if
                 isfile(join(config["gdelt"]["in_process_csv_directory"], f))]
    logger.info('Downloaded GDELT export zip file from  {} ... '.format(export_url))
    return csv_files


def move_csv_files_to_processed_folder():
    logger.info("Moving csv files to processed folder")
    src = os.path.abspath(config["gdelt"]["in_process_csv_directory"])
    dst = os.path.abspath(config["gdelt"]["processed_csv_directory"])
    list_of_files = os.listdir(src)
    for f in list_of_files:
        full_path = src + "\\" + f
        subprocess.Popen("move " + " " + full_path + " " + dst, shell=True)  # move command is os dependent
        logger.info("Moved files [" + full_path + "] to [" + dst + "]")


def run():
    logger.info(
        "Running GDELT script at {} minutes away from the next new 15-minute updates".format(
            (60 - datetime.datetime.now().minute) % 15))
    logger.info('Looking for new 15-minute GDELT updates')

    events_list = list()

    logger.info('Reading GDELT last update text at {} ...'.format(config["gdelt"]["last_update_url"]))

    # Retrieving gdelt_export_url
    gdelt_export_url = get_gdelt_export_url(config["gdelt"]["last_update_url"])

    # Download the csv zip files from gdelt_export_url
    gdelt_csv_files = get_gdelt_csv_files(gdelt_export_url)

    has_files = False
    if gdelt_csv_files:
        has_files = True
        logger.info(
            'Successfully downloaded {} csv files to directory at {} ...'.format(gdelt_csv_files,
                                                                                 config["gdelt"]["csv_directory"]))
    else:
        logger.error('Failed to download any GDELT csv files')

    if has_files:
        logger.info("Number of GDELT CSV file(s) to process: {}".format(len(gdelt_csv_files)))
        for i in range(len(gdelt_csv_files)):
            logger.info("Processing #{} GDELT CSV file(s) ...".format(i))
            csv_file = gdelt_csv_files[i]
            csv_file_path = config["gdelt"]["in_process_csv_directory"] + '\\' + csv_file
            csv_reader = csv.reader(open(csv_file_path, newline=''), delimiter=' ', quotechar='|')
            num_empty_rows = 0
            num_rows = 0
            num_error_rows = 0
            set_of_urls = set()

            try:
                for row in csv_reader:
                    if len(row) > 0:
                        num_rows += 1
                        value = ''.join(row)
                        # logger.info(value)

                        values = value.split("\t")

                        event_root_code = values[headers.index("EventRootCode")]
                        event_base_code = values[headers.index("EventBaseCode")]

                        if int(event_root_code) < 4:
                            continue
                        if 9 <= int(event_root_code) <= 13:
                            continue
                        if int(event_root_code) == 4 or int(event_root_code) == 5 or int(event_root_code) == 6 or int(
                                event_root_code) == 14:
                            if event_base_code not in base_codes_we_want:
                                continue

                        country_code = values[headers.index("ActionGeo_CountryCode")]

                        if country_code not in countries_we_want:
                            continue

                        event_date = values[headers.index("SQLDATE")]
                        lat = values[headers.index("ActionGeo_Lat")]
                        lng = values[headers.index("ActionGeo_Long")]

                        source = values[headers.index("SOURCEURL")]
                        source = source.replace("\r", "")
                        source = source.replace("\n", "")

                        if source in set_of_urls:
                            continue
                        else:
                            set_of_urls.add(source)  # ensures that we don't have duplicate records per run

                        event_type = values[headers.index("EventCode")]
                        num_mentions = values[headers.index("NumMentions")]
                        num_sources = values[headers.index("NumSources")]
                        num_articles = values[headers.index("NumArticles")]
                        avg_tone = values[headers.index("AvgTone")]

                        is_root_event = values[headers.index("IsRootEvent")]

                        logger.info('Start building event from article ...')
                        ts = time.time()
                        created_datetime = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')

                        rich_preview_dict = get_article_preview(source)
                        headline = rich_preview_dict["headline"]
                        # logger.info headline.encode("utf-8")
                        description = rich_preview_dict["description"]

                        content = get_article_content(source)
                        if content is not None:
                            if len(content) > 10:
                                description = content

                        # logger.info description.encode("utf-8")
                        logger.info("Searching article against any keywords we want...")

                        hit_list = list()
                        if headline is not None and description is not None:
                            discard = True
                            for keyword in keywords_we_want:
                                if keyword in headline.lower():
                                    logger.debug('[' + keyword + '] is hit in [' + headline + ']')
                                    hit_list.append(keyword)
                                    discard = False
                                if keyword in description.lower():
                                    logger.debug('[' + keyword + '] is hit in [' + description + ']')
                                    hit_list.append(keyword)
                                    discard = False
                            if discard:
                                logger.info("Discarding article since no hit in headline or description...")
                                continue
                        else:
                            continue
                        logger.info("Done and passed! Checking if article contains any keywords we want...")

                        category_list = list()
                        event_type = str(event_type)
                        if len(event_type) <= 2:
                            event_type = "0" + event_type
                        event_str = event_codes_mapping[event_type]
                        category_list.append({"category": event_str})
                        logger.info('Event category = {}'.format(event_str))
                        author_list = list()
                        author_list.append({"author": "OPEN-SOURCE INTERNET"})
                        try:
                            event_object = events_utils.EventsParser.generate_events(headline,
                                                                                     description, source,
                                                                                     created_datetime,
                                                                                     countries_mapping[country_code],
                                                                                     str(lat),
                                                                                     str(lng), category_list,
                                                                                     author_list,
                                                                                     hit_list)
                        except UnicodeDecodeError:
                            logger.exception('UnicodeDecodeError in ' + csv_file + '.')
                            logger.error(row)
                            num_error_rows += num_error_rows
                            continue
                        events_list.append(event_object)
                        logger.info('Completed building event from article')
                        logger.info('Currently {} event(s) built'.format(len(events_list)))

                    else:
                        num_empty_rows += 1
            except UnicodeDecodeError:
                logger.exception('UnicodeDecodeError in ' + csv_file + '.')
                logger.error(csv_file)

            logger.info('#### Summary of {} ###'.format(csv_file))
            logger.info('Number of events generated from {} = {}'.format(csv_file, len(events_list)))
            logger.info('Number of rows in {} = {}'.format(csv_file, num_rows))
            logger.info('Number of erroneous rows in {} = {}'.format(csv_file, num_error_rows))
            logger.info('Number of empty rows in {} = {}\n'.format(csv_file, num_empty_rows))

            EventsXML = events_utils.EventsParser().get_tree(events_list)
            EventsJSON = events_utils.EventsParser().get_json(events_list)
            EventsCSV = events_utils.EventsParser().get_csv(events_list)

    move_csv_files_to_processed_folder()

    logger.info('Done: {} minutes to the next new 15-minute updates'.format((60 - datetime.datetime.now().minute) % 15))


if __name__ == '__main__':
    App.setup_directories()
    App.setup_logging()
    run()
