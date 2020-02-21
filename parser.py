import requests
import xmltodict
import re
from bs4 import BeautifulSoup
import json


def parse_article(link):
    soup = BeautifulSoup(requests.get(link).content, features='lxml')

    text = [x.text for x in soup.find('div', {"class": "article-body"}).findChildren("p", recursive=False)]
    translator_node = soup.find('div', {"class": "article-body"}).findChildren("address")
    translator = translator_node[0].text if translator_node else ""
    comment_node = soup.find('div', {"class": "user-comment"})
    comments = [x.text for x in comment_node] if comment_node else []

    return text, translator, comments


def parse_comments(id, lang):
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

    comment_response = requests.get(f"https://www.swissinfo.ch/elastic/social/{lstring}/comments?teasable=contentbean:{id}&cmnavigation=contentbean:{lcode}&numberOfComments=100")
    soup = BeautifulSoup(comment_response.content, features='lxml')
    return [x.text for x in soup.find_all("div", attrs={"class": "user-comment"})]


result = requests.get("https://www.swissinfo.ch/service/eng/rssxml/top-news/rss")

rss_xml = result.content.decode("UTF-8")
rss_dict = xmltodict.parse(rss_xml)
articles = rss_dict['rss']['channel']['item']

article_id_matcher = re.compile("https://www.swissinfo.ch/.*?/.*?/(?P<articleid>\d+).*")

for article in articles:
    soup = BeautifulSoup(requests.get(article["link"]).content, features='lxml')

    other_lang_nodes = soup.find(name="div", attrs={"class": "lngLink"})
    other_lang_nodes = other_lang_nodes.findChildren("ul")[0].findChildren("li") if other_lang_nodes else []
    languages = [x.text for x in other_lang_nodes]
    languages = [x.split()[0] for x in languages]
    links = [x.findChildren('a')[0]['href'] for x in other_lang_nodes]

    languages.append("English")
    links.append(article['link'])

    article['content'] = {}

    for link, language in zip(links, languages):
        article['content'][language] = {}
        article['content'][language]['id'] = article_id_matcher.match(link).group("articleid")

        text, translator, comments = parse_article(link)
        article['content'][language]['text'] = text
        article['content'][language]['translator'] = translator
        article['content'][language]['comments'] = parse_comments(article['content'][language]['id'], language)

    with open("articles.json", "w", encoding="UTF-8") as articles_json:
        json.dump(articles, articles_json, ensure_ascii=False, indent=2)
