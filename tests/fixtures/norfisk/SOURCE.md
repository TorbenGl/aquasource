# Fixture sources: `norfisk`

All files retrieved 2026-10-06 with User-Agent `aquasource-research/0.1 (+https://github.com/torbengl/aquasource)`.
Dataset: NorFisk Dataset, DataverseNO, doi:10.18710/H5G3K5 (licence CC0 1.0, record level).

| File | Exact URL | Trimming / notes |
|---|---|---|
| `dataverse_schemaorg.json` | https://dataverse.no/api/datasets/export?exporter=schema.org&persistentId=doi:10.18710/H5G3K5 | None. Byte-for-byte copy of the response (3,663 bytes). Holds `license`, `distribution[].contentUrl`, `contentSize`. |
| `dataverse_dataset_trimmed.json` | https://dataverse.no/api/datasets/:persistentId/?persistentId=doi:10.18710/H5G3K5 | Dropped one field: the `datasetContact` entry of `latestVersion.metadataBlocks.citation.fields`, because it holds a personal e-mail address. Re-serialized with `json.dump(indent=1, ensure_ascii=False)`. No value was edited. Holds `license`, `dateOfCollection` (2017-01-01 to 2020-08-01), `files[]` with ids 86886 / 86889, sizes and MD5s. |
| `00_ReadMe_excerpt.txt` | https://dataverse.no/api/access/datafile/86886 (`00_ReadMe.txt`, doi:10.18710/H5G3K5/CPGKKO) | Dropped line 13 (the contact e-mail line). The other 90 lines are unchanged. Says "depths ranges between 1 and 50 meters", "2017 to 2020", GoPro Hero 4/5/8, 1 frame/s. Mentions no site. |
| `saithe.000001.txt` | Zip member `saithe/annotations/saithe.000001.txt` inside https://dataverse.no/api/access/datafile/86889 (`NorFisk_v1.0.zip`, 2,641,300,775 bytes; 303 redirect to a pre-signed S3 URL). Read with HTTP Range requests: the central directory (bytes 2638671501-2641300752), then the saithe annotation block (bytes 142-430961). | None. Exact member bytes (47 bytes, stored and uncompressed, CRC32 checked against the zip header). Format: `file_name,class,xmin,ymin,xmax,ymax,width,height`. |
| `salmonid.000001.txt` | Zip member `salmonid/annotations/salmonid.000001.txt` of the same zip, from Range bytes 932306983-933725384 | None. Exact member bytes (53 bytes, CRC32 checked). It is the same row the README gives as its example. |
| `publication_sites.csv` | Derived (see below) | Built by hand from the publication and a gazetteer lookup. It is not a provider file. |

## publication_sites.csv: derivation

Publication: Crescitelli, A. M., Gansel, L. C., Zhang, H. (2021). NorFisk: fish image dataset from Norwegian fish farms
for species recognition using deep neural networks. *Modeling, Identification and Control* 42(1):1-16.
doi:10.4173/mic.2021.1.1. PDF: https://www.mic-journal.no/PDF/2021/MIC-2021-1-1.pdf (retrieved 2026-10-06).

Quote, Section 3.2 "Data collection", page 9:

> "The video footage has been taken in a fish farm at different times on different days between 2017 to 2020.
> Videos were taken in different weather conditions and at different depths as well. The farm is located near
> lesund in Norway (see figure 7)"

The printed PDF reads "near lesund". A 150-dpi render of the page confirmed this: the "Å" was lost in typesetting.
We read it as **Ålesund** for three reasons: the word is lower-case, all authors are at NTNU Ålesund, and the dataset
README gives the institution as "NTNU i Ålesund".
The paper's Figure 7 caption reads "Fish farm where video footage for the experiments was collected."
The paper prints no coordinates, no farm name and no table of sites.
The companion conference paper (Crescitelli et al. 2020, ICIEA, doi:10.1109/ICIEA48937.2020.9248107) says in its abstract
"video samples were taken inside and outside cages of a fish farm in Norway".

Gazetteer lookup (1 request):
`https://nominatim.openstreetmap.org/search?q=%C3%85lesund%2C%20Norway&format=jsonv2&limit=3`.
It returned `node 31264149, place=city, "Ålesund, Møre og Romsdal, 6004, Norge", lat 62.4711412, lon 6.1551755`.
We used the city node, not the municipality relation 16873323, whose centroid is 62.4802364 / 6.5550739.

Uncertainty is set to 30,000 m. The paper gives only "near Ålesund", and salmon farms in the Ålesund, Giske, Sula, Hareid
and Haram archipelago lie within about 30 km of the city node. `depth_m` is left empty because only a range is given:
"depths ranges between 1 and 50 meters" (README), with no value per image.

Check on the other reading (1 request):
`https://nominatim.openstreetmap.org/search?q=Lesund&countrycodes=no&format=jsonv2&limit=5`.
It returned a hamlet "Lesund, Aure, Møre og Romsdal" at 63.3308569, 8.4669104, about 130 km north-east.
We consider this reading unlikely, for the reasons above. It is listed as a risk in research/norfisk.md.
