
# Defeating Machine Learning-based XSS Classifier using Adversarial Examples


## Installation 

```
#sudo apt-get install python3-pip virtualenv fdupes
virtualenv -p python3 venv
. venv/bin/activate
pip install -r requirements.txt
```


## Scraping Data

Please edit `scraping/scraping/settings.py@19` to identify yourself.

### Getting the Alexa top sites list

If the source file is not available anymore, use the `top-100000.csv` included in this repository. Data were generated the `2017-07-18 12:51:20.000000000 -0400`.

```
cd scraping/alexa
wget http://s3.amazonaws.com/alexa-static/top-1m.csv.zip && \
unzip top-1m.csv.zip && \
head -100000 top-1m.csv > top-100000.csv

stat -c %y top-1m.csv # time of last modification of the top 1 million
#2017-07-25 12:52:54.000000000 +0000
rm top-1m.csv
cd ..
```

### Executing scrapy

```
scrapy crawl xssed -o xssed.json --logfile log_xssed.txt --loglevel INFO

# number of malicious observations
wc -l xssed.json # minus 2 for the first and last lines
#38637 xssed.json
```

Edit the `custom_settings` at `scraping/scraping/spiders/randomwalk.py@72` before using the randomwalk spider. Among others settings, it's important to set `CLOSESPIDER_ITEMCOUNT` which defines the number of benign web pages to save. We recommend to scrape more benign data than malicious ones: 

- to plan the deletion of duplicated pages
- to perform a posterior (uniform) random sample

```
scrapy crawl randomwalk -o randomwalk.json --logfile log_randomwalk.txt --loglevel INFO
```


Note: if you encounter the error `OSError: [Errno 24] Too many open files:` in the log, try `ulimit -n 30000` (this modification only applies to the current session).

### Remove oversized files

Some files are just too big.

```
find html/ -size +50M -exec ls -lh {} \+
```

For example, `html/xssed/full/7aee06aa9087469b5766a8b8d27194a41e2e51c0` that weights 193Mio!

```
rm html/xssed/full/7aee06aa9087469b5766a8b8d27194a41e2e51c0
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

