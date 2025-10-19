"""Domain models shared between ingestion, engine, and reporting layers."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel
from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, MetaData, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Declarative base class configured for naming conventions."""

    metadata = MetaData()


class SwapORM(Base):
    """Raw swap executions normalized across data providers."""

    __tablename__ = "swaps"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    token_address: Mapped[str] = mapped_column(String(64), index=True)
    pool_address: Mapped[str] = mapped_column(String(64), index=True)
    side: Mapped[str] = mapped_column(String(4))  # buy / sell relative to quote token
    ts: Mapped[datetime] = mapped_column(DateTime, index=True)
    block_number: Mapped[int] = mapped_column(Integer)
    price: Mapped[float] = mapped_column(Float)
    amount_in: Mapped[float] = mapped_column(Float)
    amount_out: Mapped[float] = mapped_column(Float)
    tx_hash: Mapped[str] = mapped_column(String(100), index=True)
    wallet: Mapped[str] = mapped_column(String(64), index=True)


class PoolStateORM(Base):
    """Aggregated reserve state to reconstruct five-second bars."""

    __tablename__ = "pool_states"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    pool_address: Mapped[str] = mapped_column(String(64), index=True)
    token0: Mapped[str] = mapped_column(String(64))
    token1: Mapped[str] = mapped_column(String(64))
    fee_bps: Mapped[int] = mapped_column(Integer)
    reserve0: Mapped[float] = mapped_column(Float)
    reserve1: Mapped[float] = mapped_column(Float)
    ts: Mapped[datetime] = mapped_column(DateTime, index=True)


class TokenMetaORM(Base):
    """Best-effort metadata enriched from chain explorers and heuristics."""

    __tablename__ = "token_meta"

    token_address: Mapped[str] = mapped_column(String(64), primary_key=True)
    deployer: Mapped[Optional[str]] = mapped_column(String(64))
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    buy_tax_bps: Mapped[Optional[int]] = mapped_column(Integer)
    sell_tax_bps: Mapped[Optional[int]] = mapped_column(Integer)
    honeypot_flag: Mapped[Optional[bool]] = mapped_column(Boolean)
    lp_locked_flag: Mapped[Optional[bool]] = mapped_column(Boolean)


class RunORM(Base):
    """Persistence model for historical runs to enable reproducibility."""

    __tablename__ = "runs"

    sim_id: Mapped[str] = mapped_column(String(40), primary_key=True)
    config_json: Mapped[Dict[str, Any]] = mapped_column(JSON)
    start_ts: Mapped[datetime] = mapped_column(DateTime)
    end_ts: Mapped[datetime] = mapped_column(DateTime)
    result_json: Mapped[Dict[str, Any]] = mapped_column(JSON)


class OrderORM(Base):
    """Orders recorded during simulations with risk controls applied."""

    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    sim_id: Mapped[str] = mapped_column(ForeignKey("runs.sim_id"), index=True)
    ts_submit: Mapped[datetime] = mapped_column(DateTime)
    ts_fill: Mapped[Optional[datetime]] = mapped_column(DateTime)
    token_address: Mapped[str] = mapped_column(String(64))
    side: Mapped[str] = mapped_column(String(4))
    quantity: Mapped[float] = mapped_column(Float)
    price_fill: Mapped[Optional[float]] = mapped_column(Float)
    gas_used: Mapped[Optional[float]] = mapped_column(Float)
    slip_bps: Mapped[Optional[float]] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String(12))
    reason: Mapped[Optional[str]] = mapped_column(String(100))

    run: Mapped["RunORM"] = relationship("RunORM", backref="orders")


class PositionORM(Base):
    """Position snapshot after each fill."""

    __tablename__ = "positions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    sim_id: Mapped[str] = mapped_column(ForeignKey("runs.sim_id"), index=True)
    token_address: Mapped[str] = mapped_column(String(64))
    quantity: Mapped[float] = mapped_column(Float)
    cost_basis: Mapped[float] = mapped_column(Float)
    pnl: Mapped[float] = mapped_column(Float)
    mtm: Mapped[float] = mapped_column(Float)
    ts: Mapped[datetime] = mapped_column(DateTime, index=True)

    run: Mapped["RunORM"] = relationship("RunORM", backref="positions")


class Swap(BaseModel):
    """Pydantic representation of swap events used in memory."""

    token_address: str
    pool_address: str
    ts: datetime
    block_number: int
    side: str
    price: float
    amount_in: float
    amount_out: float
    tx_hash: str
    wallet: str


class PoolState(BaseModel):
    """Pydantic model mirroring :class:`PoolStateORM` for compute pipelines."""

    pool_address: str
    token0: str
    token1: str
    fee_bps: int
    reserve0: float
    reserve1: float
    ts: datetime


class TokenMeta(BaseModel):
    """Metadata tied to tokens that informs taxes and guardrails."""

    token_address: str
    deployer: Optional[str] = None
    created_at: Optional[datetime] = None
    buy_tax_bps: Optional[int] = None
    sell_tax_bps: Optional[int] = None
    honeypot_flag: Optional[bool] = None
    lp_locked_flag: Optional[bool] = None


@dataclass(slots=True)
class Signal:
    """Signal emitted by strategies, enriched with explainability metadata."""

    strategy: str
    token_address: str
    ts: datetime
    score: float
    meta: Dict[str, Any]


class Order(BaseModel):
    """Serialized form of :class:`OrderORM` for analytics and reports."""

    sim_id: str
    ts_submit: datetime
    ts_fill: Optional[datetime]
    token_address: str
    side: str
    quantity: float
    price_fill: Optional[float]
    gas_used: Optional[float]
    slip_bps: Optional[float]
    status: str
    reason: Optional[str] = None


class Position(BaseModel):
    """Position state used for equity curve construction."""

    sim_id: str
    token_address: str
    quantity: float
    cost_basis: float
    pnl: float
    mtm: float
    ts: datetime


class Run(BaseModel):
    """Metadata about an executed simulation run."""

    sim_id: str
    config_json: Dict[str, Any]
    start_ts: datetime
    end_ts: datetime
    result_json: Dict[str, Any]
