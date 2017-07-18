
# Defeating ML-based XSS Classifier using Adversarial Examples

## Installation 

```
#sudo pip3 install virtualenv fdupes
virtualenv -p python3 venv
. venv/bin/activate
pip install -r requirements.txt
```


## Scraping Data

```
cd scraping
scrapy crawl xssed -o xssed.json --logfile log_xssed.txt --loglevel INFO
scrapy crawl randomwalk -o randomwalk.json --logfile log_randomwalk.txt --loglevel INFO
# filter duplicated HTML files of random walk
cd html/randomsample/
fdupes -r . # grouped dupliacted files
fdupes -rf . | grep -v '^$' > ../duplicated_randomsample_files.txt
less ../duplicated_randomsample_files.txt # check files
xargs -a ../duplicated_randomsample_files.txt rm -v # delete files
cd ../..
```


