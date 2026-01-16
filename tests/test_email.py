#!/usr/bin/env python3
"""
测试阿里云邮件发送功能
"""

import sys
import os

# 添加父目录到路径以便导入模块
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.email_sender import EmailSender
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()


def test_email_config():
    """测试邮件配置"""
    print("="*70)
    print("📧 测试邮件配置")
    print("="*70)
    
    sender = EmailSender()
    
    if sender.test_connection():
        print("\n✅ 配置检查通过，可以发送邮件")
        return sender
    else:
        print("\n❌ 配置检查失败，请检查配置文件")
        return None


def test_send_simple_email():
    """测试发送简单邮件"""
    print("\n" + "="*70)
    print("📧 测试发送简单邮件")
    print("="*70)
    
    sender = EmailSender()
    
    # 创建测试论文数据
    test_papers = [
        {
            "title": "测试论文：大语言模型的推理能力研究",
            "authors": ["张三", "李四", "王五"],
            "affiliations": ["清华大学", "北京大学"],
            "abstract": "本文研究了大语言模型在复杂推理任务中的表现，提出了一种新的提示工程方法，能够显著提升模型的推理准确率。实验结果表明，该方法在多个基准测试上取得了SOTA性能。",
            "url": "https://arxiv.org/abs/2401.12345",
            "pdf_url": "https://arxiv.org/pdf/2401.12345.pdf",
            "published_date": "2026-01-10",
            "citations": 0,
            "venue": "arXiv preprint",
            "source": "arXiv",
            "importance_score": 8.5,
            "summary": "提出了一种新的提示工程方法，显著提升大语言模型的推理能力，在多个基准测试上达到SOTA性能。",
            "key_methods": [
                "链式思维提示（Chain-of-Thought Prompting）",
                "自我一致性验证（Self-Consistency Verification）",
                "多步骤推理分解（Multi-Step Reasoning Decomposition）"
            ],
            "innovations": [
                "首次将认知心理学理论应用于提示工程设计",
                "提出了可解释的推理路径生成机制"
            ],
            "applications": [
                "数学问题求解",
                "逻辑推理任务",
                "常识推理增强"
            ]
        },
        {
            "title": "测试论文：多模态大模型的视觉理解能力",
            "authors": ["赵六", "钱七"],
            "affiliations": ["复旦大学"],
            "abstract": "本文探讨了多模态大模型在视觉理解任务中的能力边界，通过大规模实验分析了模型在不同场景下的表现。",
            "url": "https://arxiv.org/abs/2401.12346",
            "pdf_url": "",
            "published_date": "2026-01-09",
            "citations": 2,
            "venue": "CVPR 2026",
            "source": "Google Scholar",
            "importance_score": 7.8,
            "summary": "系统分析了多模态大模型的视觉理解能力，揭示了模型在复杂场景下的局限性。",
            "key_methods": [
                "跨模态注意力机制",
                "视觉-语言对齐学习"
            ],
            "innovations": [
                "构建了新的多模态评测基准"
            ],
            "applications": [
                "图像描述生成",
                "视觉问答系统"
            ]
        }
    ]
    
    # 发送测试邮件
    topic = "AI/LLM 最新研究进展（测试邮件）"
    date_range = "2026-01-04 ~ 2026-01-11"
    
    success = sender.send_email(test_papers, topic, date_range)
    
    if success:
        print("\n✅ 测试邮件发送成功！")
        print("📬 请检查收件箱: 42213885@qq.com")
        return True
    else:
        print("\n❌ 测试邮件发送失败")
        return False


def main():
    """主函数"""
    print("\n" + "="*70)
    print("🧪 阿里云邮件发送功能测试")
    print("="*70)
    
    # 1. 测试配置
    sender = test_email_config()
    if not sender:
        return
    
    # 2. 询问是否发送测试邮件
    print("\n" + "-"*70)
    choice = input("是否发送测试邮件? (y/n, 默认n): ").strip().lower()
    
    if choice == 'y':
        test_send_simple_email()
    else:
        print("\n✅ 已跳过发送测试")
    
    print("\n" + "="*70)
    print("🎉 测试完成")
    print("="*70)


if __name__ == "__main__":
    main()
