"""German Bight drift videos (R/V Heincke HE415/HE416, HE436, Helgoland 2011) on PANGAEA.

Reference adapter: each table row is one station video with the station
position next to the movie URL, so every frame gets ``geo_precision: station``
and ``geo_inferred: true``.
"""

from __future__ import annotations

from ._pangaea_table import PangaeaTableAdapter
from .base import register


@register
class GermanBightAdapter(PangaeaTableAdapter):
    key = "german_bight"
    name = "German Bight seafloor video (HE415/HE416, HE436, Helgoland 2011)"
    homepage = "https://doi.pangaea.de/10.1594/PANGAEA.907386"
    citation = "Papenmeier & Hass (2019), PANGAEA; see each sample's attribution for the exact dataset citation"
    media_types = ("video",)
    dataset_ids = ("907386", "909999", "831731")
    # MP4 first (smaller), then AVI; LRV/THM are GoPro previews and thumbnails.
    media_columns = ("URL movie (MP4)", "URL movie", "URL video")
    depth_columns = ("Bathy depth [m]", "Depth water [m]", "Elevation [m]")
    row_precision = "station"
