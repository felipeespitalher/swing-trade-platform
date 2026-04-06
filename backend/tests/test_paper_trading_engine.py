"""
Tests for PaperPortfolio and PaperTradingEngine.

Covers: balance accounting, slippage, commission, risk limits,
duplicate positions, serialization, and full trade cycles.
No Redis or database required.
"""
import uuid
from decimal import Decimal

import pytest

from app.services.paper_trading_engine import (
    COMMISSION_PCT,
    DEFAULT_RISK_LIMIT_PCT,
    SLIPPAGE_PCT,
    PaperPortfolio,
    PaperTradingEngine,
    Position,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_portfolio(balance: str = "10000") -> PaperPortfolio:
    return PaperPortfolio(strategy_id=uuid.uuid4(), initial_balance=Decimal(balance))


def make_engine(portfolio: PaperPortfolio, risk_limit_pct: str = "10") -> PaperTradingEngine:
    return PaperTradingEngine(portfolio, risk_limit_pct=Decimal(risk_limit_pct))


# ---------------------------------------------------------------------------
# 1. Portfolio initial state
# ---------------------------------------------------------------------------

def test_portfolio_initial_balance():
    """New portfolio has current_balance equal to initial_balance."""
    portfolio = make_portfolio("10000")
    assert portfolio.current_balance == Decimal("10000")
    assert portfolio.initial_balance == Decimal("10000")


# ---------------------------------------------------------------------------
# 2. Entry reduces balance
# ---------------------------------------------------------------------------

def test_entry_reduces_balance():
    """After simulate_entry, current_balance is less than initial_balance."""
    portfolio = make_portfolio("10000")
    engine = make_engine(portfolio)
    engine.simulate_entry("BTC/USDT", Decimal("50000"), Decimal("0.01"))
    assert portfolio.current_balance < Decimal("10000")


# ---------------------------------------------------------------------------
# 3. Entry creates position
# ---------------------------------------------------------------------------

def test_entry_creates_position():
    """After simulate_entry, the symbol appears in open_positions."""
    portfolio = make_portfolio("10000")
    engine = make_engine(portfolio)
    position = engine.simulate_entry("BTC/USDT", Decimal("50000"), Decimal("0.01"))
    assert position is not None
    assert "BTC/USDT" in portfolio.open_positions


# ---------------------------------------------------------------------------
# 4. Slippage applied on entry
# ---------------------------------------------------------------------------

def test_entry_applies_slippage():
    """Fill price on entry is higher than requested price by ~0.05%."""
    portfolio = make_portfolio("10000")
    engine = make_engine(portfolio)
    requested_price = Decimal("50000")
    position = engine.simulate_entry("BTC/USDT", requested_price, Decimal("0.01"))
    assert position is not None
    expected_fill = requested_price * (1 + SLIPPAGE_PCT)
    assert position.entry_price == expected_fill.quantize(Decimal("0.00000001"))


# ---------------------------------------------------------------------------
# 5. Commission charged on entry
# ---------------------------------------------------------------------------

def test_entry_charges_commission():
    """Balance is reduced by trade_value + commission after entry."""
    portfolio = make_portfolio("10000")
    engine = make_engine(portfolio)
    price = Decimal("50000")
    qty = Decimal("0.01")
    position = engine.simulate_entry("BTC/USDT", price, qty)
    assert position is not None

    fill_price = position.entry_price
    trade_value = fill_price * qty
    expected_commission = (trade_value * COMMISSION_PCT).quantize(Decimal("0.00000001"))
    total_cost = trade_value + expected_commission

    assert portfolio.current_balance == Decimal("10000") - total_cost


# ---------------------------------------------------------------------------
# 6. Exit returns trade dict with pnl
# ---------------------------------------------------------------------------

def test_exit_returns_trade_dict():
    """simulate_exit returns a dict containing a 'pnl' key."""
    portfolio = make_portfolio("10000")
    engine = make_engine(portfolio)
    engine.simulate_entry("BTC/USDT", Decimal("50000"), Decimal("0.01"))
    result = engine.simulate_exit("BTC/USDT", Decimal("51000"))
    assert result is not None
    assert "pnl" in result


# ---------------------------------------------------------------------------
# 7. Exit removes position
# ---------------------------------------------------------------------------

def test_exit_removes_position():
    """After simulate_exit, symbol is no longer in open_positions."""
    portfolio = make_portfolio("10000")
    engine = make_engine(portfolio)
    engine.simulate_entry("BTC/USDT", Decimal("50000"), Decimal("0.01"))
    engine.simulate_exit("BTC/USDT", Decimal("51000"))
    assert "BTC/USDT" not in portfolio.open_positions


# ---------------------------------------------------------------------------
# 8. Exit increases balance on profitable trade
# ---------------------------------------------------------------------------

def test_exit_increases_balance():
    """Balance increases after a profitable exit (sell price > buy price)."""
    portfolio = make_portfolio("10000")
    engine = make_engine(portfolio)
    engine.simulate_entry("BTC/USDT", Decimal("50000"), Decimal("0.01"))
    balance_before_exit = portfolio.current_balance
    engine.simulate_exit("BTC/USDT", Decimal("51000"))
    assert portfolio.current_balance > balance_before_exit


# ---------------------------------------------------------------------------
# 9. Exit realizes PnL in portfolio
# ---------------------------------------------------------------------------

def test_exit_realizes_pnl():
    """portfolio.realized_pnl is updated after a closed trade."""
    portfolio = make_portfolio("10000")
    engine = make_engine(portfolio)
    engine.simulate_entry("BTC/USDT", Decimal("50000"), Decimal("0.01"))
    result = engine.simulate_exit("BTC/USDT", Decimal("51000"))
    assert portfolio.realized_pnl != Decimal("0")
    assert portfolio.realized_pnl == Decimal(str(result["pnl"])).quantize(Decimal("0.00000001"))


# ---------------------------------------------------------------------------
# 10. Slippage applied on exit (adverse — fill < requested)
# ---------------------------------------------------------------------------

def test_slippage_applied_on_exit():
    """Fill price on exit is lower than requested sell price by ~0.05%."""
    portfolio = make_portfolio("10000")
    engine = make_engine(portfolio)
    engine.simulate_entry("BTC/USDT", Decimal("50000"), Decimal("0.01"))
    requested_exit_price = Decimal("51000")
    result = engine.simulate_exit("BTC/USDT", requested_exit_price)
    assert result is not None
    expected_fill = (requested_exit_price * (1 - SLIPPAGE_PCT)).quantize(Decimal("0.00000001"))
    assert Decimal(str(result["exit_price"])).quantize(Decimal("0.00000001")) == expected_fill


# ---------------------------------------------------------------------------
# 11. Risk limit blocks oversized position
# ---------------------------------------------------------------------------

def test_risk_limit_blocks_oversized_position():
    """A quantity whose trade_value exceeds risk_limit_pct returns None."""
    portfolio = make_portfolio("10000")
    engine = make_engine(portfolio, risk_limit_pct="10")  # max 10% = $1000
    # At $50000/BTC, buying 0.1 BTC costs ~$5000 — far above $1000 limit
    result = engine.simulate_entry("BTC/USDT", Decimal("50000"), Decimal("0.1"))
    assert result is None
    assert "BTC/USDT" not in portfolio.open_positions


# ---------------------------------------------------------------------------
# 12. Cannot enter twice on same symbol
# ---------------------------------------------------------------------------

def test_cannot_enter_twice_same_symbol():
    """A second simulate_entry for the same symbol returns None."""
    portfolio = make_portfolio("10000")
    engine = make_engine(portfolio)
    first = engine.simulate_entry("BTC/USDT", Decimal("50000"), Decimal("0.01"))
    second = engine.simulate_entry("BTC/USDT", Decimal("50000"), Decimal("0.005"))
    assert first is not None
    assert second is None
    # Only one position exists
    assert len(portfolio.open_positions) == 1


# ---------------------------------------------------------------------------
# 13. Portfolio serialization round-trip
# ---------------------------------------------------------------------------

def test_portfolio_serialization():
    """to_dict() → from_dict() round-trip preserves all relevant fields."""
    portfolio = make_portfolio("10000")
    engine = make_engine(portfolio)
    engine.simulate_entry("BTC/USDT", Decimal("50000"), Decimal("0.01"))

    data = portfolio.to_dict()
    restored = PaperPortfolio.from_dict(data)

    assert restored.strategy_id == portfolio.strategy_id
    assert restored.initial_balance == portfolio.initial_balance
    assert restored.current_balance == portfolio.current_balance
    assert restored.realized_pnl == portfolio.realized_pnl
    assert restored.trade_count == portfolio.trade_count
    assert "BTC/USDT" in restored.open_positions

    orig_pos = portfolio.open_positions["BTC/USDT"]
    rest_pos = restored.open_positions["BTC/USDT"]
    assert rest_pos.entry_price == orig_pos.entry_price
    assert rest_pos.quantity == orig_pos.quantity
    assert rest_pos.entry_commission == orig_pos.entry_commission


# ---------------------------------------------------------------------------
# 14. Profitable trade cycle
# ---------------------------------------------------------------------------

def test_profitable_trade_cycle():
    """Buy low, sell higher → pnl > 0, trade_count == 1."""
    portfolio = make_portfolio("10000")
    engine = make_engine(portfolio)
    engine.simulate_entry("BTC/USDT", Decimal("50000"), Decimal("0.01"))
    result = engine.simulate_exit("BTC/USDT", Decimal("55000"))

    assert result is not None
    assert result["pnl"] > 0
    assert portfolio.trade_count == 1
    assert portfolio.realized_pnl > Decimal("0")


# ---------------------------------------------------------------------------
# 15. Losing trade cycle
# ---------------------------------------------------------------------------

def test_losing_trade_cycle():
    """Buy high, sell lower → pnl < 0."""
    portfolio = make_portfolio("10000")
    engine = make_engine(portfolio)
    engine.simulate_entry("BTC/USDT", Decimal("50000"), Decimal("0.01"))
    result = engine.simulate_exit("BTC/USDT", Decimal("45000"))

    assert result is not None
    assert result["pnl"] < 0
    assert portfolio.realized_pnl < Decimal("0")
    assert portfolio.trade_count == 1
