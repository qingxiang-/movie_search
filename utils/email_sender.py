"""
Email Sender - 邮件发送功能（基于阿里云 DirectMail）
"""

import os
import yaml
from datetime import datetime
from typing import List, Dict, Any

# 加载 .env 文件（如果存在）
dotenv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
if os.path.exists(dotenv_path):
    with open(dotenv_path, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ.setdefault(key.strip(), value.strip())

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
    
    def _generate_detailed_html(self, papers: List[Dict[str, Any]], topic: str, date_range: str) -> str:
        """
        生成深入详细的 HTML 邮件内容（精选多篇论文，深入讲解）
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
</head>
<body style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; line-height: 1.6; color: #333; padding: 20px; max-width: 800px; margin: 0 auto;">
    <h2 style="color: #2c3e50; border-bottom: 1px solid #eee; padding-bottom: 10px;">
        Daily AI Research Update
    </h2>
    
    <div style="color: #666; font-size: 14px; margin-bottom: 20px;">
        <p><strong>Topic:</strong> {topic}<br>
        <strong>Date Range:</strong> {date_range}<br>
        <strong>Selected Papers:</strong> {len(papers)}</p>
    </div>
    
    <p style="font-size: 15px;">
        This report summarizes {len(papers)} high-quality research papers selected based on their potential impact and technical insight.
    </p>
    
    <div style="border-top: 1px solid #eee; margin: 20px 0;"></div>
"""
        
        for i, paper in enumerate(papers, 1):
            score = paper.get('importance_score', 0)
            authors = ', '.join(paper.get('authors', [])[:3])
            if len(paper.get('authors', [])) > 3:
                authors += ' et al.'
            
            html += f"""
    <div style="margin-bottom: 40px; padding: 10px;">
        <h3 style="color: #1a73e8; margin-top: 0; margin-bottom: 10px;">
            {i}. {paper.get('title', 'N/A')}
        </h3>
        
        <div style="color: #5f6368; font-size: 13px; margin-bottom: 15px;">
            <strong>Authors:</strong> {authors} | 
            <strong>Score:</strong> {score:.1f}/10 | 
            <strong>Source:</strong> {paper.get('source', 'N/A')} | 
            <strong>Updated:</strong> {paper.get('published_date', 'N/A')}
        </div>
"""
            
            # 核心观点
            if paper.get('summary'):
                html += f"""
        <div style="margin-bottom: 15px;">
            <strong style="color: #3c4043; display: block; margin-bottom: 5px;">Key Insight:</strong>
            <p style="margin: 0; font-size: 14px;">{paper.get('summary', 'N/A')}</p>
        </div>
"""
            
            # 关键方法
            if paper.get('key_methods'):
                methods = paper.get('key_methods', [])
                html += f"""
        <div style="margin-bottom: 15px;">
            <strong style="color: #3c4043; display: block; margin-bottom: 5px;">Methodology:</strong>
            <ul style="margin: 0; padding-left: 20px; font-size: 14px;">
"""
                for method in methods[:4]:
                    html += f"                <li>{method}</li>\n"
                html += """            </ul>
        </div>
"""
            
            # 创新点
            if paper.get('innovations'):
                innovations = paper.get('innovations', [])
                html += f"""
        <div style="margin-bottom: 15px;">
            <strong style="color: #3c4043; display: block; margin-bottom: 5px;">Innovations:</strong>
            <ul style="margin: 0; padding-left: 20px; font-size: 14px;">
"""
                for innovation in innovations[:4]:
                    html += f"                <li>{innovation}</li>\n"
                html += """            </ul>
        </div>
"""
            
            # 应用场景
            if paper.get('applications'):
                applications = paper.get('applications', [])
                html += f"""
        <div style="margin-bottom: 15px;">
            <strong style="color: #3c4043; display: block; margin-bottom: 5px;">Applications:</strong>
            <ul style="margin: 0; padding-left: 20px; font-size: 14px;">
"""
                for app in applications[:4]:
                    html += f"                <li>{app}</li>\n"
                html += """            </ul>
        </div>
"""
            
            # 论文链接
            html += f"""
        <div style="margin-top: 15px;">
            <a href="{paper.get('url', '#')}" style="color: #1a73e8; text-decoration: none; font-weight: 500; font-size: 14px;">
                View Original Paper →
            </a>
        </div>
    </div>
    <div style="border-top: 1px solid #f1f3f4; margin: 20px 0;"></div>
"""
        
        html += f"""
    <p style="color: #70757a; font-size: 12px; text-align: center; margin-top: 40px;">
        This automated report was generated on {timestamp}.
    </p>
</body>
</html>
"""
        return html
        
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
        html_content = self._generate_detailed_html(papers, topic, date_range)
        subject = f"Academic Paper Recommendations: {topic[:30]} ({datetime.now().strftime('%Y-%m-%d')})"
        
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
    
    def generate_stock_html_email(self, email_data: Dict[str, Any], topic: str, date_range: str) -> str:
        """
        生成股票推荐的 HTML 邮件内容
        
        Args:
            email_data: 包含 stocks, market_overview, investment_strategy, risk_warning
            topic: 邮件主题
            date_range: 日期范围
            
        Returns:
            HTML 字符串
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        stocks = email_data.get('stocks', [])
        market_overview = email_data.get('market_overview', 'N/A')
        investment_strategy = email_data.get('investment_strategy', 'N/A')
        risk_warning = email_data.get('risk_warning', 'N/A')
        
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
</head>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; padding: 20px; max-width: 800px;">
    <h2 style="color: #2c3e50; border-bottom: 2px solid #e74c3c; padding-bottom: 10px;">
        📈 美股投资推荐
    </h2>
    
    <p style="color: #666;">
        <strong>主题:</strong> {topic}<br>
        <strong>时间:</strong> {date_range}<br>
        <strong>报告:</strong> 已分析 {len(stocks)} 只关注列表股票
    </p>
    
    <div style="background: #fff3cd; padding: 15px; border-left: 4px solid #ffc107; margin: 20px 0;">
        <strong style="color: #856404;">📊 市场概览</strong>
        <p style="margin: 8px 0 0 0; font-size: 14px; color: #856404;">{market_overview}</p>
    </div>
    
    <hr style="border: none; border-top: 1px solid #ddd; margin: 20px 0;">
"""
        
        for stock in stocks:
            rank = stock.get('rank', 0)
            symbol = stock.get('symbol', 'N/A')
            company = stock.get('company_name', 'N/A')
            recommendation = stock.get('recommendation', 'N/A')
            score = stock.get('investment_score', 0)
            target_price = stock.get('target_price', 'N/A')
            time_horizon = stock.get('time_horizon', 'N/A')
            
            # 根据推荐类型设置颜色
            rec_color = '#27ae60' if recommendation == '买入' else '#3498db' if recommendation == '持有' else '#95a5a6'
            
            html += f"""
    <div style="margin: 30px 0; padding: 20px; border: 2px solid #e0e0e0; border-radius: 8px; background: #fafafa;">
        <h3 style="color: #2c3e50; margin-top: 0;">
            No.{rank}: {symbol} - {company}
        </h3>
        
        <p style="color: #666; font-size: 14px; margin: 10px 0;">
            <strong>现价:</strong> {stock.get('current_price', 'N/A')} | <strong>目标价:</strong> {target_price}
        </p>
        
        <div style="display: flex; gap: 15px; margin: 10px 0;">
            <span style="background: {rec_color}; color: white; padding: 5px 12px; border-radius: 4px; font-size: 13px; font-weight: bold;">
                {recommendation}
            </span>
            <span style="background: #3498db; color: white; padding: 5px 12px; border-radius: 4px; font-size: 13px;">
                评分: {score}/10
            </span>
            <span style="background: #9b59b6; color: white; padding: 5px 12px; border-radius: 4px; font-size: 13px;">
                {time_horizon}
            </span>
        </div>
        
        <p style="color: #666; font-size: 13px; margin: 10px 0;">
        </p>
"""
            
            # 公司背景
            if stock.get('background'):
                html += f"""
        <div style="background: #f5f5f5; padding: 12px; margin: 15px 0; border-left: 3px solid #607d8b;">
            <strong style="color: #455a64;">📋 公司背景</strong>
            <p style="margin: 8px 0 0 0; font-size: 14px;">{stock.get('background')}</p>
        </div>
"""
            
            # 最新动态
            if stock.get('latest_news_summary'):
                html += f"""
        <div style="background: #e3f2fd; padding: 12px; margin: 15px 0; border-left: 3px solid #2196f3;">
            <strong style="color: #1976d2;">📰 最新动态</strong>
            <p style="margin: 8px 0 0 0; font-size: 14px;">{stock.get('latest_news_summary')}</p>
        </div>
"""
            
            # 投资亮点
            if stock.get('investment_highlights'):
                html += f"""
        <div style="background: #e8f5e9; padding: 12px; margin: 15px 0; border-left: 3px solid #27ae60;">
            <strong style="color: #27ae60;">💡 投资亮点</strong>
            <ul style="margin: 8px 0 0 0; padding-left: 20px; font-size: 14px;">
"""
                for highlight in stock.get('investment_highlights', []):
                    html += f"                <li>{highlight}</li>\n"
                html += """            </ul>
        </div>
"""
            
            # 选股理由
            if stock.get('selection_reason'):
                html += f"""
        <div style="background: #fff8e1; padding: 12px; margin: 15px 0; border-left: 3px solid #ffa000;">
            <strong style="color: #f57c00;">🎯 选股理由</strong>
            <p style="margin: 8px 0 0 0; font-size: 14px;">{stock.get('selection_reason')}</p>
        </div>
"""
            
            # 催化剂
            if stock.get('catalysts'):
                html += f"""
        <div style="background: #fff3e0; padding: 12px; margin: 15px 0; border-left: 3px solid #ff9800;">
            <strong style="color: #e65100;">🚀 催化剂</strong>
            <ul style="margin: 8px 0 0 0; padding-left: 20px; font-size: 14px;">
"""
                for catalyst in stock.get('catalysts', []):
                    html += f"                <li>{catalyst}</li>\n"
                html += """            </ul>
        </div>
"""
            
            # 风险提示
            if stock.get('risks'):
                html += f"""
        <div style="background: #ffebee; padding: 12px; margin: 15px 0; border-left: 3px solid #e74c3c;">
            <strong style="color: #c62828;">⚠️ 风险提示</strong>
            <ul style="margin: 8px 0 0 0; padding-left: 20px; font-size: 14px;">
"""
                for risk in stock.get('risks', []):
                    html += f"                <li>{risk}</li>\n"
                html += """            </ul>
        </div>
"""
            
            # 综合分析
            if stock.get('detailed_analysis'):
                html += f"""
        <div style="background: #fff; padding: 12px; margin: 15px 0; border-left: 3px solid #3498db;">
            <strong style="color: #3498db;">📝 综合分析</strong>
            <p style="margin: 8px 0 0 0; font-size: 14px;">{stock.get('detailed_analysis', 'N/A')}</p>
        </div>
"""
            
            html += """    </div>
"""
        
        # 投资策略
        html += f"""
    <div style="background: #e3f2fd; padding: 15px; border-left: 4px solid #2196f3; margin: 20px 0;">
        <strong style="color: #1565c0;">💡 投资策略</strong>
        <p style="margin: 8px 0 0 0; font-size: 14px; color: #1565c0;">{investment_strategy}</p>
    </div>
"""
        
        # 风险警告
        html += f"""
    <div style="background: #ffebee; padding: 15px; border-left: 4px solid #f44336; margin: 20px 0;">
        <strong style="color: #c62828;">⚠️ 风险警告</strong>
        <p style="margin: 8px 0 0 0; font-size: 14px; color: #c62828;">{risk_warning}</p>
    </div>
"""
        
        html += f"""
    <hr style="border: none; border-top: 1px solid #ddd; margin: 30px 0 20px 0;">
    <p style="color: #999; font-size: 12px; text-align: center;">
        本邮件由美股智能分析系统自动生成 | {timestamp}<br>
        <strong style="color: #e74c3c;">免责声明: 本邮件内容仅供参考，不构成投资建议。投资有风险，入市需谨慎。</strong>
    </p>
</body>
</html>
"""
        
        return html
    
    def send_stock_email(self, email_data: Dict[str, Any], topic: str, date_range: str) -> bool:
        """
        发送股票推荐邮件
        
        Args:
            email_data: 股票数据（包含 stocks, market_overview, investment_strategy, risk_warning）
            topic: 邮件主题
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
        
        stocks = email_data.get('stocks', [])
        if not stocks:
            print("⚠️  没有股票需要发送")
            return False
        
        # 生成 HTML 内容
        html_content = self.generate_stock_html_email(email_data, topic, date_range)
        subject = f"📈 美股投资推荐: {topic} ({datetime.now().strftime('%Y-%m-%d')})"
        
        # 保存 HTML 到 data 文件夹
        os.makedirs('data', exist_ok=True)
        safe_topic = topic.replace(' ', '_').replace('/', '_').replace('\\', '_').replace(':', '_')
        html_filename = f"data/email_stock_{safe_topic}_{datetime.now().strftime('%Y-%m-%d')}.html"
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
            print(f"✅ 邮件发送成功！发送到 {success_count}/{len(self.recipients)} 个收件人，共分析 {len(stocks)} 只股票")
            return True
        else:
            print(f"❌ 所有邮件发送失败")
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

    def send_email_report(self, html_content: str, subject: str = None) -> bool:
        """
        发送HTML报告邮件（简单接口）

        Args:
            html_content: HTML邮件内容
            subject: 邮件主题（可选）

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

        # 使用默认主题
        if not subject:
            from datetime import datetime
            subject = f"Alpha158 选股报告 ({datetime.now().strftime('%Y-%m-%d')})"

        # 发送给每个收件人
        success_count = 0
        for recipient in self.recipients:
            try:
                if self._send_to_recipient(recipient, subject, html_content):
                    success_count += 1
            except Exception as e:
                print(f"❌ 发送到 {recipient} 失败: {e}")

        if success_count > 0:
            print(f"✅ 邮件发送成功！发送到 {success_count}/{len(self.recipients)} 个收件人")
            return True
        else:
            print(f"❌ 所有邮件发送失败")
            return False
