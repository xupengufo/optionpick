"""
SQLite 持久化层
Persistence layer for portfolio positions and analysis history
"""
import sqlite3
import json
import os
import logging
from datetime import datetime
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class PortfolioStore:
    """投资组合持久化存储"""

    def __init__(self, db_path: str = "data/portfolio.db"):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        """获取数据库连接"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        """初始化数据库表"""
        conn = self._get_conn()
        try:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS positions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    strategy_type TEXT NOT NULL,
                    strike REAL NOT NULL,
                    expiry_date TEXT NOT NULL,
                    contracts INTEGER NOT NULL DEFAULT 1,
                    premium_per_contract REAL NOT NULL DEFAULT 0,
                    open_date TEXT NOT NULL,
                    close_date TEXT,
                    close_premium REAL,
                    status TEXT NOT NULL DEFAULT 'open',
                    notes TEXT DEFAULT '',
                    wheel_state TEXT DEFAULT '',
                    delta REAL DEFAULT 0,
                    theta REAL DEFAULT 0,
                    gamma REAL DEFAULT 0,
                    vega REAL DEFAULT 0,
                    created_at TEXT NOT NULL DEFAULT (datetime('now')),
                    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
                );

                CREATE TABLE IF NOT EXISTS analysis_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL DEFAULT (datetime('now')),
                    symbols TEXT NOT NULL,
                    strategy_preset TEXT DEFAULT '',
                    num_opportunities INTEGER DEFAULT 0,
                    results_json TEXT,
                    market_context_json TEXT
                );

                CREATE INDEX IF NOT EXISTS idx_positions_status
                    ON positions(status);
                CREATE INDEX IF NOT EXISTS idx_positions_symbol
                    ON positions(symbol);
                CREATE INDEX IF NOT EXISTS idx_analysis_timestamp
                    ON analysis_history(timestamp);
            """)
            conn.commit()
            # 兼容旧数据库
            self._ensure_columns(conn)
        except Exception as e:
            logger.error(f"数据库初始化失败: {e}")
        finally:
            conn.close()

    def _ensure_columns(self, conn: sqlite3.Connection):
        """确保新列存在（兼容旧数据库）"""
        existing = {row[1] for row in
                    conn.execute("PRAGMA table_info(positions)").fetchall()}
        new_cols = {
            'wheel_state': "TEXT DEFAULT ''",
            'delta': "REAL DEFAULT 0",
            'theta': "REAL DEFAULT 0",
            'gamma': "REAL DEFAULT 0",
            'vega': "REAL DEFAULT 0",
        }
        for col, definition in new_cols.items():
            if col not in existing:
                try:
                    conn.execute(
                        f"ALTER TABLE positions ADD COLUMN {col} {definition}")
                    conn.commit()
                except Exception:
                    pass

    # ===== 持仓 CRUD =====

    def add_position(self, symbol: str, strategy_type: str, strike: float,
                     expiry_date: str, contracts: int = 1,
                     premium_per_contract: float = 0,
                     open_date: Optional[str] = None,
                     notes: str = "",
                     wheel_state: str = "") -> Optional[int]:
        """添加新持仓，返回 ID"""
        if open_date is None:
            open_date = datetime.now().strftime("%Y-%m-%d")

        conn = self._get_conn()
        try:
            cursor = conn.execute("""
                INSERT INTO positions
                    (symbol, strategy_type, strike, expiry_date, contracts,
                     premium_per_contract, open_date, notes, wheel_state)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (symbol.upper(), strategy_type, strike, expiry_date,
                  contracts, premium_per_contract, open_date, notes,
                  wheel_state))
            conn.commit()
            return cursor.lastrowid
        except Exception as e:
            logger.error(f"添加持仓失败: {e}")
            return None
        finally:
            conn.close()

    def get_positions(self, status: str = "open") -> List[Dict]:
        """获取指定状态的持仓列表"""
        conn = self._get_conn()
        try:
            if status == "all":
                rows = conn.execute(
                    "SELECT * FROM positions ORDER BY open_date DESC"
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM positions WHERE status = ? ORDER BY open_date DESC",
                    (status,)
                ).fetchall()
            return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"获取持仓失败: {e}")
            return []
        finally:
            conn.close()

    def close_position(self, position_id: int,
                       close_premium: float = 0,
                       close_date: Optional[str] = None) -> bool:
        """关闭持仓"""
        if close_date is None:
            close_date = datetime.now().strftime("%Y-%m-%d")

        conn = self._get_conn()
        try:
            conn.execute("""
                UPDATE positions
                SET status = 'closed', close_date = ?, close_premium = ?,
                    updated_at = datetime('now')
                WHERE id = ?
            """, (close_date, close_premium, position_id))
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"关闭持仓失败: {e}")
            return False
        finally:
            conn.close()

    def delete_position(self, position_id: int) -> bool:
        """删除持仓"""
        conn = self._get_conn()
        try:
            conn.execute("DELETE FROM positions WHERE id = ?", (position_id,))
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"删除持仓失败: {e}")
            return False
        finally:
            conn.close()

    # ===== Wheel 策略跟踪 =====

    WHEEL_STATES = {
        'sell_put': '🔵 卖 Put（等待行权或过期）',
        'assigned': '🟡 已被行权（持有股票）',
        'sell_call': '🟠 卖 Call（等待被叫走或过期）',
        'called_away': '🟢 已被叫走（一轮完成）',
        'idle': '⚪ 空闲',
    }

    def update_wheel_state(self, position_id: int,
                           new_state: str) -> bool:
        """更新 Wheel 策略状态"""
        if new_state not in self.WHEEL_STATES:
            logger.warning(f"无效的 Wheel 状态: {new_state}")
            return False
        conn = self._get_conn()
        try:
            conn.execute("""
                UPDATE positions
                SET wheel_state = ?, updated_at = datetime('now')
                WHERE id = ?
            """, (new_state, position_id))
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"更新 Wheel 状态失败: {e}")
            return False
        finally:
            conn.close()

    def get_wheel_positions(self) -> List[Dict]:
        """获取所有 Wheel 策略相关持仓"""
        conn = self._get_conn()
        try:
            rows = conn.execute("""
                SELECT * FROM positions
                WHERE wheel_state != '' AND wheel_state IS NOT NULL
                ORDER BY symbol, open_date DESC
            """).fetchall()
            return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"获取 Wheel 持仓失败: {e}")
            return []
        finally:
            conn.close()

    # ===== 组合 Greeks =====

    def update_position_greeks(self, position_id: int,
                               delta: float, theta: float,
                               gamma: float = 0,
                               vega: float = 0) -> bool:
        """更新单个持仓的 Greeks"""
        conn = self._get_conn()
        try:
            conn.execute("""
                UPDATE positions
                SET delta = ?, theta = ?, gamma = ?, vega = ?,
                    updated_at = datetime('now')
                WHERE id = ?
            """, (delta, theta, gamma, vega, position_id))
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"更新 Greeks 失败: {e}")
            return False
        finally:
            conn.close()

    def get_portfolio_greeks(self) -> Dict:
        """聚合所有 open 持仓的 Greeks"""
        conn = self._get_conn()
        try:
            rows = conn.execute("""
                SELECT symbol, strategy_type, contracts, delta, theta,
                       gamma, vega
                FROM positions WHERE status = 'open'
            """).fetchall()

            total_delta = 0.0
            total_theta = 0.0
            total_gamma = 0.0
            total_vega = 0.0
            by_symbol: Dict[str, Dict] = {}

            for row in rows:
                contracts = row['contracts']
                d = row['delta'] * contracts * 100
                t = row['theta'] * contracts * 100
                g = row['gamma'] * contracts * 100
                v = row['vega'] * contracts * 100
                total_delta += d
                total_theta += t
                total_gamma += g
                total_vega += v

                sym = row['symbol']
                if sym not in by_symbol:
                    by_symbol[sym] = {'delta': 0, 'theta': 0,
                                      'gamma': 0, 'vega': 0}
                by_symbol[sym]['delta'] += d
                by_symbol[sym]['theta'] += t
                by_symbol[sym]['gamma'] += g
                by_symbol[sym]['vega'] += v

            return {
                'total_delta': round(total_delta, 2),
                'total_theta': round(total_theta, 2),
                'total_gamma': round(total_gamma, 4),
                'total_vega': round(total_vega, 2),
                'by_symbol': {
                    sym: {k: round(v, 2) for k, v in vals.items()}
                    for sym, vals in by_symbol.items()
                },
            }
        except Exception as e:
            logger.error(f"聚合 Greeks 失败: {e}")
            return {'total_delta': 0, 'total_theta': 0,
                    'total_gamma': 0, 'total_vega': 0, 'by_symbol': {}}
        finally:
            conn.close()

    def get_portfolio_summary(self) -> Dict:
        """获取投资组合汇总"""
        conn = self._get_conn()
        try:
            open_positions = conn.execute(
                "SELECT * FROM positions WHERE status = 'open'"
            ).fetchall()
            closed_positions = conn.execute(
                "SELECT * FROM positions WHERE status = 'closed'"
            ).fetchall()

            realized_pnl = 0.0
            for pos in closed_positions:
                entry_credit = pos['premium_per_contract'] * pos['contracts'] * 100
                exit_debit = (pos['close_premium'] or 0) * pos['contracts'] * 100
                realized_pnl += entry_credit - exit_debit

            total_premium_collected = sum(
                pos['premium_per_contract'] * pos['contracts'] * 100
                for pos in open_positions
            )

            strategies = {}
            for pos in open_positions:
                st = pos['strategy_type']
                if st not in strategies:
                    strategies[st] = 0
                strategies[st] += 1

            symbols = {}
            for pos in open_positions:
                sym = pos['symbol']
                if sym not in symbols:
                    symbols[sym] = 0
                symbols[sym] += 1

            return {
                'open_count': len(open_positions),
                'closed_count': len(closed_positions),
                'realized_pnl': realized_pnl,
                'total_premium_collected': total_premium_collected,
                'strategy_distribution': strategies,
                'symbol_distribution': symbols,
            }
        except Exception as e:
            logger.error(f"获取组合汇总失败: {e}")
            return {}
        finally:
            conn.close()

    # ===== 分析历史 =====

    def save_analysis(self, symbols: List[str], opportunities: List[Dict],
                      market_context: Dict,
                      strategy_preset: str = "") -> Optional[int]:
        """保存分析结果"""
        conn = self._get_conn()
        try:
            simplified = []
            for opp in opportunities:
                simplified.append({
                    'symbol': opp.get('symbol', ''),
                    'strategy_type': opp.get('strategy_type', ''),
                    'strike': opp.get('strike', 0),
                    'expiry_date': opp.get('expiry_date', ''),
                    'score': opp.get('score', 0),
                    'returns': opp.get('returns', {}),
                    'probabilities': opp.get('probabilities', {}),
                })

            cursor = conn.execute("""
                INSERT INTO analysis_history
                    (symbols, strategy_preset, num_opportunities,
                     results_json, market_context_json)
                VALUES (?, ?, ?, ?, ?)
            """, (
                json.dumps(symbols),
                strategy_preset,
                len(opportunities),
                json.dumps(simplified, ensure_ascii=False),
                json.dumps(market_context, ensure_ascii=False),
            ))
            conn.commit()
            return cursor.lastrowid
        except Exception as e:
            logger.error(f"保存分析历史失败: {e}")
            return None
        finally:
            conn.close()

    def get_analysis_history(self, limit: int = 20) -> List[Dict]:
        """获取历史分析记录"""
        conn = self._get_conn()
        try:
            rows = conn.execute("""
                SELECT id, timestamp, symbols, strategy_preset,
                       num_opportunities
                FROM analysis_history
                ORDER BY timestamp DESC
                LIMIT ?
            """, (limit,)).fetchall()
            return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"获取分析历史失败: {e}")
            return []
        finally:
            conn.close()

    def get_analysis_detail(self, analysis_id: int) -> Optional[Dict]:
        """获取单次分析的详细结果"""
        conn = self._get_conn()
        try:
            row = conn.execute(
                "SELECT * FROM analysis_history WHERE id = ?",
                (analysis_id,)
            ).fetchone()
            if row:
                result = dict(row)
                result['symbols'] = json.loads(result['symbols'])
                result['results_json'] = json.loads(
                    result['results_json'] or '[]')
                result['market_context_json'] = json.loads(
                    result['market_context_json'] or '{}')
                return result
            return None
        except Exception as e:
            logger.error(f"获取分析详情失败: {e}")
            return None
        finally:
            conn.close()
