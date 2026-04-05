"""
OHLCV (candlestick) data model for TimescaleDB hypertable.

Note: No UUID primary key — TimescaleDB requires the time column
as the partition key for hypertable functionality.
Composite primary key: (timestamp, exchange, symbol, timeframe)
"""

from sqlalchemy import Column, String, Numeric, BigInteger, Index
from app.models.user import Base


class OHLCV(Base):
    """
    OHLCV candlestick data stored in TimescaleDB hypertable.

    Composite PK: (timestamp, exchange, symbol, timeframe)
    Partitioned by timestamp (7-day chunks).
    """
    __tablename__ = "ohlcv"

    timestamp = Column(
        BigInteger,
        primary_key=True,
        comment="Unix timestamp in milliseconds (CCXT format)"
    )
    exchange = Column(
        String(50),
        primary_key=True,
        comment="Exchange identifier (e.g., 'binance')"
    )
    symbol = Column(
        String(20),
        primary_key=True,
        comment="Trading pair (e.g., 'BTC/USDT')"
    )
    timeframe = Column(
        String(10),
        primary_key=True,
        comment="Candlestick timeframe (e.g., '1h', '4h', '1d')"
    )
    open = Column(Numeric(20, 8), nullable=False)
    high = Column(Numeric(20, 8), nullable=False)
    low = Column(Numeric(20, 8), nullable=False)
    close = Column(Numeric(20, 8), nullable=False)
    volume = Column(Numeric(30, 8), nullable=False)

    __table_args__ = (
        # Index for common query patterns
        Index("ix_ohlcv_symbol_timeframe_ts", "symbol", "timeframe", "timestamp"),
        Index("ix_ohlcv_exchange_symbol", "exchange", "symbol"),
    )

    def to_list(self) -> list:
        """Return CCXT-compatible list format: [timestamp, open, high, low, close, volume]"""
        return [
            self.timestamp,
            float(self.open),
            float(self.high),
            float(self.low),
            float(self.close),
            float(self.volume),
        ]

    def __repr__(self) -> str:
        return (
            f"<OHLCV {self.exchange}:{self.symbol} {self.timeframe} "
            f"@ {self.timestamp} close={self.close}>"
        )
