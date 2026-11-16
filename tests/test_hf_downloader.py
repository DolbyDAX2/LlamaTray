"""
HuggingFace Downloader Unit Tests.
Saf mantık, quantization eşleme, boyut biçimlendirme ve token yönetimi testleri (ADR-003).
"""

import os
import stat
import shutil
import tempfile
import threading
import http.server
import socketserver
import unittest

from LlamaTray.components.hf_downloader import (
    fmt_downloads,
    fmt_size,
    is_recommended_quant,
    match_quant_filter,
    HfModelInfo,
    save_hf_token,
    load_saved_hf_token,
    DownloadThread,
    ThemeColors,
    is_dark_theme,
)


class TestHfDownloaderPureLogic(unittest.TestCase):
    """Saf biçimlendirme ve filtreleme mantığı testleri."""

    def test_theme_colors(self):
        dark_c = ThemeColors.get(dark=True)
        light_c = ThemeColors.get(dark=False)
        self.assertIn("card_bg", dark_c)
        self.assertIn("badge_dl_text", dark_c)
        self.assertEqual(dark_c["badge_dl_text"], "#60a5fa")  # Vibrant blue
        self.assertEqual(light_c["badge_dl_text"], "#1d4ed8")  # Deep blue
        self.assertIn("status_success", dark_c)
        self.assertEqual(dark_c["status_success"], "#4ade80")  # Vibrant emerald

    def test_fmt_downloads(self):
        self.assertEqual(fmt_downloads(0), "0")
        self.assertEqual(fmt_downloads(500), "500")
        self.assertEqual(fmt_downloads(1000), "1.0K")
        self.assertEqual(fmt_downloads(45200), "45.2K")
        self.assertEqual(fmt_downloads(1500000), "1.5M")

    def test_fmt_size(self):
        self.assertEqual(fmt_size(500), "500 B")
        self.assertEqual(fmt_size(1024), "1.0 KB")
        self.assertEqual(fmt_size(1048576), "1.00 MB")
        self.assertEqual(fmt_size(1610612736), "1.50 GB")

    def test_is_recommended_quant(self):
        self.assertTrue(is_recommended_quant("Meta-Llama-3-8B-Instruct-Q4_K_M.gguf"))
        self.assertTrue(is_recommended_quant("Qwen2.5-7B-Instruct-Q5_K_M.gguf"))
        self.assertTrue(is_recommended_quant("model.q4_k_m.gguf"))
        self.assertTrue(is_recommended_quant("model_q5_k_m_00001-of-00002.gguf"))

        self.assertFalse(is_recommended_quant("Meta-Llama-3-8B-Instruct-Q4_K_S.gguf"))
        self.assertFalse(is_recommended_quant("Meta-Llama-3-8B-Instruct-Q8_0.gguf"))
        self.assertFalse(is_recommended_quant("Meta-Llama-3-8B-Instruct-BF16.gguf"))
        self.assertFalse(is_recommended_quant("Qwen2.5-7B-Instruct-IQ3_M.gguf"))

    def test_match_quant_filter_all(self):
        self.assertTrue(match_quant_filter("model-BF16.gguf", "all"))
        self.assertTrue(match_quant_filter("model-Q4_K_M.gguf", "all"))

    def test_match_quant_filter_q4(self):
        self.assertTrue(match_quant_filter("model-Q4_K_M.gguf", "q4"))
        self.assertTrue(match_quant_filter("model-Q4_0.gguf", "q4"))
        self.assertTrue(match_quant_filter("model-IQ4_XS.gguf", "q4"))
        self.assertFalse(match_quant_filter("model-Q5_K_M.gguf", "q4"))
        self.assertFalse(match_quant_filter("model-Q8_0.gguf", "q4"))

    def test_match_quant_filter_q5(self):
        self.assertTrue(match_quant_filter("model-Q5_K_M.gguf", "q5"))
        self.assertTrue(match_quant_filter("model-Q5_0.gguf", "q5"))
        self.assertTrue(match_quant_filter("model-IQ5_M.gguf", "q5"))
        self.assertFalse(match_quant_filter("model-Q4_K_M.gguf", "q5"))

    def test_match_quant_filter_q8(self):
        self.assertTrue(match_quant_filter("model-Q8_0.gguf", "q8"))
        self.assertTrue(match_quant_filter("model-IQ8_M.gguf", "q8"))
        self.assertFalse(match_quant_filter("model-Q4_K_M.gguf", "q8"))

    def test_match_quant_filter_small(self):
        self.assertTrue(match_quant_filter("model-Q2_K.gguf", "small"))
        self.assertTrue(match_quant_filter("model-IQ2_XXS.gguf", "small"))
        self.assertTrue(match_quant_filter("model-Q3_K_M.gguf", "small"))
        self.assertTrue(match_quant_filter("model-IQ3_M.gguf", "small"))
        self.assertFalse(match_quant_filter("model-Q4_K_M.gguf", "small"))

    def test_hf_model_info_structure(self):
        info = HfModelInfo(
            id="Qwen/Qwen2.5-7B-Instruct-GGUF",
            downloads=12500,
            likes=450,
            gated=True,
            last_modified="2026-10-01"
        )
        self.assertEqual(info.id, "Qwen/Qwen2.5-7B-Instruct-GGUF")
        self.assertEqual(info.downloads, 12500)
        self.assertEqual(info.likes, 450)
        self.assertTrue(info.gated)
        self.assertEqual(info.last_modified, "2026-10-01")

        # Geriye dönük demet (tuple) açılımı
        repo_id, downloads, likes, gated, last_mod = info
        self.assertEqual(repo_id, "Qwen/Qwen2.5-7B-Instruct-GGUF")
        self.assertEqual(downloads, 12500)


class TestHfTokenStorage(unittest.TestCase):
    """HF Token dosya kaydetme ve izin testleri."""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="llamatray_hf_test_")
        self.original_home = os.environ.get("HOME")
        os.environ["HOME"] = self.test_dir

    def tearDown(self):
        if self.original_home is not None:
            os.environ["HOME"] = self.original_home
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_save_and_load_hf_token(self):
        test_token = "hf_TestTokenSecure123456789"
        save_hf_token(test_token)

        loaded = load_saved_hf_token()
        self.assertEqual(loaded, test_token)

        # 0600 dosya izinlerini doğrula
        token_path = os.path.join(self.test_dir, ".llamatray", "hf_token")
        self.assertTrue(os.path.exists(token_path))
        file_mode = stat.S_IMODE(os.stat(token_path).st_mode)
        self.assertEqual(file_mode, 0o600)

    def test_save_empty_token_removes_file(self):
        test_token = "hf_temporary"
        save_hf_token(test_token)
        token_path = os.path.join(self.test_dir, ".llamatray", "hf_token")
        self.assertTrue(os.path.exists(token_path))

        save_hf_token("")
        self.assertFalse(os.path.exists(token_path))
        self.assertEqual(load_saved_hf_token(), "")


class MockRangeHTTPHandler(http.server.BaseHTTPRequestHandler):
    """Range header destekli hafif mock HTTP sunucusu."""
    payload = b"A" * (1024 * 1024) + b"B" * (1024 * 1024) + b"C" * (1024 * 1024)  # 3 MB

    def log_message(self, format, *args):
        pass  # Test çıktısını temiz tut

    def do_HEAD(self):
        auth = self.headers.get("Authorization", "")
        if "forbidden" in auth:
            self.send_response(401)
            self.end_headers()
            return
        self.send_response(200)
        self.send_header("Content-Length", str(len(self.payload)))
        self.end_headers()

    def do_GET(self):
        auth = self.headers.get("Authorization", "")
        if "forbidden" in auth:
            self.send_response(401)
            self.end_headers()
            return

        range_hdr = self.headers.get("Range")
        if range_hdr and range_hdr.startswith("bytes="):
            start = int(range_hdr[6:].rstrip("-"))
            self.send_response(206)
            self.send_header("Content-Range", f"bytes {start}-{len(self.payload)-1}/{len(self.payload)}")
            self.send_header("Content-Length", str(len(self.payload) - start))
            self.end_headers()
            self.wfile.write(self.payload[start:])
        else:
            self.send_response(200)
            self.send_header("Content-Length", str(len(self.payload)))
            self.end_headers()
            self.wfile.write(self.payload)


class TestDownloadThreadResume(unittest.TestCase):
    """DownloadThread HTTP Range resume ve yetkilendirme testleri."""

    @classmethod
    def setUpClass(cls):
        cls.httpd = socketserver.TCPServer(("127.0.0.1", 0), MockRangeHTTPHandler)
        cls.port = cls.httpd.server_address[1]
        cls.server_thread = threading.Thread(target=cls.httpd.serve_forever)
        cls.server_thread.daemon = True
        cls.server_thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.httpd.server_close()

    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="llamatray_dl_test_")
        self.save_path = os.path.join(self.test_dir, "test_model.gguf")

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_full_download(self):
        url = f"http://127.0.0.1:{self.port}/test_model.gguf"
        thread = DownloadThread(url=url, save_path=self.save_path)

        finished_path = []
        thread.finished.connect(lambda p: finished_path.append(p))
        thread.run()

        self.assertEqual(len(finished_path), 1)
        self.assertEqual(finished_path[0], self.save_path)
        self.assertTrue(os.path.exists(self.save_path))
        self.assertEqual(os.path.getsize(self.save_path), len(MockRangeHTTPHandler.payload))
        with open(self.save_path, "rb") as f:
            self.assertEqual(f.read(), MockRangeHTTPHandler.payload)

    def test_resume_download(self):
        # 1 MB kısmı zaten indirilmiş simüle et (.part dosyası)
        part_path = self.save_path + ".part"
        initial_part = MockRangeHTTPHandler.payload[: 1024 * 1024]
        with open(part_path, "wb") as f:
            f.write(initial_part)

        url = f"http://127.0.0.1:{self.port}/test_model.gguf"
        thread = DownloadThread(url=url, save_path=self.save_path)

        finished_path = []
        thread.finished.connect(lambda p: finished_path.append(p))
        thread.run()

        self.assertEqual(len(finished_path), 1)
        self.assertTrue(os.path.exists(self.save_path))
        self.assertFalse(os.path.exists(part_path))
        self.assertEqual(os.path.getsize(self.save_path), len(MockRangeHTTPHandler.payload))
        with open(self.save_path, "rb") as f:
            self.assertEqual(f.read(), MockRangeHTTPHandler.payload)

    def test_gated_unauthorized(self):
        url = f"http://127.0.0.1:{self.port}/gated_model.gguf"
        thread = DownloadThread(url=url, save_path=self.save_path, token="forbidden")

        errors = []
        thread.error.connect(lambda e: errors.append(e))
        thread.run()

        self.assertEqual(len(errors), 1)
        self.assertIn("HTTP 401", errors[0])

