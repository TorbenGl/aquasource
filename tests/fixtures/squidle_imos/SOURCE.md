# squidle_imos fixtures: sources

Retrieved 2026-10-07 (research) and spot-checked live on 2026-10-08 (verification). Metadata only; no images were downloaded.
All files are unmodified provider records except for the trimming noted.

| file | source URL | trimming |
|---|---|---|
| `imos_s3_dive_csv_ScottReef201108_excerpt.csv` | https://imos-data.s3-ap-southeast-2.amazonaws.com/IMOS/AUV/auv_viewer_data/csv_outputs/ScottReef201108/DATA_ScottReef201108_r20110810_042127_04_scott_long_leg_auv8.csv | lines 1-6 kept: 2-line dive header, column header, first 3 image rows |
| `squidle_deployment_export_213_excerpt.csv` | https://squidle.org/api/deployment/213/export?template=dataframe.csv&f={"operations":[{"module":"pandas","method":"json_normalize"}]} (202 background task; poll https://squidle.org/task/<task_id> with `Accept: application/json`, download https://squidle.org/task/<task_id>/result) | header plus first 3 rows |
| `squidle_api_pose_deployment22_page1.json` | https://squidle.org/api/pose?q={"filters":[{"name":"media","op":"has","val":{"name":"deployment_id","op":"eq","val":22}}]}&results_per_page=3&page=1 | 3 objects, untrimmed; the second object is the WMS ortho-mosaic pose |
| `squidle_api_pose_deployment11646_page1.json` | https://squidle.org/api/pose?q={"filters":[{"name":"media","op":"has","val":{"name":"deployment_id","op":"eq","val":11646}}]}&results_per_page=3&page=1 | 3 objects, untrimmed; the second object is the WMS ortho-mosaic pose |
| `squidle_deployment_export_16821_boss_dropcam.csv` | https://squidle.org/api/deployment/16821/export?template=dataframe.csv (same `f` as above) | 4 rows, untrimmed; UWA BOSS Dropcam, tier U, used only to test the station branch |

Licence of the IMOS AUV records: CC BY 4.0, AODN record https://catalogue-imos.aodn.org.au/geonetwork/srv/api/records/af5d0ff9-bb9c-4b7c-a63c-854a630b6984/formatters/xml
Acknowledgement: "Data was sourced from Australia's Integrated Marine Observing System (IMOS) - IMOS is enabled by the National Collaborative Research Infrastructure strategy (NCRIS)."
The BOSS fixture (platform "UWA BOSS Dropcam") has no verified licence; do not redistribute it.
Note: the pose-page ordering is not guaranteed to be stable; the fixtures were saved from the research-time response.
