#!/usr/bin/env python3
"""
Weekly Keyword Updater - 每周关键词更新脚本
每周运行一次，自动发现热门研究主题并更新搜索关键词
"""

import os
import sys
import json
import asyncio
from datetime import datetime
from typing import List, Dict, Any

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 加载环境变量
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, val = line.split('=', 1)
                    os.environ[key.strip()] = val.strip()

# 设置代理
if 'HTTP_PROXY' not in os.environ:
    os.environ['HTTP_PROXY'] = 'http://127.0.0.1:7890'
    os.environ['HTTPS_PROXY'] = 'http://127.0.0.1:7890'

# 直接导入避免循环依赖
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'core'))
from llm_client import LLMClient
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'utils'))
from hot_topic_discovery import HotTopicDiscovery


def load_keyword_config(config_path: str = "config/paper_keywords.json") -> Dict[str, Any]:
    """加载关键词配置"""
    if os.path.exists(config_path):
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {
        "seed_keywords": [],
        "discovered_keywords": [],
        "dynamic_mode": True,
        "rotation": {
            "enabled": True,
            "keywords_per_day": 12,
            "max_keywords_pool": 50
        }
    }


def save_keyword_config(config: Dict[str, Any], config_path: str = "config/paper_keywords.json"):
    """保存关键词配置"""
    os.makedirs(os.path.dirname(config_path), exist_ok=True)
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
    print(f"💾 配置已保存到: {config_path}")


def backup_config(config: Dict[str, Any], backup_dir: str = "data/keyword_backups"):
    """备份当前配置"""
    os.makedirs(backup_dir, exist_ok=True)
    backup_path = os.path.join(backup_dir, f"paper_keywords_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
    with open(backup_path, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
    print(f"📦 配置已备份到: {backup_path}")


async def update_keywords(max_keywords: int = 20) -> Dict[str, Any]:
    """
    更新关键词

    Args:
        max_keywords: 最大关键词数量

    Returns:
        更新结果
    """
    print("=" * 70)
    print("🔄 每周关键词更新")
    print("=" * 70)
    print(f"📅 时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # 初始化LLM客户端
    llm_client = LLMClient()

    # 加载当前配置
    config_path = "config/paper_keywords.json"
    current_config = load_keyword_config(config_path)

    # 备份当前配置
    print("📦 备份当前配置...")
    backup_config(current_config)

    # 获取旧的种子关键词用于比较
    old_seed_keywords = current_config.get('seed_keywords', [])

    # 创建热门主题发现器
    brave_api_key = os.getenv("BRAVE_API_KEY", "")
    discovery = HotTopicDiscovery(llm_client, brave_api_key)

    # 发现热门主题
    print("\n🔍 发现热门研究主题...")
    topics = await discovery.discover_trending_topics()

    if not topics:
        print("❌ 未能发现热门主题，保留现有配置")
        return {"success": False, "message": "No topics discovered"}

    # 生成关键词
    print("\n📝 从热门主题生成关键词...")
    keywords = await discovery.generate_keywords_from_topics(topics)

    if not keywords:
        # 回退：直接从主题提取关键词
        print("   使用主题默认关键词...")
        keywords = []
        for topic in topics[:10]:
            keywords.extend(topic.get('keywords', [])[:2])

    # 去重并限制数量
    keywords = list(dict.fromkeys(keywords))[:max_keywords]

    # 更新配置
    new_config = current_config.copy()
    new_config['seed_keywords'] = keywords

    # 添加weekly_update信息
    new_config['weekly_update'] = {
        "enabled": True,
        "last_updated": datetime.now().isoformat(),
        "update_source": "hot_topic_discovery",
        "topics_covered": [{"topic": t['topic'], "priority": t['priority']} for t in topics[:10]]
    }

    # 保存新配置
    print("\n💾 保存新配置...")
    save_keyword_config(new_config, config_path)

    # 打印变更摘要
    print("\n" + "=" * 70)
    print("📊 更新摘要")
    print("=" * 70)

    new_keywords = [k for k in keywords if k not in old_seed_keywords]
    removed_keywords = [k for k in old_seed_keywords if k not in keywords]

    print(f"\n✅ 关键词总数: {len(keywords)}")
    print(f"🆕 新增关键词: {len(new_keywords)}")
    print(f"❌ 移除关键词: {len(removed_keywords)}")

    if new_keywords:
        print(f"\n新增关键词列表:")
        for kw in new_keywords:
            print(f"   + {kw}")

    if removed_keywords:
        print(f"\n移除关键词列表:")
        for kw in removed_keywords:
            print(f"   - {kw}")

    print("\n✅ 关键词更新完成!")

    return {
        "success": True,
        "total_keywords": len(keywords),
        "new_keywords": new_keywords,
        "removed_keywords": removed_keywords,
        "topics_covered": len(topics)
    }


async def main():
    """主函数"""
    result = await update_keywords()

    if result.get('success'):
        print(f"\n🎉 每周关键词更新成功!")
        print(f"   总关键词: {result['total_keywords']}")
        print(f"   新增: {len(result['new_keywords'])}")
        print(f"   移除: {len(result['removed_keywords'])}")
    else:
        print(f"\n⚠️ 关键词更新失败: {result.get('message', 'Unknown error')}")

    return result


if __name__ == "__main__":
    asyncio.run(main())