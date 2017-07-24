# -*- coding: utf-8 -*-
import scrapy
import re

from scraping.items import xssedItem

class XssedSpider(scrapy.Spider):
    name = 'xssed'
    allowed_domains = ['xssed.com']
    start_urls = ['http://www.xssed.com/archive']
    custom_settings = { # overrides settings.py option to use a dedicated folder
        'FILES_STORE': 'html/xssed/',
    }

    def parse(self, response):
        #response.xpath("//th[@id='tableborder']/table[1]/tr[not(@id='legends')]").extract()
        list_pages = response.xpath("//a[./text()='mirror']/@href").extract() # pages to scrape
        for page in list_pages:
            yield response.follow(page, self.parse_detail)
        next_page = response.xpath("//a[./text()='>']/@href").extract_first() # next page of the list
        if next_page is not None:
            yield response.follow(next_page, self.parse)

    def parse_detail(self, response):
        item = xssedItem()
        item["id"] = response.url.split('/')[-2]
        item["file_urls"]  = response.xpath("//a[./text()='Click here to view the mirror']/@href").extract() # will be downloaded by FilesPipeline
        item["date"]       = response.xpath("//th[contains(./text(), 'Date submitted:')]/text()").extract_first()
        item["status"]     = response.xpath("//th[contains(./text(), 'Status:')]/text()[2]").extract_first()
        item["domain"]     = response.xpath("//th[contains(./text(), 'Domain:')]/text()").extract_first()
        item["category"]   = response.xpath("//th[contains(./text(), 'Category:')]/text()").extract_first()
        item["pagerank"]   = response.xpath("//th[contains(./text(), 'Pagerank:')]/text()").extract_first()
        item["url"]        = ''.join(response.xpath("//th[contains(./text(), 'URL:')]//text()").extract()) # URL can be splited: http://www.xssed.com/mirror/78538/

        # clean data
        for i in ["date", "status", "domain", "category", "pagerank"]: # remove non-breaking space encoded in Latin1
            item[i] = item[i].replace(u'\xa0', u'')
        item['date']     = item['date'].replace('Date submitted:', '')
        item['status']   = item['status'].replace('Status:', '')
        item['domain']   = item['domain'].replace('Domain:', '')
        item['category'] = item['category'].replace('Category:', '')
        item['pagerank'] = item['pagerank'].replace('Pagerank:', '')
        item['url']      = item['url'].replace('URL:', '')
        for i in item.keys():
            if i not in ["file_urls"]:
                item[i] = item[i].strip()
        if item['category'] != 'XSS':
            self.logger.info('not saving this non-XSS item: %s (%s)', response.url, item['category']) # example: http://www.xssed.com/mirror/76616/
        else:
            yield item
