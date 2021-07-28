#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import urllib3
import re
from urllib.parse import urlparse, urljoin
from time import sleep, time
from random import randint
from argparse import ArgumentParser
import json

class Crawler:
	"""
		:host the root of the website
		:delay_func the function to call to simulate the human activity
	"""
	def __init__(self, host, delay_func=lambda:sleep(randint(0, 20)/10), timeout=3600):
		# It represent the current webpage
		self.url = '/'
		# it represent the url to craw
		self.url_to_crawl = [self.url]
		# We create an ConnectionPool instance of its host.
		self.conn = urllib3.connection_from_url(host)
		# It represent the current data while the crawling
		self.content = b''
		# We build a regular expression to get url link in a text
		self.HTML_TAG_REGEX = re.compile(r'<a[^<>]+?href=([\'\"])(.*?)\1', re.IGNORECASE)
		self.HTML_OUTER_REGEX = re.compile(r'>(.*?)<', re.IGNORECASE)
		# We build the user agent
		self.HEADERS = {
			"User-Agent": "Mozilla/5.0 (Windows NT 6.1; Win64; rv:74.0) Gecko/20100101 Firefox/74.0",
			"Accept": "text/html",
		}
		#
		self.wait = delay_func
		self.timeout = timeout
		# Output file of the logging
		self.logstream = open('%s.log' % time(), 'a')
		self.logstream.write('HOST: %s\n' % self.conn.host)
		self.results = {}

	# This method permit to get the content of a webpage
	def getContent(self):
		print('[INFO] Getting content from %s ...' % self.url, file=self.logstream)
		
		try:
			r = self.conn.request('GET', self.url, preload_content=False, headers=self.HEADERS, timeout=self.timeout)
		except urllib3.exceptions.MaxRetryError:
			self.content = ''
			print('[WARNING] Timeout exceed for %s, no content got' % self.url, file=self.logstream)
			return
		
		# We verify if the request has succeed
		if r.status != 200:
			if r.status == 404:
				print("[ERROR] [%s]: %s" % (r.status, self.url), file=self.logstream)
			else:
				raise Exception('CODE %s not managed' % r.status)
		# We get only html text file less than 100kb
		elif r.headers['Content-type'].startswith('text/html') and (('Content-Length' not in r.headers) or int(r.headers['Content-Length']) < 1024*100):
			# We decode the response
			try:
				self.content = r.data.decode()
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
					# /path (root path)
					# eg: /a/b/c a/b/c a/b/c.d
					self.url_to_crawl.append(urljoin(self.url, url.path))

	# This method permit to get the text in the webpage
	def getData(self):
		print('[INFO] Getting data from %s ...' % self.url, file=self.logstream)
		
		return self.HTML_OUTER_REGEX.findall(self.content)

	# This method start the crawling
	def start(self):
		print('[INFO] Crawling launched of %s ...' % self.conn.host, file=self.logstream)
		
		while self.url_to_crawl:
			self.wait()

			# We get the first url
			self.url = self.url_to_crawl.pop(0)
			
			if self.url in self.results:
				continue
			else:
				#print(self.url)
				print('[DEBUG] Crawling launched on %s ...' % self.url, file=self.logstream)
				self.getContent()
				self.results[self.url] = self.getData()
				self.getUrlLinks()

		# We save the data parse
		with open(str(time())+'.json', 'w') as f:
			json.dump(self.results, f)

if __name__ == '__main__':
	parser = ArgumentParser()
	parser.add_argument('HOST', help='Eg: http://example.com')
	parser.add_argument('-t', '--timeout', type=int, default=3600)
	parser.add_argument('-n', '--min_delay', type=int, default=1)
	parser.add_argument('-x', '--max_delay', type=int, default=5)
	args = parser.parse_args()
	Crawler(
		args.HOST,
		delay_func=lambda:sleep(randint(args.min_delay, args.max_delay)),
		timeout=args.timeout,
	).start()