#-*- coding: utf-8 -*-
import feedparser
import hashlib
import cPickle
import urllib
import base64
import utils
import time
import re

import sys
reload(sys)
sys.setdefaultencoding("utf-8")

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
			if rss_count == 0:
				rss_count += 1
				continue
			skip = False
			summary_html = ""
			post_id = a.guid
			html = ""
			if post_id in already_used:
				rss_count += 1
				continue
			video_rez = utils.html_decode(re.findall('Video: (.*?)\<br />', \
				a.content[0]['value'])[0]).split(',')[2].split('×')[1].lstrip()
			filename = utils.html_decode(re.findall('Release name: (.*?)\<br />', \
				a.content[0]['value'])[0])
			magnet_link = re.findall('(magnet:\?xt=[^\"<]*)', \
				a.content[0]['value'])
			download_urls = re.findall('<a href="?\'?([^"\'>]*)', \
				a.content[0]['value'])
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

			episode_number = utils.get_episode_number(filename)
			series_name = utils.get_new_name(utils.get_series_name(filename, episode_number))
			if series_name == "SKIP":
				continue
			episode_number = episode_number + utils.get_remove_ep(series_name)

			if episode_number == utils.get_last_ep(series_name):
				# Is last episode
				post_title = "{0} Episode {1} Final".format(series_name, episode_number)
			elif not episode_number:
				# Is movie/ova
				post_title = "{0}".format(series_name)
			else:
				# Is normal episode
				post_title = "{0} Episode {1}".format(series_name, episode_number)
			# CHANGE TO 1
			if episode_number <= 1 or not episode_number:
				# New series
				if not utils.get_if_stored(series_name):
					utils.get_series_info(series_name)

			html = utils.html_download_div(series_name, episode_number, video_rez, \
					filename, download_urls)

			print "New Post:"
			print post_title
			print
			print "HTML:"
			print html
			already_used.append(post_id)
			break

		cPickle.dump(already_used, open("used_links.pkl", 'w'))
		time.sleep(15)

if __name__ == "__main__":
	main()