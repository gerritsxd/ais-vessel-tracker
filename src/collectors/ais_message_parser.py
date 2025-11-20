"""
AIS message parsing utilities.

Extracts structured vessel data from different AIS message types.
"""

from typing import Optional, Dict, Any, Tuple
import json


def calculate_vessel_dimensions(dimension_data: Dict[str, int]) -> Tuple[Optional[int], Optional[int]]:
    """
    Calculate vessel length and beam from AIS dimension components.
    
    AIS reports ship dimensions as distances from reference point to bow/stern/port/starboard:
    - A: Distance to bow
    - B: Distance to stern
    - C: Distance to port
    - D: Distance to starboard
    
    Args:
        dimension_data: Dictionary with keys A, B, C, D
        
    Returns:
        Tuple of (length, beam) in meters, or (None, None) if invalid
    """
    distance_to_bow = dimension_data.get("A", 0)
    distance_to_stern = dimension_data.get("B", 0)
    distance_to_port = dimension_data.get("C", 0)
    distance_to_starboard = dimension_data.get("D", 0)
    
    total_length = distance_to_bow + distance_to_stern
    total_beam = distance_to_port + distance_to_starboard
    
    length = total_length if total_length > 0 else None
    beam = total_beam if total_beam > 0 else None
    
    return length, beam


def parse_ship_static_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Parse ShipStaticData message (AIS Message Type 5).
    
    Contains full vessel information including IMO number.
    
    Args:
        data: Parsed JSON message from AISStream
        
    Returns:
        Dictionary with vessel attributes (mmsi, name, type, dimensions, etc.)
    """
    metadata = data.get("MetaData", {})
    ship_data = data.get("Message", {}).get("ShipStaticData", {})
    
    # Extract core identifiers
    mmsi = metadata.get("MMSI") or ship_data.get("UserID")
    vessel_name = ship_data.get("Name", "").strip() or metadata.get("ShipName", "").strip() or None
    vessel_type = ship_data.get("Type") or ship_data.get("ShipType")
    
    # Calculate dimensions
    dimension = ship_data.get("Dimension", {})
    length, beam = calculate_vessel_dimensions(dimension)
    
    # Extract additional data
    call_sign = ship_data.get("CallSign", "").strip() or None
    imo = ship_data.get("ImoNumber") or None
    destination = ship_data.get("Destination", "").strip() or None
    draught = ship_data.get("MaximumStaticDraught") or None
    nav_status = metadata.get("NavigationalStatus") or None
    
    # Parse ETA (might be dict or None)
    eta_raw = ship_data.get("Eta")
    eta = json.dumps(eta_raw) if eta_raw and isinstance(eta_raw, dict) else None
    
    return {
        "mmsi": mmsi,
        "name": vessel_name,
        "ship_type": vessel_type,
        "length": length,
        "beam": beam,
        "imo": imo,
        "call_sign": call_sign,
        "destination": destination,
        "eta": eta,
        "draught": draught,
        "nav_status": nav_status
    }


def parse_static_data_report(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Parse StaticDataReport message (AIS Message Type 24).
    
    Class B transponders - typically lacks IMO number.
    
    Args:
        data: Parsed JSON message from AISStream
        
    Returns:
        Dictionary with vessel attributes (mmsi, name, type, dimensions)
    """
    metadata = data.get("MetaData", {})
    static_report = data.get("Message", {}).get("StaticDataReport", {})
    report_b = static_report.get("ReportB", {})
    
    # Extract core identifiers
    mmsi = metadata.get("MMSI") or static_report.get("UserID")
    vessel_name = metadata.get("ShipName", "").strip() or None
    
    # Extract ship type from ReportB if valid
    if report_b.get("Valid"):
        ship_type_val = report_b.get("ShipType", 0)
        vessel_type = ship_type_val if ship_type_val > 0 else None
    else:
        vessel_type = None
    
    # Calculate dimensions from ReportB if valid
    dimension = report_b.get("Dimension", {})
    if report_b.get("Valid"):
        length, beam = calculate_vessel_dimensions(dimension)
    else:
        length, beam = None, None
    
    # Extract call sign
    call_sign = report_b.get("CallSign", "").strip() or None if report_b.get("Valid") else None
    
    return {
        "mmsi": mmsi,
        "name": vessel_name,
        "ship_type": vessel_type,
        "length": length,
        "beam": beam,
        "imo": None,  # Not available in Class B messages
        "call_sign": call_sign,
        "destination": None,
        "eta": None,
        "draught": None,
        "nav_status": None
    }


def parse_position_report(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Parse PositionReport message (AIS Message Types 1-3, 18-19).
    
    Contains minimal vessel info but allows catching ships already at sea.
    
    Args:
        data: Parsed JSON message from AISStream
        
    Returns:
        Dictionary with basic vessel attributes (mmsi, name, type)
    """
    metadata = data.get("MetaData", {})
    
    mmsi = metadata.get("MMSI")
    vessel_name = metadata.get("ShipName", "").strip() or None
    vessel_type = metadata.get("ShipType")
    
    return {
        "mmsi": mmsi,
        "name": vessel_name,
        "ship_type": vessel_type,
        "length": None,
        "beam": None,
        "imo": None,
        "call_sign": None,
        "destination": None,
        "eta": None,
        "draught": None,
        "nav_status": None
    }


def should_save_vessel(vessel_data: Dict[str, Any], min_length: int = 100, 
                        min_type: int = 70, max_type: int = 89) -> bool:
    """
    Determine if a vessel meets filtering criteria for database storage.
    
    Filters for cargo (70-79) and tanker (80-89) vessels >= 100m length.
    
    Args:
        vessel_data: Parsed vessel dictionary
        min_length: Minimum vessel length in meters
        min_type: Minimum ship type code (inclusive)
        max_type: Maximum ship type code (inclusive)
        
    Returns:
        True if vessel should be saved, False otherwise
    """
    mmsi = vessel_data.get("mmsi")
    length = vessel_data.get("length")
    ship_type = vessel_data.get("ship_type")
    
    if not mmsi:
        return False
    
    # Check length requirement (if available)
    if length is not None and length < min_length:
        return False
    
    # Check ship type requirement (if available)
    if ship_type is not None and not (min_type <= ship_type <= max_type):
        return False
    
    return True
