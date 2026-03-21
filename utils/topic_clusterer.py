"""
Topic Clusterer - 论文主题聚类模块
使用LLM将论文按研究主题分组
"""

import os
import json
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime

# 添加项目根目录到路径
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.llm_client import LLMClient
from prompts.topic_prompts import get_paper_clustering_prompt


class TopicClusterer:
    """论文主题聚类器"""

    def __init__(self, llm_client: LLMClient, min_clusters: int = 2, max_clusters: int = 5):
        """
        初始化聚类器

        Args:
            llm_client: LLM客户端
            min_clusters: 最小聚类数
            max_clusters: 最大聚类数
        """
        self.llm_client = llm_client
        self.min_clusters = min_clusters
        self.max_clusters = max_clusters

    async def cluster_papers(self, papers: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """
        将论文聚类到不同研究主题

        Args:
            papers: 论文列表

        Returns:
            聚类结果 {
                topic_name: {
                    "description": str,
                    "key_insights": List[str],
                    "papers": List[Dict]
                }
            }
        """
        if not papers:
            return {}

        print(f"\n🔄 开始聚类 {len(papers)} 篇论文...")

        # 使用LLM进行聚类
        clusters = await self._llm_cluster(papers)

        if not clusters:
            # 回退到简单聚类
            print("   ⚠️  LLM聚类失败，使用简单聚类")
            clusters = self._simple_cluster(papers)

        print(f"   ✅ 聚类完成，共 {len(clusters)} 个主题")

        return clusters

    async def _llm_cluster(self, papers: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """
        使用LLM进行聚类

        Args:
            papers: 论文列表

        Returns:
            聚类结果
        """
        prompt = get_paper_clustering_prompt(papers)

        try:
            result = await self.llm_client.call(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.5,
                max_tokens=3000
            )

            if result.get('success'):
                content = result['content']
                # 提取JSON
                json_start = content.find('{')
                json_end = content.rfind('}') + 1
                if json_start >= 0 and json_end > json_start:
                    json_str = content[json_start:json_end]
                    data = json.loads(json_str)

                    # 转换为标准格式
                    clusters = {}
                    for cluster in data.get('clusters', []):
                        topic_name = cluster.get('topic_name', 'Other')
                        paper_ids = cluster.get('paper_ids', [])

                        # 根据paper_id获取对应论文
                        topic_papers = [papers[i-1] for i in paper_ids if 0 < i <= len(papers)]

                        if topic_papers:
                            clusters[topic_name] = {
                                "description": cluster.get('topic_description', ''),
                                "key_insights": cluster.get('key_insights', []),
                                "papers": topic_papers
                            }

                    return clusters

        except Exception as e:
            print(f"   ⚠️  LLM聚类失败: {e}")

        return {}

    def _simple_cluster(self, papers: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """
        简单聚类（回退方案）
        基于论文的关键词/方法进行简单分组
        """
        # 定义主题关键词映射
        topic_keywords = {
            "LLM Agent": ["agent", "tool", "autonomous", "planning", "action"],
            "Multimodal LLM": ["multimodal", "vision", "image", "video", "visual"],
            "LLM Reasoning": ["reasoning", "chain-of-thought", "cot", "think", "logic"],
            "Test-Time Compute": ["test-time", "inference", "compute", "scaling"],
            "LLM Training": ["training", "fine-tuning", "pre-training", "optimization"],
            "LLM Evaluation": ["benchmark", "evaluation", "assessment", "test"],
            "AI Safety": ["safety", "alignment", "risk", "harmful", "jailbreak"],
            "Code Generation": ["code", "programming", "software", "generation"]
        }

        clusters = {}
        assigned = set()

        # 按关键词分配
        for topic, keywords in topic_keywords.items():
            topic_papers = []
            for i, paper in enumerate(papers):
                if i in assigned:
                    continue

                title = paper.get('title', '').lower()
                abstract = paper.get('abstract', '').lower()
                methods = ' '.join(paper.get('key_methods', [])).lower()

                text = f"{title} {abstract} {methods}"

                # 检查是否匹配任何关键词
                if any(kw in text for kw in keywords):
                    topic_papers.append(paper)
                    assigned.add(i)

            if topic_papers:
                clusters[topic] = {
                    "description": f"Research on {topic.lower()}",
                    "key_insights": [],
                    "papers": topic_papers
                }

        # 处理未分配的论文
        unassigned_papers = [papers[i] for i in range(len(papers)) if i not in assigned]
        if unassigned_papers:
            clusters["Other Research"] = {
                "description": "Other AI research topics",
                "key_insights": [],
                "papers": unassigned_papers
            }

        return clusters

    def get_topic_statistics(self, clusters: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """
        获取聚类统计信息

        Args:
            clusters: 聚类结果

        Returns:
            统计信息
        """
        total_papers = sum(len(c.get('papers', [])) for c in clusters.values())

        stats = {
            "total_topics": len(clusters),
            "total_papers": total_papers,
            "topics": []
        }

        for topic_name, topic_data in clusters.items():
            papers = topic_data.get('papers', [])
            avg_score = sum(p.get('importance_score', 0) for p in papers) / len(papers) if papers else 0

            stats["topics"].append({
                "name": topic_name,
                "paper_count": len(papers),
                "avg_score": round(avg_score, 1)
            })

        # 按论文数量排序
        stats["topics"].sort(key=lambda x: x["paper_count"], reverse=True)

        return stats


async def main():
    """测试论文聚类"""
    # 创建测试数据
    test_papers = [
        {
            "title": "Test-Time Compute: Scaling Inference for Better Reasoning",
            "abstract": "We propose a new method for scaling compute during test time to improve LLM reasoning capabilities.",
            "importance_score": 9.0,
            "key_methods": ["test-time scaling", "reasoning"]
        },
        {
            "title": "Multimodal LLM Agent for Visual Task Solving",
            "abstract": "A multimodal agent that can understand images and solve visual tasks using tools.",
            "importance_score": 8.5,
            "key_methods": ["multimodal understanding", "agent"]
        },
        {
            "title": "Chain-of-Thought Reasoning in Large Language Models",
            "abstract": "We analyze the effectiveness of chain-of-thought prompting for complex reasoning.",
            "importance_score": 8.0,
            "key_methods": ["chain-of-thought", "reasoning"]
        }
    ]

    # 初始化
    llm_client = LLMClient()
    clusterer = TopicClusterer(llm_client)

    # 聚类
    clusters = await clusterer.cluster_papers(test_papers)

    # 打印结果
    print("\n📊 聚类结果:")
    for topic, data in clusters.items():
        print(f"\n主题: {topic}")
        print(f"  描述: {data['description']}")
        print(f"  论文数: {len(data['papers'])}")
        for paper in data['papers']:
            print(f"    - {paper['title']}")


if __name__ == "__main__":
    asyncio.run(main())