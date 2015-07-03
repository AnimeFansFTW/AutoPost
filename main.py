#-*- coding: utf-8 -*-
from utils import replace_all
from utils import scrape_site
import feedparser
import requests
import hashlib
import cPickle
#import bencode # For another time
import urllib
import base64
import time
import re

def find_mal(anime_name):
	# Temp
	# For support of movies and OVAs later
	anime_type = "TV"
	#####
	img_html = ""
	summary_html = "<center><h3><b>Plot Summary</b></h3><br />"
	anime_gens = []
	url_api = "http://cdn.animenewsnetwork.com/encyclopedia/api.xml?anime="
	url = "http://www.animenewsnetwork.com/encyclopedia/search/name?q="
	anime_name = anime_name.replace(" ", "+")
	url = url + anime_name + "+"
	soup = scrape_site(url)
	a_links = soup.findAll('a')
	anime_html = ""
	for a in a_links:
		if "encyclopedia/anime.php?id=" in a['href']:
			if anime_type == "TV" and " (TV)" in str(a):
				anime_html = a
				break
	anime_id = anime_html['href'].split("id=")[1]
	url = url_api + anime_id
	soup = scrape_site(url, True)
	root = soup.getroot()
	for child in root:
		irit = 0
		for babu_child in child:
			if irit == 0:
				# First one, will have image data
				for info in babu_child:
					# Nothing for now. ANN images are terrible
					pass
			if babu_child.tag == "info":
				for keys, values in babu_child.attrib.items():
					if values == "Main title":
						global series_name
						try:
							print babu_child.text
							series_name = babu_child.text
							series_name = series_name.encode('utf-8')
						except:
							# Name has some shit in it, best to keep with original
							pass

					if values == "Genres" or values == "Themes":
						anime_gens.append(str(babu_child.text).title())

					if values == "Plot Summary":
						summary_html += babu_child.text
			irit += 1
	ann_url = "http://www.animenewsnetwork.com/encyclopedia/anime.php?id=" + anime_id
	mal_url = "http://myanimelist.net/anime.php?q=" + anime_name
	mal_html = "<br /><a href=\"%s\">MAL</a> | <a href=\"%s\">ANN</a>" % (mal_url, ann_url)
	summary_html += "<br /><b>Genres:</b> " + ', '.join(anime_gens) + mal_html + "</center>"
	summary_html = summary_html.encode('utf-8')
	return summary_html

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

def re_episode_num(filename):
	rep = {"480p": "", "720p": "", "1080p": "", \
	"1280×720": "", "": "",}
	filename = re.sub(r'\[(?:[^\]|]*\|)?([^\]|]*)\]', '', filename).strip()
	temp_name = replace_all(filename, rep)
	match = re.search(
		r'''(?ix)				 # Ignore case (i), and use verbose regex (x)
		(?:					   # non-grouping pattern
		  e| - | – |.|x|episode|^		   # e or x or episode or start of a line
		  )					   # end non-grouping pattern 
		\s*					   # 0-or-more whitespaces
		(\d{3}|\d{2})				   # exactly 2/3 digits
		''', temp_name)
	if match:
		return match.group(1)

def re_series_name(filename):
	filename = re.sub(r'\[(?:[^\]|]*\|)?([^\]|]*)\]', '', filename).strip()
	epinum = re_episode_num(filename)
	if epinum is None:
		# Movie / one off OVA/ONA
		pass
	else:
		at = filename.index(epinum)
		filename = filename[:at]
	fullstops = filename.count('.')
	if fullstops > 1:
		filename = filename.replace(".", " ")
	rep = {".mkv": "", ".mp4": "", ".avi": "",}
	filename = replace_all(filename, rep)
	filename = filename.replace(" - ", "").replace(" – ", "")
	filename = re.sub(' +', ' ', filename).strip()
	old_filename = filename
	title_names = {}
	new_names = open("filenames_to_posts.txt", "r").read().splitlines()
	for line in new_names:
		line = line.split("||")
		try:
			ep_remove = line[2]
		except:
			ep_remove = 0
		title_names[line[0].lower().strip()] = [line[1].lstrip(), ep_remove]
	try:
		# Name replacement found
		filename = title_names[old_filename.lower()][0].strip()
		global episode_num
		episode_num = int(episode_num) + int(title_names[old_filename.lower()][1])
	except:
		# No name replacement found
		pass
	return filename

while True:
	d = feedparser.parse('http://www.otakubot.org/feed/')

	try:
		already_used = cPickle.load(open('used_links.pkl', 'r'))
	except:
		already_used = []

	rss_count = 0
	for a in d.entries:
		skip = False
		summary_html = ""
		file_name = a.title.encode('utf-8').replace(" mkv", ".mkv").replace(" avi", ".avi").replace(" mp4", ".mp4")
		post_id = a.guid.encode('utf-8')
		html = ""
		if post_id in already_used:
			continue
		magnet_link = re.findall('(magnet:\?xt=[^\"<]*)', \
			a.content[0]['value'].decode('utf-8'))
		download_urls = re.findall('<a href="?\'?([^"\'>]*)', \
			a.content[0]['value'].decode('utf-8'))
		download_urls.append(magnet_link)
		if "otakubot" in download_urls[0] or "zupimages" in download_urls[0]:
			download_urls.pop(0)
		if "otakubot" in download_urls[0] or "zupimages" in download_urls[0]:
			download_urls.pop(0)

		count = 0
		for url in download_urls:
			if "Go4UP" in url[20:]:
				download_urls[count] = url.replace("Go4UP", "")
			elif "Hugefiles" in url[20:]:
				download_urls[count] = url.replace("Hugefiles", "")
			elif "Uploaded" in url[20:]:
				download_urls[count] = url.replace("Uploaded", "")
			elif "Torrent" in url[20:]:
				download_urls[count] = url.replace("Torrent", "")
				download_urls[count + 1] = get_magnet(download_urls[count])
			count += 1
		series_name = re_series_name(file_name)
		episode_num = re_episode_num(file_name)
		if not episode_num:
			# Movie/OVA/ONA
			# Try looking at MAL first
			# For now default to movie
			episode_num = "MOVIE"
		elif int(episode_num) == 1:
			summary_html = find_mal(series_name)
		if series_name == "IGNORE":
			skip = True
		if skip != True:
			html = html_download_div(file_name, download_urls)
			while series_name == re_series_name(d.entries[rss_count + 1].title.encode('utf-8')) and episode_num == re_episode_num(file_name):
				next_post = d.entries[rss_count + 1]
				file_name = next_post.title.encode('utf-8').replace(" mkv", ".mkv").replace(" avi", ".avi").replace(" mp4", ".mp4")
				already_used.append(next_post.guid.encode('utf-8'))
				download_urls = re.findall('<a href="?\'?([^"\'>]*)', \
						next_post.content[0]['value'].decode('utf-8'))
				count = 0
				for url in download_urls:
					if "Go4UP" in url[20:]:
						download_urls[count] = url.replace("Go4UP", "")
					elif "Hugefiles" in url[20:]:
						download_urls[count] = url.replace("Hugefiles", "")
					elif "Uploaded" in url[20:]:
						download_urls[count] = url.replace("Uploaded", "")
					elif "Torrent" in url[20:]:
						download_urls[count] = url.replace("Torrent", "")
					count += 1
				html += html_download_div(file_name, download_urls)
				rss_count += 1
			if episode_num == "MOVIE":
				post_title = series_name
			else:
				post_title = series_name + " Episode " + str(int(episode_num))
			already_used.append(post_id)
			#Not found, create post.
			#create_post(post_title, series_name, html)
			print "New Post:"
			print post_title
			print "HTML:"
			print summary_html + "<br />" + html
			break

	cPickle.dump(already_used, open("used_links.pkl", 'w'))
	time.sleep(30)
	#time.sleep(1 * 60)