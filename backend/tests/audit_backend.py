"""Isolated functional/security audit. Uses temporary SQLite, uploads and Chroma.

Run from the project root with: python backend/tests/audit_backend.py
PASS = required behavior observed; ISSUE = reproduced defect; ERROR = probe failed.
This is an audit runner, so reproduced issues do not produce a failing exit code.
"""
import csv
import hashlib
import io
import json
import logging
import os
from pathlib import Path
import sqlite3
import sys
import tempfile
from datetime import datetime, timedelta
from unittest.mock import patch, Mock

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
RESULTS = []


def run(case_id, name, callback, defect=False):
    try:
        ok, evidence = callback()
        status = "PASS" if ok else ("ISSUE" if defect else "FAIL")
        RESULTS.append(dict(id=case_id, name=name, status=status, evidence=evidence))
    except Exception as exc:
        RESULTS.append(dict(id=case_id, name=name, status="ERROR", evidence=f"{type(exc).__name__}: {exc}"))
    print(f"{RESULTS[-1]['status']:5} {case_id} {name}", flush=True)


def expect(response, code=200):
    if response.status_code != code:
        raise AssertionError(f"Expected HTTP {code}, got {response.status_code}: {response.text[:300]}")
    return response.json()


def fingerprints():
    values = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
              for p in (ROOT / "backend/data").rglob("*")
              if p.is_file() and "chroma_db" not in p.parts}
    # A running Uvicorn reloader can touch Chroma's maintenance tables when new
    # test files are saved. Compare business rows, not storage-maintenance bytes.
    chroma_path = ROOT / "backend/data/chroma_db/chroma.sqlite3"
    with sqlite3.connect(f"file:{chroma_path.as_posix()}?mode=ro", uri=True) as conn:
        for table in ["collections", "embeddings", "embedding_metadata", "embedding_metadata_array"]:
            rows = sorted(conn.execute(f'SELECT * FROM "{table}"').fetchall(), key=repr)
            values[f"chroma_logical:{table}"] = hashlib.sha256(repr(rows).encode()).hexdigest()
    return values


def source_fingerprints():
    return {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for directory in [ROOT / "backend/app", ROOT / "frontend/src"]
            for p in directory.rglob("*") if p.is_file() and p.suffix in {".py", ".js", ".vue"}}


def main():
    before = fingerprints()
    sources_before = source_fingerprints()
    with tempfile.TemporaryDirectory(prefix="enterprise-rag-audit-") as task_dir:
        task_root = Path(task_dir)
        uploads = task_root / "uploads"
        uploads.mkdir()
        os.environ["DATABASE_URL"] = "sqlite:///" + (task_root / "audit.db").as_posix()
        os.environ["CHROMA_DIR"] = str(task_root / "chroma")
        os.environ["UPLOAD_DIR"] = str(uploads)
        os.environ["SECRET_KEY"] = "rag-enterprise-secret-key-change-in-production-2026"
        from app import config
        assert config.settings.CHROMA_DIR.resolve() == (task_root / "chroma").resolve()
        assert config.settings.DATABASE_URL == os.environ["DATABASE_URL"]
        # The upload route imports this module constant instead of settings.UPLOAD_DIR.
        # Patch it to keep ALL audit uploads away from the existing knowledge base.
        config.UPLOAD_DIR = uploads
        from app.main import app
        from app.database import SessionLocal, engine
        from app.models.user import User
        from app.models.document import Document
        from app.models.chat import ChatMessage, ChatSession
        from app.services.vector_store import vector_service, HashFallbackEmbeddings
        from app.services.rag_service import rag_service
        from app.services.text_splitter import TextChunkSplitter
        from app.core.security import get_password_hash, verify_password
        from fastapi.testclient import TestClient
        from jose import jwt
        from langchain_core.documents import Document as LCDocument
        from init_db import init
        logging.getLogger().setLevel(logging.CRITICAL)
        init()
        vector_service.get_embeddings_model = lambda: HashFallbackEmbeddings()
        # All language-model calls are deliberately offline; no enterprise content leaves the machine.
        offline = lambda *args, **kwargs: (_ for _ in ()).throw(ConnectionError("audit offline mode"))
        rag_service._call_ollama = offline
        rag_service._call_openai_compatible = offline
        client = TestClient(app, raise_server_exceptions=False)

        def login(username="admin", password="admin123"):
            data = expect(client.post("/api/auth/login", json=dict(username=username, password=password)))
            return {"Authorization": "Bearer " + data["access_token"]}

        admin = login()
        staff = login("staff", "staff123")

        def create_user(name, role="employee"):
            return expect(client.post("/api/users", headers=admin,
                                      json=dict(username=name, password="AuditPass123!", role=role)))

        def upload(name, data):
            doc = expect(client.post("/api/documents/upload", headers=admin,
                                     files={"file": (name, data)}))
            return next(d for d in expect(client.get("/api/documents", headers=admin)) if d["id"] == doc["id"])

        def count_vectors(doc_id):
            return len(vector_service.get_collection().get(where={"document_id": doc_id})["ids"])

        def functional_auth():
            codes = [client.get("/").status_code, client.get("/openapi.json").status_code,
                     client.get("/api/users").status_code,
                     client.post("/api/auth/login", json=dict(username="admin", password="wrong")).status_code,
                     client.post("/api/auth/token", data=dict(username="staff", password="staff123")).status_code]
            me = expect(client.get("/api/auth/me", headers=staff))
            return codes == [200, 200, 401, 400, 200] and "password_hash" not in me, {"http_codes": codes}
        run("F01", "Health, login, form login and anonymous access", functional_auth)

        def staff_permissions():
            probes = [("GET", "/api/users", None), ("POST", "/api/users", dict(username="denied", password="123456")),
                      ("PUT", "/api/users/1", dict(role="employee")), ("DELETE", "/api/users/1", None),
                      ("POST", "/api/users/1/reset-password", dict(new_password="123456")),
                      ("GET", "/api/documents", None), ("GET", "/api/documents/1/preview", None),
                      ("DELETE", "/api/documents/1", None), ("POST", "/api/documents/1/reindex", None),
                      ("GET", "/api/documents/chroma/stats", None), ("POST", "/api/documents/chroma/clear", None),
                      ("GET", "/api/settings", None), ("PUT", "/api/settings", {}),
                      ("GET", "/api/settings/logs", None),
                      ("POST", "/api/settings/test-model", dict(provider="ollama", base_url="http://unused", model="unused"))]
            codes = [client.request(method, url, headers=staff, json=body).status_code for method, url, body in probes]
            codes.append(client.post("/api/documents/upload", headers=staff, files={"file": ("denied.txt", b"test")}).status_code)
            return all(c == 403 for c in codes), {"admin_routes_checked": len(codes), "http_codes": codes}
        run("F02", "Employee denied access to all administrator operations", staff_permissions)

        def sessions():
            session = expect(client.post("/api/chat/sessions", headers=staff, json={"title": "audit session"}))
            sid = session["id"]
            expect(client.put(f"/api/chat/sessions/{sid}", headers=staff, json={"title": "renamed"}))
            paths = [("GET", f"/api/chat/sessions/{sid}/messages", None),
                     ("PUT", f"/api/chat/sessions/{sid}", {"title": "intrusion"}),
                     ("POST", f"/api/chat/sessions/{sid}/clear", None),
                     ("DELETE", f"/api/chat/sessions/{sid}", None)]
            denied = [client.request(m, p, headers=admin, json=b).status_code for m, p, b in paths]
            answer = expect(client.post("/api/chat/ask", headers=staff, json={"session_id": sid, "content": "empty knowledge question"}))
            history = expect(client.get(f"/api/chat/sessions/{sid}/messages", headers=staff))
            expect(client.post(f"/api/chat/sessions/{sid}/clear", headers=staff))
            cleared = expect(client.get(f"/api/chat/sessions/{sid}/messages", headers=staff))
            expect(client.delete(f"/api/chat/sessions/{sid}", headers=staff))
            return denied == [404]*4 and len(history) == 2 and not cleared and answer["assistant_message"]["sources"] == [], {"cross_user_codes": denied, "history_messages": len(history), "empty_kb_refusal": answer["assistant_message"]["content"] == rag_service.NO_INFO_MESSAGE}
        run("F03", "Session CRUD, ownership isolation, history and empty-KB refusal", sessions)

        def users():
            user = create_user("functional_employee")
            auth = login(user["username"], "AuditPass123!")
            expect(client.put(f"/api/users/{user['id']}", headers=admin, json={"is_active": False}))
            disabled = client.get("/api/auth/me", headers=auth).status_code
            expect(client.put(f"/api/users/{user['id']}", headers=admin, json={"is_active": True, "role": "admin"}))
            promoted = client.get("/api/users", headers=auth).status_code
            expect(client.delete(f"/api/users/{user['id']}", headers=admin))
            deleted = client.get("/api/auth/me", headers=auth).status_code
            return [disabled, promoted, deleted] == [403, 200, 401], {"disabled_promoted_deleted": [disabled, promoted, deleted]}
        run("F04", "User create, disable, enable, role change and delete", users)

        def settings_and_logs():
            cfg = expect(client.get("/api/settings", headers=admin))
            expect(client.put("/api/settings", headers=admin, json=cfg))
            invalid = client.put("/api/settings", headers=admin, json={**cfg, "top_k": 0}).status_code
            logs = expect(client.get("/api/settings/logs?module=AUTH&page_size=2", headers=admin))
            return invalid == 422 and all(x["module"] == "AUTH" for x in logs["items"]) and len(logs["items"]) <= 2, {"invalid_top_k": invalid, "log_total": logs["total"]}
        run("F05", "Configuration roundtrip, numeric validation and log filtering", settings_and_logs)

        def formats():
            from docx import Document as WordDocument
            from pypdf import PdfWriter
            from pypdf.generic import DictionaryObject, NameObject, DecodedStreamObject
            word = WordDocument()
            word.add_paragraph("Annual leave policy: employees receive 12 days.")
            word.add_table(rows=1, cols=1).cell(0, 0).text = "Table audit content"
            word_bytes = io.BytesIO()
            word.save(word_bytes)
            writer = PdfWriter()
            page = writer.add_blank_page(width=612, height=792)
            font = DictionaryObject({NameObject("/Type"): NameObject("/Font"), NameObject("/Subtype"): NameObject("/Type1"), NameObject("/BaseFont"): NameObject("/Helvetica")})
            page[NameObject("/Resources")] = DictionaryObject({NameObject("/Font"): DictionaryObject({NameObject("/F1"): writer._add_object(font)})})
            stream = DecodedStreamObject()
            stream.set_data(b"BT /F1 12 Tf 72 720 Td (PDF audit policy content) Tj ET")
            page[NameObject("/Contents")] = writer._add_object(stream)
            pdf_bytes = io.BytesIO()
            writer.write(pdf_bytes)
            fixtures = [("audit.txt", "员工年休假为十二天。".encode()), ("audit.md", "# 报销制度\n住宿费上限五百元。".encode()),
                        ("audit.docx", word_bytes.getvalue()), ("audit.pdf", pdf_bytes.getvalue())]
            outcomes = []
            for name, data in fixtures:
                doc = upload(name, data)
                preview = expect(client.get(f"/api/documents/{doc['id']}/preview", headers=admin))
                vectors = count_vectors(doc["id"])
                expect(client.delete(f"/api/documents/{doc['id']}", headers=admin))
                outcomes.append(dict(format=Path(name).suffix, status=doc["status"], chunks=doc["chunk_count"], preview_chars=preview["total_chars"], deleted_vectors=count_vectors(doc["id"])))
                if doc["status"] != "completed" or not vectors or count_vectors(doc["id"]):
                    return False, outcomes
            return True, outcomes
        run("F06", "TXT/MD/DOCX/PDF upload, parse, vectorize, preview and delete", formats)

        def bad_uploads():
            unsupported = client.post("/api/documents/upload", headers=admin, files={"file": ("test.exe", b"test")}).status_code
            oversized = client.post("/api/documents/upload", headers=admin, files={"file": ("large.txt", b"x" * (20*1024*1024+1))}).status_code
            empty = upload("empty.txt", b"")
            broken = upload("broken.pdf", b"not a pdf")
            return unsupported == oversized == 400 and empty["status"] == broken["status"] == "failed", {"unsupported": unsupported, "oversized": oversized, "empty_status": empty["status"], "broken_pdf_status": broken["status"]}
        run("F07", "Unsupported/oversized/empty/corrupt uploads", bad_uploads)

        def forged_token():
            forged = jwt.encode({"sub": "admin"}, config.settings.SECRET_KEY, algorithm="HS256")
            response = client.get("/api/users", headers={"Authorization": "Bearer " + forged})
            return response.status_code == 401, {"token_has_exp": False, "admin_route_http": response.status_code}
        run("S01", "Known default JWT key permits forged administrator tokens without expiry", forged_token, True)

        def token_invalidation():
            user = create_user("token_lifecycle")
            auth = login(user["username"], "AuditPass123!")
            expect(client.post("/api/auth/logout", headers=auth))
            after_logout = client.get("/api/auth/me", headers=auth).status_code
            expect(client.post(f"/api/users/{user['id']}/reset-password", headers=admin, json={"new_password": "ChangedPass456!"}))
            after_reset = client.get("/api/auth/me", headers=auth).status_code
            expect(client.delete(f"/api/users/{user['id']}", headers=admin))
            create_user("token_lifecycle")
            after_recreate = client.get("/api/auth/me", headers=auth).status_code
            return [after_logout, after_reset, after_recreate] == [401]*3, {"old_token_after_logout_reset_recreate": [after_logout, after_reset, after_recreate]}
        run("S02", "Logout/password reset/account recreation do not revoke old tokens", token_invalidation, True)

        def orphan_leak():
            victim = create_user("deleted_victim")
            victim_auth = login(victim["username"], "AuditPass123!")
            secret_session = expect(client.post("/api/chat/sessions", headers=victim_auth, json={"title": "victim confidential session"}))
            with patch.object(rag_service, "answer_question", return_value={"answer": "victim confidential answer", "sources": []}):
                expect(client.post("/api/chat/ask", headers=victim_auth, json={"session_id": secret_session["id"], "content": "victim confidential question"}))
            expect(client.delete(f"/api/users/{victim['id']}", headers=admin))
            replacement = create_user("replacement_employee")
            replacement_auth = login(replacement["username"], "AuditPass123!")
            listed = expect(client.get("/api/chat/sessions", headers=replacement_auth))
            leaked = any(s["id"] == secret_session["id"] for s in listed)
            messages = client.get(f"/api/chat/sessions/{secret_session['id']}/messages", headers=replacement_auth)
            return not leaked and messages.status_code == 404, {"deleted_user_id": victim["id"], "new_user_id": replacement["id"], "old_session_visible": leaked, "old_messages_http": messages.status_code}
        run("S03", "Deleted user's chat history leaks to a newly created user via SQLite ID reuse", orphan_leak, True)

        def password_collision():
            p1, p2 = "a"*72 + "FIRST", "a"*72 + "OTHER"
            collision = verify_password(p2, get_password_hash(p1))
            return not collision, {"different_passwords_accepted_as_equal": collision, "both_allowed_by_schema": True}
        run("S04", "Passwords differing after byte 72 are silently equivalent", password_collision, True)

        def history_window():
            session = expect(client.post("/api/chat/sessions", headers=staff, json={"title": "history audit"}))
            with SessionLocal() as db:
                for i in range(10):
                    db.add(ChatMessage(session_id=session["id"], role="user" if i % 2 == 0 else "assistant", content=f"history-{i}", created_at=datetime(2020, 1, 1) + timedelta(seconds=i)))
                row = db.get(ChatSession, session["id"])
                row.updated_at = datetime(2020, 1, 1)
                db.commit()
            with patch.object(rag_service, "answer_question", return_value={"answer": "ok", "sources": []}) as mocked:
                expect(client.post("/api/chat/ask", headers=staff, json={"session_id": session["id"], "content": "next question"}))
                actual = [m["content"] for m in mocked.call_args.kwargs["chat_history"]]
            with SessionLocal() as db:
                updated = db.get(ChatSession, session["id"]).updated_at
            return actual == [f"history-{i}" for i in range(4, 10)], {"actual_history": actual, "expected_history": [f"history-{i}" for i in range(4, 10)], "session_updated_at_after_new_messages": updated.isoformat()}
        run("L01", "Multi-turn RAG reads oldest six messages; session update time stays stale", history_window, True)

        def invalid_session():
            result = client.post("/api/chat/ask", headers=staff, json={"session_id": 987654, "content": "stale session"})
            return result.status_code == 404, {"invalid_session_http": result.status_code, "created_replacement_session": result.json().get("session_id")}
        run("L02", "Invalid supplied chat session silently creates a replacement", invalid_session, True)

        def rag_failure():
            session = expect(client.post("/api/chat/sessions", headers=staff, json={"title": "failure audit"}))
            with patch.object(rag_service, "answer_question", side_effect=RuntimeError("audit backend internal path")):
                response = client.post("/api/chat/ask", headers=staff, json={"session_id": session["id"], "content": "retry question"})
            messages = expect(client.get(f"/api/chat/sessions/{session['id']}/messages", headers=staff))
            with patch.object(rag_service, "answer_question", return_value={"answer": "retry succeeds", "sources": []}):
                expect(client.post("/api/chat/ask", headers=staff, json={"session_id": session["id"], "content": "retry question"}))
            retried = expect(client.get(f"/api/chat/sessions/{session['id']}/messages", headers=staff))
            return not messages, {"http": response.status_code, "messages_after_failure": len(messages), "user_messages_after_retry": sum(m["role"] == "user" for m in retried), "raw_exception_exposed": "audit backend internal path" in response.text}
        run("L03", "RAG failure leaves orphan question; retry duplicates it and exception leaks", rag_failure, True)

        def invalid_chunk_configuration():
            cfg = expect(client.get("/api/settings", headers=admin))
            response = client.put("/api/settings", headers=admin, json={**cfg, "chunk_size": 100, "chunk_overlap": 500})
            doc = upload("bad_chunk_config.txt", "考勤打卡时间为九点。".encode())
            expect(client.put("/api/settings", headers=admin, json=cfg))
            return response.status_code == 422, {"save_http": response.status_code, "new_document_status": doc["status"], "error": doc["error_msg"]}
        run("L04", "Overlap larger than chunk size is saved and breaks document processing", invalid_chunk_configuration, True)

        def embedding_switch():
            vector_service.clear_all()
            doc = LCDocument(page_content="公司年假政策", metadata={"document_id": 99901, "chunk_index": 0})
            vector_service.add_documents([doc])
            class DifferentDimension(HashFallbackEmbeddings):
                def __init__(self):
                    super().__init__(dimension=768)
            try:
                with patch.object(vector_service, "get_embeddings_model", return_value=DifferentDimension()):
                    vector_service.similarity_search_with_score("公司年假政策")
                error = None
            except Exception as exc:
                error = f"{type(exc).__name__}: {exc}"
            vector_service.clear_all()
            return error is None, {"indexed_dimension": 384, "query_dimension": 768, "error": error}
        run("L05", "Changing/restoring embedding model breaks queries against existing collection", embedding_switch, True)

        def large_batch():
            max_batch = vector_service.chroma_client.get_max_batch_size()
            docs = [LCDocument(page_content="测试", metadata={"document_id": 99902, "chunk_index": i}) for i in range(max_batch + 1)]
            try:
                vector_service.add_documents(docs)
                error = None
            except Exception as exc:
                error = str(exc)
            vector_service.clear_all()
            return error is None, {"chroma_max_batch": max_batch, "submitted_chunks": len(docs), "error": error}
        run("L06", "Large supported documents exceed Chroma batch limit", large_batch, True)

        def vector_delete_failure():
            doc = upload("delete_failure.txt", "机密资料删除验证。".encode())
            broken_collection = Mock()
            broken_collection.delete.side_effect = RuntimeError("simulated vector deletion failure")
            with patch.object(vector_service, "get_collection", return_value=broken_collection):
                response = client.delete(f"/api/documents/{doc['id']}", headers=admin)
            remaining = count_vectors(doc["id"])
            vector_service.delete_by_document_id(doc["id"])
            return response.status_code != 200 and remaining == 0, {"delete_http": response.status_code, "deleted_document_vectors_remaining": remaining}
        run("L07", "Vector deletion errors swallowed while API claims complete deletion", vector_delete_failure, True)

        def reindex_failure():
            doc = upload("reindex_failure.txt", "重新向量化保留原有知识测试。".encode())
            old = count_vectors(doc["id"])
            with patch.object(vector_service, "add_documents", side_effect=RuntimeError("simulated embedding failure")):
                response = client.post(f"/api/documents/{doc['id']}/reindex", headers=admin)
            remaining = count_vectors(doc["id"])
            state = next(x for x in expect(client.get("/api/documents", headers=admin)) if x["id"] == doc["id"])
            return remaining == old, {"submit_http": response.status_code, "vectors_before": old, "vectors_after_failure": remaining, "status": state["status"], "recorded_chunks": state["chunk_count"]}
        run("L08", "Failed reindex destroys previous vectors and leaves stale chunk count", reindex_failure, True)

        def clear_failure():
            doc = upload("clear_failure.txt", "向量库清空失败验证。".encode())
            with patch.object(vector_service.chroma_client, "delete_collection", side_effect=RuntimeError("simulated storage failure")):
                response = client.post("/api/documents/chroma/clear", headers=admin)
            remaining = count_vectors(doc["id"])
            state = next(x for x in expect(client.get("/api/documents", headers=admin)) if x["id"] == doc["id"])
            return response.status_code != 200, {"clear_http": response.status_code, "vectors_remaining": remaining, "recorded_chunks": state["chunk_count"], "document_status": state["status"]}
        run("L09", "Vector clear failure reported as success and DB state becomes inaccurate", clear_failure, True)

        def scanned_pdf():
            from pypdf import PdfWriter
            writer = PdfWriter()
            writer.add_blank_page(width=612, height=792)
            buffer = io.BytesIO()
            writer.write(buffer)
            doc = upload("no_text.pdf", buffer.getvalue())
            return doc["status"] == "failed", {"textless_pdf_status": doc["status"], "chunks": doc["chunk_count"]}
        run("L10", "Textless/scanned PDF placeholder is indexed and reported as successful", scanned_pdf, True)

        def csv_export():
            with patch.object(rag_service, "answer_question", return_value={"answer": "CSV answer", "sources": []}):
                result = expect(client.post("/api/chat/ask", headers=staff, json={"content": "=1+1"}))
            response = client.get(f"/api/chat/export?session_id={result['session_id']}", headers=staff)
            expect_code = response.status_code == 200
            rows = list(csv.reader(io.StringIO(response.content.decode("utf-8-sig"))))
            double_bom = response.content.startswith(b"\xef\xbb\xbf" * 2)
            formula_cells = [c for row in rows[1:] for c in row if c.startswith(("=", "+", "-", "@"))]
            return expect_code and not double_bom and not formula_cells, {"http": response.status_code, "double_bom": double_bom, "first_header": repr(rows[0][0]), "unescaped_formula_cells": formula_cells}
        run("S05", "CSV export retains formulas and writes two BOMs", csv_export, True)

        def unicode_export():
            user = create_user("中文员工")
            auth = login(user["username"], "AuditPass123!")
            response = client.get("/api/chat/export", headers=auth)
            return response.status_code == 200, {"unicode_username_export_http": response.status_code, "detail": response.json() if response.status_code != 200 else "ok"}
        run("L11", "Allowed Chinese username makes CSV download fail with HTTP 500", unicode_export, True)

        def self_demote():
            response = client.put("/api/users/1", headers=admin, json={"role": "employee"})
            with SessionLocal() as db:
                count = db.query(User).filter(User.role == "admin", User.is_active.is_(True)).count()
                user = db.get(User, 1)
                user.role = "admin"
                db.commit()
            return response.status_code == 400 and count >= 1, {"self_demotion_http": response.status_code, "remaining_active_admins": count}
        run("L12", "Last administrator can demote themselves and lock out administration", self_demote, True)

        # Evaluate the actual supplied demo corpus, using real parsing, chunking, Chroma and offline RAG.
        def demo_corpus():
            vector_service.clear_all()
            docs = []
            for file in (ROOT / "backend/data/demo_docs").glob("*.md"):
                docs.append(upload(file.name, file.read_bytes()))
            cases = [("员工每年的年休假有几天？", ["5 天", "10 天", "15 天"]),
                     ("员工账号密码的安全复杂度规范是什么？", ["12", "大写", "小写"]),
                     ("内部研发代码是否可以上传到外部公开仓库？", ["严禁", "源代码"])]
            outcomes = []
            for question, required_facts in cases:
                result = rag_service.answer_question(question)
                outcomes.append({"question": question, "has_sources": bool(result["sources"]),
                                 "required_facts": required_facts, "answer_has_required_facts": all(fact in result["answer"] for fact in required_facts), "answer": result["answer"]})
            return len(docs) >= 2 and all(o["has_sources"] and o["answer_has_required_facts"] for o in outcomes), outcomes
        run("L16", "Offline answers omit required facts from the supplied demo policy documents", demo_corpus, True)

        def unrelated_questions():
            outcomes = []
            for question in ["量子计算机的购买价格是多少？", "法国首都在哪里？", "公司一二线城市的出差住宿报销标准是多少？", "公司员工考勤的弹性打卡时间是多久？"]:
                result = rag_service.answer_question(question)
                outcomes.append({"question": question, "refused": result["answer"] == rag_service.NO_INFO_MESSAGE, "sources": [s["filename"] for s in result["sources"]], "answer": result["answer"]})
            # First two definitely have no answer in these enterprise policy files.
            return all(o["refused"] for o in outcomes[:2]), outcomes
        run("L13", "Unrelated queries and advertised quick questions in offline RAG", unrelated_questions, True)

        def repeated_reindex():
            doc = upload("concurrent_reindex.txt", "并发重建任务检测。".encode())
            with patch("app.api.documents.process_document_task") as task:
                first = client.post(f"/api/documents/{doc['id']}/reindex", headers=admin)
                second = client.post(f"/api/documents/{doc['id']}/reindex", headers=admin)
            return second.status_code == 409, {"first_http": first.status_code, "second_while_processing_http": second.status_code, "tasks_started": task.call_count}
        run("L14", "Repeated reindex starts overlapping jobs for the same document", repeated_reindex, True)

        def malicious_offline_content():
            context = '<img src=x onerror="globalThis.__audit_xss=1"> 年假为5天。'
            result = rag_service._fallback_extract_answer("年假几天", context,
                [{"filename": "policy.md", "document_id": 1, "chunk_index": 0}])
            return "onerror" not in result, {"untrusted_html_in_answer": "onerror" in result, "answer": result}
        run("S06", "Document HTML reaches an assistant answer through the offline extraction path", malicious_offline_content, True)

        def ollama_https_override():
            cfg = expect(client.get("/api/settings", headers=admin))
            expect(client.put("/api/settings", headers=admin,
                              json={**cfg, "llm_provider": "ollama", "llm_base_url": "https://private-ollama.example"}))
            actual = expect(client.get("/api/settings", headers=admin))["llm_provider"]
            expect(client.put("/api/settings", headers=admin, json=cfg))
            return actual == "ollama", {"selected_provider": "ollama", "saved_provider_for_https_ollama": actual}
        run("L15", "HTTPS Ollama endpoint silently switches to incompatible OpenAI protocol", ollama_https_override, True)

        client.close()
        engine.dispose()
        vector_service.chroma_client.close()
    after = fingerprints()
    run("F09", "Original SQL database, uploads and logical vector records unchanged", lambda: (before == after, {"files_or_logical_tables_checked": len(before), "changed_entries": [name for name in before if before[name] != after.get(name)]}))

    # Read-only deployed-data checks; do not return secrets, password hashes or chat contents.
    conn = sqlite3.connect(f"file:{(ROOT / 'backend/data/rag_system.db').as_posix()}?mode=ro", uri=True)
    deployed = {"users": [], "documents": []}
    for username, password_hash, role, active in conn.execute("SELECT username, password_hash, role, is_active FROM users"):
        default = {"admin": "admin123", "staff": "staff123"}.get(username)
        deployed["users"].append({"username": username, "role": role, "active": bool(active), "uses_published_default_password": bool(default and verify_password(default, password_hash))})
    for filename, file_path, status, chunk_count in conn.execute("SELECT filename, file_path, status, chunk_count FROM documents"):
        deployed["documents"].append({"filename": filename, "status": status, "chunks": chunk_count, "source_file_exists": Path(file_path).is_file()})
    conn.close()
    summary = {status: sum(r["status"] == status for r in RESULTS) for status in ["PASS", "ISSUE", "FAIL", "ERROR"]}
    sources_after = source_fingerprints()
    source_changes = [name for name in sources_before if sources_before[name] != sources_after.get(name)]
    report = {"summary": summary, "model_mode": "real Chroma + hash embedding; LLM calls mocked offline",
              "source_changes_during_run": source_changes, "source_sha256": sources_before,
              "results": RESULTS, "deployed_read_only": deployed}
    destination = ROOT / "docs/audit-backend-results.json"
    destination.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary))
    return int(bool(summary["FAIL"] or summary["ERROR"] or source_changes))


if __name__ == "__main__":
    raise SystemExit(main())
