"""
数据缓存管理 - 实现智能数据缓存和增量更新策略
"""

import os
import json
import pickle
import hashlib
import zlib
from typing import Any, Dict, Optional
from datetime import datetime, timedelta
from pathlib import Path


class DataCache:
    """数据缓存管理器"""

    def __init__(self, cache_dir: str = "data/cache", compress: bool = True, ttl: int = 86400):
        """
        初始化数据缓存管理器

        Args:
            cache_dir: 缓存目录
            compress: 是否压缩数据
            ttl: 数据过期时间（秒），默认24小时
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        self.compress = compress
        self.ttl = ttl

    def _get_cache_key(self, identifier: str) -> str:
        """
        生成缓存键

        Args:
            identifier: 标识符

        Returns:
            生成的缓存键（哈希值）
        """
        return hashlib.sha256(identifier.encode('utf-8')).hexdigest()

    def _get_cache_path(self, cache_key: str, extension: str = "pkl") -> Path:
        """
        获取缓存文件路径

        Args:
            cache_key: 缓存键
            extension: 文件扩展名

        Returns:
            缓存文件路径
        """
        subdir = cache_key[:2]  # 使用前2位字符作为子目录，避免单个目录文件过多
        subdir_path = self.cache_dir / subdir
        subdir_path.mkdir(exist_ok=True)

        return subdir_path / f"{cache_key}.{extension}"

    def _is_expired(self, cache_path: Path) -> bool:
        """
        检查缓存是否过期

        Args:
            cache_path: 缓存文件路径

        Returns:
            是否过期
        """
        if not cache_path.exists():
            return True

        file_mtime = datetime.fromtimestamp(cache_path.stat().st_mtime)
        current_time = datetime.now()

        return (current_time - file_mtime) > timedelta(seconds=self.ttl)

    def get(self, identifier: str) -> Optional[Any]:
        """
        获取缓存数据

        Args:
            identifier: 数据标识符

        Returns:
            缓存数据或None（如果不存在或已过期）
        """
        cache_key = self._get_cache_key(identifier)
        cache_path = self._get_cache_path(cache_key)

        if self._is_expired(cache_path):
            # 删除过期缓存
            if cache_path.exists():
                cache_path.unlink()

            return None

        try:
            with open(cache_path, 'rb') as f:
                data = f.read()

            if self.compress:
                data = zlib.decompress(data)

            return pickle.loads(data)

        except Exception as e:
            print(f"读取缓存时出错: {identifier} - {e}")
            try:
                cache_path.unlink()
            except:
                pass

            return None

    def set(self, identifier: str, data: Any) -> bool:
        """
        保存数据到缓存

        Args:
            identifier: 数据标识符
            data: 要保存的数据

        Returns:
            是否成功
        """
        try:
            cache_key = self._get_cache_key(identifier)
            cache_path = self._get_cache_path(cache_key)

            serialized = pickle.dumps(data)

            if self.compress:
                serialized = zlib.compress(serialized)

            with open(cache_path, 'wb') as f:
                f.write(serialized)

            return True

        except Exception as e:
            print(f"保存缓存时出错: {identifier} - {e}")
            return False

    def exists(self, identifier: str) -> bool:
        """
        检查缓存是否存在且未过期

        Args:
            identifier: 数据标识符

        Returns:
            缓存是否存在且未过期
        """
        cache_key = self._get_cache_key(identifier)
        cache_path = self._get_cache_path(cache_key)

        return cache_path.exists() and not self._is_expired(cache_path)

    def delete(self, identifier: str) -> bool:
        """
        删除缓存

        Args:
            identifier: 数据标识符

        Returns:
            是否成功删除
        """
        try:
            cache_key = self._get_cache_key(identifier)
            cache_path = self._get_cache_path(cache_key)

            if cache_path.exists():
                cache_path.unlink()

            return True

        except Exception as e:
            print(f"删除缓存时出错: {identifier} - {e}")
            return False

    def clear_expired(self) -> int:
        """
        清理过期的缓存

        Returns:
            清理的文件数量
        """
        cleared = 0

        for subdir in self.cache_dir.iterdir():
            if subdir.is_dir():
                for cache_file in subdir.iterdir():
                    if cache_file.is_file():
                        if self._is_expired(cache_file):
                            try:
                                cache_file.unlink()
                                cleared += 1
                            except:
                                pass

        return cleared

    def clear_all(self) -> int:
        """
        清理所有缓存

        Returns:
            清理的文件数量
        """
        cleared = 0

        for subdir in self.cache_dir.iterdir():
            if subdir.is_dir():
                for cache_file in subdir.iterdir():
                    if cache_file.is_file():
                        try:
                            cache_file.unlink()
                            cleared += 1
                        except:
                            pass

        return cleared

    def get_stats(self) -> Dict[str, int]:
        """
        获取缓存统计信息

        Returns:
            统计信息
        """
        total = 0
        expired = 0

        for subdir in self.cache_dir.iterdir():
            if subdir.is_dir():
                for cache_file in subdir.iterdir():
                    if cache_file.is_file():
                        total += 1
                        if self._is_expired(cache_file):
                            expired += 1

        return {
            "total": total,
            "expired": expired,
            "valid": total - expired
        }


class StockDataCache(DataCache):
    """股票数据缓存管理器"""

    def __init__(self, cache_dir: str = "data/cache/stock", compress: bool = True, ttl: int = 86400):
        """
        初始化股票数据缓存管理器

        Args:
            cache_dir: 缓存目录
            compress: 是否压缩数据
            ttl: 数据过期时间（秒）
        """
        super().__init__(cache_dir, compress, ttl)

    def get_quote(self, ticker: str) -> Optional[Dict]:
        """
        获取股票报价数据

        Args:
            ticker: 股票代码

        Returns:
            股票报价数据
        """
        return self.get(f"quote:{ticker}")

    def set_quote(self, ticker: str, quote_data: Dict) -> bool:
        """
        保存股票报价数据

        Args:
            ticker: 股票代码
            quote_data: 股票报价数据

        Returns:
            是否成功
        """
        return self.set(f"quote:{ticker}", quote_data)

    def get_history(self, ticker: str, period: str = "1y", interval: str = "1d") -> Optional[Dict]:
        """
        获取股票历史数据

        Args:
            ticker: 股票代码
            period: 时间范围
            interval: 数据间隔

        Returns:
            股票历史数据
        """
        return self.get(f"history:{ticker}:{period}:{interval}")

    def set_history(self, ticker: str, history_data: Dict, period: str = "1y", interval: str = "1d") -> bool:
        """
        保存股票历史数据

        Args:
            ticker: 股票代码
            history_data: 股票历史数据
            period: 时间范围
            interval: 数据间隔

        Returns:
            是否成功
        """
        return self.set(f"history:{ticker}:{period}:{interval}", history_data)

    def get_financials(self, ticker: str, statement_type: str = "income") -> Optional[Dict]:
        """
        获取财务报表数据

        Args:
            ticker: 股票代码
            statement_type: 报表类型 (income, balance, cashflow)

        Returns:
            财务报表数据
        """
        return self.get(f"financials:{ticker}:{statement_type}")

    def set_financials(self, ticker: str, financials_data: Dict, statement_type: str = "income") -> bool:
        """
        保存财务报表数据

        Args:
            ticker: 股票代码
            financials_data: 财务报表数据
            statement_type: 报表类型 (income, balance, cashflow)

        Returns:
            是否成功
        """
        return self.set(f"financials:{ticker}:{statement_type}", financials_data)


class NewsCache(DataCache):
    """新闻数据缓存管理器"""

    def __init__(self, cache_dir: str = "data/cache/news", compress: bool = True, ttl: int = 3600):
        """
        初始化新闻数据缓存管理器

        Args:
            cache_dir: 缓存目录
            compress: 是否压缩数据
            ttl: 数据过期时间（秒），默认1小时
        """
        super().__init__(cache_dir, compress, ttl)

    def get_news(self, query: str, limit: int = 10) -> Optional[list]:
        """
        获取新闻数据

        Args:
            query: 搜索查询
            limit: 结果数量

        Returns:
            新闻数据列表
        """
        return self.get(f"news:{query}:{limit}")

    def set_news(self, query: str, news_data: list, limit: int = 10) -> bool:
        """
        保存新闻数据

        Args:
            query: 搜索查询
            news_data: 新闻数据列表
            limit: 结果数量

        Returns:
            是否成功
        """
        return self.set(f"news:{query}:{limit}", news_data)


# 全局缓存实例
stock_cache = StockDataCache()
news_cache = NewsCache()


# 使用示例
if __name__ == "__main__":
    print("测试数据缓存管理器...")

    # 创建测试数据
    test_data = {
        "ticker": "AAPL",
        "price": 175.50,
        "change": 2.50,
        "volume": 100000000
    }

    # 测试股票数据缓存
    stock_cache = StockDataCache()

    print("\n1. 测试股票数据缓存:")
    stock_cache.set_quote("AAPL", test_data)
    retrieved = stock_cache.get_quote("AAPL")
    print("   保存和读取成功:", retrieved is not None)
    if retrieved:
        print(f"   价格: ${retrieved['price']:.2f}")

    # 测试统计信息
    print("\n2. 测试缓存统计:")
    stats = stock_cache.get_stats()
    print(f"   总缓存数: {stats['total']}")
    print(f"   有效缓存数: {stats['valid']}")
    print(f"   过期缓存数: {stats['expired']}")

    # 测试新闻数据缓存
    news_cache = NewsCache()

    print("\n3. 测试新闻数据缓存:")
    test_news = [
        {
            "title": "Apple股价上涨",
            "source": "CNBC",
            "url": "https://www.cnbc.com/apple"
        },
        {
            "title": "Apple发布新品",
            "source": "Reuters",
            "url": "https://www.reuters.com/apple"
        }
    ]

    news_cache.set_news("Apple", test_news, limit=2)
    retrieved_news = news_cache.get_news("Apple", limit=2)
    print("   保存和读取成功:", retrieved_news is not None)
    if retrieved_news:
        print(f"   新闻数量: {len(retrieved_news)}")

    print("\n✅ 数据缓存管理器测试完成!")
