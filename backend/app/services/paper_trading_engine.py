"""
Paper Trading Engine — order simulation state machine.

Simulates order fills with realistic execution:
- 0.05% slippage on entry and exit
- 0.1% commission per trade
- No lookahead bias: signal on candle N → fill at candle N+1 open
- Risk limit enforcement (max position size as % of portfolio)

Components:
- PaperPortfolio: Tracks balance, positions, and realized PnL
- PaperTradingEngine: Simulates entry and exit order fills
"""

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional, Dict, List

logger = logging.getLogger(__name__)

# Execution constants
SLIPPAGE_PCT = Decimal("0.0005")   # 0.05%
COMMISSION_PCT = Decimal("0.001")  # 0.10%
DEFAULT_INITIAL_BALANCE = Decimal("10000")
DEFAULT_RISK_LIMIT_PCT = Decimal("10")  # Max 10% of portfolio per trade


@dataclass
class Position:
    """Represents an open paper trading position."""
    id: uuid.UUID
    strategy_id: uuid.UUID
    symbol: str
    entry_price: Decimal
    quantity: Decimal
    entry_commission: Decimal
    entry_time: datetime
    direction: str = "long"  # Phase 2: long only

    @property
    def cost_basis(self) -> Decimal:
        """Total cost including entry commission."""
        return (self.entry_price * self.quantity) + self.entry_commission


@dataclass
class PaperPortfolio:
    """
    Tracks the state of a paper trading portfolio.

    Attributes:
        strategy_id: UUID of the strategy this portfolio belongs to
        initial_balance: Starting balance in USDT
        current_balance: Available USDT balance
        open_positions: Dict[symbol, Position]
        realized_pnl: Total realized profit/loss
        trade_count: Number of completed round-trips
    """
    strategy_id: uuid.UUID
    initial_balance: Decimal = field(default_factory=lambda: DEFAULT_INITIAL_BALANCE)
    current_balance: Decimal = field(init=False)
    open_positions: Dict[str, Position] = field(default_factory=dict)
    realized_pnl: Decimal = field(default_factory=lambda: Decimal("0"))
    trade_count: int = 0

    def __post_init__(self):
        self.current_balance = self.initial_balance

    @property
    def total_equity(self) -> Decimal:
        """current_balance + unrealized value of open positions."""
        position_value = sum(
            p.entry_price * p.quantity for p in self.open_positions.values()
        )
        return self.current_balance + position_value

    def to_dict(self) -> dict:
        """Serialize portfolio state to dict (for Redis storage)."""
        return {
            "strategy_id": str(self.strategy_id),
            "initial_balance": str(self.initial_balance),
            "current_balance": str(self.current_balance),
            "realized_pnl": str(self.realized_pnl),
            "trade_count": self.trade_count,
            "open_positions": {
                symbol: {
                    "id": str(pos.id),
                    "symbol": pos.symbol,
                    "entry_price": str(pos.entry_price),
                    "quantity": str(pos.quantity),
                    "entry_commission": str(pos.entry_commission),
                    "entry_time": pos.entry_time.isoformat(),
                    "direction": pos.direction,
                }
                for symbol, pos in self.open_positions.items()
            },
        }

    @classmethod
    def from_dict(cls, data: dict) -> "PaperPortfolio":
        """Deserialize portfolio from dict (from Redis storage)."""
        portfolio = cls(
            strategy_id=uuid.UUID(data["strategy_id"]),
            initial_balance=Decimal(data["initial_balance"]),
        )
        portfolio.current_balance = Decimal(data["current_balance"])
        portfolio.realized_pnl = Decimal(data["realized_pnl"])
        portfolio.trade_count = data["trade_count"]

        for symbol, pos_data in data.get("open_positions", {}).items():
            portfolio.open_positions[symbol] = Position(
                id=uuid.UUID(pos_data["id"]),
                strategy_id=portfolio.strategy_id,
                symbol=pos_data["symbol"],
                entry_price=Decimal(pos_data["entry_price"]),
                quantity=Decimal(pos_data["quantity"]),
                entry_commission=Decimal(pos_data["entry_commission"]),
                entry_time=datetime.fromisoformat(pos_data["entry_time"]),
                direction=pos_data.get("direction", "long"),
            )

        return portfolio


class PaperTradingEngine:
    """
    Simulates paper trading order fills.

    Design principles:
    - No lookahead bias: signal fires on candle N close, fill at candle N+1 open
    - Slippage: 0.05% applied to entry and exit prices
    - Commission: 0.1% of trade value charged on each side
    - Risk limit: max position size enforced (default 10% of portfolio)
    - One position per symbol: cannot add to existing position
    """

    def __init__(
        self,
        portfolio: PaperPortfolio,
        risk_limit_pct: Decimal = DEFAULT_RISK_LIMIT_PCT,
    ):
        self.portfolio = portfolio
        self.risk_limit_pct = risk_limit_pct

    def simulate_entry(
        self,
        symbol: str,
        price: Decimal,
        quantity: Optional[Decimal] = None,
    ) -> Optional[Position]:
        """
        Simulate a market buy entry order.

        Signal fires on candle N close; price should be candle N+1 open
        to avoid lookahead bias.

        Args:
            symbol: Trading pair (e.g., 'BTC/USDT')
            price: Entry price (candle N+1 open, not N close)
            quantity: Quantity in base currency. If None, uses risk limit.

        Returns:
            Position object if entry successful, None if blocked by risk limit
            or insufficient balance.
        """
        if symbol in self.portfolio.open_positions:
            logger.debug(f"Already have open position for {symbol}, skipping entry")
            return None

        # Apply slippage to entry (price goes up on buy)
        fill_price = price * (1 + SLIPPAGE_PCT)
        fill_price = fill_price.quantize(Decimal("0.00000001"), rounding=ROUND_HALF_UP)

        # Calculate max position size based on risk limit
        max_position_value = (
            self.portfolio.current_balance * self.risk_limit_pct / 100
        )

        if quantity is None:
            # Use risk limit to size position
            quantity = max_position_value / fill_price
            quantity = quantity.quantize(Decimal("0.00000001"), rounding=ROUND_HALF_UP)

        # Calculate total cost including commission
        trade_value = fill_price * quantity
        commission = trade_value * COMMISSION_PCT
        commission = commission.quantize(Decimal("0.00000001"), rounding=ROUND_HALF_UP)
        total_cost = trade_value + commission

        # Check risk limit
        if trade_value > max_position_value:
            logger.warning(
                f"Position size {trade_value} exceeds risk limit "
                f"{max_position_value} for {symbol}"
            )
            return None

        # Check balance
        if total_cost > self.portfolio.current_balance:
            logger.warning(
                f"Insufficient balance for {symbol}: need {total_cost}, "
                f"have {self.portfolio.current_balance}"
            )
            return None

        # Deduct cost from balance
        self.portfolio.current_balance -= total_cost

        # Create position
        position = Position(
            id=uuid.uuid4(),
            strategy_id=self.portfolio.strategy_id,
            symbol=symbol,
            entry_price=fill_price,
            quantity=quantity,
            entry_commission=commission,
            entry_time=datetime.now(timezone.utc),
        )
        self.portfolio.open_positions[symbol] = position

        logger.info(
            f"Paper entry: {symbol} qty={quantity} @ {fill_price} "
            f"(commission={commission}, balance_after={self.portfolio.current_balance})"
        )
        return position

    def simulate_exit(
        self,
        symbol: str,
        price: Decimal,
        reason: str = "signal",
    ) -> Optional[dict]:
        """
        Simulate a market sell exit order.

        Args:
            symbol: Trading pair to exit
            price: Exit price (candle N+1 open)
            reason: Exit reason ('signal', 'stop_loss', 'take_profit', 'manual')

        Returns:
            Trade dict with full PnL details, or None if no open position.
        """
        position = self.portfolio.open_positions.get(symbol)
        if not position:
            logger.debug(f"No open position for {symbol}, cannot exit")
            return None

        # Apply slippage to exit (price goes down on sell)
        fill_price = price * (1 - SLIPPAGE_PCT)
        fill_price = fill_price.quantize(Decimal("0.00000001"), rounding=ROUND_HALF_UP)

        # Calculate proceeds and commission
        gross_proceeds = fill_price * position.quantity
        exit_commission = gross_proceeds * COMMISSION_PCT
        exit_commission = exit_commission.quantize(
            Decimal("0.00000001"), rounding=ROUND_HALF_UP
        )
        net_proceeds = gross_proceeds - exit_commission

        # Calculate PnL
        pnl = net_proceeds - position.cost_basis
        pnl = pnl.quantize(Decimal("0.00000001"), rounding=ROUND_HALF_UP)

        # Update portfolio
        self.portfolio.current_balance += net_proceeds
        self.portfolio.realized_pnl += pnl
        self.portfolio.trade_count += 1
        del self.portfolio.open_positions[symbol]

        trade_dict = {
            "position_id": str(position.id),
            "strategy_id": str(position.strategy_id),
            "symbol": symbol,
            "direction": position.direction,
            "entry_price": float(position.entry_price),
            "exit_price": float(fill_price),
            "quantity": float(position.quantity),
            "entry_commission": float(position.entry_commission),
            "exit_commission": float(exit_commission),
            "pnl": float(pnl),
            "pnl_pct": float(pnl / position.cost_basis * 100),
            "entry_time": position.entry_time.isoformat(),
            "exit_time": datetime.now(timezone.utc).isoformat(),
            "reason": reason,
            "is_paper_trade": True,
        }

        logger.info(
            f"Paper exit: {symbol} qty={position.quantity} @ {fill_price} "
            f"pnl={pnl} ({trade_dict['pnl_pct']:.2f}%)"
        )
        return trade_dict
