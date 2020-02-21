import requests
import xmltodict
import os
import re
from tqdm import tqdm
from bs4 import BeautifulSoup
import json


def parse_article(link):
    """
    Parses an SWI article
    :param link: A valid link to a SWI article
    :return: Parsed text, translator, comments and category
    """
    try:
        soup = BeautifulSoup(requests.get(link).content, features='lxml')
    except:
        return None
    article_body = soup.find('div', {"class": "article-body"})
    if article_body is None:
        return None
    text = [x.text for x in article_body.findChildren("p", recursive=False)]
    translator_node = soup.find('div', {"class": "article-body"}).findChildren("address")
    translator = translator_node[0].text if translator_node else ""
    comment_node = soup.find_all('div', {"class": "user-comment"})
    comments = [x.text for x in comment_node] if comment_node else []
    category_node = soup.find_all("span", {"itemprop": "keywords"})
    category = [x.text for x in category_node] if category_node else []

    return text, translator, comments, category


def parse_comments(id, lang):
    """
    Parses the comments for an SWI article
    :param id: The identifier for the article.
    :param lang: The language code for the article.
    :return: A list of comments for the article.
    """
    language_map = {
        "German": ("ger", 40000532),
        "English": ("eng", 40000108),
        "Arabic": ("ara", 40000690),
        "Spanish": ("spa", 40000430),
        "French": ("fre", 40000920),
        "Italian": ("ita", 40001010),
        "Japanese": ("jpn", 40000268),
        "Portuguese": ("por", 40000082),
        "Chinese": ("chi", 40000610),
        "Russian": ("rus", 40000348)
        }

    lstring, lcode = language_map[lang]
    try:
        comment_response = requests.get(f"https://www.swissinfo.ch/elastic/social/{lstring}/comments?teasable=contentbean:{id}&cmnavigation=contentbean:{lcode}&numberOfComments=100")
    except:
        return []
    soup = BeautifulSoup(comment_response.content, features='lxml')
    return [x.text for x in soup.find_all("div", attrs={"class": "user-comment"})]


# result = requests.get("https://www.swissinfo.ch/service/eng/rssxml/top-news/rss")
#
# rss_xml = result.content.decode("UTF-8")
# rss_dict = xmltodict.parse(rss_xml)
# articles = rss_dict['rss']['channel']['item']

article_cid_matcher = re.compile("https?://www\.swissinfo\.ch/.*?cid=(?P<articleid>\d+)")
article_id_matcher = re.compile("https?://www\.swissinfo\.ch/.*?/(?P<articleid>\d+)")

with open("article_list.json", 'r', encoding="UTF-8") as articles_json:
    articles = json.load(articles_json)

if os.path.exists("articles.json"):
    with open("articles.json", "r", encoding="UTF-8") as articles_json:
        output_articles = json.load(articles_json)
else:
    output_articles = []

for idx, article in enumerate(tqdm(articles[::-1])):

    if idx < len(output_articles):
        continue
    article_cid_match = article_cid_matcher.match(article["link"])

    if article_cid_match is None:
        continue

    try:
        soup = BeautifulSoup(requests.get(article["link"]).content, features='lxml')
    except:
        continue

    other_lang_nodes = soup.find(name="div", attrs={"class": "lngLink"})
    other_lang_nodes = other_lang_nodes.findChildren("ul")[0].findChildren("li") if other_lang_nodes else []
    languages = [x.text for x in other_lang_nodes]
    languages = [x.split()[0] for x in languages]
    links = [x.findChildren('a')[0]['href'] for x in other_lang_nodes]

    languages.append("English")
    links.append(article['link'])

    article['content'] = {}

    for link, language in zip(links, languages):

        article_id_match = article_id_matcher.match(link)

        parsed_article = parse_article(link)
        if not parsed_article:
            continue

        text, translator, comments, category = parsed_article

        article['content'][language] = {}
        if language == "English":
            article['content'][language]['id'] = article_cid_match.group("articleid")
        else:
            article['content'][language]['id'] = article_id_match.group("articleid")


        article['content'][language]['link'] = link
        article['content'][language]['text'] = text
        article['content'][language]['translator'] = translator
        article['content'][language]['comments'] = parse_comments(article['content'][language]['id'], language)
        article['content'][language]['cateogry'] = category

    if 'English' in article['content']:
        globalCategory = article['content']['English']['cateogry']
        if len(globalCategory) == 0:
            article['category'] = 'NA'
        else:
            article['category'] = globalCategory

        output_articles.append(article)

        with open("articles.json", "w", encoding="UTF-8") as articles_json:
            json.dump(output_articles, articles_json, ensure_ascii=False, indent=2)
