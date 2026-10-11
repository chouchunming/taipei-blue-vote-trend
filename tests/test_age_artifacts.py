import json
import tempfile
import unittest
from pathlib import Path

from taipei_blue_vote.age_structure import (
    AgeModel,
    AgeObservation,
    AgePrediction,
    ModelCoefficient,
)
from taipei_blue_vote.artifacts import write_age_artifacts


class AgeArtifactTests(unittest.TestCase):
    def test_write_age_artifacts_creates_village_model_and_manifest_files(self):
        observation = AgeObservation(
            district="信義區",
            village="景新里",
            population=1000,
            young_share=0.2,
            middle_share=0.5,
            senior_share=0.3,
            age_75_plus_share=0.1,
            valid_votes=700,
            blue_votes=315,
            blue_share=0.45,
        )
        model = AgeModel(
            coefficients=(
                ModelCoefficient("intercept", 0.2, None),
                ModelCoefficient("young_share", -0.4, -4.0),
                ModelCoefficient("senior_share", 0.8, 8.0),
            ),
            predictions=(AgePrediction(observation, 0.44, 0.01, 1, 1),),
            weighted_r2=0.42,
            baseline_district="信義區",
        )

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_age_artifacts(
                root,
                model,
                coverage=(1, 1),
                source_manifest={"snapshot": "2023-12", "sha256": "fixture"},
            )

            village = (root / "data/derived/village_age_structure_2024.csv").read_text()
            self.assertIn("district,village,population", village)
            self.assertIn("信義區,景新里,1000,20.0000,50.0000,30.0000,10.0000", village)
            self.assertIn(
                "predicted_blue_votes,predicted_blue_share,vote_residual",
                village.splitlines()[0],
            )
            self.assertIn(",315,45.0000,308,44.0000,7,1.0000,1,1", village)
            model_csv = (root / "data/derived/age_model_2024.csv").read_text()
            self.assertIn("young_share,-0.400000,-4.0000", model_csv)
            manifest = json.loads((root / "data/derived/age_source_manifest.json").read_text())
            self.assertEqual(manifest["snapshot"], "2023-12")
            svg = (root / "charts/village-age-model-2024.svg").read_text()
            html = (root / "charts/village-age-model-2024.html").read_text()
            self.assertIn("年齡結構模型", svg)
            self.assertIn("1 里加權生態迴歸", svg)
            self.assertIn("青年占比 +10pp", svg)
            self.assertIn("長者占比 +10pp", svg)
            self.assertEqual(svg.count('class="village-point"'), 1)
            self.assertIn("<svg", html)


if __name__ == "__main__":
    unittest.main()
