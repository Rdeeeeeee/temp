from bs4 import BeautifulSoup
import re
import json
import pymongo
from collections import deque
import time
import requests
from lxml import etree
import hashlib

DEQ = deque()
SEARCHED = []

MONGO_HOST = 'localhost'
MONGO_PORT = 27017
MONGO_DB = 'xhs'
MONGO_COLLECTION = 'requests_note'
PROXY_POOL_URL = 'http://127.0.0.1:5555/random'

ORDER_NO = "ZF202010307553xzHsqH"
SECRET = "5f3d33c12a4a42668fc06e0bbe9591ed"
IP = "forward.xdaili.cn"
PORT = "80"
IP_PORT = IP + ":" + PORT
TIMESTAMP = str(int(time.time()))
STRING = "orderno=" + ORDER_NO + "," + "secret=" + SECRET + "," + "timestamp=" + TIMESTAMP
MD5_STRING = hashlib.md5(STRING.encode('utf-8')).hexdigest()
SIGN = MD5_STRING.upper()
AUTH = "sign=" + SIGN + "&" + "orderno=" + ORDER_NO + "&" + "timestamp=" + TIMESTAMP
PROXY = {"http": "http://" + IP_PORT, "https": "https://" + IP_PORT}
HEADERS = {"Proxy-Authorization": AUTH,
           "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/85.0.4183.83 Safari/537.36"}


def note_get(note_id):
    """获取文章页面的信息
    :params article_id: str文章的id
    return dict:dict """
    r = requests.get("https://www.xiaohongshu.com/discovery/item/"+note_id, headers=HEADERS, proxies=PROXY, verify=False, allow_redirects=False)
    dic = {}
    if r.status_code == 200:
        html = etree.HTML(r.text)
        # 获取文章id
        dic['article_id'] = re.match(r'^.*/(.*)$', r.url).groups()[0]
        # 获取标题信息
        dic['title'] = html.xpath('//div[@class="note-top"]/h1[@class="title"]')[0].text.strip()
        # 获取内容信息
        dic['note'] = ''.join(html.xpath('//*[@id="app"]/div/div[2]/div[1]/main/div/p/text()'))
        # 获取作者名
        dic['author'] = html.xpath('//span[@class="name-detail"]')[0].text
        # 获取作者信息
        temp = r.text
        bs = BeautifulSoup(temp, 'lxml')
        dic['author_info'] = json.loads(bs.find('script', type='application/ld+json').string, strict=False)['author']
        # 获取点赞数
        dic['like'] = html.xpath('//span[@class="like"]/span')[0].text
        # 获取评论数
        dic['comment'] = html.xpath('//span[@class="comment"]/span')[0].text
        # 获取收藏数
        dic['star'] = html.xpath('//span[@class="star"]/span')[0].text
        # 获取发布日期
        dic['publish_date'] = html.xpath('//div[@class="publish-date"]/span')[0].text
        # 获取图片连接
        pic_lst = html.xpath('//div[contains(@class, "each")]/i/@style')
        dic['pics'] = list(map(lambda x: re.match('background-image:url(.*);', x).group(1)[1:-1], pic_lst))
        # url后面还差一点
        # 获取相关文章的id,用于进一步爬取
        related_notes = html.xpath('//div[@class="panel-list"]/a/@href')
        dic['related_notes'] = list(map(lambda x: re.match(r'^.*/(.*)$', x).groups()[0], related_notes))
        print(dic)
        return dic, dic['related_notes']
    else:
        f = open("error.txt", "a+")
        f.write(':'.join([note_id, str(r.status_code)]))
        f.write('\r\n')
        f.close()
        return None, None


def save_to_mongo(result, db):
    """将爬取到的信息存储到MongoDB
    :params result: dict 字典类型的爬取结果"""
    try:
        if db[MONGO_COLLECTION].insert_one(result):
            print('存储到MongoDB成功')
    except Exception:
        print('存储到MongoDB失败')


def main():
    """
    主程序
    """
    client = pymongo.MongoClient(MONGO_HOST, MONGO_PORT)
    db = client[MONGO_DB]
    while True:
        note_id = DEQ.popleft()
        if note_id in SEARCHED:
            continue
        else:
            note, related_notes = note_get(note_id)
            SEARCHED.append(note_id)
            if note and related_notes:
                save_to_mongo(note, db)
                SEARCHED.append(note_id)
                for j in related_notes:
                    bool(j in SEARCHED)
                    if j not in SEARCHED:
                        DEQ.append(j)
            else:
                f = open("rest.txt", "w")
                f.write(str(list(DEQ)))
                f.close()
                f = open("searched.txt", "w")
                f.write(str(SEARCHED))
                f.close()
                continue
        time.sleep(4)


if __name__ == '__main__':
    temp_lst = ['5f5224fd0000000001008490', '5f62c7f10000000001000d8b', '5f4aea1c000000000100982b', '5f6037b2000000000100693e', '5f50a3ee000000000101e58c', '5f676f300000000001009347', '5f38c1380000000001002dd1', '5f55c77000000000010062c3', '5f56e380000000000100a0d3', '5f60daf2000000000101d1ac']
    for i in temp_lst:
        DEQ.append(i)
    main()
