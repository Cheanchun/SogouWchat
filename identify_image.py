# -*- coding: utf-8 -*-

from __future__ import absolute_import, unicode_literals, print_function

# ws_cache = WechatCache()
import io
import time

import requests
from PIL import Image

# from chaojiying import Chaojiying_Client
# from wechatsogou.exceptions import WechatSogouVcodeOcrException
# from wechatsogou.filecache import WechatCache
# from wechatsogou.five import readimg, input
from exceptions import WechatSogouVcodeOcrException
from filecache import WechatCache

ws_cache = WechatCache()


def identify_image_callback_by_hand(im: bytes):
    """im：图片数据流"""
    im = Image.open(io.BytesIO(im))
    im.show()
    code = input("请输入验证码：")
    return code
def unlock_weixin_callback_example(url, req, resp, img, identify_image_callback):
    """手动打码解锁

    Parameters
    ----------
    url : str or unicode
        验证码页面 之前的 url
    req : requests.sessions.Session
        requests.Session() 供调用解锁
    resp : requests.models.Response
        requests 访问页面返回的，已经跳转了
    img : bytes
        验证码图片二进制数据
    identify_image_callback : callable
        处理验证码函数，输入验证码二进制数据，输出文字，参见 identify_image_callback_example

    Returns
    -------
    dict
        {
            'ret': '',
            'errmsg': '',
            'cookie_count': '',
        }
    """
    # no use resp

    unlock_url = 'https://mp.weixin.qq.com/mp/verifycode'
    data = {
        'cert': time.time() * 1000,
        'input': identify_image_callback(img)
    }
    headers = {
        'Host': 'mp.weixin.qq.com',
        'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'Referer': url
    }
    r_unlock = req.post(unlock_url, data, headers=headers)
    if not r_unlock.ok:
        raise WechatSogouVcodeOcrException(
            'unlock[{}] failed: {}[{}]'.format(unlock_url, r_unlock.text, r_unlock.status_code))

    return r_unlock.json()

def identify_image_by_hand(im: bytes):
    """im：图片数据流"""
    im = Image.open(io.BytesIO(im))
    im.show()
    code = input("请输入验证码：")
    return code


def unlock_sogou_callback_example(url, req, resp, img, identify_image_callback):  # 微信公众号查询打码接口
    """手动打码解锁
    Parameters
    ----------
    url : str or unicode
        验证码页面 之前的 url
    req : requests.sessions.Session
        requests.Session() 供调用解锁
    resp : requests.models.Response
        requests 访问页面返回的，已经跳转了
    img : bytes
        验证码图片二进制数据
    identify_image_callback : callable
        处理验证码函数，输入验证码二进制数据，输出文字，参见 identify_image_callback_example

    Returns
    -------
    dict
        {
            'code': '',
            'msg': '',
        }
    """
    # no use resp
    url_quote = url.split('weixin.sogou.com/')[-1]
    unlock_url = 'http://weixin.sogou.com/antispider/thank.php'
    data = {
        'c': identify_image_by_hand(im=img),  # todo 打码验证 直接返回打码结果 img 验证码 流
        'r': url_quote,
        'v': 5
    }
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'Referer': 'http://weixin.sogou.com/antispider/?from=' + url_quote
    }
    r_unlock = req.post(unlock_url, data, headers=headers)
    r_unlock.encoding = 'utf-8'
    if not r_unlock.ok:
        raise Exception(
            'unlock[{}] failed: {}'.format(unlock_url, r_unlock.text, r_unlock.status_code))
    return r_unlock.json()


def unlock_weixin_callback_example(url, req, resp, img, identify_image_callback):
    """手动打码解锁

    Parameters
    ----------
    url : str or unicode
        验证码页面 之前的 url
    req : requests.sessions.Session
        requests.Session() 供调用解锁
    resp : requests.models.Response
        requests 访问页面返回的，已经跳转了
    img : bytes
        验证码图片二进制数据
    identify_image_callback : callable
        处理验证码函数，输入验证码二进制数据，输出文字，参见 identify_image_callback_example

    Returns
    -------
    dict
        {
            'ret': '',
            'errmsg': '',
            'cookie_count': '',
        }
    """
    # no use resp

    unlock_url = 'https://mp.weixin.qq.com/mp/verifycode'
    data = {
        'cert': time.time() * 1000,
        'input': identify_image_callback(img)
    }
    headers = {
        'Host': 'mp.weixin.qq.com',
        'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'Referer': url
    }
    r_unlock = req.post(unlock_url, data, headers=headers)
    if not r_unlock.ok:
        raise WechatSogouVcodeOcrException(
            'unlock[{}] failed: {}[{}]'.format(unlock_url, r_unlock.text, r_unlock.status_code))

    return r_unlock.json()
