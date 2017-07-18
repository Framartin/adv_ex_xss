# -*- coding: utf-8 -*-

# Define here the models for your scraped items
#
# See documentation in:
# http://doc.scrapy.org/en/latest/topics/items.html

import scrapy


class xssedItem(scrapy.Item):
    # define the fields for your item here like:
    # name = scrapy.Field()
    id = scrapy.Field()
    date = scrapy.Field()
    status = scrapy.Field()
    domain = scrapy.Field()
    category = scrapy.Field()
    pagerank = scrapy.Field()
    url = scrapy.Field()
    file_urls = scrapy.Field() # for FilesPipeline
    files = scrapy.Field() # for FilesPipeline

class randomWalkItem(scrapy.Item):
    url = scrapy.Field()
    file_path = scrapy.Field()
