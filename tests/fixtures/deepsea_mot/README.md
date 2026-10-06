---
language:
- en
license: cc-by-sa-4.0
tags:
- biology
- marine
- multi-object-tracking
- video
- underwater
annotations_creators:
- expert-generated
pretty_name: DeepSea MOT
size_categories:
- n<1K
- 1K<n<10K
- 10K<n<100K
task_categories:
- object-detection
---

# DeepSea MOT

**DeepSea MOT** is a benchmark dataset for multi-object tracking on deep-sea video.

## Dataset Description

DeepSea MOT consists of 4 video sequences (2 midwater, 2 benthic) with a total of 2,400 frames and 57,376 annotated objects comprising 188 tracks. The videos were captured by the [Monterey Bay Aquarium Research Institute (MBARI)](https://www.mbari.org/) using remotely operated vehicles (ROVs) [*Doc Ricketts*](https://www.mbari.org/technology/rov-doc-ricketts/) and [*Ventana*](https://www.mbari.org/technology/rov-ventana/) in deep-sea environments, showcasing a variety of marine species and underwater scenes.

- **Paper:** https://arxiv.org/abs/2509.03499
- **Workflow:** https://docs.mbari.org/benchmark_eval/

**[2025-12-08] New 4K Sequences:** In addition to the original sequences, DeepSea MOT now includes two new 4K resolution sequences (Benthic Simple and Midwater Simple) to facilitate research on high-resolution underwater video analysis.

**[2026-02-08] New Marine Debris Sequences:** DeepSea MOT now includes five marine debris sequences to facilitate detection of debris in underwater video. Three video sequences were collected by MBARI (`MD_ROP`, `MD_CAN`, and `MD_CLS`) and two sequences were collected by IFREMER (`MD_BOT` and `MD_FLN`). 

*Note: these sequences use a different class ID mapping than the original DeepSea MOT sequences.*

## File Structure

The dataset is organized as follows:

```
data/
├── vidseq_names.txt          # TrackEval sequence names file
├── BD/                       # Benthic Difficult sequence
│   ├── BD.mov                # Source video file
│   ├── gt.txt                # MOT Challenge format ground truth
│   ├── seqinfo.ini           # TrackEval sequence information
│   ├── images/               # Frame images (JPG format)
│   │   ├── BD_001.jpg
│   │   ├── BD_002.jpg
│   │   └── ...
│   ├── labels/               # YOLO-formatted annotation files (TXT)
│   └── xml/                  # Pascal VOC annotation files (from RectLabel)
├── BS/                       # Benthic Simple sequence
│   ├── BS.mov
│   ├── gt.txt
│   ├── seqinfo.ini
│   ├── images/
│   ├── labels/
│   └── xml/
├── MWD/                      # Midwater Difficult sequence
│   ├── MWD.mov
│   ├── gt.txt
│   ├── seqinfo.ini
│   ├── images/
│   ├── labels/
│   └── xml/
├── MWS/                      # Midwater Simple sequence
|   ├── MWS.mov
|   ├── gt.txt
|   ├── seqinfo.ini
|   ├── images/
|   ├── labels/
|   └── xml/
├── ...
```

Each sequence directory contains:
- **Source video** (`.mov`): Original ROV footage
- **Ground truth** (`gt.txt`): MOT Challenge format annotations for tracking evaluation
- **Sequence info** (`seqinfo.ini`): Metadata file for TrackEval compatibility
- **Images** (`images/`): Individual frame extractions in JPG format
- **YOLO labels** (`labels/`): Object detection annotations in YOLO format (TXT files)
- **Pascal VOC** (`xml/`): Object detection annotations in Pascal VOC format (generated via [RectLabel](https://rectlabel.com/))

## Additional Information

### Dataset Curators

Authors of [[1]](https://arxiv.org/abs/2509.03499):

- Kevin Barnard
- Elaine Liu
- Kristine Walz
- Brian Schlining
- Nancy Jacobsen Stout
- Lonny Lundsten

### Citation Information

```bibtex
@article{barnard2025deepseamot,
    author = {Barnard, Kevin and Liu, Elaine and Walz, Kristine and Schlining, Brian and Stout, Nancy Jacobsen and Lundsten, Lonny},
    title = { {DeepSea MOT}: A benchmark dataset for multi-object tracking on deep-sea video},
    year = {2025},
    journal = {arXiv preprint arXiv:2509.03499},
    doi = {10.48550/arXiv.2509.03499},
}
```