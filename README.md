
# Defeating ML-based XSS Classifier using Adversarial Examples

## Installation 

```
#sudo pip3 install virtualenv
virtualenv -p python3 venv
. venv/bin/activate
pip install -r requirements.txt
```


## Scraping Data

```
cd scraping
scrapy crawl xssed -o xssed.json --logfile log_xssed.txt --loglevel INFO
scrapy crawl alexa -o alexa.json --logfile log_alexa.txt --loglevel INFO
```


