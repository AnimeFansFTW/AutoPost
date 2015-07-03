def replace_all(text, dic):
	for i, j in dic.iteritems():
		text = text.replace(i, j)
	return text

def scrape_site(url, xml=False):
	from bs4 import BeautifulSoup
	import urllib2
	hdr = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.11 (KHTML, like Gecko) Chrome/23.0.1271.64 Safari/537.11',
	'Accept': 'text/html,application/xhtml+xml,application/json,application/xml;q=0.9,*/*;q=0.8',
	'Accept-Charset': 'ISO-8859-1,utf-8;q=0.7,*;q=0.3',
	'Accept-Encoding': 'none',
	'Accept-Language': 'en-US,en;q=0.8',
	'Connection': 'keep-alive'}
	request = urllib2.Request(url, headers=hdr)
	response = urllib2.urlopen(request)
	if xml:
		import xml.etree.cElementTree as ET
		return ET.ElementTree(file=response)
	else:
		return BeautifulSoup(response)