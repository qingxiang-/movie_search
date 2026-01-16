#!/usr/bin/env python3
"""
测试新的邮件格式 - 精选3篇论文深度解读
"""

import sys
import os
import json

# 添加父目录到路径以便导入模块
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.email_sender import EmailSender
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()


def main():
    """主函数"""
    print("\n" + "="*70)
    print("🧪 测试新邮件格式 - 精选3篇论文深度解读")
    print("="*70)
    
    # 读取真实论文数据
    json_file = "data/paper_pool_autonomous_reasoning_agents_wi_2026-01-11.json"
    
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            all_papers = data.get('papers', [])
    except Exception as e:
        print(f"❌ 读取论文数据失败: {e}")
        return
    
    # 按评分排序，选择前3篇
    sorted_papers = sorted(all_papers, key=lambda x: x.get('importance_score', 0), reverse=True)
    top3_papers = sorted_papers[:3]
    
    print(f"\n📄 从 {len(all_papers)} 篇论文中精选出评分最高的 3 篇：")
    for i, paper in enumerate(top3_papers, 1):
        score = paper.get('importance_score', 0)
        print(f"   {i}. [{score:.1f}分] {paper.get('title', 'N/A')[:60]}...")
    
    sender = EmailSender()
    
    # 测试配置
    print("\n📧 测试邮件配置")
    print("="*70)
    if not sender.test_connection():
        print("\n❌ 配置检查失败，退出测试")
        return
    
    print("\n✅ 配置检查通过")
    
    # 发送邮件
    print("\n📧 发送深度解读邮件（3篇精选论文）")
    print("="*70)
    print("   每篇论文包含：")
    print("   - 💡 核心观点")
    print("   - 🔬 研究方法")
    print("   - ✨ 主要创新")
    print("   - 🎯 应用场景")
    
    topic = "autonomous reasoning agents with dynamic tool orchestration"
    date_range = "2026-01-04 ~ 2026-01-11"
    
    success = sender.send_email(top3_papers, topic, date_range)
    
    if success:
        print("\n✅ 测试邮件发送成功！")
        print("📬 请检查收件箱: 42213885@qq.com")
        print("\n💡 新邮件格式特点：")
        print("   - 只发送3篇最有价值的论文")
        print("   - 每篇论文都有深入解读")
        print("   - 包含方法、创新、应用等详细信息")
    else:
        print("\n❌ 测试邮件发送失败")
        print("   如果被拦截，可能需要进一步调整格式")
    
    print("\n" + "="*70)
    print("🎉 测试完成")
    print("="*70)


if __name__ == "__main__":
    main()
