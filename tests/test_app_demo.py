from datetime import date
from pathlib import Path
import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

import app_demo
from src.ui.demo_service import DEMO_SCENARIOS

APP_DEMO_PATH = str(Path(__file__).resolve().parent.parent / "app_demo.py")


def test_import_and_constants():
    assert hasattr(app_demo, "main")
    assert hasattr(app_demo, "get_risk_badge_color")
    assert hasattr(app_demo, "get_benchmark_metrics_df")
    assert hasattr(app_demo, "find_doc_id_for_article")
    assert hasattr(app_demo, "check_ollama_available")
    assert "P3_FullSystem (Đề xuất)" in app_demo.PIPELINE_MAP
    assert "P2_TemporalGraphRAG" in app_demo.PIPELINE_MAP
    assert "P1_FlatRAG (Baseline)" in app_demo.PIPELINE_MAP


def test_get_risk_badge_color():
    assert app_demo.get_risk_badge_color(0) == "#2b8a3e"
    assert app_demo.get_risk_badge_color(20) == "#2b8a3e"
    assert app_demo.get_risk_badge_color(21) == "#e67700"
    assert app_demo.get_risk_badge_color(50) == "#e67700"
    assert app_demo.get_risk_badge_color(51) == "#d9480f"
    assert app_demo.get_risk_badge_color(75) == "#d9480f"
    assert app_demo.get_risk_badge_color(76) == "#c92a2a"
    assert app_demo.get_risk_badge_color(100) == "#c92a2a"


def test_get_benchmark_metrics_df():
    df = app_demo.get_benchmark_metrics_df()
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 3
    for col in ("Pipeline", "P", "R", "Acc_temp"):
        assert col in df.columns
    assert "P1_FlatRAG (Baseline)" in df["Pipeline"].values
    assert "P2_TemporalGraphRAG" in df["Pipeline"].values
    assert "P3_FullSystem (Đề xuất)" in df["Pipeline"].values


def test_find_doc_id_for_article():
    sample_corpus = [
        {
            "id": "LUAT_48_2024",
            "articles": [{"id": "LUAT_48_2024_D9"}],
            "chapters": [],
        },
        {
            "id": "ND_181_2025",
            "articles": [],
            "chapters": [{"articles": [{"id": "ND_181_2025_D9"}]}],
        },
    ]
    assert app_demo.find_doc_id_for_article("LUAT_48_2024_D9", sample_corpus) == "LUAT_48_2024"
    assert app_demo.find_doc_id_for_article("ND_181_2025_D9", sample_corpus) == "ND_181_2025"
    assert app_demo.find_doc_id_for_article("UNKNOWN_ART", sample_corpus) is None


def test_apptest_initial_render():
    at = AppTest.from_file(APP_DEMO_PATH).run()
    assert len(at.exception) == 0
    assert len(at.sidebar.selectbox) == 1
    assert len(at.sidebar.radio) == 1
    assert len(at.sidebar.checkbox) == 1
    assert at.sidebar.checkbox[0].value is False
    assert len(at.text_area) == 1
    assert at.text_area[0].value == DEMO_SCENARIOS[0]["query"]
    assert at.date_input[0].value == date.fromisoformat(DEMO_SCENARIOS[0]["as_of_date"])


def test_apptest_switch_scenario():
    at = AppTest.from_file(APP_DEMO_PATH).run()
    assert len(at.exception) == 0
    at.sidebar.selectbox[0].select_index(1).run()
    assert len(at.exception) == 0
    assert at.text_area[0].value == DEMO_SCENARIOS[1]["query"]
    assert at.date_input[0].value == date.fromisoformat(DEMO_SCENARIOS[1]["as_of_date"])


def test_apptest_ollama_toggle_offline(monkeypatch):
    monkeypatch.setattr("src.engine.llm_client.check_ollama_available", lambda: False)
    at = AppTest.from_file(APP_DEMO_PATH).run()
    assert len(at.exception) == 0
    at.sidebar.checkbox[0].check().run()
    assert len(at.exception) == 0
    assert at.sidebar.checkbox[0].value is True
    warnings = [w.value for w in at.sidebar.warning]
    assert any("Ollama chưa bật (fallback về Tất định an toàn)" in w for w in warnings)


def test_apptest_run_pipeline_execution():
    at = AppTest.from_file(APP_DEMO_PATH, default_timeout=15).run(timeout=15)
    assert len(at.exception) == 0
    at.button[0].click().run(timeout=15)
    assert len(at.exception) == 0
    assert len(at.download_button) == 1
    assert len(at.tabs) == 4
    captions = [c.value for c in at.caption]
    assert any("Chế độ Tất định An toàn (Deterministic Safe Mode • 0 VNĐ)" in c for c in captions)


def test_apptest_run_pipeline_with_llm(monkeypatch):
    monkeypatch.setattr("src.engine.llm_client.check_ollama_available", lambda: True)
    monkeypatch.setattr(
        "src.ui.demo_service.generate_llm_response",
        lambda *args, **kwargs: "Issue: test\nRule: test\nApplication: test\nConclusion: test",
    )

    from src.ui import demo_service
    orig_exec = demo_service.execute_demo_query
    def mock_exec(*args, **kwargs):
        res = orig_exec(*args, **kwargs)
        res["llm_used"] = kwargs.get("use_llm", False)
        return res
    monkeypatch.setattr(demo_service, "execute_demo_query", mock_exec)

    at = AppTest.from_file(APP_DEMO_PATH, default_timeout=15).run(timeout=15)
    at.sidebar.checkbox[0].check().run(timeout=15)
    assert len(at.sidebar.success) >= 1
    assert any("Ollama Online (qwen2.5:7b)" in s.value for s in at.sidebar.success)

    at.button[0].click().run(timeout=15)
    assert len(at.exception) == 0
    captions = [c.value for c in at.caption]
    assert any("Lập luận tự nhiên sinh bởi Ollama Local (qwen2.5:7b) • Đã qua chốt chặn Verifier" in c for c in captions)


def test_handle_run_pipeline_llm_flag(monkeypatch):
    called_kwargs = {}
    def mock_exec(*args, **kwargs):
        called_kwargs.update(kwargs)
        return {
            "query": "test",
            "as_of_date": "2025-01-01",
            "pipeline": "P3_FullSystem",
            "citations": [],
            "active_article_ids": [],
            "risk_score": 0,
            "risk_level": "LOW",
            "warnings": [],
            "irac_sections": {},
            "llm_used": kwargs.get("use_llm", False),
            "raw_llm_response": None,
        }

    monkeypatch.setattr(app_demo, "execute_demo_query", mock_exec)
    app_demo.st.session_state["query_input"] = "Test query"
    app_demo.st.session_state["as_of_date_input"] = date(2025, 1, 1)

    app_demo.handle_run_pipeline([], "P3_FullSystem", use_llm=True)
    assert called_kwargs.get("use_llm") is True
    assert called_kwargs.get("model") == "qwen2.5:7b"

    app_demo.handle_run_pipeline([], "P3_FullSystem", use_llm=False)
    assert called_kwargs.get("use_llm") is False
    assert called_kwargs.get("model") == "qwen2.5:7b"
