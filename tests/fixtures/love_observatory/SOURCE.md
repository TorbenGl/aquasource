# love_observatory fixtures (metadata only, read 2026-10-08)

No real metadata record could be saved: every record endpoint found refused the request.
- https://data.arcticobserving.org/metsis/metadata/IMR_LOVE_NODE4 (also reached via https://saon.met.no/metsis/metadata/IMR_LOVE_NODE4, 301): HTTP 401 (after drupal_cbp_check redirect).
- https://data.arcticobserving.org/metsis/metadata/IMR_LOVE_NODE7: HTTP 401.
- https://metadata.nmdc.no/metadata/IMR_LOVE_NODE4: HTTP 404.
- https://geonorge.no/geonetworktest/srv/api/records/IMR_LOVE_NODE4: HTTP 404.
- https://www.gceocean.no/projects/gce/love-ocean-observatory/ : project page, no licence, no data URL, no coordinates (only "west of Hovden, Vesteralen").
- https://www.loveocean.no and https://love.equinor.com: not reachable from this environment (curl exit 000 / no answer).
- Search snippets (not fetched records) report "Access constraint: Open" and "Data Availability: open" (IQOE profile, https://www.iqoe.org/data/21037); Use constraint field empty in the snippet. Not verified.

Nothing copied here is a licence statement. Fixtures to add once a record is readable: one node metadata record (title, use/access constraint, bbox, distribution URLs).
