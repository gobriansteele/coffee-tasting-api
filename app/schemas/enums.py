"""Shared enums for schemas."""

from enum import Enum


class ProcessingMethod(str, Enum):
    """Coffee processing methods."""

    WASHED = "washed"
    NATURAL = "natural"
    HONEY = "honey"
    ANAEROBIC = "anaerobic"


class RoastLevel(str, Enum):
    """Coffee roast levels."""

    LIGHT = "light"
    MEDIUM = "medium"
    MEDIUM_DARK = "medium_dark"
    DARK = "dark"


class BrewMethod(str, Enum):
    """Coffee brewing methods."""

    POUROVER = "pourover"
    ESPRESSO = "espresso"
    FRENCH_PRESS = "french_press"
    AEROPRESS = "aeropress"
    DRIP = "drip"
    COLD_BREW = "cold_brew"
    MOKA_POT = "moka_pot"


class GrindSize(str, Enum):
    """Coffee grind sizes."""

    FINE = "fine"
    MEDIUM_FINE = "medium_fine"
    MEDIUM = "medium"
    MEDIUM_COARSE = "medium_coarse"
    COARSE = "coarse"
