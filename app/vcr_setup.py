import os
from typing import Any


class _VCRContext:
    def __init__(self) -> None:
        self.cassette: Any | None = None

    def start(self) -> None:
        if os.environ.get("USE_VCR") != "true":
            return

        import vcr

        vcr_e2e = vcr.VCR(
            cassette_library_dir="e2e/e2e_cassettes",
            record_mode="once",
            match_on=["uri", "method"],
            filter_headers=["Authorization"],
        )
        self.cassette = vcr_e2e.use_cassette("e2e_weather_mocks.yaml", allow_playback_repeats=True)
        self.cassette.__enter__()

    def stop(self) -> None:
        if self.cassette is not None:
            self.cassette.__exit__(None, None, None)
            self.cassette = None


vcr_context = _VCRContext()


def apply_vcr_if_e2e() -> None:
    """Activates VCR if USE_VCR env var is true."""
    vcr_context.start()


def stop_vcr() -> None:
    vcr_context.stop()
