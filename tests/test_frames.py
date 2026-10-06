import shutil
import subprocess

import pytest

from aquasource.adapters.base import Adapter, register
from aquasource.core.config import load_config
from aquasource.core.licence import make_licence
from aquasource.core.schema import Candidate, Geo
from aquasource.frames import extract_frames
from aquasource.runner import run_source

pytestmark = pytest.mark.skipif(not shutil.which("ffmpeg"), reason="ffmpeg not installed")


@register
class FakeVideoAdapter(Adapter):
    key = "fake_video_source"
    media_types = ("video",)

    def discover(self):
        yield Candidate(self.key, "vid-1", "video", "https://example.invalid/v.mp4", "https://example.invalid/v", ext="mp4")

    def resolve_licence(self, cand):
        return make_licence("CC BY 4.0", level="record", url=None, attribution="Fake")

    def resolve_geo(self, cand):
        return Geo(54.5, 10.2, 12.0, "station", "station table", True, 500.0)

    def fetch_media(self, cand, ref, dest):
        dest.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["ffmpeg", "-nostdin", "-loglevel", "error", "-f", "lavfi", "-i", "testsrc=duration=4:size=64x48:rate=5", str(dest)], check=True)
        return dest.stat().st_size, "sha"


def test_frames_inherit_geo(tmp_path):
    cfg = load_config(None, data_root=tmp_path)
    run_source(cfg, "fake_video_source", "download")
    counts = extract_frames(cfg, "fake_video_source", every_s=1.0, max_per_video=3)
    assert counts == {"videos": 1, "frames": 3, "skipped": 0}
    again = extract_frames(cfg, "fake_video_source", every_s=1.0, max_per_video=3)
    assert again["frames"] == 0  # idempotent
    import json

    rows = [json.loads(l) for l in (tmp_path / "fake_video_source" / "metadata" / "samples.jsonl").read_text().splitlines()]
    frames = [r for r in rows if r["media_type"] == "image"]
    assert len(frames) == 3
    assert all(f["geo_precision"] == "station" and f["geo_inferred"] and f["extra"]["from_video"] for f in frames)
