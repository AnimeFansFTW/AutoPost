#-*- coding: utf-8 -*-
from utils import get_series_info
from utils import check_new_name
from utils import replace_all
from utils import scrape_site
import feedparser
#import requests # For another time
import hashlib
import cPickle
#import bencode # For another time
import urllib
import base64
import time
import re

import sys
reload(sys)
sys.setdefaultencoding("utf-8")

""" TODO:
Re-add episode remove/add support.
Sort out 1080p, 720p, 480p order for post
"""

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
	"1280×720": "", "": "", "mkv": "", "mp4": "", "avi": ""}
	filename = replace_all(filename, rep)
	if "movie" in filename.lower():
		return None
	if "persona" in filename.lower():
		filename = filename[10:]
	filename = re.sub(r'\[(?:[^\]|]*\|)?([^\]|]*)\]', '', filename).strip()
	temp_name = replace_all(filename, rep)
	match = re.search(
		r'''(?ix)				 # Ignore case (i), and use verbose regex (x)
		(?:					   # non-grouping pattern
		  | - | – |x|episode|^		   # e or x or episode or start of a line
		  )					   # end non-grouping pattern 
		\s*					   # 0-or-more whitespaces
		(\d{2}\.\d{1}|\d{1}\.\d{1}|\d{3}|\d{2}|\d{1})				   # exactly 2/3 digits
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
	rep = {"mkv": "", "mp4": "", "avi": "", " –": ":", " -": ""}
	filename = replace_all(filename, rep)
	if filename[-2] == ":":
		filename = filename[0:-2]
	filename = re.sub(' +',' ', filename).strip()
	old_filename = filename
	title_names = {}
	new = check_new_name(filename)
	if new is not None:
		filename = new
	return filename

def main():
	while True:
		rss_urls = ["http://www.otakubot.org/feed/",
		 "http://www.otakubot.org/feed/?paged=2",
		 "http://www.otakubot.org/feed/?paged=3"]
		d = []
		for url in rss_urls:
			d.extend(feedparser.parse(url).entries)
		try:
			already_used = cPickle.load(open('used_links.pkl', 'r'))
		except:
			already_used = []

		rss_count = 0
		for a in d:
			skip = False
			summary_html = ""
			filename = a.title
			post_id = a.guid
			html = ""
			if post_id in already_used:
				rss_count += 1
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
			try:
				episode_num = float(re_episode_num(filename))
				if (episode_num).is_integer():
					episode_num = int(episode_num)
			except:
				# Movie/OVA
				pass

			series_name = re_series_name(filename)
			anime_info = get_series_info(series_name)

			if anime_info[1] == "TV":
				post_title = series_name + " Episode " + str(episode_num)
			else:
				post_title = series_name

			if str(episode_num) == "1":
				summary_html = anime_info[2]
			elif episode_num is None:
				summary_html = anime_info[2]

			if series_name == "IGNORE":
				skip = True

			if skip != True:
				html = html_download_div(filename, download_urls)
				rss_count += 1
				try:
					while str(series_name) == str(re_series_name(d[rss_count].title)) and int(episode_num) == int(re_episode_num(d[rss_count].title)):
						next_post = d[rss_count]
						filename = next_post.title
						already_used.append(next_post.guid)
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
						html += html_download_div(filename, download_urls)
						rss_count += 1
						time.sleep(5)
				except:
					# Feed end
					pass

				already_used.append(post_id)
				print "New Post:"
				print post_title
				print "HTML:"
				print summary_html + "<br />" + html
				break

		cPickle.dump(already_used, open("used_links.pkl", 'w'))
		time.sleep(20)

if __name__ == "__main__":
	main()
	# Test stuff under
	"""
	test = "[FFF] Classroom Crisis – 01 [C6D2C330].mkv"
	try:
		episode_num = float(re_episode_num(test))
		if (episode_num).is_integer():
			episode_num = int(episode_num)
	except:
		# Movie/OVA
		pass
	page_title = re_series_name(test)
	anime_info = get_series_info(page_title)
	if anime_info[1] == "TV":
		post_title = page_title + " Episode " + str(episode_num)
	else:
		post_title = page_title
	print post_title
	quit()"""

