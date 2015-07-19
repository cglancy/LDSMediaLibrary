# TABLES
# category_table: id, name_text, parent_id
# category_video_table: video_id, category_id
# video_table: video_id, title_text, thumb_url, length_text, summary_text
# file_table: video_id, quality_text, url, size_text

from bs4 import BeautifulSoup
import requests
import json
import csv
from urllib.parse import urlparse

categories_url = 'https://www.lds.org/media-library/video/categories?lang=eng'
categories_url_ase = 'https://www.lds.org/media-library/video/categories?lang=eng&clang=ase'
categories_url_spa = 'https://www.lds.org/media-library/video/categories?lang=spa'

youth_category_url = 'https://www.lds.org/media-library/video/categories/youth?lang=eng'
video_id_with_bom_character = '2012-07-1010-a-message-to-students-of-the-book-of-mormon'
null_video_data_url = 'https://www.lds.org/media-library/video/social-media-sharable-videos?lang=eng&start=37&end=48&order=default'
topic_url = 'https://www.lds.org/media-library/video/categories/topics?lang=eng'
topic_humility_url = 'https://www.lds.org/media-library/video/topics/humility?lang=eng'
bom_url = 'https://www.lds.org/media-library/video/categories/book-of-mormon-list-view?lang=eng'
video_id_with_pop_character = '2012-06-3701-im-a-mormon-costa-rican-and-charmer-of-the-viola'
im_a_mormon_url = 'https://www.lds.org/media-library/video/categories/im-a-mormon?lang=eng'

biblevideo_category_url = 'https://www.lds.org/media-library/video/bible-videos-the-life-of-jesus-christ?lang=eng'
biblevideo_chrono_url = 'https://www.lds.org/media-library/video/categories/bible-videos-chronologically?lang=eng'
biblevideo_scripture_url = 'https://www.lds.org/media-library/video/categories/bible-videos-by-book?lang=eng'
biblevideo_category_path = '/media-library/video/bible-videos-the-life-of-jesus-christ'
biblevideo_extra_urls = {'Life of Jesus Videos Chronologically':biblevideo_chrono_url, 'Life of Jesus Videos by Book':biblevideo_scripture_url}

do_not_visit_path = '/media-library/video/categories/video-list-view'

next_category_id = 0
category_dict = {}
category_table = []
category_video_table = []
video_id_set = set()
video_table = []
file_table = []



def write_table(table, filename):
	with open(filename, 'w', newline='') as fp:
		writer = csv.writer(fp, delimiter=',')
		for row in table:
			writer.writerow(row)
		fp.close()

def get_video_stacks_data(soup):
	data_list = []
	select_list = soup.select('.video-stacks li h3 a')
	for a in select_list:
		data = {}
		data['url'] = a.attrs.get('href')
		data['title'] = a.text.strip()
		data_list.append(data)
	return data_list

def get_table_category(category_string):
	index = category_string.find(')')
	if index != -1:
		category = category_string[index+2:].strip()
	else:
		category = category_string.strip()
	return category

def get_video_id(relative_url):
	vid = ''
	if relative_url.startswith('/media-library/video/bible-videos-the-life-of-jesus-christ'):
		vid = relative_url[relative_url.find('#')+1:]
	else:
		vid = relative_url[21:relative_url.find('?')]
	return vid

def get_video_table_data(soup, page_url, parent_id):
	global next_category_id

	heading_id = parent_id

	select_list = soup.select('#primary table tbody tr td')
	for td in select_list:

		category = get_table_category(td.text)

		h2 = td.find('h2')
		a = td.find('a')

		if h2 and len(category) > 0:
			next_category_id += 1
			heading_id = next_category_id

			category_row = [heading_id, category, parent_id]
			category_table.append(category_row)

		elif a:
			if len(category) == 0:
				category = a.text
			if len(category) > 0:
				next_category_id += 1
				category_id = next_category_id

				vid = get_video_id(a.attrs.get('href'))

				category_row = [category_id, category, heading_id]
				category_table.append(category_row)

				category_video_row = [vid, category_id]
				category_video_table.append(category_video_row)

def process_data(data):
		page_url = data['page_url']
		category_id = data['category_id']
		videos = data['video_data']['videos']

		for vid, v in videos.items():

			downloads = v['downloads']
			for d in downloads:
				file_row = [vid, d['quality'], d['link'], d['size']]
				file_table.append(file_row)

			# special case handling for an unicode easter egg in one video title
			title = v['title']
			if vid == video_id_with_bom_character:
				title = title.replace('\ufeff', '')

			# special case for pop character
			summary = v['summary']
			if vid == video_id_with_pop_character:
				summary = summary.replace('\u202c', '')

			if vid not in video_id_set:
				video_id_set.add(vid)
				video_row = [vid, title, v['thumbURL'], v['length'], summary]
				video_table.append(video_row)

			category_video_row = [vid, category_id]
			category_video_table.append(category_video_row)

def get_video_data(soup, url, category_id):
	data = {}
	data['category_id'] = category_id;
	data['page_url'] = url;

	for script in soup.select('script'):
		text = script.get_text();
		if text.startswith('video_data'):
			video_data_text = text[text.find('{'):text.rfind('}')+1]
			if video_data_text.find('null') == -1:
				video_data = json.loads(video_data_text);
				data['video_data'] = video_data;
				process_data(data)

def visit_page(url, parent_id, page_title):
	global next_category_id

	parsed_url = urlparse(url)

	if parsed_url.path == do_not_visit_path:
		return

	print('visiting ' + url)

	response = requests.get(url)
	soup = BeautifulSoup(response.text)

	category_id = 0
	add_category = False
	if parsed_url.path in category_dict:
		category_id = category_dict[parsed_url.path]
	else:
		next_category_id += 1
		category_id = next_category_id
		category_dict[parsed_url.path] = category_id
		add_category = True

	get_video_data(soup, url, category_id)

	stacks_data = get_video_stacks_data(soup)
	if len(stacks_data) > 0:
		for stack_data in stacks_data:
			visit_page(stack_data['url'], category_id, stack_data['title'])
	else:
		get_video_table_data(soup, url, category_id)

	next_page_url = [a.attrs.get('href') for a in soup.select('.pagination .next')]
	if len(next_page_url) == 1:
		visit_page(next_page_url[0], parent_id, page_title)

	if add_category:
		category_row = [category_id, page_title, parent_id]
		category_table.append(category_row)

visit_page(categories_url, 0, 'LDS Media Library')

if biblevideo_category_path in category_dict:
	print('adding extra bible video categories')
	biblevideo_category = category_dict[biblevideo_category_path]
	for title in biblevideo_extra_urls:
		visit_page(biblevideo_extra_urls[title], biblevideo_category, title)

print('found {0} videos and {1} files.'.format(len(video_table), len(file_table)))

write_table(video_table, 'videos.csv')
write_table(file_table, 'files.csv')
write_table(category_table, 'categories.csv')
write_table(category_video_table, 'categoryvideos.csv')