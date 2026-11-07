import prod


def test_health_check_reports_sqlite_backend_without_database_url(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "")
    monkeypatch.setenv("SQLITE_PATH", str(tmp_path / "smoke.db"))

    health = prod.health_check()

    assert health["backend"] == "sqlite"
    assert health["postings"] == 0
    assert any("DATABASE_URL" in warning for warning in health["warnings"])


def test_health_check_reports_postgres_backend_with_database_url(monkeypatch):
    monkeypatch.setattr(prod.job_store, "database_url", lambda: "postgresql://u:p@host/db?sslmode=require")
    monkeypatch.setattr(prod.job_store, "init_db", lambda: None)
    monkeypatch.setattr(prod.job_store, "store_available", lambda: True)
    monkeypatch.setattr(prod.job_store, "count_postings", lambda: 7)

    health = prod.health_check()

    assert health["backend"] == "postgres"
    assert health["postings"] == 7
    assert health["store_available"] is True


def test_health_check_never_leaks_secret(monkeypatch):
    secret = "postgresql://user:PA55WORD@host/db"
    monkeypatch.setattr(prod.job_store, "database_url", lambda: secret)
    monkeypatch.setattr(prod.job_store, "init_db", lambda: None)
    monkeypatch.setattr(prod.job_store, "store_available", lambda: True)
    monkeypatch.setattr(prod.job_store, "count_postings", lambda: 1)

    health = prod.health_check()

    assert "PA55WORD" not in str(health)
    assert secret not in str(health)


def test_build_streamlit_command_uses_port_and_app():
    command = prod.build_streamlit_command(host="0.0.0.0", port=7860, app_py="app.py")

    assert command[1] == "run"
    assert "app.py" in command
    assert "--server.port" in command
    assert "7860" in command


def test_main_check_only_returns_zero_without_starting_server(monkeypatch, capsys):
    monkeypatch.setattr(prod.job_store, "database_url", lambda: "")
    monkeypatch.setattr(prod.job_store, "init_db", lambda: None)
    monkeypatch.setattr(prod.job_store, "store_available", lambda: False)
    monkeypatch.setattr(prod.job_store, "count_postings", lambda: 0)
    started = []
    monkeypatch.setattr(prod, "start_streamlit", lambda host, port: started.append((host, port)))

    assert prod.main(["--check-only"]) == 0
    assert started == []
    assert "health" in capsys.readouterr().out.lower()
