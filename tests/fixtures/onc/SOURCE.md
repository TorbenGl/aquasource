# onc fixtures

**SYNTHETIC. Not live ONC records.** No ONC_TOKEN was available in the research environment (2026-10-08), and every
Oceans 3.0 API call answers HTTP 401 / errorCode 128 without a token. The two files are shaped after the response
structure in the ONC Python client 2.6.0 source (PyPI `onc`, modules/_OncArchive.py and _MultiPage.py: archivefile
responses carry `files` (file names) and `next` (`parameters` of the next page); deployments carry deviceCode, begin,
end, lat, lon, depth). Coordinates and device codes are made up for the tests and must not be used as data.

Replace with real responses once a token is available: `ONC_TOKEN=... uv run aquasource download onc --dry-run --opt locations=<code>`
writes the cache under metadata/raw/onc/ (copy one deployments and one archivefile page here, redact nothing else).

Sources read (metadata only):
- API guide: https://oceannetworkscanada.github.io/Oceans3.0-API/API_Guide.html
- Data policy (CC BY 4.0 for ONC-owned data, partner data may be restricted): https://www.oceannetworks.ca/data/data-policy/
- Client library: https://pypi.org/project/onc/2.6.0/ (source: https://github.com/OceanNetworksCanada/api-python-client)
