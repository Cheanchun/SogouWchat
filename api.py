# coding=utf-8
import random
import re
import time
from urllib.parse import urlencode

import requests
from lxml import etree

from const import agents, _WechatSogouSearchArticleTimeConst
from exceptions import WechatSogouRequestsException
from exceptions import WechatSogouVcodeOcrException
from identify_image import identify_image_callback_by_hand
from identify_image import unlock_sogou_callback_example
from identify_image import ws_cache

index_url = "https://weixin.sogou.com/"


class WechatSogouAPI:
    def __init__(self, captcha_break_time=1, headers=None, **kwargs):
        assert isinstance(captcha_break_time, int) and 0 < captcha_break_time < 20

        self.captcha_break_times = captcha_break_time
        self.requests_kwargs = kwargs
        self.headers = headers
        if self.headers:
            self.headers['User-Agent'] = random.choice(agents)

        else:
            self.headers = {'User-Agent': random.choice(agents)}
        self.gzh_query_url = "https://weixin.sogou.com/weixin?{}"
        self.base_url = "https://weixin.sogou.com/weixin"
        self.index_url = "https://weixin.sogou.com/"

    def __set_cookie(self, suv=None, snuid=None, referer=None):
        suv = ws_cache.get('suv') if suv is None else suv
        snuid = ws_cache.get('snuid') if snuid is None else snuid
        _headers = {'Cookie': 'SUV={};SNUID={};'.format(suv, snuid)}
        if referer is not None:
            _headers['Referer'] = referer
        return _headers

    def __get(self, url, session, headers):
        h = {}
        if headers:
            for k, v in headers.items():
                h[k] = v
        if self.headers:
            for k, v in self.headers.items():
                h[k] = v
        if url:
            resp = session.get(url, headers=h, **self.requests_kwargs)
        else:
            raise Exception("__get:url为空", )
        if not resp.ok:
            raise WechatSogouRequestsException('WechatSogouAPI get error', resp)
        return resp

    def __set_cache(self, suv, snuid):
        ws_cache.set('suv', suv)
        ws_cache.set('snuid', snuid)

    def __unlock_sogou(self, url, resp, session, unlock_callback=None, identify_image_callback=None):
        if unlock_callback is None:
            unlock_callback = unlock_sogou_callback_example
        millis = int(round(time.time() * 1000))
        r_captcha = session.get('http://weixin.sogou.com/antispider/util/seccode.php?tc={}'.format(millis), headers={
            'Referer': url,
        })
        if not r_captcha.ok:
            raise WechatSogouRequestsException('WechatSogouAPI get img', r_captcha)
        r_unlock = unlock_callback(url, session, resp, r_captcha.content, identify_image_callback)
        if r_unlock['code'] != 0:
            raise WechatSogouVcodeOcrException(
                '[WechatSogouAPI identify image] code: {code}, msg: {msg}'.format(code=r_unlock.get('code'),
                                                                                  msg=r_unlock.get('msg')))
        else:
            self.__set_cache(session.cookies.get('SUID'), r_unlock['id'])

    def __get_by_unlock(self, url, referer=None, unlock_platform=None, unlock_callback=None,
                        identify_image_callback=None, session=None):
        assert unlock_platform is None or callable(unlock_platform)
        if identify_image_callback is None:
            identify_image_callback = identify_image_callback_by_hand
        assert unlock_callback is None or callable(unlock_callback)
        assert callable(identify_image_callback)

        if not session:
            session = requests.session()
        resp = self.__get(url, session, headers=self.__set_cookie(referer=referer))
        resp.encoding = 'utf-8'
        if 'antispider' in resp.url or '请输入验证码' in resp.text:
            for i in range(self.captcha_break_times):
                try:
                    unlock_platform(url=url, resp=resp, session=session, unlock_callback=unlock_callback,
                                    identify_image_callback=identify_image_callback)
                    break
                except WechatSogouVcodeOcrException as e:
                    if i == self.captcha_break_times - 1:
                        raise WechatSogouVcodeOcrException(e)

            if '请输入验证码' in resp.text:
                headers = self.__set_cookie(referer=referer)
                headers['User-Agent'] = 'Mozilla/5.0 (Windows NT 6.1; WOW64)'
                resp = self.__get(url, session, headers)
                resp.encoding = 'utf-8'
        return resp

    @staticmethod
    def _paras_gzh_list(resp):
        gzh_list = []
        html = etree.HTML(resp.text)
        query_list = html.xpath("//ul[@class='news-list2']/li")
        for item in query_list:
            data = {}
            try:
                data["wx_pub_id"] = "".join(
                    item.xpath(".//p[@class='info']/label[@name='em_weixinhao']/text()"))  # 微信号
                data["wx_name"] = "".join(item.xpath(".//p[@class='tit']/a//text()"))  # 公众号名称
                data["wx_query_id"] = "".join(item.xpath(".//@d"))  # 查询ID
                data["wx_identify_company"] = "".join(
                    [i.strip() for i in item.xpath(".//i[@class='identify']/parent::dd/text()")])  # 认证公司名称
                data["recently_article"] = "".join(item.xpath(".//a[@uigs]/text()"))  # 最近文章title
                # data["source_url"] = "" # todo 解析文章链接
                gzh_list.append(data)
            except Exception as e:
                raise KeyError("页面错误", resp.content.decode("utf-8"), e.args)
        return gzh_list

    def get_wx_info(self, gzh_name: str, unlock_sogou_callback=None) -> list:
        """
        用于获取微信公众号相关信息,如果公众号名称或者ID确定,那么列表第一个就是要搜索的公众号

        :return:
        [
            {
            "wx_pub_id": 微信号
            "wx_name": 微信名称
            "wx_query_id": 私有ID
            "wx_identify_company": 微信认证公司
            "recently_article" 最近文章名称
            },
            {..}..
        ]
        """
        params = {"type": 1,
                  "query": gzh_name,
                  "ie": "utf-8",
                  "s_from": "input",
                  "_sug_": "n",
                  "_sug_type_": ""
                  }
        url = self.gzh_query_url.format(urlencode(params))
        if unlock_sogou_callback is None:
            unlock_sogou_callback = self.__unlock_sogou
        while url:
            resp = self.__get_by_unlock(url, referer=url, unlock_platform=unlock_sogou_callback)
            gzh_list = self._paras_gzh_list(resp)
            url = self._is_exist_next_page(resp=resp)
            yield gzh_list

    @staticmethod
    def paras_list(resp) -> list:
        articles = []
        resp.encoding = "utf-8"
        html = etree.HTML(resp.text)
        for item in html.xpath("//ul[@class='news-list']/li"):
            data = {}
            data["title"] = "".join([i.strip() for i in item.xpath(".//h3/a/text()")])
            data["brief"] = "".join([i.strip() for i in item.xpath(".//div[@class='txt-box']/p//text()")])
            data["pub_gzh"] = "".join([i.strip() for i in item.xpath(".//div[@class='s-p']/a//text()")])
            data["pub_time"] = time.strftime('%Y-%m-%d', time.localtime(int(item.xpath(".//div[@class='s-p']/@t")[0])))
            data["source_url"] = "".join(item.xpath(".//div[@class='txt-box']/h3/a/@data-share"))
            articles.append(data)
        return articles

    def query_article(self, keyword: str, gzh: str = None,
                      sec_id: str = None,
                      tsn: str = _WechatSogouSearchArticleTimeConst.anytime,
                      ft: str = None,
                      et: str = None,
                      interation: str = None,
                      unlock_sogou_callback=None) -> list:
        """
        通过私有ID或者公众号名称查询与该公众号有关的关键字相关文章

        :param keyword: 查询关键字
        :param gzh: 公众号名称
        :param sec_id: 微信私有ID
        :param tsn: 查询时间类型 1:一天内,2:一周内,3:一月内,4:一年内,5:自定义时间
        :param ft:自定义开始时间 format-eg:2019-06-08
        :param et:自定义结束时间
        :return:文章列表
        """
        url = "https://weixin.sogou.com/weixin?{}"
        if not sec_id and gzh:
            gzh_list = self.get_wx_info(gzh)
            sec_id = next(gzh_list)[0].get("wx_query_id") if gzh_list else None
        assert sec_id is not None
        if tsn is "5" and not ft and not et:
            raise KeyError("参数错误")
        elif tsn is "5" and ft and et:
            if not re.match("\d{4}-[01]\d-[01]\d", et) and not re.match("\d{4}-[01]\d-[01]\d", ft):
                raise KeyError("date error", ft, et)
        params = {
            "type": 2,
            "ie": "utf-8",
            "query": keyword,
            "wxid": sec_id,
            "usip": gzh,
            "tsn": tsn,
            "ft": ft,
            'et': et,
            "interation": interation
        }
        url = url.format(urlencode(params))
        if unlock_sogou_callback is None:
            unlock_sogou_callback = self.__unlock_sogou
        while url:
            resp = self.__get_by_unlock(url, referer=url, unlock_platform=unlock_sogou_callback)
            gzh_list = self.paras_list(resp)
            url = self._is_exist_next_page(resp=resp)
            yield gzh_list

    @staticmethod
    def get_article_content(url, session=None):
        session = requests.Session() if not session else session
        resp = session.get(url)
        return resp.text

    @staticmethod
    def _is_exist_next_page(resp):
        base_url = "https://weixin.sogou.com/weixin"
        if "下一页" in resp.text:
            return base_url + str(etree.HTML(resp.text).xpath("//a[@id='sogou_next']/@href")[0])
        else:
            return False


if __name__ == '__main__':
    t = WechatSogouAPI()
    KEY = ""
    while KEY != "quit":
        KEY = input("请输入查询关键字(quit退出):")
        gzh = input("请输入公众号:")
        temp = t.query_article(keyword=KEY, gzh=gzh)
        for item in temp:
            print(item)

"""
验证码之后,会重复一个页面的数据
"""
