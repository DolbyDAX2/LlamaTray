"""
LlamaTray v1.5.5 Core Logic Unit Tests.
Saf mantık, argüman üretimi, veri güvenliği ve doğrulama testleri.
"""

import os
import json
import shutil
import tempfile
import unittest

from LlamaTray.ui_utils import save_json_atomic, get_log_file_path, get_file_logger
from LlamaTray.server import build_server_args, LlamaServerManager


class TestAtomicJsonSave(unittest.TestCase):
    """Atomik JSON kaydetme ve veri güvenliği testleri."""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="llamatray_test_")
        self.file_path = os.path.join(self.test_dir, "profiles.json")

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_save_and_read_json(self):
        data = {"model_default": {"gpu_layers": 33, "context_size": 16384}}
        save_json_atomic(self.file_path, data)

        self.assertTrue(os.path.exists(self.file_path))
        with open(self.file_path, "r", encoding="utf-8") as f:
            loaded = json.load(f)
        self.assertEqual(loaded, data)

    def test_atomic_overwrite(self):
        initial_data = {"key": "initial_value"}
        save_json_atomic(self.file_path, initial_data)

        updated_data = {"key": "updated_value", "number": 42}
        save_json_atomic(self.file_path, updated_data)

        with open(self.file_path, "r", encoding="utf-8") as f:
            loaded = json.load(f)
        self.assertEqual(loaded, updated_data)

    def test_nested_directory_creation(self):
        nested_path = os.path.join(self.test_dir, "nested", "sub", "config.json")
        save_json_atomic(nested_path, {"test": True})
        self.assertTrue(os.path.exists(nested_path))


class TestServerArgs(unittest.TestCase):
    """llama-server komut satırı argüman üretim ve doğrulama testleri."""

    def test_single_model_args_default(self):
        args = build_server_args(
            model_path="/models/test.gguf",
            gpu_layers=32,
            context_size=8192,
            port=8080
        )
        self.assertIn("-m", args)
        self.assertIn("/models/test.gguf", args)
        self.assertIn("--n-gpu-layers", args)
        self.assertIn("32", args)
        self.assertIn("--ctx-size", args)
        self.assertIn("8192", args)
        self.assertIn("--port", args)
        self.assertIn("8080", args)

    def test_router_mode_args(self):
        args = build_server_args(
            router_mode=True,
            models_dir="/models/all",
            gpu_layers=99,
            context_size=16384,
            port=9000,
            no_models_autoload=True,
            jinja=True
        )
        self.assertIn("--models-dir", args)
        self.assertIn("/models/all", args)
        self.assertIn("--no-models-autoload", args)
        self.assertIn("--jinja", args)
        self.assertIn("--port", args)
        self.assertIn("9000", args)
        self.assertIn("-ngl", args)
        self.assertIn("99", args)

    def test_mmproj_parameter(self):
        args = build_server_args(
            model_path="/models/vision.gguf",
            mmproj_path="/models/vision.mmproj",
            gpu_layers=20,
            context_size=4096,
            port=8080
        )
        self.assertIn("--mmproj", args)
        self.assertIn("/models/vision.mmproj", args)

    def test_extra_parameters_splitting(self):
        args = build_server_args(
            model_path="/models/test.gguf",
            extra_params="-t 8 --flash-attn --prompt \"sample prompt test\""
        )
        self.assertIn("-t", args)
        self.assertIn("8", args)
        self.assertIn("--flash-attn", args)
        self.assertIn("--prompt", args)
        self.assertIn("sample prompt test", args)

    def test_invalid_context_size(self):
        with self.assertRaises(ValueError):
            build_server_args(model_path="/models/test.gguf", context_size=100)
        with self.assertRaises(ValueError):
            build_server_args(model_path="/models/test.gguf", context_size="not_a_number")

    def test_invalid_port(self):
        with self.assertRaises(ValueError):
            build_server_args(model_path="/models/test.gguf", port=80)
        with self.assertRaises(ValueError):
            build_server_args(model_path="/models/test.gguf", port=70000)

    def test_missing_model_path(self):
        with self.assertRaises(ValueError):
            build_server_args(model_path="", router_mode=False)

    def test_missing_models_dir_in_router(self):
        with self.assertRaises(ValueError):
            build_server_args(models_dir="", router_mode=True)


class TestLoggingAndShutdown(unittest.TestCase):
    """Loglama ve sunucu durumu testleri."""

    def test_log_file_path(self):
        path = get_log_file_path()
        self.assertTrue(path.endswith("llamatray.log"))
        self.assertTrue(os.path.isabs(path))

    def test_server_manager_initial_state(self):
        manager = LlamaServerManager()
        self.assertFalse(manager.is_running())
        # Sunucu kapalıyken stop_server çağrısının güvenli ve hızlı sonlandığını doğrula
        manager.stop_server()
        self.assertFalse(manager.is_running())


if __name__ == "__main__":
    unittest.main()
