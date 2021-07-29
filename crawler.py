#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import urllib3
import re
from urllib.parse import urlparse, urljoin
from time import sleep, time
from random import randint
from argparse import ArgumentParser
import json
import urllib.robotparser

class Crawler:
	"""
		:host the root of the website
		:delay_func the function to call to simulate the human activity
	"""
	def __init__(self, host, timeout=3600, delay=1):
		# It represent the current webpage
		self.url = '/'
		# it represent the url to craw
		self.url_to_crawl = [self.url]
		# We create an ConnectionPool instance of its host.
		self.conn = urllib3.connection_from_url(host)
		# It represent the current data while the crawling
		self.content = b''
		self.MAX_SIZE_PER_PAGE = 1024*256 # 256Kb
		# We build a regular expression to get url link in a text
		self.HTML_TAG_REGEX = re.compile(r'<a[^<>]+?href=([\'\"])(.*?)\1', re.IGNORECASE)
		self.HTML_OUTER_REGEX = re.compile(r'>(.*?)<', re.IGNORECASE)
		self.SITEMAP_TAG_REGEX = re.compile(r'<loc>(.*?)</loc>', re.IGNORECASE)
		# We set the robotparser
		self.ROBOT_PARSER = urllib.robotparser.RobotFileParser(urljoin(host, 'robots.txt'))
		# We set the user agent
		self.USER_AGENT = "Codexbot"
		self.HEADERS = {
			"User-Agent": self.USER_AGENT,
			"Accept": "text/html",
		}
		#
		self.delay = self.ROBOT_PARSER.crawl_delay(self.USER_AGENT)
		self.wait = lambda:sleep(self.delay if self.delay else delay)
		self.timeout = timeout
		# Output file of the logging
		self.logstream = open('%s.log' % time(), 'a')
		self.logstream.write('HOST: %s\n' % self.conn.host)
		self.results = {}

	# This method permit to read the sitemaps and get the urls inside
	def getUrlFromSiteMap(self):
		for sitemap in self.ROBOT_PARSER.sitemaps:
			r = self.conn.request('GET', urlparse(sitemap).path, preload_content=False, headers=self.HEADERS, timeout=self.timeout)
			resp = r.read(self.MAX_SIZE_PER_PAGE, decode_content=True).decode()
			for url in self.SITEMAP_TAG_REGEX.findall(resp):
				self.url_to_crawl.append(urlparse(url).path)

	# This method permit to get the content of a webpage
	def getContent(self):
		print('[INFO] Getting content from %s ...' % self.url, file=self.logstream)
		
		try:
			r = self.conn.request('GET', self.url, preload_content=False, headers=self.HEADERS, timeout=self.timeout)
		except urllib3.exceptions.MaxRetryError:
			self.content = ''
			print('[WARNING] Timeout exceed for %s, no content got' % self.url, file=self.logstream)
		else:
		
			# We verify if the request has succeed
			if r.status != 200:
				if r.status == 404:
					# It's possible that an URL catched not exists
					print("[ERROR] [%s]: %s" % (r.status, self.url), file=self.logstream)
				else:
					raise Exception('CODE %s not managed' % r.status)
			# We get only html text file
			elif r.headers['Content-type'].startswith('text/html') and (('Content-Length' not in r.headers) or int(r.headers['Content-Length']) < self.MAX_SIZE_PER_PAGE):
				# We decode the response
				try:
					self.content = r.read(self.MAX_SIZE_PER_PAGE, decode_content=True).decode()
				except UnicodeDecodeError:
					print('[CRITICAL] Decoding of %s failed, type: %s' % (self.url, r.headers['Content-type']), file=self.logstream)

			else:
				print('[WARNING] Content of %s ignored %s' % (self.url, [r.headers['Content-type'], r.headers['Content-Length']]), file=self.logstream)
				self.content = ''

	# This method permit to get the url links present in the webpage
	def getUrlLinks(self):
		print('[INFO] Getting urls from %s ...' % self.url, file=self.logstream)
		
		for i in self.HTML_TAG_REGEX.findall(self.content):
			url = urlparse(i[1])
			#print(self.url, i[1], url)
			
			# scheme://netloc... (root path)
			# We verify the structure of the url and if it is valid
			# eg: http://exemple.com/a/b/c
			if url.scheme:
				
				if url.netloc == self.conn.host:
					self.url_to_crawl.append(urljoin('/', url.path))
				else:
					print('[DEBUG] %s not belong %s...' % (i[1], self.conn.host), file=self.logstream)
			# path
			# eg: /a/b/c
			else:
				
				# //path (root path)
				# eg: //a/b/c
				if url.netloc:
					# We build and add the url
					self.url_to_crawl.append(urljoin('/' + url.netloc, url.path))
				else:
					# /path (root or sub path)
					# eg: /a/b/c a/b/c a/b/c.d
					self.url_to_crawl.append(urljoin(self.url, url.path))

	# This method permit to get the text in the webpage
	def getData(self):
		print('[INFO] Getting data from %s ...' % self.url, file=self.logstream)
		
		return self.HTML_OUTER_REGEX.findall(self.content)

	# This method start the crawling
	def start(self):
		print('[INFO] Crawling launched of %s ...' % self.conn.host, file=self.logstream)
		
		print('[INFO] Reading of the robots.txt ...', file=self.logstream)
		# We load the robots.txt
		self.ROBOT_PARSER.read()

		print('[INFO] Loading of the sitemaps ...', file=self.logstream)
		# We read the sitemap if present in the robots.txt
		self.getUrlFromSiteMap()
		
		while self.url_to_crawl:
			self.wait()

			# We get the first url
			self.url = self.url_to_crawl.pop(0)

			# We verify if url not already used or not empty
			if not self.url or self.url in self.results:
				continue
			# We verify if our robot can is allowed to fetch this url
			elif self.ROBOT_PARSER.can_fetch(self.USER_AGENT, self.url):
				print(self.url)
				print('[DEBUG] Crawling launched on %s ...' % self.url, file=self.logstream)
				self.getContent()
				self.results[self.url] = self.getData()
				self.getUrlLinks()
			else:
				print("[WARNING] We aren't allowed to fetch the url %s" % self.url, file=self.logstream)

		# We save the data parse
		with open(str(time())+'.json', 'w') as f:
			json.dump(self.results, f)

if __name__ == '__main__':
	parser = ArgumentParser()
	parser.add_argument('HOST', help='Eg: http://example.com')
	parser.add_argument('-t', type=int, default=3600, help='It represent the timeout')
	parser.add_argument('-d', type=float, default=1, help='This delay will be used if no delay specified by the robots.txt')
	args = parser.parse_args()
	Crawler(
		args.HOST,
		timeout=args.t,
		delay=args.d,
	).start()