from enum import Enum
from typing import Optional, List
from uuid import UUID
from decimal import Decimal

from sqlalchemy import String, Text, Integer, Numeric, ForeignKey, Boolean
from sqlalchemy.dialects.postgresql import ENUM
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class BrewMethod(str, Enum):
    POUR_OVER = "pour_over"
    FRENCH_PRESS = "french_press"
    ESPRESSO = "espresso"
    AEROPRESS = "aeropress"
    CHEMEX = "chemex"
    V60 = "v60"
    KALITA = "kalita"
    SIPHON = "siphon"
    COLD_BREW = "cold_brew"
    MOKA_POT = "moka_pot"
    DRIP = "drip"
    OTHER = "other"


class GrindSize(str, Enum):
    EXTRA_FINE = "extra_fine"
    FINE = "fine"
    MEDIUM_FINE = "medium_fine"
    MEDIUM = "medium"
    MEDIUM_COARSE = "medium_coarse"
    COARSE = "coarse"
    EXTRA_COARSE = "extra_coarse"


class TastingSession(Base):
    """A coffee tasting session with brewing parameters."""
    __tablename__ = "tasting_session"
    
    # Basic info
    coffee_id: Mapped[UUID] = mapped_column(ForeignKey("coffee.id"), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)  # From auth system
    
    # Brewing parameters
    brew_method: Mapped[BrewMethod] = mapped_column(
        ENUM(BrewMethod, name="brew_method_enum"),
        nullable=False
    )
    grind_size: Mapped[Optional[GrindSize]] = mapped_column(
        ENUM(GrindSize, name="grind_size_enum"),
        nullable=True
    )
    
    # Measurements
    coffee_dose: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 1), nullable=True)  # grams
    water_amount: Mapped[Optional[Decimal]] = mapped_column(Numeric(6, 1), nullable=True)  # grams or ml
    water_temperature: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # celsius
    brew_time: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # e.g., "4:30", "2m 30s"
    
    # Equipment
    grinder: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    brewing_device: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    filter_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    # Session notes
    session_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    overall_rating: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # 1-10 scale
    would_buy_again: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    
    # Relationships
    coffee: Mapped["Coffee"] = relationship("Coffee", back_populates="tasting_sessions")
    tasting_notes: Mapped[List["TastingNote"]] = relationship("TastingNote", back_populates="tasting_session", cascade="all, delete-orphan")


class TastingNote(Base):
    """Individual flavor notes from a tasting session."""
    __tablename__ = "tasting_note"
    
    tasting_session_id: Mapped[UUID] = mapped_column(ForeignKey("tasting_session.id"), nullable=False, index=True)
    flavor_tag_id: Mapped[UUID] = mapped_column(ForeignKey("flavortag.id"), nullable=False, index=True)
    
    # Intensity and characteristics
    intensity: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # 1-10 scale
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # Additional notes about this flavor
    
    # Tasting phases
    aroma: Mapped[bool] = mapped_column(Boolean, default=False)  # Detected in aroma
    flavor: Mapped[bool] = mapped_column(Boolean, default=False)  # Detected in flavor
    aftertaste: Mapped[bool] = mapped_column(Boolean, default=False)  # Detected in aftertaste
    
    # Relationships
    tasting_session: Mapped["TastingSession"] = relationship("TastingSession", back_populates="tasting_notes")
    flavor_tag: Mapped["FlavorTag"] = relationship("FlavorTag", back_populates="tasting_notes")