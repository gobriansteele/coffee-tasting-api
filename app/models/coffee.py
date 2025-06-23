from enum import Enum
from typing import Optional, List
from uuid import UUID
from decimal import Decimal

from sqlalchemy import String, Text, Numeric, ForeignKey, Table, Column
from sqlalchemy.dialects.postgresql import ENUM
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class ProcessingMethod(str, Enum):
    WASHED = "washed"
    NATURAL = "natural"
    HONEY = "honey"
    SEMI_WASHED = "semi_washed"
    WET_HULLED = "wet_hulled"
    CARBONIC_MACERATION = "carbonic_maceration"
    OTHER = "other"


class RoastLevel(str, Enum):
    LIGHT = "light"
    MEDIUM_LIGHT = "medium_light"
    MEDIUM = "medium"
    MEDIUM_DARK = "medium_dark"
    DARK = "dark"


# Association table for coffee flavor tags
coffee_flavors = Table(
    'coffee_flavors',
    Base.metadata,
    Column('coffee_id', ForeignKey('coffee.id'), primary_key=True),
    Column('flavor_tag_id', ForeignKey('flavortag.id'), primary_key=True)
)


class Roaster(Base):
    """Coffee roaster model."""
    __tablename__ = "roaster"
    
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    location: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    website: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Relationships
    coffees: Mapped[List["Coffee"]] = relationship("Coffee", back_populates="roaster")


class Coffee(Base):
    """Coffee model representing a specific coffee offering."""
    __tablename__ = "coffee"
    
    # Basic info
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    roaster_id: Mapped[UUID] = mapped_column(ForeignKey("roaster.id"), nullable=False, index=True)
    
    # Origin info
    origin_country: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    origin_region: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    farm_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    producer: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    altitude: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)  # e.g., "1200-1400m"
    
    # Processing
    processing_method: Mapped[Optional[ProcessingMethod]] = mapped_column(
        ENUM(ProcessingMethod, name="processing_method_enum"),
        nullable=True
    )
    variety: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)  # Coffee variety/cultivar
    
    # Roasting
    roast_level: Mapped[Optional[RoastLevel]] = mapped_column(
        ENUM(RoastLevel, name="roast_level_enum"),
        nullable=True
    )
    roast_date: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # Flexible date format
    
    # Additional info
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    price: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), nullable=True)
    bag_size: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # e.g., "12oz", "340g"
    
    # Relationships
    roaster: Mapped["Roaster"] = relationship("Roaster", back_populates="coffees")
    tasting_sessions: Mapped[List["TastingSession"]] = relationship("TastingSession", back_populates="coffee")
    flavor_tags: Mapped[List["FlavorTag"]] = relationship("FlavorTag", secondary=coffee_flavors, back_populates="coffees")


class FlavorTag(Base):
    """Flavor descriptors for coffee."""
    __tablename__ = "flavortag"
    
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    category: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # e.g., "fruity", "nutty", "floral"
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Relationships
    coffees: Mapped[List["Coffee"]] = relationship("Coffee", secondary=coffee_flavors, back_populates="flavor_tags")
    tasting_notes: Mapped[List["TastingNote"]] = relationship("TastingNote", back_populates="flavor_tag")