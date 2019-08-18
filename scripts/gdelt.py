import csv
import datetime
import io
import logging.config
import os
import subprocess
import time
import urllib
import urllib.request
import zipfile
import re
from os.path import isfile, join

import requests
from bs4 import BeautifulSoup
from goose3 import Goose
import datefinder
from datetime import timedelta

import App
from gdelt_countries_mapping import countries_mapping
from gdelt_events_mapping import event_codes_mapping
from gdelt_headers import headers
from utils import config_utils, events_utils

config = config_utils.get_app_config()

browser_headers = config["gdelt"]["browser"]["headers"]
browser_timeout = config["gdelt"]["browser"]["time_out"]
base_codes_we_want = config["gdelt"]["event_base_codes_we_want"]
countries_we_want = config["gdelt"]["countries_we_want"]
keywords_we_want = config["gdelt"]["keywords_we_want"]
is_delta_crawl = config["gdelt"]["is_delta_crawl"]
max_urls_to_crawl = config["gdelt"]["max_csv_urls_to_crawl"]
month_abbreviations = config["gdelt"]["month_abbreviations"]
months_of_year = config["gdelt"]["months_of_year"]

logger = logging.getLogger("GDELT")

erroneous_urls = list()


def get_article_preview(url):
    title = None
    try:
        logger.info('Getting preview of: ' + url)

        if config["proxy"]["enabled"].lower() == "true":
            proxy_handler = urllib.request.ProxyHandler(
                {
                    "http": config["proxy"]["http_ip_port"],
                    "https": config["proxy"]["https_ip_port"]
                }
            )
            logger.info("Added proxy handler")
            opener = urllib.request.build_opener(proxy_handler)
            urllib.request.install_opener(opener)

        article_preview_request = requests.get(url, headers=browser_headers, timeout=20, stream=True)

        logger.info('Opening page now...')

        page = article_preview_request.content

        logger.info('Page loaded, parsing page now')

        soup = BeautifulSoup(page, "html.parser")
        title = soup.find('title').get_text()
        title = title.replace("\r", "")
        title = title.replace("\n", "")
        title_tag = soup.find("meta", property="og:title")

        page_headline = None
        if title_tag is not None:
            page_headline = title_tag.get("content")
            if page_headline is not None:
                page_headline = page_headline.replace("\r", "")
                page_headline = page_headline.replace("\n", "")
        else:
            logger.info("Page Html missing meta title tag")
        # headline = headline.trim()

        page_description = None
        description_tag = soup.find("meta", property="og:description")
        if description_tag is not None:
            page_description = description_tag.get("content")
            if page_description is not None:
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
    except Exception:
        logger.exception("Failed to get article preview at url: {}".format(url))
        erroneous_urls.append({"url": url, "error": "Unable to get preview"})
        return {"headline": title, "description": None}


def get_article_content(url):
    try:
        logger.info("Getting article content of " + url + " with Goose")
        goose_config = {
            'browser_user_agent': 'Mozilla',
            'parser_class': 'lxml',  # soup or lxml for parsing xml and html
            # 'enable_image_fetching': True,
            'http_timeout': browser_timeout
        }

        if config["proxy"]["enabled"].lower() == "true":
            goose_config["http_proxy"] = config["proxy"]["http_ip_port"]
            goose_config["https_proxy"] = config["proxy"]["https_ip_port"]

        g = Goose(goose_config)
        logger.debug("Goose current parser is {}".format(g.config.get_parser()))
        article = g.extract(url=url)
        logger.debug("Extracted content of article from {}".format(url))
        content = article.cleaned_text.replace("\n", " ")
        cleaned_text = article.cleaned_text
        paragraphs_list = list()
        paragraphs_list = paragraphs_list + cleaned_text.split('\n')

        logger.debug(content)

        return {"content": content, "paragraphs_list": paragraphs_list}
    except Exception as e:
        logging.exception("Error getting article's content from {}".format(url))
        erroneous_urls.append({"url": url, "error": "Unable to get content"})
        content = ""
        return {"content": content, "paragraphs_list": list()}


# Attempt to extract the probable event dates based on the set of dates returned by the date_finder library
def extract_probable_event_dates(content, article_timestamp):
    month_keywords = months_of_year + month_abbreviations
    probable_event_date_set = set()
    article_datetime = datetime.datetime.fromtimestamp(article_timestamp)
    article_datetime_plus_one_year = article_datetime + timedelta(days=365)
    article_datetime_string = article_datetime.strftime('%Y-%m-%d %H:%M:%S')
    probable_event_date_set.add(article_datetime_string)
    extracted_dates = datefinder.find_dates(content, True, False, False)
    for date in extracted_dates:
        try:
            has_month_reference = False
            is_month_only = False
            for keyword in month_keywords:
                if re.search(r'\b' + keyword + r'\b', date[1]):
                    has_month_reference = True
                    if keyword == date[1]:
                        is_month_only = True
                    if "by " + keyword == date[1].lower():
                        is_month_only = True
                    if "of " + keyword == date[1].lower():
                        is_month_only = True
                    if keyword + " by" == date[1].lower():
                        is_month_only = True
                    if keyword + " of" == date[1].lower():
                        is_month_only = True
            if (date[0] > article_datetime) and (date[0] < article_datetime_plus_one_year) \
                    and has_month_reference and not is_month_only:
                adjusted_date = date[0]
                extracted_date_string = adjusted_date.strftime('%Y-%m-%d %H:%M:%S')
                probable_event_date_set.add(extracted_date_string)
        except Exception as e:
            logger.exception("Failed to compare dates")
            continue
    return list(probable_event_date_set)


def get_gdelt_export_url(url):
    r = requests.get(url, headers=browser_headers, timeout=10)
    text = r.text
    return text.split('\n')[0].split(' ')[2]


def get_gdelt_export_urls(url, max_urls=100):
    logger.info("Retrieving gdelt export urls with max number of urls = {}".format(max_urls))
    r = requests.get(url, headers=browser_headers, timeout=10)
    text = r.text
    lines = text.split('\n')
    urls = list()

    for i in reversed(range(len(lines))):
        if len(urls) > max_urls:
            break
        try:
            line = lines[i]
            url = line.split(' ')[2]
            if "export" in url:
                urls.append(url)
        except Exception:
            continue

    return urls


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
        subprocess.Popen("move " + "\"" + full_path + "\" \"" + dst + "\"", shell=True)  # move command is os dependent
        logger.info("Moved file [" + full_path + "] to [" + dst + "]")


def find_keyword(keyword, content):
    if re.search(keyword, content.lower()):
        return True
    else:
        return False


def run():
    time_now = datetime.datetime.now()

    logger.info(
        "Running GDELT script at {} minutes away from the next new 15-minute updates".format(
            (60 - datetime.datetime.now().minute) % 15))
    logger.info('Looking for new 15-minute GDELT updates')

    events_list = list()
    gdelt_export_urls = list()
    gdelt_csv_files = list()

    if is_delta_crawl:
        logger.info('Reading GDELT last update text at {} ...'.format(config["gdelt"]["last_update_url"]))
        # Retrieving gdelt_export_url
        gdelt_export_url = get_gdelt_export_url(config["gdelt"]["last_update_url"])
        gdelt_export_urls.append(gdelt_export_url)

    else:
        logger.info('Reading GDELT master file list text at {} ...'.format(config["gdelt"]["master_file_list_url"]))
        gdelt_export_urls = get_gdelt_export_urls(config["gdelt"]["master_file_list_url"],
                                                  config["gdelt"]["max_csv_urls_to_crawl"])

    # Download the csv zip files from gdelt_export_url(s)
    for gdelt_url in gdelt_export_urls:
        try:
            csv_files = get_gdelt_csv_files(gdelt_url)
            for c in csv_files:
                gdelt_csv_files.append(c)
        except Exception:
            logger.exception("Failed to download csv files from {}".format(gdelt_url))
            continue

    has_files = False
    if gdelt_csv_files:
        has_files = True
        logger.info(
            'Successfully downloaded {} csv files to directory at {} ...'.format(gdelt_csv_files,
                                                                                 config["gdelt"][
                                                                                     "in_process_csv_directory"]))
    else:
        logger.error('Failed to download any GDELT csv files')

    if has_files:
        logger.info("Number of GDELT CSV file(s) to process: {}".format(len(gdelt_csv_files)))
        for i in range(len(gdelt_csv_files)):
            logger.info("Processing #{} GDELT CSV file(s) ...".format(i + 1))
            csv_file = gdelt_csv_files[i]
            csv_file_path = config["gdelt"]["in_process_csv_directory"] + '\\' + csv_file
            csv_reader = csv.reader(open(csv_file_path, newline='', encoding='utf-8'), delimiter=' ', quotechar='|')
            num_empty_rows = 0
            num_rows = 0
            num_error_rows = 0
            set_of_urls = set()

            try:
                for row in csv_reader:
                    if len(row) > 0:
                        try:
                            num_rows += 1
                            value = ''.join(row)

                            values = value.split("\t")

                            event_base_code = values[headers.index("EventBaseCode")]

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
                            description = rich_preview_dict["description"]

                            parsed_article = get_article_content(source)
                            content = parsed_article["content"]
                            content_paragraphs_list = parsed_article["paragraphs_list"]
                            if content is not None:
                                if len(content) > 10:
                                    description = content

                            logger.info("Searching article against any keywords we want...")

                            hit_set = set()
                            if headline is not None and description is not None:
                                discard = True
                                for keyword in keywords_we_want:
                                    if find_keyword(keyword, headline):
                                        logger.debug('[' + keyword + '] is hit in [' + headline + ']')
                                        hit_set.add(keyword.replace("\\b", ""))
                                        discard = False
                                    if find_keyword(keyword, description):
                                        logger.debug('[' + keyword + '] is hit in [' + description + ']')
                                        hit_set.add(keyword.replace("\\b", ""))
                                        discard = False
                                if discard:
                                    logger.info("Discarding article since no hit in headline or description...")
                                    continue
                            else:
                                continue
                            logger.info("Completed searching article against any keywords we want")

                            probable_event_date_list = extract_probable_event_dates(description, ts)

                            category_list = list()
                            event_type = str(event_type)
                            if len(event_type) <= 2:
                                event_type = "0" + event_type
                            event_str = event_codes_mapping[event_type]
                            category_list.append({"category": event_str})
                            logger.debug('Event category = {}'.format(event_str))
                            author_list = list()
                            author_list.append("GDELT")

                            event_object = events_utils.generate_event(
                                headline,
                                description,
                                content_paragraphs_list,
                                source,
                                created_datetime,
                                probable_event_date_list,
                                countries_mapping[country_code],
                                float(lat),
                                float(lng),
                                category_list,
                                author_list,
                                list(hit_set)
                            )

                            events_list.append(event_object)
                            logger.info('Completed building event from article')
                            logger.info('Currently {} event(s) built'.format(len(events_list)))
                        except Exception:
                            logger.exception('Failed in ' + csv_file + '.')
                            logger.error(row)
                        continue

                    else:
                        num_empty_rows += 1
            except Exception:
                num_error_rows += 1
                logger.exception('Exception in ' + csv_file + '.')
                logger.error(csv_file)
                continue

            # Generate json output by default
            events_utils.get_json(events_list)

            if config["gdelt"]["generate_xml_files"]:
                events_utils.get_xml_tree(events_list)

            # EventsCSV = events_utils.get_csv(events_list)

            logger.info('\n\n#### Summary of GDELT #{} {} ###'.format(i + 1, csv_file))
            logger.info('Number of events generated from {} = {}'.format(csv_file, len(events_list)))
            logger.info('Number of rows in {} = {}'.format(csv_file, num_rows))
            logger.info('Number of error rows in {} = {}'.format(csv_file, num_error_rows))
            logger.info('Number of empty rows in {} = {}'.format(csv_file, num_empty_rows))
            logger.info('Number of erroneous urls in {} = {}'.format(csv_file, len(erroneous_urls)))
            logger.info('Erroneous urls:  {}\n'.format(erroneous_urls))

    move_csv_files_to_processed_folder()

    time_later = datetime.datetime.now()
    time_taken = time_later - time_now
    logger.info("Time taken = {} seconds".format(time_taken.total_seconds()))
    logger.info(
        'Done: {} minutes to the next new 15-minute updates'.format((60 - datetime.datetime.now().minute) % 15))


if __name__ == '__main__':
    App.setup_directories()
    App.setup_logging()

    # FOR TESTING

    # get_article_preview(
    #     "https://www.msn.com/en-au/news/australia/slain-brisbane-gp-dr-luping-zeng-laid-to-rest/ar-BBWlwrD")
    # get_article_content(
    #     "https://www.msn.com/en-au/news/australia/slain-brisbane-gp-dr-luping-zeng-laid-to-rest/ar-BBWlwrD")

    # export_urls = get_gdelt_export_urls("http://data.gdeltproject.org/gdeltv2/masterfilelist.txt")
    # logger.info(export_urls)
    run()
