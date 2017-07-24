
# Defeating ML-based XSS Classifier using Adversarial Examples

## Installation 

```
#sudo pip3 install virtualenv fdupes
virtualenv -p python3 venv
. venv/bin/activate
pip install -r requirements.txt
```


## Scraping Data

### Getting the Alexa top sites list

If the source file is not available anymore, use the `top-10000.csv` included in this repository. Data were generated the `2017-07-18 12:51:20.000000000 -0400`.

```
cd scraping/alexa
wget http://s3.amazonaws.com/alexa-static/top-1m.csv.zip && \
unzip top-1m.csv.zip && \
head -10000 top-1m.csv > top-10000.csv

stat -c %y top-1m.csv # time of last modification of the top 1 million
rm top-1m.csv
cd ..
```

### Executing scrapy

```
scrapy crawl xssed -o xssed.json --logfile log_xssed.txt --loglevel INFO
scrapy crawl randomwalk -o randomwalk.json --logfile log_randomwalk.txt --loglevel INFO
```

### Remove duplicated files

We need to filter duplicated HTML files download from the random walks. See `scraping/scraping/spiders/randomwalk.py` for more informations.

```
cd html/randomsample/
fdupes -r . # see duplicated files by groups
fdupes -rf . | grep -v '^$' > ../duplicated_randomsample_files.txt
less ../duplicated_randomsample_files.txt # check files
xargs -a ../duplicated_randomsample_files.txt rm -v # delete files
cd ../..
```


## Parsing HTML files to generate features

```
python3 generate_data.py
ls -lh data.csv
```

