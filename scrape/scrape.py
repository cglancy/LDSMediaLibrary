

from bs4 import BeautifulSoup
import requests
import json
from urllib.parse import urlparse
from lxml import etree

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

category_dict = {}
video_id_set = set()
file_count = 0



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

def get_video_table_data(soup, page_url, parent_node):

	heading_node = parent_node

	select_list = soup.select('#primary table tbody tr td')
	for td in select_list:

		category = get_table_category(td.text)

		h2 = td.find('h2')
		a = td.find('a')

		if h2 and len(category) > 0:
			heading_node = etree.SubElement(parent_node, 'category', name=category)

		elif a:
			if len(category) == 0:
				category = a.text
			if len(category) > 0:
				category_node = etree.SubElement(heading_node, 'category', name=category)

				vid = get_video_id(a.attrs.get('href'))

				video_ref = etree.SubElement(category_node, 'videoref', id=vid)

def process_data(data):
	global videos_element
	global file_count

	page_url = data['page_url']
	category_node = data['category_node']
	videos = data['video_data']['videos']

	for vid, v in videos.items():

		video_ref = etree.SubElement(category_node, 'videoref', id=vid)

		if vid not in video_id_set:
			video_id_set.add(vid)

			# special case handling for an unicode easter egg in one video title
			title = v['title']
			if vid == video_id_with_bom_character:
				title = title.replace('\ufeff', '')

			# special case for pop character
			summary = v['summary']
			if vid == video_id_with_pop_character:
				summary = summary.replace('\u202c', '')

			video_element = etree.SubElement(videos_element, 'video', id=vid, title=title, summary=summary,
				thumbUrl=v['thumbURL'], length=v['length'])

			downloads = v['downloads']
			for d in downloads:
				file_count += 1
				file_element = etree.SubElement(video_element, 'file', quality=d['quality'], link=d['link'], size=d['size'])

def get_video_data(soup, url, category_node):
	data = {}
	data['category_node'] = category_node;
	data['page_url'] = url;

	for script in soup.select('script'):
		text = script.get_text();
		if text.startswith('video_data'):
			video_data_text = text[text.find('{'):text.rfind('}')+1]
			video_data = json.loads(video_data_text);
			data['video_data'] = video_data;
			process_data(data)

def visit_page(url, parent_node, page_title):

	parsed_url = urlparse(url)

	if parsed_url.path == do_not_visit_path:
		return

	print('visiting ' + url)

	response = requests.get(url)
	soup = BeautifulSoup(response.text)

	if parsed_url.path in category_dict:
		category_node = category_dict[parsed_url.path]
	else:
		category_node = etree.SubElement(parent_node, 'category', name=page_title)
		category_dict[parsed_url.path] = category_node

	get_video_data(soup, url, category_node)

	stacks_data = get_video_stacks_data(soup)
	if len(stacks_data) > 0:
		for stack_data in stacks_data:
			visit_page(stack_data['url'], category_node, stack_data['title'])
	else:
		get_video_table_data(soup, url, category_node)

	next_page_url = [a.attrs.get('href') for a in soup.select('.pagination .next')]
	if len(next_page_url) == 1:
		visit_page(next_page_url[0], parent_node, page_title)


library = etree.Element('library', name='LDS Media Library')
categories = etree.SubElement(library, 'categories')
videos_element = etree.SubElement(library, 'videos')
root_node = etree.SubElement(categories, 'category', name='LDS Media Library')

root_url = categories_url
parsed_url = urlparse(root_url)
category_dict[parsed_url.path] = root_node

visit_page(root_url, root_node, 'LDS Media Library')

if biblevideo_category_path in category_dict:
	print('adding extra bible video categories')
	biblevideo_category = category_dict[biblevideo_category_path]
	for title in biblevideo_extra_urls:
		visit_page(biblevideo_extra_urls[title], biblevideo_category, title)

print('found {0} videos and {1} files.'.format(len(video_id_set), file_count))

tree = etree.ElementTree(library)
tree.write("lds-media-library.xml", encoding='utf-8', xml_declaration=True, pretty_print=True)

