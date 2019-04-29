# Events App

This is a simple python app to interface with open sources to bulk index events to Elasticsearch.

## Open Sources
* GDELT - [The GDELT Project](https://www.gdeltproject.org/about.html)
    * Supported by [Google Jigsaw](https://jigsaw.google.com/), the GDELT Project monitors the world's broadcast, print, and web news from nearly every corner of every country in over 100 languages and identifies the people, locations, organizations, themes, sources, emotions, counts, quotes, images and events driving our global society every second of every day, creating a free open platform for computing on the entire world.

* GDACS - [Global Disasters Alert & Coordination System](http://www.gdacs.org/About/overview.aspx)
    * GDACS is a cooperation framework between the United Nations and the European Commission. It includes disaster managers and disaster information systems worldwide and aims at filling the information and coordination gaps in the first phase after major disasters. GDACS provides real-time access to web‐based disaster information systems and related coordination tools. A more detailed description of GDACS purpose, content and guidelines, agreed and approved by the steering committee can be found here. GDACS activities are presented and endorsed by the GDACS Advisory Board, which is currently chaired by the Joint Research Centre. Annual GDACS Advisory Group meetings are attended by disaster managers, scientists, map experts, webmasters and other professionals, to define standards for information exchange and a strategy for further development of related tools and services. The Activation and Coordination Support Unit (ACSU) or Emergency Response Support Branch (ERSB) in the United Nations Office for Coordination of Humanitarian Affairs (OCHA) in Geneva acts as GDACS Secretariat. 

## Installation
* Setup Python 3
* pip install bs4
* pip install goose3
* pip install requests
* pip install numpy

## IDE
PyCharm

## Known Issues
* Error with feedparser.py due to geoRSS
    * Hotfix is to replace feedparser.py with [this](https://gitlab.com/klevstul/muninn/raw/master/additional_resources/feedparser_hotfix/feedparser.py)
