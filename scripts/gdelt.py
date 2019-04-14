import io
from os import listdir
from os.path import isfile, join

import requests
import zipfile

gdelt_last_update_url = 'http://data.gdeltproject.org/gdeltv2/lastupdate.txt'
gdelt_csv_directory = 'C:\\Users\\junwen29\\PycharmProjects\\GDELTApp\\data'

headers = {'User-Agent': "Mozilla/5.0 (Windows NT 5.1; rv:10.0.1) Gecko/20100101 Firefox/10.0.1", 'Accept': '*/*'}

print('\nReading GDELT last update text at {} ...\n'.format(gdelt_last_update_url))

# Retrieving gdelt_export_url
r = requests.get(gdelt_last_update_url, headers=headers, timeout=10)
text = r.text
gdelt_export_url = text.split('\n')[0].split(' ')[2]

# Download the csv zip files
print('Downloading GDELT export zip file from  {} ... \n'.format(gdelt_export_url))
r = requests.get(gdelt_export_url, headers=headers, timeout=10, stream=True)
z = zipfile.ZipFile(io.BytesIO(r.content))
gdelt_csv_zipfile = z.extractall(gdelt_csv_directory)
gdelt_csv_files = [f for f in listdir(gdelt_csv_directory) if isfile(join(gdelt_csv_directory, f))]
print('Downloaded {} csv files to directory at {} ... \n'.format(gdelt_csv_files, gdelt_csv_directory))














