#!/usr/bin/env python3
"""
自动测试阿里云邮件发送功能（无需手动输入）
"""

import sys
import os

# 添加父目录到路径以便导入模块
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.email_sender import EmailSender
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()


def main():
    """主函数"""
    print("\n" + "="*70)
    print("🧪 阿里云邮件发送功能自动测试")
    print("="*70)
    
    sender = EmailSender()
    
    # 1. 测试配置
    print("\n📧 测试邮件配置")
    print("="*70)
    if not sender.test_connection():
        print("\n❌ 配置检查失败，退出测试")
        return
    
    print("\n✅ 配置检查通过")
    
    # 2. 创建测试论文数据
    test_papers = [
        {
            "title": "测试论文：大语言模型的推理能力研究",
            "authors": ["张三", "李四", "王五"],
            "affiliations": ["清华大学", "北京大学"],
            "abstract": "本文研究了大语言模型在复杂推理任务中的表现，提出了一种新的提示工程方法，能够显著提升模型的推理准确率。",
            "url": "https://arxiv.org/abs/2401.12345",
            "pdf_url": "https://arxiv.org/pdf/2401.12345.pdf",
            "published_date": "2026-01-10",
            "citations": 0,
            "venue": "arXiv preprint",
            "source": "arXiv",
            "importance_score": 8.5,
            "summary": "提出了一种新的提示工程方法，显著提升大语言模型的推理能力。",
            "key_methods": [
                "链式思维提示（Chain-of-Thought Prompting）",
                "自我一致性验证（Self-Consistency Verification）"
            ],
            "innovations": [
                "首次将认知心理学理论应用于提示工程设计"
            ],
            "applications": [
                "数学问题求解",
                "逻辑推理任务"
            ]
        }
    ]
    
    # 3. 发送测试邮件
    print("\n📧 发送测试邮件")
    print("="*70)
    
    topic = "AI/LLM 最新研究进展（自动测试）"
    date_range = "2026-01-04 ~ 2026-01-11"
    
    success = sender.send_email(test_papers, topic, date_range)
    
    if success:
        print("\n✅ 测试邮件发送成功！")
        print("📬 请检查收件箱: 42213885@qq.com")
    else:
        print("\n❌ 测试邮件发送失败")
    
    print("\n" + "="*70)
    print("🎉 测试完成")
    print("="*70)


if __name__ == "__main__":
    main()
