"""
Email Sender - 邮件发送功能（基于阿里云 DirectMail）
"""

import os
import yaml
from datetime import datetime
from typing import List, Dict, Any

from alibabacloud_dm20151123.client import Client as Dm20151123Client
from alibabacloud_tea_openapi import models as open_api_models
from alibabacloud_dm20151123 import models as dm_20151123_models
from alibabacloud_tea_util import models as util_models


class EmailSender:
    """邮件发送器（阿里云 DirectMail）"""
    
    def __init__(self, config_file: str = "email_config.yaml"):
        """初始化邮件发送器"""
        # 从 .env 读取阿里云 AccessKey（保密信息）
        self.access_key_id = os.getenv("ALIYUN_ACCESS_KEY_ID", "")
        self.access_key_secret = os.getenv("ALIYUN_ACCESS_KEY_SECRET", "")
        
        # 从 YAML 读取邮件配置（非保密信息）
        self.sender_email = ""
        self.recipients = []
        self.region = "cn-hangzhou"
        
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
                self.sender_email = config.get('sender', '')
                self.recipients = config.get('recipients', [])
                self.region = config.get('settings', {}).get('region', 'cn-hangzhou')
        except Exception as e:
            print(f"⚠️  读取邮件配置文件失败: {e}，使用默认配置")
        
        # 初始化阿里云客户端
        self.client = None
        if self.access_key_id and self.access_key_secret:
            self.client = self._create_client()
    
    def generate_html_email(self, papers: List[Dict[str, Any]], topic: str, date_range: str) -> str:
        """
        生成深入详细的 HTML 邮件内容（精选3篇论文，深入讲解）
        
        Args:
            papers: 论文列表（最多3篇）
            topic: 搜索主题
            date_range: 日期范围
            
        Returns:
            HTML 字符串
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
</head>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; padding: 20px; max-width: 800px;">
    <h2 style="color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px;">
        学术论文深度解读
    </h2>
    
    <p style="color: #666;">
        <strong>主题:</strong> {topic}<br>
        <strong>时间:</strong> {date_range}<br>
        <strong>精选:</strong> {len(papers)} 篇最有价值的论文
    </p>
    
    <p style="background: #e8f4f8; padding: 12px; border-left: 4px solid #3498db; font-size: 14px;">
        本期为您精选了 {len(papers)} 篇高质量论文，每篇都进行了深入解读，包括研究方法、创新点和主要结论。
    </p>
    
    <hr style="border: none; border-top: 1px solid #ddd; margin: 20px 0;">
"""
        
        for i, paper in enumerate(papers, 1):
            score = paper.get('importance_score', 0)
            authors = ', '.join(paper.get('authors', [])[:3])
            if len(paper.get('authors', [])) > 3:
                authors += ' 等'
            
            html += f"""
    <div style="margin: 30px 0; padding: 20px; border: 2px solid #e0e0e0; border-radius: 8px; background: #fafafa;">
        <h3 style="color: #2c3e50; margin-top: 0;">
            {i}. {paper.get('title', 'N/A')}
        </h3>
        
        <p style="color: #666; font-size: 13px; margin: 8px 0;">
            <strong>作者:</strong> {authors}<br>
            <strong>评分:</strong> {score:.1f}/10 | <strong>来源:</strong> {paper.get('source', 'N/A')}
        </p>
"""
            
            # 核心观点
            if paper.get('summary'):
                html += f"""
        <div style="background: #fff; padding: 12px; margin: 15px 0; border-left: 3px solid #27ae60;">
            <strong style="color: #27ae60;">💡 核心观点</strong>
            <p style="margin: 8px 0 0 0; font-size: 14px;">{paper.get('summary', 'N/A')}</p>
        </div>
"""
            
            # 关键方法
            if paper.get('key_methods'):
                methods = paper.get('key_methods', [])
                html += f"""
        <div style="background: #fff; padding: 12px; margin: 15px 0; border-left: 3px solid #3498db;">
            <strong style="color: #3498db;">🔬 研究方法</strong>
            <ul style="margin: 8px 0 0 0; padding-left: 20px; font-size: 14px;">
"""
                for method in methods[:4]:  # 最多4个方法
                    html += f"                <li>{method}</li>\n"
                html += """            </ul>
        </div>
"""
            
            # 创新点
            if paper.get('innovations'):
                innovations = paper.get('innovations', [])
                html += f"""
        <div style="background: #fff; padding: 12px; margin: 15px 0; border-left: 3px solid #e74c3c;">
            <strong style="color: #e74c3c;">✨ 主要创新</strong>
            <ul style="margin: 8px 0 0 0; padding-left: 20px; font-size: 14px;">
"""
                for innovation in innovations[:4]:  # 最多4个创新点
                    html += f"                <li>{innovation}</li>\n"
                html += """            </ul>
        </div>
"""
            
            # 应用场景
            if paper.get('applications'):
                applications = paper.get('applications', [])
                html += f"""
        <div style="background: #fff; padding: 12px; margin: 15px 0; border-left: 3px solid #f39c12;">
            <strong style="color: #f39c12;">🎯 应用场景</strong>
            <ul style="margin: 8px 0 0 0; padding-left: 20px; font-size: 14px;">
"""
                for app in applications[:4]:  # 最多4个应用
                    html += f"                <li>{app}</li>\n"
                html += """            </ul>
        </div>
"""
            
            # 论文链接
            html += f"""
        <p style="margin-top: 15px;">
            <a href="{paper.get('url', '#')}" style="color: #3498db; text-decoration: none; font-weight: bold;">
                📄 查看论文原文 →
            </a>
        </p>
    </div>
"""
        
        html += f"""
    <hr style="border: none; border-top: 1px solid #ddd; margin: 30px 0 20px 0;">
    <p style="color: #999; font-size: 12px; text-align: center;">
        本邮件由学术论文搜索系统自动生成 | {timestamp}
    </p>
</body>
</html>
"""
        
        return html
    
    def _create_client(self) -> Dm20151123Client:
        """创建阿里云 DirectMail 客户端"""
        config = open_api_models.Config(
            access_key_id=self.access_key_id,
            access_key_secret=self.access_key_secret
        )
        config.endpoint = f'dm.aliyuncs.com'
        return Dm20151123Client(config)
    
    def send_email(self, papers: List[Dict[str, Any]], topic: str, date_range: str) -> bool:
        """
        发送邮件（使用阿里云 DirectMail SDK）
        
        Args:
            papers: 论文列表
            topic: 搜索主题
            date_range: 日期范围
            
        Returns:
            是否发送成功
        """
        if not self.client:
            print("❌ 阿里云邮件客户端未初始化，请检查 .env 文件")
            return False
        
        if not self.sender_email:
            print("❌ 未配置发件人，请检查 email_config.yaml")
            return False
        
        if not self.recipients:
            print("❌ 未配置收件人，请检查 email_config.yaml")
            return False
        
        if not papers:
            print("⚠️  没有论文需要发送")
            return False
        
        # 生成 HTML 内容
        html_content = self.generate_html_email(papers, topic, date_range)
        subject = f"📚 学术论文推荐: {topic[:30]} ({datetime.now().strftime('%Y-%m-%d')})"
        
        # 保存 HTML 到 data 文件夹
        os.makedirs('data', exist_ok=True)
        # 清理文件名中的特殊字符
        safe_topic = topic.replace(' ', '_').replace('/', '_').replace('\\', '_').replace(':', '_')
        html_filename = f"data/email_{safe_topic[:30]}_{datetime.now().strftime('%Y-%m-%d')}.html"
        try:
            with open(html_filename, 'w', encoding='utf-8') as f:
                f.write(html_content)
            print(f"💾 邮件内容已保存到: {html_filename}")
        except Exception as e:
            print(f"⚠️  保存 HTML 文件失败: {e}")
        
        # 发送给每个收件人
        success_count = 0
        for recipient in self.recipients:
            try:
                if self._send_to_recipient(recipient, subject, html_content):
                    success_count += 1
            except Exception as e:
                print(f"❌ 发送到 {recipient} 失败: {e}")
        
        if success_count > 0:
            print(f"✅ 邮件发送成功！发送到 {success_count}/{len(self.recipients)} 个收件人，共 {len(papers)} 篇论文")
            return True
        else:
            print(f"❌ 所有邮件发送失败")
            return False
    
    def _send_to_recipient(self, recipient: str, subject: str, html_body: str) -> bool:
        """发送邮件到单个收件人（使用阿里云 SDK）"""
        try:
            request = dm_20151123_models.SingleSendMailRequest(
                account_name=self.sender_email,
                address_type=1,
                reply_to_address=False,
                to_address=recipient,
                subject=subject,
                html_body=html_body
            )
            runtime = util_models.RuntimeOptions()
            response = self.client.single_send_mail_with_options(request, runtime)
            
            # 检查响应
            if response and response.body:
                return True
            else:
                print(f"⚠️  发送到 {recipient} 响应异常")
                return False
                
        except Exception as e:
            print(f"❌ 发送到 {recipient} 失败: {str(e)}")
            return False
    
    def test_connection(self) -> bool:
        """测试阿里云 DirectMail 配置"""
        if not self.access_key_id or not self.access_key_secret:
            print("❌ 阿里云 AccessKey 未配置")
            return False
        
        if not self.sender_email:
            print("❌ 发件人地址未配置")
            return False
        
        if not self.recipients:
            print("❌ 收件人列表为空")
            return False
        
        print(f"✅ 邮件配置检查通过")
        print(f"   发件人: {self.sender_email}")
        print(f"   收件人: {', '.join(self.recipients)}")
        print(f"   区域: {self.region}")
        return True
