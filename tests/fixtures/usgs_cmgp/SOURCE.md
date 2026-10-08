# Fixture sources: `usgs_cmgp`

All files were retrieved on 2026-10-06 (research date of the workflow; the actual requests were made 2026-10-08) with User-Agent `aquasource-research/0.1 (+https://github.com/torbengl/aquasource)`. Values are unmodified. Files are the provider's response bodies unless trimming is noted.

| File | Exact URL | Trimming |
|---|---|---|
| `wfs_usgsvideoframe_video_rows.json` | https://data.axds.co/gs/wfs?service=WFS&version=1.0.0&request=GetFeature&typeName=axiom:usgsvideoframe&outputFormat=application/json&maxFeatures=3 | None. Full response body: the first 3 rows (video navigation points, `frame` = seconds into the video, spacing 10 s) of the California Seafloor Mapping Program layer (924,759 rows in total, see `totalFeatures`). Note that `geometry.coordinates` is rounded to 4 decimals but `properties.lat/lon` are full precision. |
| `wfs_usgsvideoframe_photo_rows.json` | https://data.axds.co/gs/wfs?service=WFS&version=1.0.0&request=GetFeature&typeName=axiom:usgsvideoframe&outputFormat=application/json&maxFeatures=2&cql_filter=picasa_id%20IS%20NOT%20NULL | None. Full response body: 2 rows that carry a still photo (`photo`, `picasa_id`, `picasa_album_id`). Here `youtube_id` is an empty string (photo-only row). |
| `wfs_woodshole_photo_row.json` | https://data.axds.co/gs/usgs_imagery/wfs?service=WFS&version=1.0.0&request=GetFeature&typeName=usgs_imagery:woodshole_media_points&outputFormat=application/json&maxFeatures=1&cql_filter=picasa_id%20IS%20NOT%20NULL | None. Full response body: 1 row of the Woods Hole (Massachusetts) layer, which has a different column set (`gid`, `picasa_album_id_original`, `cruiseid`, `photo` = original file name). Row with both a photo and a video reference. |
| `neighborhoodFrames_seafloor_video.json` | https://spatial-imagery.srv.axds.co/seafloor/neighborhoodFrames/?frames=5&video=C0212SC_Tape65&startFrame=2750 | None. Full response body (JSON, the JSONP callback is optional). Shows the 2-s navigation spacing of a modern tape, the two YouTube IDs (`youtube_ids`: vertical and oblique camera), the photo-server URLs and the photo capture `date`. Frames 2756 -> 2758 contain a 3.7 km position jump (real source data, a quality-control case). |
| `fgdc_metadata.xml` | https://data.usgs.gov/datacatalog/metadata/USGS.fa1a6827-fbde-442a-80f6-b607892854a5.xml (identical copy: http://files.axiomalaska.com/usgs/cmgvideo/Coastal_and_Video_and_Photography_Portal.xml) | None. Full FGDC record of DOI 10.5066/F7JH3J7N. Licence evidence: `<useconst>` ("USGS-authored or produced data and information are in the public domain ..."). The lineage section describes the navigation join. |
| `portal_layergroup_ca_seafloor.json` | https://search.axds.co/v2/search?portalId=42&type=layer_group&page=1 (JSONP, `callback(...)` wrapper removed) | Kept only `results[0]` (the layer group "Seafloor Video and Photography", California Seafloor Mapping Program Imagery) out of the 10 results of page 1, re-indented. It contains the sentence on the +/- 10 m position offset. No value edited. |

## Expected `resolve_geo` results

| Fixture record | lat | lon | geo_precision | geo_inferred | geo_uncertainty_m |
|---|---|---|---|---|---|
| video row `id` 1, `frame` 0 (frame extracted at exactly 0 s) | 33.88664 | -118.43536 | image | false | 10 |
| video frame extracted at t = 5 s of `O-1-00-SC_St-SM1-1.mp4` (between rows `frame` 0 and 10) | 33.88661 | -118.43534 | segment | true | 10 |
| photo row `id` 161881 (`photo` 11695) | 41.151148 | -124.181668 | image | false | 10 |
| woodshole photo row `id` 44957 (`IMG_1463.JPG`) | 42.369143 | -70.661438 | image | false | 10 |
| nav frame 2756 of `C0212SC_Tape65` (has a photo, date 2012-08-26) | 36.878388 | -122.02922 | image | false | 10 |

For all rows depth_m = null (no depth field in any layer). The uncertainty 10 m is the provider statement quoted from `portal_layergroup_ca_seafloor.json`; deeper or longer cable layback surveys can be worse.

An EXIF check (not stored as a fixture): the full-size JPEG
https://servomatic9000.axiomalaska.com/photo-server/usgs/5821795839062507905/5833695139547831826/photo?
(3,559,764 bytes; the server ignored the HTTP Range header and sent the whole file, which was deleted after reading) has EXIF `GPSLatitude` 36 deg 52.70328' N, `GPSLongitude` 122 deg 1.7532' W, `GPSDateStamp` 2012:08:26, `GPSTimeStamp` 17:31:17, `DateTimeOriginal` 2012:08:26 17:31:18, Canon EOS 60D, 5184x3456. That is 36.878388, -122.02922, identical to the navigation row `frame` 2756 above, so the EXIF GPS and the WFS coordinate are the same value.

No `publication_sites.csv`: geolocation is per navigation row, not from a publication table.

Timing caveat from the same check: the portal's `date` for that photo is "Aug 26, 2012 05:08:18 PM" (from `neighborhoodFrames_seafloor_video.json`), while the EXIF `DateTimeOriginal`/`GPSTimeStamp` say 17:31:18/17:31:17 on the same day. The seconds agree and the minutes differ by 23, so the camera clock and the navigation clock are offset for this survey. Use the coordinate from the row, never re-derive it from EXIF time.
