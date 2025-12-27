import ee
from typing import Optional, Sequence

def parse_bbox_string(bbox_str: str) -> Optional[Sequence[float]]:
    """Parse bbox string '[min_lon, min_lat, max_lon, max_lat]' or '[min_lon min_lat max_lon max_lat]' -> list of floats."""
    if bbox_str is None:
        return None
    try:
        # Remove brackets and split by comma or whitespace
        cleaned = bbox_str.strip("[]")
        # Try splitting by comma first, then by whitespace
        if ',' in cleaned:
            coords = [float(c.strip()) for c in cleaned.split(',')]
        else:
            coords = [float(c) for c in cleaned.split()]
        if len(coords) == 4:
            return coords
    except (ValueError, AttributeError):
        return None
    return None

def init_earthengine(authenticate_if_needed=False):
    """Initialize Earth Engine. Returns True if successful."""
    try:
        ee.Initialize(project="earth-engine-481316")
        return True
    except Exception as e:
        if authenticate_if_needed:
            try:
                ee.Authenticate()
                ee.Initialize(project="earth-engine-481316")
                return True
            except Exception as e2:
                print(f"Earth Engine initialization failed: {e2}")
                return False
        return False

# Load ESA WorldCover 2021
_worldcover = None
_forest_mask = None

def _get_forest_mask():
    """Get or create forest mask."""
    global _worldcover, _forest_mask
    if _forest_mask is None:
        _worldcover = ee.Image('ESA/WorldCover/v200/2021').select('Map')
        # Define forest classes (10=Tree cover, 95=Mangroves)
        _forest_mask = _worldcover.eq(10).Or(_worldcover.eq(95))
    return _forest_mask

def calculate_forest_percentage(bbox_coords):
    """Compute forest % for bbox coordinates using Earth Engine."""
    if bbox_coords is None:
        return None
    
    min_lon, min_lat, max_lon, max_lat = bbox_coords
    region = ee.Geometry.Rectangle([min_lon, min_lat, max_lon, max_lat])
    forest_mask = _get_forest_mask()
    
    try:
        stats = forest_mask.reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=region,
            scale=10,
            maxPixels=1e9
        ).getInfo()
        
        forest_fraction = stats.get('Map', 0)
        return float(forest_fraction) * 100 if forest_fraction is not None else 0.0
    except Exception as e:
        print(f"Error calculating forest percentage: {e}")
        return None

