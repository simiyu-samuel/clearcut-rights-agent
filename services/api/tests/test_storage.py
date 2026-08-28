from clearcut_api.storage import GcsObjectStore


class FakeBlob:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def create_resumable_upload_session(self, **kwargs: object) -> str:
        self.calls.append(kwargs)
        return "https://storage.example/upload-session"


class FakeBucket:
    name = "clearcut-assets"

    def __init__(self, blob: FakeBlob) -> None:
        self._blob = blob

    def blob(self, _: str) -> FakeBlob:
        return self._blob


def test_gcs_resumable_session_forwards_browser_origin() -> None:
    blob = FakeBlob()
    store = object.__new__(GcsObjectStore)
    store.bucket = FakeBucket(blob)  # type: ignore[assignment]

    upload_url = store.create_resumable_upload_session(
        "demo-org/project/video.media",
        "video/mp4",
        1024,
        origin="https://clearcut-web.example.run.app",
    )

    assert upload_url == "https://storage.example/upload-session"
    assert blob.calls == [
        {
            "content_type": "video/mp4",
            "size": 1024,
            "origin": "https://clearcut-web.example.run.app",
        }
    ]
