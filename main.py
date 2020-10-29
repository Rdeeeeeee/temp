from selenium import webdriver
from bs4 import BeautifulSoup
import re
import json as js
import pymongo
from collections import deque
import time
import requests


MONGO_HOST = 'localhost'
PORT = 27017
MONGO_DB = 'xhs'
MONGO_COLLECTION = 'note'
PROXY_POOL_URL = 'http://127.0.0.1:5555/random'


def note_get(article_id, proxy=None):
    """获取文章页面的信息
    :params article_id: str文章的id
    return dict:dict """
    dic = {}
    proxy = get_proxy()  # 相当于每次更换一次代理
    # TODO 修改为多少次更换一次代理，或者不响应了更换代理
    # print(proxy)
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument("--proxy-server=http://" + proxy)
    chrome_options.add_argument("--headless")
    browser = webdriver.Chrome(options=chrome_options)  # 使用Chrome浏览器
    browser.get("https://www.xiaohongshu.com/discovery/item/"+article_id)
    # TODO 捕获异常，没有响应怎么办？或者其他异常
    # 获取标题信息
    dic['title'] = browser.find_element_by_xpath('//h1[@class="title"]').text
    # print(dic['title'])
    # 获取内容信息
    dic['note'] = browser.find_element_by_xpath('//div[@class="content"]').text
    # 获取作者名
    dic['author'] = browser.find_element_by_xpath('//span[@class="name-detail"]').text
    # 获取作者信息
    html = browser.page_source
    bs = BeautifulSoup(html, 'lxml')
    dic['author_info'] = js.loads(bs.find('script', type='application/ld+json').string, strict=False)['author']
    # 获取文章id
    dic['article_id'] = re.match(r'^.*/(.*)$', browser.current_url).groups()[0]
    # 获取点赞数
    dic['like'] = browser.find_element_by_xpath('//span[@class="like"]').text
    # 获取评论数
    dic['comment'] = browser.find_element_by_xpath('//span[@class="comment"]').text
    # 获取收藏数
    dic['star'] = browser.find_element_by_xpath('//span[@class="star"]').text
    # 获取发布日期
    dic['publish_date'] = browser.find_element_by_xpath('//div[@class="publish-date"]').text
    # 获取照片链接，以列表的形式存储
    pics = browser.find_elements_by_xpath('//div[contains(@class, "each")]/i')
    dic['pics'] = list(map(lambda x: re.match(r'^.*"(.*)".*$', x.get_attribute('style')).group(1), pics))
    # 获取相关文章的id,用于进一步爬取
    related_notes = browser.find_elements_by_xpath('//div[@class="panel-list"]/a')
    dic['related_notes_lst'] = list(map(lambda x: re.match(r'^.*/(.*)$', x.get_attribute('href')).groups()[0], related_notes))
    # 关闭标签页
    browser.close()
    return dic, dic['related_notes_lst']


def author_get(author_id):
    """根据author_id获取author页面的相关信息
    :params author_id: str 作者编号
    return dict:author页面的相关信息"""
    dic = {}
    browser = webdriver.Chrome()  # 使用Chrome浏览器
    browser.get("https://www.xiaohongshu.com/user/profile/"+author_id)
    # 获取作者姓名
    dic['author_name'] = browser.find_element_by_xpath('//span[@class="name-detail"]').text
    # 获取作者简介
    dic['brief'] = browser.find_element_by_xpath('//div[@class="user-brief"]').text
    # 获取关注数
    dic['fellow'] = browser.find_elements_by_xpath('//div[@class="info"]/span[@class="info-number"]')[0].text
    # 获取粉丝数
    dic['fans'] = browser.find_elements_by_xpath('//div[@class="info"]/span[@class="info-number"]')[1].text
    # 获取赞和收藏数
    dic['like'] = browser.find_elements_by_xpath('//div[@class="info"]/span[@class="info-number"]')[2].text
    # 获取作者位置信息
    dic['location'] = browser.find_element_by_xpath('//span[@class="location-text"]').text
    # 获取作者页面的10条note
    ten_notes = browser.find_elements_by_xpath('//div[@class="note-info"]/a[@class="info"]')
    dic['ten_notes_lst'] = list(map(lambda x: re.match(r'^.*/(.*)$', x.get_attribute('href')).groups()[0], ten_notes))
    # 关闭标签页
    browser.close()
    return dic


def save_to_mongo(result, db):
    """将爬取到的信息存储到MongoDB
    :params result: dict 字典类型的爬取结果"""
    try:
        if db[MONGO_COLLECTION].insert_one(result):
            print('存储到MongoDB成功')
    except Exception:
        print('存储到MongoDB失败')


def get_proxy():
    """从代理池中获取代理"""
    try:
        response = requests.get("http://httpbin.org/get")
        if response.status_code == 200:
            return response.text
    except ConnectionError:
        return None


def main():
    """
    主程序
    """
    client = pymongo.MongoClient(MONGO_HOST, PORT)
    db = client[MONGO_DB]
    deq = deque()
    deq.append('5f842538000000000101eece')
    searched_lst = []
    while True:
        note_id = deq.popleft()
        if note_id in searched_lst:
            continue
        else:
            note, related_note = note_get(note_id)
            save_to_mongo(note, db)
            searched_lst.append(note_id)
            for i in related_note:
                if i in searched_lst:
                    break
                else:
                    deq.append(i)
            time.sleep(3)
        if len(searched_lst) >= 50:
            break
    print('searched_lst:', searched_lst, len(searched_lst))
    print('deq:', deq)


def test_proxy():
    proxy = get_proxy()
    print(proxy)
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument("--proxy-server=http://" + proxy)
    browser = webdriver.Chrome(options=chrome_options)  # 使用Chrome浏览器
    browser.get("http://httpbin.org/get")
    print(browser.page_source)


if __name__ == '__main__':
    main()
