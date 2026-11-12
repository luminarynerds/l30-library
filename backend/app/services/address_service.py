# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
import re
from dataclasses import dataclass
from typing import Optional

# USPS State abbreviations
US_STATES = {
    "ALABAMA": "AL", "ALASKA": "AK", "ARIZONA": "AZ", "ARKANSAS": "AR",
    "CALIFORNIA": "CA", "COLORADO": "CO", "CONNECTICUT": "CT", "DELAWARE": "DE",
    "FLORIDA": "FL", "GEORGIA": "GA", "HAWAII": "HI", "IDAHO": "ID",
    "ILLINOIS": "IL", "INDIANA": "IN", "IOWA": "IA", "KANSAS": "KS",
    "KENTUCKY": "KY", "LOUISIANA": "LA", "MAINE": "ME", "MARYLAND": "MD",
    "MASSACHUSETTS": "MA", "MICHIGAN": "MI", "MINNESOTA": "MN", "MISSISSIPPI": "MS",
    "MISSOURI": "MO", "MONTANA": "MT", "NEBRASKA": "NE", "NEVADA": "NV",
    "NEW HAMPSHIRE": "NH", "NEW JERSEY": "NJ", "NEW MEXICO": "NM", "NEW YORK": "NY",
    "NORTH CAROLINA": "NC", "NORTH DAKOTA": "ND", "OHIO": "OH", "OKLAHOMA": "OK",
    "OREGON": "OR", "PENNSYLVANIA": "PA", "RHODE ISLAND": "RI", "SOUTH CAROLINA": "SC",
    "SOUTH DAKOTA": "SD", "TENNESSEE": "TN", "TEXAS": "TX", "UTAH": "UT",
    "VERMONT": "VT", "VIRGINIA": "VA", "WASHINGTON": "WA", "WEST VIRGINIA": "WV",
    "WISCONSIN": "WI", "WYOMING": "WY",
    # Territories
    "DISTRICT OF COLUMBIA": "DC", "PUERTO RICO": "PR", "GUAM": "GU",
    "AMERICAN SAMOA": "AS", "VIRGIN ISLANDS": "VI", "NORTHERN MARIANA ISLANDS": "MP",
    # Canadian provinces (for cross-border)
    "ALBERTA": "AB", "BRITISH COLUMBIA": "BC", "MANITOBA": "MB",
    "NEW BRUNSWICK": "NB", "NEWFOUNDLAND AND LABRADOR": "NL",
    "NORTHWEST TERRITORIES": "NT", "NOVA SCOTIA": "NS", "NUNAVUT": "NU",
    "ONTARIO": "ON", "PRINCE EDWARD ISLAND": "PE", "QUEBEC": "QC",
    "SASKATCHEWAN": "SK", "YUKON": "YT"
}

# Reverse lookup
STATE_ABBREVS = {v: k for k, v in US_STATES.items()}
VALID_STATE_CODES = set(US_STATES.values())

# USPS street suffix abbreviations
STREET_SUFFIXES = {
    "ALLEY": "ALY", "ANNEX": "ANX", "ARCADE": "ARC", "AVENUE": "AVE",
    "BAYOU": "BYU", "BEACH": "BCH", "BEND": "BND", "BLUFF": "BLF",
    "BOULEVARD": "BLVD", "BRANCH": "BR", "BRIDGE": "BRG", "BROOK": "BRK",
    "BYPASS": "BYP", "CAMP": "CP", "CANYON": "CYN", "CAPE": "CPE",
    "CAUSEWAY": "CSWY", "CENTER": "CTR", "CIRCLE": "CIR", "CLIFF": "CLF",
    "CLUB": "CLB", "CORNER": "COR", "COURT": "CT", "COVE": "CV",
    "CREEK": "CRK", "CRESCENT": "CRES", "CROSSING": "XING", "DALE": "DL",
    "DAM": "DM", "DIVIDE": "DV", "DRIVE": "DR", "ESTATES": "EST",
    "EXPRESSWAY": "EXPY", "EXTENSION": "EXT", "FALL": "FALL", "FALLS": "FLS",
    "FERRY": "FRY", "FIELD": "FLD", "FLAT": "FLT", "FORD": "FRD",
    "FOREST": "FRST", "FORGE": "FRG", "FORK": "FRK", "FORT": "FT",
    "FREEWAY": "FWY", "GARDEN": "GDN", "GATEWAY": "GTWY", "GLEN": "GLN",
    "GREEN": "GRN", "GROVE": "GRV", "HARBOR": "HBR", "HAVEN": "HVN",
    "HEIGHTS": "HTS", "HIGHWAY": "HWY", "HILL": "HL", "HOLLOW": "HOLW",
    "INLET": "INLT", "ISLAND": "IS", "JUNCTION": "JCT", "KEY": "KY",
    "KNOLL": "KNL", "LAKE": "LK", "LANDING": "LNDG", "LANE": "LN",
    "LIGHT": "LGT", "LOAF": "LF", "LOCK": "LCK", "LODGE": "LDG",
    "LOOP": "LOOP", "MALL": "MALL", "MANOR": "MNR", "MEADOW": "MDW",
    "MILL": "ML", "MISSION": "MSN", "MOUNT": "MT", "MOUNTAIN": "MTN",
    "NECK": "NCK", "ORCHARD": "ORCH", "OVAL": "OVAL", "PARK": "PARK",
    "PARKWAY": "PKWY", "PASS": "PASS", "PATH": "PATH", "PIKE": "PIKE",
    "PINE": "PNE", "PLACE": "PL", "PLAIN": "PLN", "PLAZA": "PLZ",
    "POINT": "PT", "PORT": "PRT", "PRAIRIE": "PR", "RADIAL": "RADL",
    "RANCH": "RNCH", "RAPID": "RPD", "REST": "RST", "RIDGE": "RDG",
    "RIVER": "RIV", "ROAD": "RD", "ROW": "ROW", "RUN": "RUN",
    "SHOAL": "SHL", "SHORE": "SHR", "SPRING": "SPG", "SQUARE": "SQ",
    "STATION": "STA", "STREAM": "STRM", "STREET": "ST", "SUMMIT": "SMT",
    "TERRACE": "TER", "TRACE": "TRCE", "TRACK": "TRAK", "TRAIL": "TRL",
    "TUNNEL": "TUNL", "TURNPIKE": "TPKE", "UNION": "UN", "VALLEY": "VLY",
    "VIADUCT": "VIA", "VIEW": "VW", "VILLAGE": "VLG", "VILLE": "VL",
    "VISTA": "VIS", "WALK": "WALK", "WAY": "WAY", "WELL": "WL"
}

# USPS secondary unit designators
UNIT_DESIGNATORS = {
    "APARTMENT": "APT", "BUILDING": "BLDG", "DEPARTMENT": "DEPT",
    "FLOOR": "FL", "HANGAR": "HNGR", "LOT": "LOT", "OFFICE": "OFC",
    "PENTHOUSE": "PH", "PIER": "PIER", "ROOM": "RM", "SLIP": "SLIP",
    "SPACE": "SPC", "STOP": "STOP", "SUITE": "STE", "TRAILER": "TRLR",
    "UNIT": "UNIT", "UPPER": "UPPR", "LOWER": "LOWR", "BASEMENT": "BSMT",
    "FRONT": "FRNT", "REAR": "REAR", "SIDE": "SIDE"
}

# Directional abbreviations
DIRECTIONALS = {
    "NORTH": "N", "SOUTH": "S", "EAST": "E", "WEST": "W",
    "NORTHEAST": "NE", "NORTHWEST": "NW", "SOUTHEAST": "SE", "SOUTHWEST": "SW"
}


@dataclass
class AddressValidationResult:
    is_valid: bool
    errors: list[str]
    warnings: list[str]
    normalized_address: Optional["NormalizedAddress"]


@dataclass
class NormalizedAddress:
    line1: str
    line2: Optional[str]
    city: str
    state: str
    zip_code: str
    zip_plus4: Optional[str]
    country: str = "USA"

    def format_for_mail(self) -> str:
        lines = [self.line1]
        if self.line2:
            lines.append(self.line2)
        zip_full = f"{self.zip_code}-{self.zip_plus4}" if self.zip_plus4 else self.zip_code
        lines.append(f"{self.city} {self.state}  {zip_full}")
        return "\n".join(lines)

    def format_single_line(self) -> str:
        parts = [self.line1]
        if self.line2:
            parts.append(self.line2)
        zip_full = f"{self.zip_code}-{self.zip_plus4}" if self.zip_plus4 else self.zip_code
        parts.append(f"{self.city}, {self.state} {zip_full}")
        return ", ".join(parts)


class AddressService:

    @staticmethod
    def validate_and_normalize(
        line1: str,
        line2: Optional[str],
        city: str,
        state: str,
        zip_code: str,
        country: str = "USA"
    ) -> AddressValidationResult:
        errors = []
        warnings = []

        # Basic required field validation
        if not line1 or not line1.strip():
            errors.append("Street address (line 1) is required")
        if not city or not city.strip():
            errors.append("City is required")
        if not state or not state.strip():
            errors.append("State is required")
        if not zip_code or not zip_code.strip():
            errors.append("ZIP code is required")

        if errors:
            return AddressValidationResult(
                is_valid=False,
                errors=errors,
                warnings=warnings,
                normalized_address=None
            )

        # Normalize state
        normalized_state = AddressService.normalize_state(state)
        if not normalized_state:
            errors.append(f"Invalid state: {state}")

        # Validate and normalize ZIP code
        zip_result = AddressService.normalize_zip_code(zip_code)
        if not zip_result:
            errors.append(f"Invalid ZIP code format: {zip_code}")

        if errors:
            return AddressValidationResult(
                is_valid=False,
                errors=errors,
                warnings=warnings,
                normalized_address=None
            )

        normalized_zip, zip_plus4 = zip_result

        # Normalize address lines
        normalized_line1 = AddressService.normalize_address_line(line1)
        normalized_line2 = AddressService.normalize_address_line(line2) if line2 else None

        # Normalize city
        normalized_city = AddressService.normalize_city(city)

        # Check for potential issues (warnings)
        if len(normalized_line1) > 35:
            warnings.append("Address line 1 exceeds 35 characters, may cause formatting issues")

        if normalized_line2 and len(normalized_line2) > 35:
            warnings.append("Address line 2 exceeds 35 characters, may cause formatting issues")

        # Check if address line has a street number (pattern: starts with digits and space)
        if not bool(re.match(r"^\d+\s", normalized_line1)):
            warnings.append("Address line 1 may be missing a street number")

        # Check if line 2 should be merged with line 1
        # Check if line is just a unit designator
        is_unit_designator = False
        if normalized_line2:
            for designator in UNIT_DESIGNATORS.values():
                if normalized_line2.startswith(designator + " "):
                    is_unit_designator = True
                    break

        if normalized_line2 and is_unit_designator:
            if len(f"{normalized_line1} {normalized_line2}") <= 35:
                normalized_line1 = f"{normalized_line1} {normalized_line2}"
                normalized_line2 = None

        normalized = NormalizedAddress(
            line1=normalized_line1,
            line2=normalized_line2,
            city=normalized_city,
            state=normalized_state,
            zip_code=normalized_zip,
            zip_plus4=zip_plus4,
            country=country.upper()
        )

        return AddressValidationResult(
            is_valid=True,
            errors=[],
            warnings=warnings,
            normalized_address=normalized
        )

    @staticmethod
    def normalize_state(state: str) -> Optional[str]:
        state = state.strip().upper()

        # Already a valid abbreviation
        if state in VALID_STATE_CODES:
            return state

        # Full state name
        if state in US_STATES:
            return US_STATES[state]

        return None

    @staticmethod
    def normalize_zip_code(zip_code: str) -> Optional[tuple[str, Optional[str]]]:
        # Remove all non-digits
        digits = re.sub(r"[^\d]", "", zip_code)

        if len(digits) == 5:
            return (digits, None)
        elif len(digits) == 9:
            return (digits[:5], digits[5:])
        elif len(digits) > 5:
            # Try to extract valid 5-digit or 9-digit
            return (digits[:5], digits[5:9] if len(digits) >= 9 else None)

        return None

    @staticmethod
    def normalize_address_line(line: str) -> str:
        if not line:
            return ""

        # Convert to uppercase
        line = line.strip().upper()

        # Remove extra whitespace
        line = re.sub(r"\s+", " ", line)

        # Replace periods with nothing (USPS standard)
        line = line.replace(".", "")

        # Normalize directionals
        for full, abbrev in DIRECTIONALS.items():
            # Replace full words with abbreviations
            line = re.sub(rf"\b{full}\b", abbrev, line)

        # Normalize street suffixes
        for full, abbrev in STREET_SUFFIXES.items():
            # Replace full words with abbreviations
            line = re.sub(rf"\b{full}\b", abbrev, line)

        # Normalize unit designators
        for full, abbrev in UNIT_DESIGNATORS.items():
            line = re.sub(rf"\b{full}\b", abbrev, line)

        # Remove commas (USPS standard)
        line = line.replace(",", "")

        # Remove # symbol before numbers (USPS prefers APT, STE, etc.)
        line = re.sub(r"#\s*(\d)", r"APT \1", line)

        return line

    @staticmethod
    def normalize_city(city: str) -> str:
        city = city.strip().upper()
        city = re.sub(r"\s+", " ", city)
        city = city.replace(".", "")
        return city

    @staticmethod
    def format_for_envelope(
        name: str,
        line1: str,
        line2: Optional[str],
        city: str,
        state: str,
        zip_code: str,
        country: str = "USA"
    ) -> list[str]:
        lines = []

        # Recipient name
        name = name.strip().upper()
        lines.append(name)

        # Address line 1
        lines.append(line1.upper() if line1 else "")

        # Address line 2 (if present)
        if line2:
            lines.append(line2.upper())

        # City, State ZIP
        zip_display = zip_code
        city_state_zip = f"{city.upper()} {state.upper()}  {zip_display}"
        lines.append(city_state_zip)

        # Country (only if not USA)
        if country and country.upper() != "USA":
            lines.append(country.upper())

        return lines

    @staticmethod
    def parse_single_line_address(address: str) -> Optional[dict]:
        if not address:
            return None

        # Try to match common patterns
        # Pattern: "123 Main St, City, ST 12345"
        pattern1 = re.compile(
            r"^(.+?),\s*(.+?),\s*([A-Z]{2})\s+(\d{5}(?:-\d{4})?)(?:,?\s*(.+))?$",
            re.IGNORECASE
        )

        # Pattern: "123 Main St City ST 12345"
        pattern2 = re.compile(
            r"^(.+?)\s+([A-Za-z\s]+?)\s+([A-Z]{2})\s+(\d{5}(?:-\d{4})?)$",
            re.IGNORECASE
        )

        match = pattern1.match(address.strip())
        if match:
            return {
                "line1": match.group(1).strip(),
                "line2": None,
                "city": match.group(2).strip(),
                "state": match.group(3).upper(),
                "zip_code": match.group(4),
                "country": match.group(5).strip() if match.group(5) else "USA"
            }

        match = pattern2.match(address.strip())
        if match:
            return {
                "line1": match.group(1).strip(),
                "line2": None,
                "city": match.group(2).strip(),
                "state": match.group(3).upper(),
                "zip_code": match.group(4),
                "country": "USA"
            }

        return None


def validate_address(
    line1: str,
    line2: Optional[str],
    city: str,
    state: str,
    zip_code: str,
    country: str = "USA"
) -> AddressValidationResult:
    return AddressService.validate_and_normalize(
        line1, line2, city, state, zip_code, country
    )
