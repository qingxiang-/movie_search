#!/usr/bin/env python3
"""
测试阿里云 DirectMail API
"""

import json
import hmac
import hashlib
import base64
import urllib.parse
from datetime import datetime
import requests
import os
import sys

# 加载.env
from dotenv import load_dotenv
load_dotenv('.env')


def percent_encode(s):
    """URL编码"""
    return urllib.parse.quote(s, safe='-_.~').replace('%7E', '~')


def signature(method, path, params, access_secret):
    """计算签名"""
    sorted_params = sorted(params.items(), key=lambda x: x[0])
    canonicalized_query_string = '&'.join([
        f'{percent_encode(k)}={percent_encode(v)}'
        for k, v in sorted_params
    ])
    string_to_sign = f'{method}&%2F&{percent_encode(canonicalized_query_string)}'
    signature = hmac.new(
        (access_secret + '&').encode('utf-8'),
        string_to_sign.encode('utf-8'),
        hashlib.sha1
    ).digest()
    return base64.b64encode(signature).decode('utf-8')


def send_email_aliyun(to_email, subject, html_content):
    """使用阿里云DirectMail API发送邮件"""
    
    # 配置
    access_key_id = os.getenv('ALIYUN_ACCESS_KEY_ID', '')
    access_secret = os.getenv('ALIYUN_ACCESS_KEY_SECRET', '')
    
    if not access_key_id or not access_secret:
        print("❌ 未配置阿里云API Key")
        return False
    
    print(f"✅ Access Key ID: {access_key_id[:10]}...")
    
    # API参数
    params = {
        'Format': 'JSON',
        'Version': '2015-11-23',
        'AccessKeyId': access_key_id,
        'SignatureMethod': 'HMAC-SHA1',
        'Timestamp': datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ'),
        'SignatureVersion': '1.0',
        'SignatureNonce': str(datetime.now().timestamp()),
        'Action': 'SingleSendMail',
        'AccountName': 'no_reply@extmail.codebu.top',
        'ReplyToAddress': 'false',
        'AddressType': '1',
        'ToAddress': to_email,
        'Subject': subject,
        'HtmlBody': html_content,
    }
    
    # 计算签名
    params['Signature'] = signature('GET', '/', params, access_secret)
    
    # 发送请求
    url = 'https://dm.aliyuncs.com/'
    
    print(f"📤 发送请求到: {url}")
    print(f"📧 收件人: {to_email}")
    print(f"📝 主题: {subject}")
    
    try:
        response = requests.get(url, params=params, timeout=30)
        print(f"\n📥 响应状态码: {response.status_code}")
        print(f"📥 响应内容:\n{response.text[:500]}")
        
        if response.status_code == 200:
            print("\n✅ 邮件发送成功！")
            return True
        else:
            print(f"\n❌ 邮件发送失败！")
            return False
            
    except Exception as e:
        print(f"\n❌ 请求异常: {e}")
        return False


def test_direct():
    """测试直接发送"""
    
    test_html = """
    <html>
    <body>
        <h1>测试邮件</h1>
        <p>这是一封测试邮件</p>
        <p>时间: {time}</p>
    </body>
    </html>
    """.format(time=datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    
    print("="*70)
    print("🔍 阿里云 DirectMail API 测试")
    print("="*70)
    print()
    
    # 检查配置
    print("📋 配置检查:")
    print(f"   AccessKeyId: {'✅ 已配置' if os.getenv('ALIYUN_ACCESS_KEY_ID') else '❌ 未配置'}")
    print(f"   AccessSecret: {'✅ 已配置' if os.getenv('ALIYUN_ACCESS_KEY_SECRET') else '❌ 未配置'}")
    print()
    
    # 发送测试
    send_email_aliyun(
        to_email='wangqingxiang@wangqingxiang.com',
        subject=f'测试邮件 - {datetime.now().strftime("%H:%M:%S")}',
        html_content=test_html
    )


if __name__ == "__main__":
    test_direct()
