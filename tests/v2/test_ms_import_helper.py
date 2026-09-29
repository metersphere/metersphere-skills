"""ms_import_helper.py 单元测试（纯本地，无网络依赖）。"""
import json
import os
import sys
from pathlib import Path
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "skills", "scripts", "v2"))
import ms_import_helper as h


def _local_server(handler):
    """启动一个线程化本地 HTTP 服务器，返回 (server, thread)。"""
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()
    return httpd, t


class SpecDownloadHandler(BaseHTTPRequestHandler):
    """提供 /spec.json 下载 + /spec-slow.json 超时 + /spec-404.json 不存在。"""

    def do_GET(self):
        if self.path == "/spec.json":
            body = b'{"openapi": "3.0.0", "info": {"title": "x", "version": "1.0"}}'
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, *args):
        pass


class TestResolveSpecToFile(unittest.TestCase):

    def test_http_download_preserves_original_name(self):
        server, t = _local_server(SpecDownloadHandler)
        try:
            port = server.server_address[1]
            path, name = h.resolve_spec_to_file(f"http://127.0.0.1:{port}/spec.json")
            self.assertEqual(name, "spec.json")
            self.assertTrue(os.path.exists(path))
            with open(path, encoding="utf-8") as fh:
                self.assertIn('"openapi"', fh.read())
            os.unlink(path)
        finally:
            server.shutdown()

    def test_file_url_download_preserves_original_name(self):
        with open("/tmp/ms-spec-src.json", "w", encoding="utf-8") as fh:
            fh.write('{"info": {"title": "src"}}')
        try:
            path, name = h.resolve_spec_to_file("file:///tmp/ms-spec-src.json")
            self.assertEqual(name, "ms-spec-src.json")
            with open(path, encoding="utf-8") as fh:
                self.assertEqual(json.load(fh)["info"]["title"], "src")
            os.unlink(path)
        finally:
            os.unlink("/tmp/ms-spec-src.json")

    def test_local_existing_file(self):
        fixture = Path(__file__).resolve().parent / "fixtures" / "springdoc-sample-bookstore.json"
        path, name = h.resolve_spec_to_file(str(fixture))
        self.assertEqual(name, "springdoc-sample-bookstore.json")
        self.assertTrue(os.path.isabs(path))

    def test_nonexistent_path_errors(self):
        with self.assertRaises(ValueError):
            h.resolve_spec_to_file("/nonexistent/definitely-not-here.json")

    def test_bad_suffix_errors(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp_dir:
            src = os.path.join(tmp_dir, "not-a-spec.txt")
            with open(src, "w", encoding="utf-8") as fh:
                fh.write("x")
            with self.assertRaises(ValueError):
                h.resolve_spec_to_file(src)

    def test_http_404_errors(self):
        server, t = _local_server(SpecDownloadHandler)
        try:
            port = server.server_address[1]
            with self.assertRaises(ValueError):
                h.resolve_spec_to_file(f"http://127.0.0.1:{port}/spec-404.json")
        finally:
            server.shutdown()

    def test_empty_source_errors(self):
        with self.assertRaises(ValueError):
            h.resolve_spec_to_file("   ")


class TestParseImportResponse(unittest.TestCase):

    def test_full_shape_three_items(self):
        resp = {
            "success": True,
            "message": "导入成功",
            "data": {
                "data": [
                    {"id": "def-1", "name": "Create book"},
                    {"id": "def-2", "name": "Search books"},
                    {"id": "def-3", "name": "Get book by id"},
                ]
            },
        }
        out = h.parse_import_response(resp)
        self.assertEqual(len(out), 3)
        self.assertEqual(out[0], {"id": "def-1", "name": "Create book"})
        self.assertEqual(out[2]["name"], "Get book by id")

    def test_flat_data_list(self):
        resp = {"success": True, "data": [{"id": "a", "name": "A"}]}
        self.assertEqual(h.parse_import_response(resp), [{"id": "a", "name": "A"}])

    def test_accepts_json_string(self):
        resp = '{"success": true, "data": {"data": [{"id": "x", "name": "X"}]}}'
        self.assertEqual(h.parse_import_response(resp), [{"id": "x", "name": "X"}])

    def test_invalid_json_errors(self):
        with self.assertRaises(ValueError):
            h.parse_import_response("not json {")

    def test_missing_array_errors(self):
        with self.assertRaises(ValueError):
            h.parse_import_response({"success": True, "data": {"foo": 1}})
        with self.assertRaises(ValueError):
            h.parse_import_response({"success": True})

    def test_entry_missing_id_or_name_errors(self):
        with self.assertRaises(ValueError):
            h.parse_import_response({"data": {"data": [{"name": "only-name"}]}})
        with self.assertRaises(ValueError):
            h.parse_import_response({"data": {"data": [{"id": "only-id"}]}})


class _TestCaseListHandler(BaseHTTPRequestHandler):
    """记录请求并在 /recorded 上报，响应按请求路径分页。"""

    requests = []
    request_bodies = []

    pages = {
        "1": {"listObject": [{"name": f"def-成功场景{i}"} for i in range(500)], "pageCount": 2, "itemCount": 501},
        "2": {"listObject": [{"name": "def-必填缺失"}], "pageCount": 2, "itemCount": 501},
    }

    def do_POST(self):
        self.requests.append((self.path, int(self.headers.get("Content-Length", 0))))
        body = b""
        if self.headers.get("Content-Length"):
            body = self.rfile.read(int(self.headers["Content-Length"]))
        self.request_bodies.append(json.loads(body or b"{}"))
        page = self.path.rstrip("/").split("/")[-2] if "/" in self.path.rstrip("/") else "1"
        req_body = self.request_bodies[-1] if self.request_bodies else {}
        if req_body.get("apiDefinitionId") == "no-such-def":
            resp_data = {"listObject": [], "pageCount": 1, "itemCount": 0}
        else:
            resp_data = self.pages.get(page, {"listObject": [], "pageCount": 1, "itemCount": 0})
        resp = {"success": True, "data": resp_data}
        payload = json.dumps(resp).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, *args):
        pass


class TestExistingCaseNames(unittest.TestCase):

    def _reset(self):
        _TestCaseListHandler.requests = []
        _TestCaseListHandler.request_bodies = []

    def test_paginated_list_returns_all_names(self):
        self._reset()
        server, t = _local_server(_TestCaseListHandler)
        try:
            port = server.server_address[1]
            names = h.existing_case_names(
                project_id="p1", api_definition_id="def-1",
                base_url=f"http://127.0.0.1:{port}", headers={"X-Test": "1"},
            )
            self.assertEqual(len(names), 501)
            self.assertIn("def-成功场景0", names)
            self.assertIn("def-必填缺失", names)
            # 请求体校验
            self.assertEqual(_TestCaseListHandler.request_bodies[0]["projectId"], "p1")
            self.assertEqual(_TestCaseListHandler.request_bodies[0]["apiDefinitionId"], "def-1")
            # 翻页: 第 2 页请求发生
            self.assertTrue(any(p[0].endswith("/2/500") for p in _TestCaseListHandler.requests))
        finally:
            server.shutdown()

    def test_empty_result(self):
        self._reset()
        server, t = _local_server(_TestCaseListHandler)
        try:
            port = server.server_address[1]
            names = h.existing_case_names("p1", "no-such-def", f"http://127.0.0.1:{port}")
            self.assertEqual(names, set())
        finally:
            server.shutdown()


if __name__ == "__main__":
    unittest.main()
