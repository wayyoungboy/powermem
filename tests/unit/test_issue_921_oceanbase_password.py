import sys
from unittest.mock import MagicMock

if "pyobvector" not in sys.modules:
    sys.modules["pyobvector"] = MagicMock()
    sys.modules["pyobvector"].ObVecClient = MagicMock()
    sys.modules["pyobvector"].VECTOR = MagicMock()
    sys.modules["pyobvector"].SPARSE_VECTOR = MagicMock()
    sys.modules["pyobvector"].cosine_distance = MagicMock()
    sys.modules["pyobvector"].inner_product = MagicMock()
    sys.modules["pyobvector"].l2_distance = MagicMock()
    sys.modules["pyobvector"].VecIndexType = MagicMock(
        HNSW="HNSW",
        HNSW_SQ="HNSW_SQ",
        IVFFLAT="IVFFLAT",
        IVFSQ="IVFSQ",
        IVFPQ="IVFPQ",
    )
    sys.modules["pyobvector"].FtsIndexParam = MagicMock()
    sys.modules["pyobvector"].FtsParser = MagicMock()
    sys.modules["pyobvector.client"] = MagicMock()
    sys.modules["pyobvector.client.index_param"] = MagicMock()
    sys.modules["pyobvector.client.index_param"].IndexParams = MagicMock()
    sys.modules["pyobvector.client.fts_index_param"] = MagicMock()
    sys.modules["pyobvector.client.fts_index_param"].FtsIndexParam = MagicMock()
    sys.modules["pyobvector.client.partitions"] = MagicMock()
    sys.modules["pyobvector.client.partitions"].ObPartition = MagicMock()
    sys.modules["pyobvector.schema"] = MagicMock()
    sys.modules["pyobvector.schema"].ReplaceStmt = MagicMock()

import powermem.config_loader as config_loader
import powermem.settings as settings
from powermem.config_loader import load_config_from_env
from powermem.storage.oceanbase.oceanbase import OceanBaseVectorStore
from powermem.utils.strings import strip_wrapping_quotes


def _disable_env_file(monkeypatch):
    monkeypatch.setattr(config_loader, "_DEFAULT_ENV_FILE", None, raising=False)
    monkeypatch.setattr(settings, "_DEFAULT_ENV_FILE", None, raising=False)


def test_oceanbase_password_strips_wrapping_quotes_from_env(monkeypatch):
    _disable_env_file(monkeypatch)
    monkeypatch.setenv("DATABASE_PROVIDER", "oceanbase")
    monkeypatch.setenv("OCEANBASE_PASSWORD", "'powermem'")

    config = load_config_from_env()

    vector_config = config["vector_store"]["config"]
    assert vector_config["password"] == "powermem"
    assert vector_config["connection_args"]["password"] == "powermem"


def test_oceanbase_vector_store_strips_wrapping_quotes_from_connection_args(monkeypatch):
    monkeypatch.setattr(
        OceanBaseVectorStore,
        "_create_client",
        lambda self, **kwargs: setattr(self, "obvector", MagicMock()),
    )
    monkeypatch.setattr(OceanBaseVectorStore, "_create_col", lambda self: None)

    store = OceanBaseVectorStore(
        collection_name="memories",
        connection_args={"password": '"powermem"'},
    )

    assert store.connection_args["password"] == "powermem"


def test_strip_wrapping_quotes_uses_trimmed_length_for_detection():
    assert strip_wrapping_quotes(" ' ") == " ' "


def test_strip_wrapping_quotes_documents_literal_quote_tradeoff():
    assert strip_wrapping_quotes("'quoted-password'") == "quoted-password"
