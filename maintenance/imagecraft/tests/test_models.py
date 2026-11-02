import io
from importlib import import_module
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "imagecraft/scripts"))
models = import_module("download_models")
jobs = import_module("ic.jobs")
main = import_module("ic.cli").main
Error = import_module("ic.common").Error
build, validate = import_module("ic.workflow").build, import_module("ic.workflow").validate
from test_runtime import FakeClient, object_info


class ModelSelection(unittest.TestCase):
    def test_reviewed_default_remains_flux_with_explicit_z_options(self):
        self.assertEqual(models.DEFAULT_MODEL, "flux-klein-4b")
        self.assertEqual(models.MODEL_IDS, ("flux-klein-4b", "z-image-turbo", "z-image-turbo-fp8"))

    def test_z_manifest_and_shared_encoder(self):
        flux = models.load_manifest("flux-klein-4b")
        z = models.load_manifest("z-image-turbo")
        self.assertEqual(z["license"], "Apache-2.0")
        self.assertEqual(sum(f["bytes"] for f in z["files"]), 14581287732)
        for key in ("bytes", "destination", "sha256"):
            self.assertEqual(flux["files"][1][key], z["files"][1][key])
        self.assertNotEqual(flux["files"][2]["sha256"], z["files"][2]["sha256"])

    def test_low_vram_variant_is_explicit_and_pinned(self):
        low = models.load_manifest("z-image-turbo-fp8")
        self.assertEqual(low["files"][1]["bytes"], 5631994051)
        self.assertEqual(low["files"][0], models.load_manifest("z-image-turbo")["files"][0])
        self.assertEqual(models.workflow_path(low["id"]), models.workflow_path("z-image-turbo"))

    def test_unknown_model_refused(self):
        for name in ("../outside", "unapproved", "qwen-image-2.1"):
            with self.assertRaises(models.ModelError):
                models.load_manifest(name)

    def test_z_graph_official_recipe(self):
        graph = build("Ceramic teapot", 1536, 1024, 123, "test/z", model="z-image-turbo")
        self.assertEqual(graph["2"]["inputs"]["type"], "lumina2")
        self.assertEqual(graph["6"]["class_type"], "EmptySD3LatentImage")
        self.assertEqual(graph["6"]["inputs"]["width"], 1536)
        self.assertEqual(graph["7"]["inputs"]["shift"], 3)
        self.assertEqual(graph["10"]["inputs"]["steps"], 8)
        self.assertEqual(graph["10"]["inputs"]["cfg"], 1)
        self.assertEqual(graph["10"]["inputs"]["seed"], 123)
        self.assertEqual(graph["10"]["inputs"]["sampler_name"], "res_multistep")
        self.assertEqual(graph["13"]["inputs"]["filename_prefix"], "test/z")
        info = {node["class_type"]: {"python_module": "nodes", "input": {"required": {k: ["ANY"] for k in node["inputs"]}}} for node in graph.values()}
        validate(graph, info)

    def test_low_profile_uses_fp8_encoder(self):
        graph = build("test", 1024, 1024, 42, "test", model="z-image-turbo-fp8")
        self.assertEqual(graph["2"]["inputs"]["clip_name"], "qwen_3_4b_fp8_mixed.safetensors")

    def test_reference_rejected_for_z(self):
        with self.assertRaisesRegex(Error, "text-to-image only"):
            build("test", 1024, 1024, 42, "test", ["input.png"], model="z-image-turbo")
        self.assertIn("20", build("test", 1024, 1024, 42, "test", ["input.png"], model="flux-klein-4b"))

    def test_plan_includes_model_and_distinct_hashes(self):
        flux = jobs.prepare_request("test", 1024, 1024, 42, "general", [], model="flux-klein-4b")
        z = jobs.prepare_request("test", 1024, 1024, 42, "general", [], model="z-image-turbo")
        self.assertNotEqual(flux["model_manifest_sha256"], z["model_manifest_sha256"])
        self.assertNotEqual(flux["workflow_template_sha256"], z["workflow_template_sha256"])
        self.assertNotEqual(jobs.fingerprint(flux), jobs.fingerprint(z))

    def test_inventory_exposes_shared_weights(self):
        with tempfile.TemporaryDirectory() as temp:
            report = models.inventory(Path(temp), model="z-image-turbo")
            self.assertEqual(report["missing_bytes"], 14581287732)
            self.assertIn("flux-klein-4b", report["files"][1]["shared_with_models"])
            self.assertEqual(len(report["files"]), 3)

    def test_cli_offline_plan_has_model(self):
        stream = io.StringIO()
        with patch("sys.stdout", stream):
            code = main(["plan", "--prompt", "test", "--model", "z-image-turbo"])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(stream.getvalue())["request"]["model"], "z-image-turbo")

    def test_submit_hashes_only_selected_model(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            graph = build("test", 1024, 1024, 42, "test", model="z-image-turbo")
            info = object_info()
            info.update({n["class_type"]: {"python_module": "nodes", "input": {"required": {k: ["ANY"] for k in n["inputs"]}}} for n in graph.values()})
            original = FakeClient.request
            def request(client, path, payload=None):
                return info if path == "/object_info" else original(client, path, payload)
            FakeClient.posts, FakeClient.fail_post, FakeClient.busy = 0, False, False
            with patch("ic.jobs.Client", FakeClient), patch.object(FakeClient, "request", request), patch("ic.jobs.inventory", return_value={"files": []}) as inventory:
                req = jobs.prepare_request("test", 1024, 1024, 42, "general", [], model="z-image-turbo")
                jobs.submit({"url": "http://127.0.0.1:8189", "models_root": str(root/"models")}, root, req)
            self.assertEqual(inventory.call_args.kwargs["model"], "z-image-turbo")
            self.assertEqual(FakeClient.posts, 1)

    def test_changed_manifest_cannot_be_submitted(self):
        with tempfile.TemporaryDirectory() as temp:
            req = jobs.prepare_request("test", 1024, 1024, 42, "general", [], model="z-image-turbo")
            req["model_manifest_sha256"] = "a" * 64
            with patch("ic.jobs.Client") as client, self.assertRaisesRegex(Error, "changed after planning"):
                jobs.submit({"url": "http://127.0.0.1:8189"}, Path(temp), req)
            client.assert_not_called()


if __name__ == "__main__":
    unittest.main()
