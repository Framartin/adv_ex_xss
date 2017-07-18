# -*- coding: utf-8 -*-
import scrapy
from scraping.items import randomWalkItem
from random import choice, randint, sample
from scipy.stats import bernoulli
from hashlib import sha1
from urllib.parse import urldefrag

# This spider implement the sampling method of the Web described in Monika R. Henzinger, Allan Heydon, Michael Mitzenmacher, Marc Najork, On near-uniform URL sampling, Computer Networks, Volume 33, Issue 1, 2000, Pages 295-308.
# This is a random walk method with random jump. This is implemented as follows:
# 1. Randomly sample NOMBER_SELECTED_SEEDS domains/URL of URL_SEEDS without replacement
# 2. For each page:
#     a. make sure that this is an html page (using https://doc.scrapy.org/en/latest/topics/request-response.html#htmlresponse-objects). If not select a new domain or a previously downloaded page and go to 2.
#     b. with probability d continue, with 1-d randomly select a new domain or a previously downloaded page and go to 2.
#     c. save the page
#     d. parse all the links (using scrapy.linkextractors, for example to not select ftp:// links)
#     e. randomly sample 1 link. If there is no link, select a new domain or a previously downloaded page and go to 2.
#     f. follow this link and go to 2.
# 3. Stop when we have saved CLOSESPIDER_ITEMCOUNT pages

# Becareful:
# 1. You have to filter out dupliacted HTML pages after crawling. Even if the spider strips out anchors in the URLs. Some URLs lead to the same page content (eg. parameters used for tracking).
# 2. Note that the URL are canonicalized in order to removed duplicated links (eg. links to the same page having different fragments: foo#1, foo#2): http://w3lib.readthedocs.io/en/latest/w3lib.html#w3lib.url.canonicalize_url
# 3. To fully implement the paper cited below, you have to compute the pageRank of each page and include it in the final sample with a probability proportional to the reverse of the page’s rank. THIS IS NOT DONE BY THIS SCRIPT.

# TODO "Scrapy filters out duplicated requests to URLs already visited, avoiding the problem of hitting servers too much because of a programming mistake" https://doc.scrapy.org/en/latest/intro/tutorial.html?highlight=duplicated
# TODO disable dupluacted request instead of dont_filter argument

def random_jump_url(URL_SEEDS, visited_urls):
    """Randomly choose one element between the 2 lists.
       For performance the 2 lists are not joined.   """
    random_index = randint(0, len(URL_SEEDS)+len(visited_urls)-1)
    if random_index <= (len(URL_SEEDS)-1):
        return URL_SEEDS[random_index]
    else:
        return visited_urls[random_index - len(URL_SEEDS)]

class RandomWalkSpider(scrapy.Spider):
    name = 'randomwalk'
    custom_settings = {
        'CLOSESPIDER_ITEMCOUNT': 10,
        'D_PROBABILITY': 1/7,
        'URL_SEEDS': ['https://google.com'], # list of URLs/domains to start, for example top500 websites
        'NOMBER_WALKS': 1, # nomber of URL to start with inside INITAL_SEEDS, ie. number of independant walks to perform at the same time
        'FILES_STORE': 'html/randomsample/'
    }
    start_urls = sample(custom_settings['URL_SEEDS'], custom_settings['NOMBER_WALKS']) # random sampling without replacement
    le = scrapy.linkextractors.LinkExtractor(canonicalize=True)  # linkextractor is smarter than xpath '//a/@href'
    visited_urls = [] # stored the visited URLs

    def parse(self, response):
        if not isinstance(response, scrapy.http.HtmlResponse): # not a HTML page
            # Choose at random an HTML page already visited or a start_urls (the initial seed)
            # Don't save the page
            # Use dont_filter=True on the request: don't filter dupliactes
            next_url = random_jump_url(self.settings.get('URL_SEEDS'), self.visited_urls)
            self.logger.debug('Not an HTML response. Random jump. %s' % response.url)
            yield response.follow(next_url, callback=self.parse, errback=self.errback_httpbin, dont_filter=True)
        else:
            d = self.settings.getfloat('D_PROBABILITY')
            random_jump = bernoulli.rvs(d)
            if random_jump == 1:
                next_url = random_jump_url(self.settings.get('URL_SEEDS'), self.visited_urls)
                self.logger.debug('Random jump from %s to %s' % (response.url, next_url))
                yield scrapy.Request(next_url, callback=self.parse, errback=self.errback_httpbin, dont_filter=True)
            else:
                if response.url not in self.visited_urls:
                    # save file
                    folder = self.settings.get('FILES_STORE')
                    filename = sha1(response.url.encode()).hexdigest()
                    with open(folder+filename, 'wb') as f:
                        f.write(response.body)
                    self.logger.debug('Saved file %s' % filename)
                    self.visited_urls.append(response.url)
                    item = randomWalkItem()
                    item['url'] = response.url
                    item['file_path'] = folder+filename
                    yield item
                urls = self.le.extract_links(response)
                urls = [link.url for link in urls if link.url != response.url] # remove links to the same page (used a lot for links to anchors)
                if len(urls) == 0:
                    # random jump because the nade has not outlink
                    self.logger.debug('No link to follow. Random jump: %s' % response.url)
                    next_url = random_jump_url(self.settings.get('URL_SEEDS'), self.visited_urls)
                    yield scrapy.Request(next_url, callback=self.parse, errback=self.errback_httpbin, dont_filter=True)
                else:
                    next_url = choice(urls)
                    self.logger.debug('Following one link of: %s' % response.url)
                    yield response.follow(next_url, callback=self.parse, errback=self.errback_httpbin, dont_filter=True)
#                if hasattr(item, 'url'):
#                    yield item
               

    def errback_httpbin(self, failure):
        # random jump in case of failure (including HTTP, DNSm and TimeOut errors)
        self.logger.error(repr(failure))
        next_url = random_jump_url(self.settings.get('URL_SEEDS'), self.visited_urls)
        self.logger.debug('HTTP error. Random jump to: %s' % next_url)
        return scrapy.Request(next_url, callback=self.parse, errback=self.errback_httpbin, dont_filter=True)

