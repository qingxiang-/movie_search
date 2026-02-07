#!/usr/bin/env python3
"""
测试阿里云 DirectMail - 多种配置
"""

import json
import hmac
import hashlib
import base64
import urllib.parse
from datetime import datetime
import requests
import os

# 加载.env
from dotenv import load_dotenv
load_dotenv('.env')


def percent_encode(s):
    return urllib.parse.quote(s, safe='-_.~').replace('%7E', '~')


def signature(method, path, params, access_secret):
    sorted_params = sorted(params.items(), key=lambda x: x[0])
    canonicalized_query_string = '&'.join([
        f'{percent_encode(k)}={percent_encode(v)}'
        for k, v in sorted_params
    ])
    string_to_sign = f'{method}&%2F&{percent_encode(canonicalized_query_string)}'
    sig = hmac.new(
        (access_secret + '&').encode('utf-8'),
        string_to_sign.encode('utf-8'),
        hashlib.sha1
    ).digest()
    return base64.b64encode(sig).decode('utf-8')


def send_email(test_name, account_name, to_email, subject):
    """发送测试邮件"""
    
    access_key_id = os.getenv('ALIYUN_ACCESS_KEY_ID', '')
    access_secret = os.getenv('ALIYUN_ACCESS_KEY_SECRET', '')
    
    if not access_key_id:
        print(f"❌ {test_name}: 未配置API Key")
        return False
    
    params = {
        'Format': 'JSON',
        'Version': '2015-11-23',
        'AccessKeyId': access_key_id,
        'SignatureMethod': 'HMAC-SHA1',
        'Timestamp': datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ'),
        'SignatureVersion': '1.0',
        'SignatureNonce': str(datetime.now().timestamp()),
        'Action': 'SingleSendMail',
        'AccountName': account_name,
        'ReplyToAddress': 'false',
        'AddressType': '1',
        'ToAddress': to_email,
        'Subject': subject,
        'HtmlBody': f"""
        <html>
        <body>
            <h1>{test_name}</h1>
            <p>测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            <p>发件人: {account_name}</p>
            <p>收件人: {to_email}</p>
        </body>
        </html>
        """,
    }
    
    params['Signature'] = signature('GET', '/', params, access_secret)
    url = 'https://dm.aliyuncs.com/'
    
    try:
        response = requests.get(url, params=params, timeout=30)
        data = response.json()
        
        if response.status_code == 200 and 'EnvId' in data:
            print(f"✅ {test_name}: 成功 (EnvId: {data['EnvId']})")
            return True
        else:
            print(f"❌ {test_name}: 失败 - {data}")
            return False
            
    except Exception as e:
        print(f"❌ {test_name}: 异常 - {e}")
        return False


def main():
    print("="*70)
    print("🔍 阿里云 DirectMail 多配置测试")
    print("="*70)
    print()
    
    # 配置1: no_reply@extmail.codebu.top -> wangqingxiang@wangqingxiang.com
    send_email(
        "配置1: no_reply@extmail.codebu.top -> wangqingxiang@wangqingxiang.com",
        "no_reply@extmail.codebu.top",
        "wangqingxiang@wangqingxiang.com",
        f"测试1 - {datetime.now().strftime('%H:%M')}"
    )
    
    # 配置2: no_reply@extmail.codebu.top -> 42213885@qq.com
    send_email(
        "配置2: no_reply@extmail.codebu.top -> 42213885@qq.com",
        "no_reply@extmail.codebu.top",
        "42213885@qq.com",
        f"测试2 - {datetime.now().strftime('%H:%M')}"
    )
    
    # 配置3: 直接用wangqingxiang@wangqingxiang.com作为AccountName
    send_email(
        "配置3: wangqingxiang@wangqingxiang.com -> 42213885@qq.com",
        "wangqingxiang@wangqingxiang.com",
        "42213885@qq.com",
        f"测试3 - {datetime.now().strftime('%H:%M')}"
    )
    
    print()
    print("="*70)


if __name__ == "__main__":
    main()
