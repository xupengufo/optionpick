"""
GitHub 公开项目股票池加载器
Load index constituents from public GitHub-backed CSV sources.
"""
import logging
import re
from typing import Dict, Iterable, List, Optional, Sequence

import pandas as pd

logger = logging.getLogger(__name__)


class GitHubStockPoolProvider:
    """从 GitHub 公开项目加载指数成分股，并构建精选池"""

    _SYMBOL_PATTERN = re.compile(r"^[A-Z]{1,5}(\.[A-Z])?$")

    def __init__(self, source_config: Dict, preferred_symbols: Optional[Sequence[str]] = None):
        self.source_config = source_config or {}
        self.preferred_symbols = [s.upper() for s in (preferred_symbols or [])]
        self._cache: Dict[str, List[str]] = {}

    @classmethod
    def _normalize_symbols(cls, symbols: Iterable[str]) -> List[str]:
        normalized: List[str] = []
        seen = set()
        for raw in symbols:
            if raw is None or (isinstance(raw, float) and pd.isna(raw)):
                continue
            symbol = str(raw).strip().upper()
            if not symbol:
                continue
            if symbol in {"NAN", "NONE"}:
                continue
            if not cls._SYMBOL_PATTERN.match(symbol):
                continue
            if symbol in seen:
                continue
            seen.add(symbol)
            normalized.append(symbol)
        return normalized

    def _resolve_symbol_column(self, df: pd.DataFrame, source: Dict) -> str:
        candidates = source.get("symbol_columns", [])
        for col in candidates:
            if col in df.columns:
                return col
        # 容错：自动找常见列名
        for col in df.columns:
            lower = str(col).lower()
            if lower in ("symbol", "ticker"):
                return col
        raise ValueError(f"未找到股票代码列，可用列: {list(df.columns)}")

    def get_index_symbols(self, index_code: str) -> List[str]:
        """获取某个指数的全部成分股代码"""
        key = index_code.strip().lower()
        if key in self._cache:
            return list(self._cache[key])

        source = (self.source_config.get("sources", {}) or {}).get(key)
        if not source:
            raise ValueError(f"未知指数代码: {index_code}")

        url = source.get("url", "").strip()
        if not url:
            raise ValueError(f"{index_code} 缺少数据源 URL")

        df = pd.read_csv(url)
        symbol_col = self._resolve_symbol_column(df, source)
        symbols = self._normalize_symbols(df[symbol_col].tolist())

        if not symbols:
            raise ValueError(f"{index_code} 未解析出有效股票代码")

        self._cache[key] = symbols
        return list(symbols)

    def _build_curated(self, universe: Sequence[str], size: int) -> List[str]:
        if size <= 0:
            return []

        universe_set = set(universe)
        preferred = [
            s for s in self.preferred_symbols
            if s in universe_set
        ]
        preferred = self._normalize_symbols(preferred)

        remaining = sorted(s for s in universe if s not in set(preferred))
        curated = preferred + remaining
        return curated[:size]

    def get_curated_symbols(self, index_code: str, size: int) -> List[str]:
        """获取单一指数精选池（优先保留常用热门股票）"""
        universe = self.get_index_symbols(index_code)
        return self._build_curated(universe, size)

    def get_combined_curated_symbols(self, index_codes: Sequence[str], size: int) -> List[str]:
        """获取多指数合并精选池"""
        merged: List[str] = []
        seen = set()
        for code in index_codes:
            symbols = self.get_index_symbols(code)
            for symbol in symbols:
                if symbol in seen:
                    continue
                seen.add(symbol)
                merged.append(symbol)
        return self._build_curated(merged, size)
