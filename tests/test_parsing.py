"""
Unit tests for AIS message parsing.

Tests the core parsing logic that extracts structured data
from AISStream WebSocket messages.
"""

import pytest
import json


def parse_static_data_message(message_json):
    """
    Parse a ShipStaticData message and extract vessel attributes.
    
    Args:
        message_json (str): Raw JSON message from AISStream
        
    Returns:
        dict: Parsed vessel data with keys: mmsi, name, ship_type, length, beam, imo
    """
    data = json.loads(message_json)
    
    metadata = data.get("MetaData", {})
    ship_data = data.get("Message", {}).get("ShipStaticData", {})
    
    # Extract MMSI
    mmsi = metadata.get("MMSI") or ship_data.get("UserID")
    
    # Extract vessel name
    vessel_name = ship_data.get("Name", "").strip() or metadata.get("ShipName", "").strip() or None
    
    # Extract ship type
    vessel_type = ship_data.get("Type") or ship_data.get("ShipType")
    
    # Extract dimensions
    dimension = ship_data.get("Dimension", {})
    dim_a = dimension.get("A", 0)
    dim_b = dimension.get("B", 0)
    dim_c = dimension.get("C", 0)
    dim_d = dimension.get("D", 0)
    length = (dim_a + dim_b) if (dim_a + dim_b) > 0 else None
    beam = (dim_c + dim_d) if (dim_c + dim_d) > 0 else None
    
    # Extract IMO
    imo = ship_data.get("ImoNumber") or None
    
    return {
        "mmsi": mmsi,
        "name": vessel_name,
        "ship_type": vessel_type,
        "length": length,
        "beam": beam,
        "imo": imo
    }


def parse_position_message(message_json):
    """
    Parse a position update message and extract navigation data.
    
    Args:
        message_json (str): Raw JSON message with position data
        
    Returns:
        dict: Parsed position data with keys: mmsi, lat, lon, speed, course
    """
    data = json.loads(message_json)
    
    # Datalastic API format (used by atlantic_tracker.py)
    if "data" in data and isinstance(data["data"], list):
        vessel = data["data"][0] if data["data"] else {}
        
        return {
            "mmsi": vessel.get("mmsi"),
            "lat": vessel.get("lat"),
            "lon": vessel.get("lon"),
            "speed": vessel.get("speed"),
            "course": vessel.get("course")
        }
    
    # AISStream format (PositionReport)
    metadata = data.get("MetaData", {})
    position = data.get("Message", {}).get("PositionReport", {})
    
    return {
        "mmsi": metadata.get("MMSI"),
        "lat": position.get("Latitude"),
        "lon": position.get("Longitude"),
        "speed": position.get("Sog"),  # Speed Over Ground
        "course": position.get("Cog")  # Course Over Ground
    }


# ========================================
# TESTS
# ========================================

def test_parse_static_data_message():
    """
    Test parsing of ShipStaticData message from AISStream.
    
    Validates that vessel attributes (MMSI, name, type, dimensions, IMO)
    are correctly extracted from the JSON structure.
    """
    # Mock AIS ShipStaticData message (Message Type 5)
    mock_message = json.dumps({
        "MessageType": "ShipStaticData",
        "MetaData": {
            "MMSI": 538007209,
            "ShipName": "MAERSK ESSEX"
        },
        "Message": {
            "ShipStaticData": {
                "Type": 70,
                "ImoNumber": 9632179,
                "Name": "MAERSK ESSEX",
                "Dimension": {
                    "A": 175,
                    "B": 67,
                    "C": 22,
                    "D": 20
                },
                "CallSign": "V7A2345"
            }
        }
    })
    
    # Parse the message
    result = parse_static_data_message(mock_message)
    
    # Assert all required fields exist
    assert "mmsi" in result
    assert "name" in result
    assert "ship_type" in result
    assert "length" in result
    assert "beam" in result
    assert "imo" in result
    
    # Assert correct values
    assert result["mmsi"] == 538007209
    assert result["name"] == "MAERSK ESSEX"
    assert result["ship_type"] == 70
    assert result["length"] == 242  # 175 + 67
    assert result["beam"] == 42     # 22 + 20
    assert result["imo"] == 9632179


def test_parse_position_message():
    """
    Test parsing of position data from Datalastic API response.
    
    Validates that navigation data (lat, lon, speed, course)
    is correctly extracted from the JSON structure.
    """
    # Mock Datalastic API response (used by atlantic_tracker.py)
    mock_message = json.dumps({
        "data": [
            {
                "mmsi": 538007209,
                "lat": 35.123456,
                "lon": -45.678901,
                "speed": 14.5,
                "course": 278.3,
                "name": "MAERSK ESSEX",
                "type": 70
            }
        ]
    })
    
    # Parse the message
    result = parse_position_message(mock_message)
    
    # Assert all required fields exist
    assert "mmsi" in result
    assert "lat" in result
    assert "lon" in result
    assert "speed" in result
    assert "course" in result
    
    # Assert correct values
    assert result["mmsi"] == 538007209
    assert result["lat"] == 35.123456
    assert result["lon"] == -45.678901
    assert result["speed"] == 14.5
    assert result["course"] == 278.3
