#-*- coding: utf-8 -*-
from xml.etree import cElementTree as ET
from os.path import isfile, join
from natsort import natsorted
from bs4 import BeautifulSoup
from datetime import date
from os import listdir
import unicodedata
import HTMLParser
import requests
import difflib
import urllib2
import json
import re
import os

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

def get_series_name(filename, episode_number=False):
	rep = {".mkv": "", ".mp4": "", ".avi": ""}
	filename = replace_all(filename, rep)
	filename = re.sub(r'\[(?:[^\]|]*\|)?([^\]|]*)\]', '', filename).strip()
	filename = re.sub(r' +', ' ', filename)

	if not episode_number:
		# Don't know EP (Movie/OVA?)
		pass
	else:
		at = filename.index(str(episode_number))
		if filename[at-1:at] == "0":
			at = at - 1
		filename = filename[:at].strip()
		if filename.endswith("-"):
			filename = filename[:-1].strip()

	# Clean filenames that replaces spaces with "."
	fullstops = filename.count('.')
	if fullstops > 1:
		filename = filename.replace(".", " ").lstrip()

	# Clean filenames that replaces spaces with "_"
	fullstops = filename.count('_')
	if fullstops > 1:
		filename = filename.replace("_", " ").lstrip()
	return filename.strip()

def get_episode_number(filename):
	filename = re.sub(r'\[(?:[^\]|]*\|)?([^\]|]*)\]', '', filename).strip()
	match = re.search(r'\d{4}', filename)
	if match:
		if int(match.group()) < 2025 or int(match.group()) > 2010:
			filename = filename.replace(match.group(), "")
	match = re.search(
		r'''(?ix)				 # Ignore case (i), and use verbose regex (x)
		(?:					   # non-grouping pattern
		  | - | – |x|episode|^		   # e or x or episode or start of a line
		  )					   # end non-grouping pattern 
		\s*					   # 0-or-more whitespaces
		(\d{2}\.\d{1}|\d{1}\.\d{1}|\d{3}|\d{2})				   # exactly 2/3 digits
		''', filename)
	if match:
		episode_num = float(match.group(1))
		if (episode_num).is_integer():
			episode_num = int(episode_num)
		return episode_num
	else:
		# Couldn't get EP at all (Movie/OVA?)
		return False

def get_new_name(old):
	show_list = open('anime_data.txt').read().splitlines()
	for line in show_list:
		line = line.split("||")
		if old in line[0]:
			return line[1]
	return old

def get_if_stored(name):
	show_list = open('anime_data.txt').read().splitlines()
	for line in show_list:
		line = line.split("||")
		if name == line[1]:
			return True
	return False

def get_last_ep(name):
	show_list = open('anime_data.txt').read().splitlines()
	for line in show_list:
		line = line.split("||")
		if name in line[1]:
			return int(line[2])
	return 999

def get_remove_ep(name):
	show_list = open('anime_data.txt').read().splitlines()
	for line in show_list:
		line = line.split("||")
		if name in line[1]:
			return int(line[3])
	return 0

def get_subgroup(filename):
	if "[" in filename[0:5]:
		try:
			m = re.search(r"\[([A-Za-z0-9_]+)\]", filename)
			return m.group(1)
		except:
			return "NONE"
	else:
		return "NONE"

def store_new_name(old, new, max, math):
	show_list = open('anime_data.txt').read().splitlines()
	for line in show_list:
		line = line.split("||")
		if old in line[1]:
			return True
	new_line = "{0}||{1}||{2}||{3}\n".format(old, new, max, math)
	with open('anime_data.txt', 'a') as show_list:
		show_list.write(new_line)

	return True

def store_html(series_name, episode_number, video_rez, group, html):
	onlyfiles = [ f for f in listdir("html") if isfile(join("html",f)) ]
	search_name = "{0} - {1} [".format(series_name, episode_number)
	found_files = []
	for html_file in onlyfiles:
		if html_file.startswith(search_name):
			found_files.append(html_file)
	found_files = list(reversed(natsorted(found_files)))
	filename = "{0} - {1} [{2}] [{3}].html".format(series_name, episode_number, video_rez, group)
	if filename not in found_files:
		path = os.path.join("html", filename)
		found_files.append(filename)
		with open(path, 'w') as openfile:
			openfile.write(html)

	html = ""
	if episode_number <= 1 or not episode_number:
		try:
			info_file = "{0} - INFO.html".format(series_name)
			path = os.path.join("html", info_file)
			html += open(path, 'r').read()
		except:
			# No info from mal, etc.
			pass

	for html_file in found_files:
		path = os.path.join("html", html_file)
		html += open(path, 'r').read()
	return html

def html_decode(s):
	"""
	Returns the ASCII decoded version of the given HTML string,
	and replace BBCode with HTML/
	This does NOT remove normal HTML tags like <p>.
	"""
	htmlCodes = (
				("'", '&#39;'),
				('"', '&quot;'),
				('>', '&gt;'),
				('<', '&lt;'),
				('&', '&amp;'),
				('—', '&mdash;'),
				('-', '&#8211;'),
				('×', '&#215;'),
				('’', '&#8217;'),
				('<i>', '[i]'),
				('</i>', '[/i]'),
				('<strong>', '[b]'),
				('uu', 'ū'),
				('and', '&'),
				('</strong>', '[/b]')	
			)
	for code in htmlCodes:
		s = s.replace(code[1], code[0])
	s = ''.join((c for c in unicodedata.normalize('NFD', unicode(s)) if unicodedata.category(c) != 'Mn')).encode('utf-8')
	return s

def html_download_div(ser, ep, rez, filename="filename", links=[]):
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
	html = store_html(ser, ep, rez, get_subgroup(filename), html)
	return html

def html_info(series_name, anime_info, site):
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
	anime_info[2] = re.sub(r'\(Source:[^)]*\)', '', anime_info[2])
	if anime_info[2].endswith("<br />\n"):
		anime_info[2] = anime_info[2][:-7]
	if anime_info[2].endswith("<br />\n"):
		anime_info[2] = anime_info[2][:-7]
	html_0 = "<p style=\"text-align: center;\"><img src=\"%s\" width=\"225px\" height=\"318px\" /></p>"  % anime_info[1]
	html_1 = "<h3 style=\"text-align: center;\"><strong>Plot Summary</strong></h3>"
	html_2 = "<p style=\"text-align: center;\">" + html_decode(anime_info[2]) + "</p>"
	if site == "MAL":
		mal_url = "http://myanimelist.net/anime/" + anime_info[5]
	else:
		mal_url = "http://myanimelist.net/anime.php?q=" +  anime_info[0]
	if site == "ANN":
		ann_url = "http://www.animenewsnetwork.com/encyclopedia/anime.php?id=" + anime_info[5]
	else:
		ann_url = "http://www.animenewsnetwork.com/encyclopedia/search/name?q=" + anime_info[0].replace(" ", "+")
	ap_url = "http://www.anime-planet.com/anime/all?name=" + anime_info[0].replace(" ", "+")
	html_3 = "<p style=\"text-align: center;\"><a href=\"%s\">MAL</a> | <a href=\"%s\">ANN</a> | <a href=\"%s\">AP</a></p>" % \
			(mal_url, ann_url, ap_url)
	html = html_0 + html_1 + html_2 + html_3
	filename = "{0} - INFO.html".format(series_name)
	path = os.path.join("html", filename)
	with open(path, 'w') as openfile:
		openfile.write(html)
	return html

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
	elements = ET.fromstring(r.text)
	results = [dict((attr.tag, attr.text) for attr in el) for el in elements]
	full_names = []
	full_list = []
	for result in results:
		if result['synopsis'] is None:
			result['synopsis'] = "No synopsis."
		if result['episodes'] == "0":
			result['episodes'] = "999"
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
	store_new_name(orginal, anime_info[0], anime_info[4], 0)
	return html_info(anime_info[0], anime_info, "MAL")

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
	store_new_name(orginal, anime_info[0], anime_info[4], 0)
	return html_info(anime_info[0], anime_info, "ANN")

def get_series_info(name):
	print "Searching info for %s" % name
	anime_info = MyAnimeList_search(name)
	if anime_info == []:
		anime_info = AnimeNewsNetword_search(name)
	if anime_info == []:
		return False
	return anime_info