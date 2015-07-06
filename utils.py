#-*- coding: utf-8 -*-
from xml.etree import cElementTree as ET
from bs4 import BeautifulSoup
from datetime import date
import unicodedata
import HTMLParser
import requests
import difflib
import urllib2
import json
import re

import sys
reload(sys)
sys.setdefaultencoding("utf-8")

user_agent = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/34.0.1847.116 Safari/537.36"

MAL_USERNAME = ""
MAL_PASSWORD = ""

def replace_all(text, dic):
	for i, j in dic.iteritems():
		text = text.replace(i, j)
	return text

def scrape_site(url, xml=False):
	hdr = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.11 (KHTML, like Gecko) Chrome/23.0.1271.64 Safari/537.11',
	'Accept': 'text/html,application/xhtml+xml,application/json,application/xml;q=0.9,*/*;q=0.8',
	'Accept-Charset': 'ISO-8859-1,utf-8;q=0.7,*;q=0.3',
	'Accept-Encoding': 'none',
	'Accept-Language': 'en-US,en;q=0.8',
	'Connection': 'keep-alive'}
	request = urllib2.Request(url, headers=hdr)
	response = urllib2.urlopen(request)
	if xml:
		return ET.ElementTree(file=response)
	else:
		return BeautifulSoup(response)

def check_new_name(old):
	with open('anime_data.json') as data_file:    
		current_json = json.load(data_file)
	for name in current_json:
		if name.lower().strip() == old.lower().strip():
			# In json, has new name!
			for new in current_json[name.lower().strip()].iteritems():
				if new[0] == "new_name":
					return new[1]

	return

def store_new_name(old, anime_info):
	with open('anime_data.json') as data_file:    
		current_json = json.load(data_file)
	for name in current_json:
		if name.lower().strip() == old.lower().strip():
			# Already in json, no need to do anything.
			return
	template = {"new_name": anime_info[0],
				"image": anime_info[1],
				"summary": anime_info[2],
				"type": anime_info[3],
				"total_eps": anime_info[4],
				"id": anime_info[5],
				"source": anime_info[6],
				"remove_eps": "0"}
	current_json[old.lower().strip()] = (template)
	anime_data_file = open('anime_data.json', 'w')
	json.dump(current_json, anime_data_file, indent=4)
	anime_data_file.close()

def html_decode(s):
	"""
	Returns the ASCII decoded version of the given HTML string,
	and replace BBCode with HTML/
	This does NOT remove normal HTML tags like <p>.
	"""
	htmlCodes = (
				("'", '&#39;'),
				("’", '&amp;rsquo;'),
				('"', '&quot;'),
				('>', '&gt;'),
				('<', '&lt;'),
				('&', '&amp;'),
				('and', '&'),
				('—', '&mdash;'),
				('<i>', '[i]'),
				('</i>', '[/i]'),
				('<strong>', '[b]'),
				('uu', 'ū'),
				('</strong>', '[/b]')	
			)
	for code in htmlCodes:
		s = s.replace(code[1], code[0])
	s = ''.join((c for c in unicodedata.normalize('NFD', unicode(s)) if unicodedata.category(c) != 'Mn')).encode('utf-8')
	return s

def html_download_div(filename="filename", links=[]):
	OtakuShare = ""
	Torrent = ""
	Magnet = ""
	Go4UP = ""
	Hugefiles = ""
	Uploaded = ""
	for link in links:
		if "otakushare.com" in link:
			OtakuShare = link
		elif "go4up.com" in link:
			Go4UP = link
		elif "hugefiles.net" in link:
			Hugefiles = link
		elif "uploaded.net" in link:
			Uploaded = link
		elif "nyaa.se" in link:
			Torrent = link
		elif "magnet:" in link:
			Magnet = link
	html = r"""
<div class="dl-box">
	<div class="dl-title">{0}</div>
	<div class="dl-item"><a href="{1}">OtakuShare</a> <strong><span style="color: #800000;">◀◀</span></strong> <strong><span style="color: #000000;">Recommended</span></strong></div>
	<div class="dl-item"><a href="{2}">Torrent</a> <a href="{3}">(Magnet)</a> ◇ <a href="{4}">Go4UP</a> ◇ <a href="{5}">Hugefiles</a> ◇ <a href="{6}">Uploaded</a></div>
</div>""".format(filename, OtakuShare, Torrent, Magnet, Go4UP, Hugefiles, Uploaded)
	return html

def html_info(anime_info, site):
	"""
	anime_info:-
	[0] = Series Name 
	[1] = Series Image 
	[2] = Series Summary (+ Genres)
	[3] = Series Type (TV/Movie/OVA)
	[4] = Series Episodes
	[5] = Site Series ID
	[6] = Site Used
	"""
	html_0 = "<p style=\"text-align: center;\"><img src=\"%s\" width=\"225px\" height=\"318px\" /></p>"  % anime_info[1]
	html_1 = "<h3 style=\"text-align: center;\"><strong>Plot Summary</strong></h3>"
	html_2 = "<p style=\"text-align: center;\">" + anime_info[2]
	if site == "MAL":
		mal_url = "http://myanimelist.net/anime/" + anime_info[5]
	else:
		mal_url = "http://myanimelist.net/anime.php?q=" +  anime_info[0]
	if site == "ANN":
		ann_url = "http://www.animenewsnetwork.com/encyclopedia/anime.php?id=" + anime_info[5]
	else:
		ann_url = "http://www.animenewsnetwork.com/encyclopedia/search/name?q=" + anime_info[0].replace(" ", "+")
	ap_url = "http://www.anime-planet.com/anime/all?name=" + anime_info[0].replace(" ", "+")
	html_3 = "<br /><a href=\"%s\">MAL</a> | <a href=\"%s\">ANN</a> | <a href=\"%s\">AP</a>" % \
			(mal_url, ann_url, ap_url)
	return html_0 + html_1 + html_2 + html_3

def MyAnimeList_search(query):
	if query == "":
		return False
	orginal = query
	base_url = "http://myanimelist.net/api"
	payload = {'q': query.lower()}
	r = requests.get(
		base_url + '/anime/search.xml',
		params=payload,
		auth=(MAL_USERNAME, MAL_PASSWORD),
		headers={'User-Agent': user_agent}
	)
	if (r.status_code == 204):
		return []
	xml_string = html_decode(r.text)
	elements = ET.fromstring(xml_string)
	results = [dict((attr.tag, attr.text) for attr in el) for el in elements]
	full_names = []
	full_list = []
	for result in results:
		if result['synopsis'] is None:
			result['synopsis'] = "No synopsis."
		if result['episodes'] == "0":
			result['episodes'] = "??"
		full_names.append(result['title'].lower())
		full_list.append([result['title'], result['image'], html_decode(result['synopsis']), result['type'], result['episodes'], result['id'], "MAL"])
	series_name = difflib.get_close_matches(query.lower(), full_names, 1, 0.25)
	if series_name == []:
		# No named found, try second search.
		return []
	else:
		series_name = series_name[0]
		for anime in full_list:
			if series_name.lower().strip() == anime[0].lower().strip():
				anime_info = anime
				break
	#if series_name.lower().strip() != orginal.lower().strip():
	store_new_name(orginal, anime_info)
	return [series_name, anime_info[3], html_info(anime_info, "MAL")]

def AnimeNewsNetword_search(query):
	if query == "":
		return False
	base_url = "http://cdn.animenewsnetwork.com/encyclopedia/api.xml?anime="
	url = "http://www.animenewsnetwork.com/encyclopedia/search/name?q="
	orginal = query
	query = query.replace(" ", "+")
	url = url + query
	soup = scrape_site(url)
	a_links = soup.findAll('a')
	good_resutls = []
	temp_name = []
	anime_html = ""
	for a in a_links:
		if "encyclopedia/anime.php?id=" in a['href']:
			good_resutls.append([html_decode(a.text), a['href']])
			temp_name.append(html_decode(a.text))
	series_names = difflib.get_close_matches(query.lower(), temp_name, 1, 0.25)
	if series_names == []:
		# No results found, go from filename
		return []
	if len(series_names) == 1:
		series_name = series_names[0]
	else:
		# More than one name, do some checks as ANN naming is weird
		query = query + " (TV %s)" % str(date.today().year)
		series_names = difflib.get_close_matches(query, temp_name)
		series_name = series_names[0]

	for a, b in good_resutls:
		if a == series_name:
			url = base_url + b.split("id=")[1]
			break
	r = requests.get(
		url,
		headers={'User-Agent': user_agent}
	)
	if (r.status_code == 204):
		return []
	xml_string = html_decode(r.text)
	elements = ET.fromstring(xml_string)
	full_list = []
	anime_gens = []
	title = ""
	image = ""
	synopsis = ""
	show_type = ""
	total_eps = "??"
	for elm in elements:
		show_type = elm.get('type')
		anime_id = elm.get('id')
		for result in elm:
			if result.tag == "info":
				if result.get('type') == "Picture":
					for img in result[-1]:
						image = img.get('src')
						break
				if result.get('type') == "Main title":
					title = result.text
				if result.get('type') == "Genres" or result.get('type') == "Themes":
					anime_gens.append(str(result.text).title())
				if result.get('type') == "Plot Summary":
					synopsis = result.text
					if anime_gens != []:
						synopsis += "<br /><b>Genres: </b>" + ', '.join(anime_gens)
				if result.get('type') == "Number of episodes":	
					total_eps = result.text

	series_name = re.sub(r'\(TV[^)]*\)', '', series_name).strip()
	anime_info = [title, image, synopsis, show_type, total_eps, anime_id, "ANN"]
	store_new_name(orginal, anime_info)
	return [series_name, anime_info[3], html_info(anime_info, "ANN")]

def get_series_info(name):
	anime_info = MyAnimeList_search(name)
	if anime_info == []:
		anime_info = AnimeNewsNetword_search(name)
	if anime_info == []:
		return False
	return anime_info