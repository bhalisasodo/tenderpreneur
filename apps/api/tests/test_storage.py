from pathlib import Path

import pytest

from app.integrations.storage import LocalStorageProvider


@pytest.mark.asyncio
async def test_local_storage_round_trip_and_path_safety(tmp_path: Path):
    storage = LocalStorageProvider(str(tmp_path))
    await storage.upload_file("documents/example.txt", b"durban boq")

    assert await storage.get_file("documents/example.txt") == b"durban boq"
    assert Path(storage.get_local_path("documents")).is_dir()

    await storage.delete_file("documents/example.txt")
    assert not Path(storage.get_local_path("documents/example.txt")).exists()

    with pytest.raises(ValueError):
        await storage.upload_file("../outside.txt", b"blocked")
