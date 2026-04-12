"""
增量更新管理器 - 实现智能数据增量更新策略
"""

import os
import json
import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from pathlib import Path


class IncrementalUpdater:
    """增量更新管理器"""

    def __init__(self, data_dir: str = "data", update_interval: int = 3600):
        """
        初始化增量更新管理器

        Args:
            data_dir: 数据目录
            update_interval: 更新间隔（秒）
        """
        self.data_dir = Path(data_dir)
        self.update_interval = update_interval

        # 确保数据目录存在
        self.data_dir.mkdir(parents=True, exist_ok=True)

        # 状态文件路径
        self.state_file = self.data_dir / "update_state.json"

        # 加载更新状态
        self._load_state()

    def _load_state(self):
        """加载更新状态"""
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r', encoding='utf-8') as f:
                    self.state = json.load(f)
            except Exception as e:
                print(f"加载更新状态时出错: {e}")
                self.state = {}
        else:
            self.state = {}

    def _save_state(self):
        """保存更新状态"""
        try:
            with open(self.state_file, 'w', encoding='utf-8') as f:
                json.dump(self.state, f, ensure_ascii=False, indent=2, default=str)
        except Exception as e:
            print(f"保存更新状态时出错: {e}")

    def _get_last_update_time(self, data_type: str, identifier: str = "default") -> Optional[datetime]:
        """
        获取最后更新时间

        Args:
            data_type: 数据类型
            identifier: 标识符

        Returns:
            最后更新时间
        """
        key = f"{data_type}:{identifier}"
        if key in self.state:
            try:
                return datetime.fromisoformat(self.state[key])
            except Exception as e:
                print(f"解析时间时出错: {e}")
                return None
        return None

    def _set_last_update_time(self, data_type: str, identifier: str = "default"):
        """
        设置最后更新时间

        Args:
            data_type: 数据类型
            identifier: 标识符
        """
        key = f"{data_type}:{identifier}"
        self.state[key] = datetime.now().isoformat()
        self._save_state()

    def needs_update(self, data_type: str, identifier: str = "default") -> bool:
        """
        检查是否需要更新

        Args:
            data_type: 数据类型
            identifier: 标识符

        Returns:
            是否需要更新
        """
        last_update = self._get_last_update_time(data_type, identifier)

        if last_update is None:
            return True

        time_since_update = datetime.now() - last_update
        return time_since_update.total_seconds() > self.update_interval

    async def update(self, data_type: str, identifier: str = "default", update_func=None, **kwargs) -> Optional[Any]:
        """
        执行增量更新

        Args:
            data_type: 数据类型
            identifier: 标识符
            update_func: 更新函数
            **kwargs: 传递给更新函数的参数

        Returns:
            更新后的数据
        """
        if self.needs_update(data_type, identifier):
            if update_func is None:
                print(f"未提供更新函数: {data_type}:{identifier}")
                return None

            try:
                print(f"正在更新: {data_type}:{identifier}")
                data = await update_func(**kwargs)

                if data is not None:
                    self._set_last_update_time(data_type, identifier)
                    print(f"更新成功: {data_type}:{identifier}")
                else:
                    print(f"更新失败: {data_type}:{identifier}")

                return data
            except Exception as e:
                print(f"更新过程出错: {data_type}:{identifier} - {e}")
                return None
        else:
            print(f"数据是最新的，不需要更新: {data_type}:{identifier}")
            return None

    def force_update(self, data_type: str, identifier: str = "default", update_func=None, **kwargs) -> Optional[Any]:
        """
        强制更新（忽略更新间隔）

        Args:
            data_type: 数据类型
            identifier: 标识符
            update_func: 更新函数
            **kwargs: 传递给更新函数的参数

        Returns:
            更新后的数据
        """
        try:
            print(f"强制更新: {data_type}:{identifier}")
            data = update_func(**kwargs)
            self._set_last_update_time(data_type, identifier)
            print(f"强制更新成功: {data_type}:{identifier}")
            return data
        except Exception as e:
            print(f"强制更新出错: {data_type}:{identifier} - {e}")
            return None

    def get_all_types(self) -> List[str]:
        """
        获取所有数据类型

        Returns:
            数据类型列表
        """
        types = set()
        for key in self.state:
            if ':' in key:
                data_type, _ = key.split(':', 1)
                types.add(data_type)
        return list(types)

    def get_all_updates(self) -> Dict[str, List[Dict]]:
        """
        获取所有更新信息

        Returns:
            更新信息字典
        """
        updates = {}
        for data_type in self.get_all_types():
            updates[data_type] = []
            for key in self.state:
                if key.startswith(f"{data_type}:"):
                    identifier = key.split(':', 1)[1]
                    last_update = self._get_last_update_time(data_type, identifier)
                    updates[data_type].append({
                        "identifier": identifier,
                        "last_update": last_update
                    })
        return updates

    def display_updates(self):
        """显示所有更新信息"""
        updates = self.get_all_updates()
        print("=" * 50)
        print("当前更新状态")
        print("=" * 50)
        for data_type, items in updates.items():
            print(f"\n数据类型: {data_type}")
            print("-" * len(data_type))
            if not items:
                print("   无更新记录")
                continue
            for item in items:
                print(f"   标识符: {item['identifier']}")
                if item['last_update']:
                    time_ago = datetime.now() - item['last_update']
                    if time_ago.total_seconds() < 3600:
                        time_str = f"{int(time_ago.total_seconds() / 60)}分钟前"
                    elif time_ago.total_seconds() < 86400:
                        time_str = f"{int(time_ago.total_seconds() / 3600)}小时前"
                    else:
                        time_str = f"{int(time_ago.total_seconds() / 86400)}天前"
                    print(f"   最后更新: {time_str}")
                else:
                    print("   最后更新: 从未更新")
                print()

    def reset_update_time(self, data_type: str, identifier: str = "default"):
        """
        重置更新时间

        Args:
            data_type: 数据类型
            identifier: 标识符
        """
        key = f"{data_type}:{identifier}"
        if key in self.state:
            del self.state[key]
            self._save_state()
            print(f"更新时间已重置: {data_type}:{identifier}")
        else:
            print(f"未找到更新记录: {data_type}:{identifier}")

    def clear_all_updates(self):
        """清除所有更新记录"""
        self.state = {}
        self._save_state()
        print("所有更新记录已清除")


class StockDataUpdater(IncrementalUpdater):
    """股票数据增量更新器"""

    def __init__(self, data_dir: str = "data", update_interval: int = 86400):
        """
        初始化股票数据增量更新器

        Args:
            data_dir: 数据目录
            update_interval: 更新间隔（秒）
        """
        super().__init__(data_dir, update_interval)

    async def update_quote(self, ticker: str, update_func=None) -> Optional[Dict]:
        """
        更新股票报价

        Args:
            ticker: 股票代码
            update_func: 更新函数

        Returns:
            股票报价数据
        """
        return await self.update("quote", ticker, update_func, ticker=ticker)

    async def update_history(self, ticker: str, period: str = "1y", interval: str = "1d", update_func=None) -> Optional[Dict]:
        """
        更新股票历史数据

        Args:
            ticker: 股票代码
            period: 时间范围
            interval: 数据间隔
            update_func: 更新函数

        Returns:
            股票历史数据
        """
        identifier = f"{ticker}:{period}:{interval}"
        return await self.update("history", identifier, update_func, ticker=ticker, period=period, interval=interval)

    async def update_financials(self, ticker: str, statement_type: str = "income", update_func=None) -> Optional[Dict]:
        """
        更新财务报表数据

        Args:
            ticker: 股票代码
            statement_type: 报表类型
            update_func: 更新函数

        Returns:
            财务报表数据
        """
        identifier = f"{ticker}:{statement_type}"
        return await self.update("financials", identifier, update_func, ticker=ticker, statement_type=statement_type)


class NewsDataUpdater(IncrementalUpdater):
    """新闻数据增量更新器"""

    def __init__(self, data_dir: str = "data", update_interval: int = 3600):
        """
        初始化新闻数据增量更新器

        Args:
            data_dir: 数据目录
            update_interval: 更新间隔（秒）
        """
        super().__init__(data_dir, update_interval)

    async def update_news(self, query: str, limit: int = 10, update_func=None) -> Optional[List]:
        """
        更新新闻数据

        Args:
            query: 搜索查询
            limit: 结果数量
            update_func: 更新函数

        Returns:
            新闻数据列表
        """
        identifier = f"{query}:{limit}"
        return await self.update("news", identifier, update_func, query=query, limit=limit)


# 全局增量更新实例
stock_updater = StockDataUpdater()
news_updater = NewsDataUpdater()


# 使用示例
if __name__ == "__main__":
    import asyncio

    async def mock_update_func(**kwargs):
        """模拟更新函数"""
        await asyncio.sleep(0.1)
        return {
            "data": "test_data",
            "timestamp": datetime.now().isoformat(),
            "parameters": kwargs
        }

    print("测试增量更新管理器...")

    # 创建股票数据更新器
    stock_updater = StockDataUpdater(update_interval=60)  # 设置60秒更新间隔

    print("\n1. 测试增量更新:")

    # 第一次调用，会立即更新
    result1 = asyncio.run(stock_updater.update_quote("AAPL", mock_update_func))
    print(f"   第一次更新成功: {result1 is not None}")

    # 第二次调用，60秒内不会更新
    result2 = asyncio.run(stock_updater.update_quote("AAPL", mock_update_func))
    print(f"   第二次更新成功: {result2 is not None}")
    print(f"   更新间隔内数据: {result2 is None}")

    print("\n2. 测试更新信息显示:")
    stock_updater.display_updates()

    # 创建新闻数据更新器
    news_updater = NewsDataUpdater(update_interval=60)

    print("\n3. 测试新闻数据更新:")

    result3 = asyncio.run(news_updater.update_news("Apple", 5, mock_update_func))
    print(f"   新闻更新成功: {result3 is not None}")

    news_updater.display_updates()

    print("\n✅ 增量更新管理器测试完成!")
