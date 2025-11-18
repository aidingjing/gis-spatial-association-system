"""
多级缓存系统

提供智能的内存和磁盘缓存管理，支持LRU淘汰策略、缓存预热和性能优化。
包括分布式缓存支持和持久化功能。

Author: CCPM Auto Development System
"""

import logging
import time
import os
import pickle
import hashlib
import tempfile
import threading
from typing import Any, Dict, List, Optional, Union, Callable, Tuple
from abc import ABC, abstractmethod
from collections import OrderedDict
from dataclasses import dataclass
import sqlite3
import json
import psutil
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """缓存条目"""
    key: str
    value: Any
    created_at: float
    last_accessed: float
    access_count: int
    size_bytes: int
    ttl_seconds: Optional[float] = None


@dataclass
class CacheStats:
    """缓存统计信息"""
    hits: int = 0
    misses: int = 0
    evictions: int = 0
    insertions: int = 0
    total_requests: int = 0
    hit_rate: float = 0.0
    current_size_bytes: int = 0
    max_size_bytes: int = 0
    entry_count: int = 0


class CacheInterface(ABC):
    """缓存接口"""

    @abstractmethod
    def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        pass

    @abstractmethod
    def put(self, key: str, value: Any, ttl_seconds: Optional[float] = None) -> bool:
        """存储缓存值"""
        pass

    @abstractmethod
    def delete(self, key: str) -> bool:
        """删除缓存项"""
        pass

    @abstractmethod
    def clear(self) -> None:
        """清空缓存"""
        pass

    @abstractmethod
    def get_stats(self) -> CacheStats:
        """获取缓存统计信息"""
        pass


class MemoryCache(CacheInterface):
    """内存缓存实现（LRU策略）"""

    def __init__(self,
                 max_size_mb: int = 512,
                 max_entries: int = 10000,
                 enable_stats: bool = True):
        """初始化内存缓存

        Args:
            max_size_mb: 最大内存大小（MB）
            max_entries: 最大条目数
            enable_stats: 是否启用统计
        """
        self.max_size_bytes = max_size_mb * 1024**2
        self.max_entries = max_entries
        self.enable_stats = enable_stats

        self.cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self.lock = threading.RLock()

        # 统计信息
        self.stats = CacheStats(max_size_bytes=self.max_size_bytes)

        logger.info(f"内存缓存初始化: 最大大小={max_size_mb}MB, "
                   f"最大条目数={max_entries}")

    def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        with self.lock:
            if key not in self.cache:
                if self.enable_stats:
                    self.stats.misses += 1
                    self.stats.total_requests += 1
                    self.stats.hit_rate = self.stats.hits / max(1, self.stats.total_requests)
                return None

            # 检查TTL
            entry = self.cache[key]
            current_time = time.time()

            if entry.ttl_seconds and (current_time - entry.created_at) > entry.ttl_seconds:
                # 过期，删除
                del self.cache[key]
                self._update_stats_on_delete(entry)
                if self.enable_stats:
                    self.stats.misses += 1
                    self.stats.total_requests += 1
                    self.stats.hit_rate = self.stats.hits / max(1, self.stats.total_requests)
                return None

            # 更新访问信息
            entry.last_accessed = current_time
            entry.access_count += 1

            # 移到末尾（LRU策略）
            self.cache.move_to_end(key)

            if self.enable_stats:
                self.stats.hits += 1
                self.stats.total_requests += 1
                self.stats.hit_rate = self.stats.hits / max(1, self.stats.total_requests)

            return entry.value

    def put(self, key: str, value: Any, ttl_seconds: Optional[float] = None) -> bool:
        """存储缓存值"""
        with self.lock:
            current_time = time.time()
            value_size = self._get_object_size(value)

            # 检查单个对象是否超过限制
            if value_size > self.max_size_bytes:
                logger.warning(f"缓存对象过大: {key} ({value_size} bytes > {self.max_size_bytes} bytes)")
                return False

            # 如果键已存在，更新值
            if key in self.cache:
                old_entry = self.cache[key]
                self._update_stats_on_delete(old_entry)
                del self.cache[key]

            # 确保有足够空间
            while (self._get_total_size() + value_size > self.max_size_bytes or
                   len(self.cache) >= self.max_entries):
                if not self.cache:
                    break  # 缓存为空，无法继续淘汰

                # LRU淘汰：移除最旧的条目
                oldest_key, oldest_entry = next(iter(self.cache.items()))
                del self.cache[oldest_key]
                self._update_stats_on_delete(oldest_entry)

                if self.enable_stats:
                    self.stats.evictions += 1

            # 创建新条目
            entry = CacheEntry(
                key=key,
                value=value,
                created_at=current_time,
                last_accessed=current_time,
                access_count=1,
                size_bytes=value_size,
                ttl_seconds=ttl_seconds
            )

            self.cache[key] = entry
            self.cache.move_to_end(key)

            if self.enable_stats:
                self.stats.insertions += 1
                self._update_current_stats()

            return True

    def delete(self, key: str) -> bool:
        """删除缓存项"""
        with self.lock:
            if key not in self.cache:
                return False

            entry = self.cache.pop(key)
            self._update_stats_on_delete(entry)
            self._update_current_stats()
            return True

    def clear(self) -> None:
        """清空缓存"""
        with self.lock:
            self.cache.clear()
            self._update_current_stats()

    def get_stats(self) -> CacheStats:
        """获取缓存统计信息"""
        with self.lock:
            self._update_current_stats()
            return self.stats

    def _get_object_size(self, obj: Any) -> int:
        """估算对象大小"""
        try:
            return len(pickle.dumps(obj))
        except Exception:
            # 如果序列化失败，使用字符串长度作为近似
            try:
                return len(str(obj))
            except Exception:
                return 100  # 默认大小

    def _get_total_size(self) -> int:
        """获取缓存总大小"""
        return sum(entry.size_bytes for entry in self.cache.values())

    def _update_stats_on_delete(self, entry: CacheEntry):
        """更新删除条目时的统计信息"""
        if self.enable_stats:
            self.stats.current_size_bytes -= entry.size_bytes

    def _update_current_stats(self):
        """更新当前统计信息"""
        if self.enable_stats:
            self.stats.current_size_bytes = self._get_total_size()
            self.stats.entry_count = len(self.cache)
            self.stats.hit_rate = self.stats.hits / max(1, self.stats.total_requests)

    def get_hot_keys(self, top_n: int = 10) -> List[Tuple[str, int]]:
        """获取热门键"""
        with self.lock:
            sorted_entries = sorted(self.cache.values(),
                                  key=lambda e: e.access_count,
                                  reverse=True)
            return [(entry.key, entry.access_count) for entry in sorted_entries[:top_n]]

    def get_expired_keys(self) -> List[str]:
        """获取过期的键"""
        with self.lock:
            current_time = time.time()
            expired_keys = []

            for key, entry in self.cache.items():
                if entry.ttl_seconds and (current_time - entry.created_at) > entry.ttl_seconds:
                    expired_keys.append(key)

            return expired_keys


class DiskCache(CacheInterface):
    """磁盘缓存实现"""

    def __init__(self,
                 cache_dir: Optional[str] = None,
                 max_size_gb: float = 2.0,
                 enable_compression: bool = False):
        """初始化磁盘缓存

        Args:
            cache_dir: 缓存目录
            max_size_gb: 最大磁盘大小（GB）
            enable_compression: 是否启用压缩
        """
        self.cache_dir = cache_dir or tempfile.mkdtemp(prefix='spatial_cache_')
        self.max_size_bytes = max_size_gb * 1024**3
        self.enable_compression = enable_compression

        # 创建缓存目录
        os.makedirs(self.cache_dir, exist_ok=True)

        # 初始化SQLite数据库
        self.db_path = os.path.join(self.cache_dir, 'cache_index.db')
        self._init_database()

        # 统计信息
        self.stats = CacheStats(max_size_bytes=self.max_size_bytes)

        self.lock = threading.RLock()

        logger.info(f"磁盘缓存初始化: 目录={self.cache_dir}, "
                   f"最大大小={max_size_gb}GB, 压缩={enable_compression}")

    def _init_database(self):
        """初始化缓存索引数据库"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS cache_entries (
                    key TEXT PRIMARY KEY,
                    filename TEXT,
                    created_at REAL,
                    last_accessed REAL,
                    access_count INTEGER,
                    size_bytes INTEGER,
                    ttl_seconds REAL
                )
            ''')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_created_at ON cache_entries(created_at)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_last_accessed ON cache_entries(last_accessed)')
            conn.commit()

    def _get_cache_filename(self, key: str) -> str:
        """获取缓存文件名"""
        # 使用MD5哈希确保文件名安全
        key_hash = hashlib.md5(key.encode()).hexdigest()
        return os.path.join(self.cache_dir, f"{key_hash}.cache")

    def _serialize_value(self, value: Any) -> bytes:
        """序列化值"""
        data = pickle.dumps(value)
        if self.enable_compression:
            try:
                import gzip
                data = gzip.compress(data)
            except ImportError:
                logger.warning("gzip不可用，跳过压缩")
        return data

    def _deserialize_value(self, data: bytes) -> Any:
        """反序列化值"""
        if self.enable_compression:
            try:
                import gzip
                if data.startswith(b'\x1f\x8b'):
                    data = gzip.decompress(data)
            except ImportError:
                pass

        return pickle.loads(data)

    def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        with self.lock:
            # 查询数据库
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    'SELECT filename, created_at, ttl_seconds FROM cache_entries WHERE key = ?',
                    (key,)
                )
                row = cursor.fetchone()

                if row is None:
                    self.stats.misses += 1
                    self.stats.total_requests += 1
                    self.stats.hit_rate = self.stats.hits / max(1, self.stats.total_requests)
                    return None

                filename, created_at, ttl_seconds = row

                # 检查文件是否存在
                if not os.path.exists(filename):
                    # 文件不存在，删除数据库记录
                    conn.execute('DELETE FROM cache_entries WHERE key = ?', (key,))
                    conn.commit()
                    self.stats.misses += 1
                    self.stats.total_requests += 1
                    self.stats.hit_rate = self.stats.hits / max(1, self.stats.total_requests)
                    return None

                # 检查TTL
                if ttl_seconds and (time.time() - created_at) > ttl_seconds:
                    # 过期，删除文件和数据库记录
                    try:
                        os.remove(filename)
                    except Exception as e:
                        logger.warning(f"删除过期缓存文件失败: {filename}, 错误: {str(e)}")

                    conn.execute('DELETE FROM cache_entries WHERE key = ?', (key,))
                    conn.commit()
                    self.stats.misses += 1
                    self.stats.total_requests += 1
                    self.stats.hit_rate = self.stats.hits / max(1, self.stats.total_requests)
                    return None

            # 读取文件
            try:
                with open(filename, 'rb') as f:
                    data = f.read()
                value = self._deserialize_value(data)

                # 更新访问信息
                with sqlite3.connect(self.db_path) as conn:
                    conn.execute(
                        'UPDATE cache_entries SET last_accessed = ?, access_count = access_count + 1 WHERE key = ?',
                        (time.time(), key)
                    )
                    conn.commit()

                self.stats.hits += 1
                self.stats.total_requests += 1
                self.stats.hit_rate = self.stats.hits / max(1, self.stats.total_requests)

                return value

            except Exception as e:
                logger.error(f"读取缓存文件失败: {filename}, 错误: {str(e)}")
                self.stats.misses += 1
                self.stats.total_requests += 1
                self.stats.hit_rate = self.stats.hits / max(1, self.stats.total_requests)
                return None

    def put(self, key: str, value: Any, ttl_seconds: Optional[float] = None) -> bool:
        """存储缓存值"""
        with self.lock:
            filename = self._get_cache_filename(key)
            current_time = time.time()

            try:
                # 序列化值
                data = self._serialize_value(value)
                size_bytes = len(data)

                # 检查单个文件大小限制
                if size_bytes > self.max_size_bytes:
                    logger.warning(f"缓存对象过大: {key} ({size_bytes} bytes)")
                    return False

                # 写入文件
                with open(filename, 'wb') as f:
                    f.write(data)

                # 更新数据库
                with sqlite3.connect(self.db_path) as conn:
                    conn.execute('''
                        INSERT OR REPLACE INTO cache_entries
                        (key, filename, created_at, last_accessed, access_count, size_bytes, ttl_seconds)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''', (key, filename, current_time, current_time, 1, size_bytes, ttl_seconds))
                    conn.commit()

                self.stats.insertions += 1
                self._cleanup_if_needed()

                return True

            except Exception as e:
                logger.error(f"写入缓存文件失败: {filename}, 错误: {str(e)}")
                # 清理可能创建的文件
                if os.path.exists(filename):
                    try:
                        os.remove(filename)
                    except Exception:
                        pass
                return False

    def delete(self, key: str) -> bool:
        """删除缓存项"""
        with self.lock:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute('SELECT filename FROM cache_entries WHERE key = ?', (key,))
                row = cursor.fetchone()

                if row is None:
                    return False

                filename = row[0]

                # 删除文件
                try:
                    if os.path.exists(filename):
                        os.remove(filename)
                except Exception as e:
                    logger.warning(f"删除缓存文件失败: {filename}, 错误: {str(e)}")

                # 删除数据库记录
                conn.execute('DELETE FROM cache_entries WHERE key = ?', (key,))
                conn.commit()

                return True

    def clear(self) -> None:
        """清空缓存"""
        with self.lock:
            # 删除所有缓存文件
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute('SELECT filename FROM cache_entries')
                for row in cursor:
                    filename = row[0]
                    try:
                        if os.path.exists(filename):
                            os.remove(filename)
                    except Exception as e:
                        logger.warning(f"删除缓存文件失败: {filename}, 错误: {str(e)}")

                # 清空数据库
                conn.execute('DELETE FROM cache_entries')
                conn.commit()

    def get_stats(self) -> CacheStats:
        """获取缓存统计信息"""
        with self.lock:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute('''
                    SELECT COUNT(*), SUM(size_bytes), SUM(access_count),
                           SUM(CASE WHEN ttl_seconds > 0 AND (strftime('%s', 'now') - created_at) > ttl_seconds THEN 1 ELSE 0 END)
                    FROM cache_entries
                ''')
                row = cursor.fetchone()

                self.stats.entry_count = row[0] or 0
                self.stats.current_size_bytes = row[1] or 0
                total_accesses = row[2] or 0

            # 计算命中率和过期项数量
            expired_count = row[3] or 0

            return self.stats

    def _cleanup_if_needed(self):
        """如果需要，清理过期文件和大小的缓存项"""
        current_time = time.time()

        with sqlite3.connect(self.db_path) as conn:
            # 清理过期项
            conn.execute('''
                DELETE FROM cache_entries
                WHERE ttl_seconds > 0 AND (? - created_at) > ttl_seconds
            ''', (current_time,))
            conn.commit()

            # 检查总大小
            cursor = conn.execute('SELECT SUM(size_bytes) FROM cache_entries')
            total_size = cursor.fetchone()[0] or 0

            if total_size > self.max_size_bytes:
                # LRU清理：删除最旧的条目
                cleanup_size = total_size - self.max_size_bytes + (self.max_size_bytes * 0.1)  # 额外清理10%

                cursor = conn.execute('''
                    SELECT key, filename, size_bytes
                    FROM cache_entries
                    ORDER BY last_accessed ASC
                ''')

                cleaned_size = 0
                for key, filename, size_bytes in cursor:
                    if cleaned_size >= cleanup_size:
                        break

                    try:
                        if os.path.exists(filename):
                            os.remove(filename)
                    except Exception as e:
                        logger.warning(f"删除缓存文件失败: {filename}, 错误: {str(e)}")

                    conn.execute('DELETE FROM cache_entries WHERE key = ?', (key,))
                    cleaned_size += size_bytes

                conn.commit()
                logger.info(f"磁盘缓存清理完成，释放空间: {cleaned_size / 1024**2:.2f}MB")


class MultiLevelCache(CacheInterface):
    """多级缓存系统

    结合内存缓存和磁盘缓存的优点，自动在不同层级间移动数据。
    """

    def __init__(self,
                 memory_limit_mb: int = 512,
                 disk_limit_gb: float = 2.0,
                 memory_ratio: float = 0.7,
                 enable_stats: bool = True):
        """初始化多级缓存

        Args:
            memory_limit_mb: 内存缓存限制（MB）
            disk_limit_gb: 磁盘缓存限制（GB）
            memory_ratio: 内存缓存占用总缓存的比率
            enable_stats: 是否启用统计
        """
        self.memory_ratio = memory_ratio
        self.enable_stats = enable_stats

        # 创建内存和磁盘缓存
        self.memory_cache = MemoryCache(
            max_size_mb=memory_limit_mb,
            enable_stats=enable_stats
        )

        self.disk_cache = DiskCache(
            max_size_gb=disk_limit_gb,
            enable_compression=True
        )

        # 统计信息
        self.stats = CacheStats()

        self.lock = threading.RLock()

        logger.info(f"多级缓存初始化: 内存限制={memory_limit_mb}MB, "
                   f"磁盘限制={disk_limit_gb}GB, 内存比率={memory_ratio}")

    def get(self, key: str) -> Optional[Any]:
        """获取缓存值（首先检查内存缓存，然后磁盘缓存）"""
        with self.lock:
            # 1. 尝试从内存缓存获取
            value = self.memory_cache.get(key)
            if value is not None:
                if self.enable_stats:
                    self.stats.hits += 1
                    self.stats.total_requests += 1
                    self.stats.hit_rate = self.stats.hits / max(1, self.stats.total_requests)
                return value

            # 2. 尝试从磁盘缓存获取
            value = self.disk_cache.get(key)
            if value is not None:
                # 3. 将数据提升到内存缓存（如果空间允许）
                value_size = self._get_object_size(value)
                if self._should_promote_to_memory(value_size):
                    self.memory_cache.put(key, value)
                    logger.debug(f"数据提升到内存缓存: {key}")

                if self.enable_stats:
                    self.stats.hits += 1
                    self.stats.total_requests += 1
                    self.stats.hit_rate = self.stats.hits / max(1, self.stats.total_requests)

                return value

            # 4. 未找到
            if self.enable_stats:
                self.stats.misses += 1
                self.stats.total_requests += 1
                self.stats.hit_rate = self.stats.hits / max(1, self.stats.total_requests)

            return None

    def put(self, key: str, value: Any, ttl_seconds: Optional[float] = None) -> bool:
        """存储缓存值（智能选择存储层级）"""
        with self.lock:
            value_size = self._get_object_size(value)
            memory_stats = self.memory_cache.get_stats()

            # 决定存储策略
            if self._should_store_in_memory(value_size, memory_stats):
                # 存储到内存缓存
                success = self.memory_cache.put(key, value, ttl_seconds)
                if success and self.enable_stats:
                    self.stats.insertions += 1
                return success
            else:
                # 存储到磁盘缓存
                success = self.disk_cache.put(key, value, ttl_seconds)
                if success and self.enable_stats:
                    self.stats.insertions += 1
                return success

    def delete(self, key: str) -> bool:
        """删除缓存项（从所有层级删除）"""
        with self.lock:
            memory_deleted = self.memory_cache.delete(key)
            disk_deleted = self.disk_cache.delete(key)
            return memory_deleted or disk_deleted

    def clear(self) -> None:
        """清空所有缓存"""
        with self.lock:
            self.memory_cache.clear()
            self.disk_cache.clear()

    def get_stats(self) -> Dict[str, Any]:
        """获取完整的缓存统计信息"""
        memory_stats = self.memory_cache.get_stats()
        disk_stats = self.disk_cache.get_stats()

        # 计算总体统计
        total_current_size = memory_stats.current_size_bytes + disk_stats.current_size_bytes
        total_entries = memory_stats.entry_count + disk_stats.entry_count

        return {
            'overall': {
                'hits': self.stats.hits,
                'misses': self.stats.misses,
                'evictions': self.stats.evictions,
                'insertions': self.stats.insertions,
                'total_requests': self.stats.total_requests,
                'hit_rate': self.stats.hit_rate,
                'current_size_bytes': total_current_size,
                'current_size_mb': total_current_size / 1024**2,
                'entry_count': total_entries
            },
            'memory_cache': {
                'hits': memory_stats.hits,
                'misses': memory_stats.misses,
                'evictions': memory_stats.evictions,
                'insertions': memory_stats.insertions,
                'hit_rate': memory_stats.hit_rate,
                'current_size_bytes': memory_stats.current_size_bytes,
                'current_size_mb': memory_stats.current_size_bytes / 1024**2,
                'max_size_bytes': memory_stats.max_size_bytes,
                'entry_count': memory_stats.entry_count,
                'max_entries': memory_stats.max_entries
            },
            'disk_cache': {
                'hits': disk_stats.hits,
                'misses': disk_stats.misses,
                'evictions': disk_stats.evictions,
                'insertions': disk_stats.insertions,
                'hit_rate': disk_stats.hit_rate,
                'current_size_bytes': disk_stats.current_size_bytes,
                'current_size_mb': disk_stats.current_size_bytes / 1024**2,
                'max_size_bytes': disk_stats.max_size_bytes,
                'entry_count': disk_stats.entry_count
            }
        }

    def _get_object_size(self, obj: Any) -> int:
        """估算对象大小"""
        try:
            return len(pickle.dumps(obj))
        except Exception:
            try:
                return len(str(obj))
            except Exception:
                return 100

    def _should_store_in_memory(self, value_size: int, memory_stats: CacheStats) -> bool:
        """判断是否应该存储到内存缓存"""
        # 如果内存缓存使用率超过阈值，存储到磁盘
        memory_usage_ratio = memory_stats.current_size_bytes / memory_stats.max_size_bytes

        # 大对象直接存储到磁盘
        if value_size > memory_stats.max_size_bytes * 0.1:  # 超过内存限制的10%
            return False

        # 内存使用率低于阈值时存储到内存
        return memory_usage_ratio < self.memory_ratio

    def _should_promote_to_memory(self, value_size: int) -> bool:
        """判断是否应该提升到内存缓存"""
        memory_stats = self.memory_cache.get_stats()
        return self._should_store_in_memory(value_size, memory_stats)

    def preload_cache(self, keys: List[str], data_source: Callable[[str], Any]):
        """缓存预热

        Args:
            keys: 需要预加载的键列表
            data_source: 数据源函数，接受键返回值
        """
        logger.info(f"开始缓存预热，键数量: {len(keys)}")
        start_time = time.time()

        loaded_count = 0
        for key in keys:
            try:
                if self.get(key) is None:  # 仅加载不存在的键
                    value = data_source(key)
                    if value is not None:
                        self.put(key, value)
                        loaded_count += 1
            except Exception as e:
                logger.warning(f"预热加载失败: {key}, 错误: {str(e)}")

        load_time = time.time() - start_time
        logger.info(f"缓存预热完成: 加载数量={loaded_count}/{len(keys)}, "
                   f"耗时={load_time:.2f}s")

    def export_stats(self, file_path: str):
        """导出统计信息到文件"""
        stats = self.get_stats()

        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(stats, f, indent=2, ensure_ascii=False)
            logger.info(f"缓存统计信息已导出到: {file_path}")
        except Exception as e:
            logger.error(f"导出统计信息失败: {str(e)}")

    def optimize_cache(self):
        """优化缓存性能"""
        logger.info("开始缓存优化...")
        start_time = time.time()

        with self.lock:
            # 清理过期的内存缓存项
            expired_keys = self.memory_cache.get_expired_keys()
            for key in expired_keys:
                self.memory_cache.delete(key)

            if expired_keys:
                logger.info(f"清理过期内存缓存项: {len(expired_keys)}")

            # 强制磁盘缓存清理
            self.disk_cache._cleanup_if_needed()

        optimization_time = time.time() - start_time
        logger.info(f"缓存优化完成，耗时: {optimization_time:.2f}s")


# 工厂函数
def create_cache(cache_type: str = 'multilevel',
                memory_limit_mb: int = 512,
                disk_limit_gb: float = 2.0,
                **kwargs) -> CacheInterface:
    """创建缓存实例的工厂函数

    Args:
        cache_type: 缓存类型 ('memory', 'disk', 'multilevel')
        memory_limit_mb: 内存限制（MB）
        disk_limit_gb: 磁盘限制（GB）
        **kwargs: 其他参数

    Returns:
        缓存实例
    """
    if cache_type == 'memory':
        return MemoryCache(max_size_mb=memory_limit_mb, **kwargs)
    elif cache_type == 'disk':
        return DiskCache(max_size_gb=disk_limit_gb, **kwargs)
    elif cache_type == 'multilevel':
        return MultiLevelCache(
            memory_limit_mb=memory_limit_mb,
            disk_limit_gb=disk_limit_gb,
            **kwargs
        )
    else:
        raise ValueError(f"不支持的缓存类型: {cache_type}")