import os

import pytest

from scripts.verify_week3 import run_verification


@pytest.mark.real_model
@pytest.mark.skipif(
    os.getenv("RUN_REAL_MODEL_TESTS") != "1",
    reason="set RUN_REAL_MODEL_TESTS=1 after downloading the official buffalo_s model",
)
def test_real_image_embedding_persists_and_matches_through_api(tmp_path) -> None:
    database_url = f"sqlite:///{(tmp_path / 'real-e2e.db').as_posix()}"

    result = run_verification(database_url)

    assert result["model"] == "buffalo_s"
    assert result["embedding_dim"] == 512
    assert result["embedding_dtype"] == "float32"
    assert result["embedding_norm"] == pytest.approx(1.0, abs=1e-5)
    assert result["profile_persisted"] is True
    assert result["check_in_status"] == "success"
    assert result["similarity_score"] == pytest.approx(1.0, abs=1e-4)
    assert result["no_face_http_status"] == 422
    assert result["persisted_statuses"] == ["no_face", "success"]
    assert result["user_history_statuses"] == ["success"]
    assert result["admin_login_http_status"] == 200
    assert result["user_login_http_status"] == 200
    assert result["auth_me_http_status"] == 200
    assert result["invalid_token_http_status"] == 401
    assert result["rbac_forbidden_http_status"] == 403
