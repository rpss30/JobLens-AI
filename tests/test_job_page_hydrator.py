import requests

from src.ingestion.job_page_hydrator import (
    JobPageHydrationResult,
    extract_visible_job_text,
    hydrate_job_page,
)


def test_extract_visible_job_text_skips_script_style_and_navigation() -> None:
    html = """
    <html>
      <head><title>Hidden title</title></head>
      <body>
        <nav>Navigation should disappear</nav>
        <script>const secret = "python";</script>
        <style>.hidden { color: red; }</style>
        <main>
          <h1>Software Engineer New Grad</h1>
          <p>Build APIs with Python and SQL.</p>
          <ul><li>Work with Docker.</li></ul>
        </main>
      </body>
    </html>
    """

    text = extract_visible_job_text(html)

    assert "Software Engineer New Grad" in text
    assert "Build APIs with Python and SQL." in text
    assert "Work with Docker." in text
    assert "Navigation should disappear" not in text
    assert "secret" not in text
    assert ".hidden" not in text


def test_hydrate_job_page_returns_fallback_for_short_static_text(monkeypatch) -> None:
    class FakeResponse:
        status_code = 200
        text = "<html><body><p>Enable JavaScript.</p></body></html>"

        def raise_for_status(self) -> None:
            return None

    monkeypatch.setattr(
        requests,
        "get",
        lambda *args, **kwargs: FakeResponse(),
    )

    result = hydrate_job_page(
        "https://example.com/job",
        min_text_chars=50,
    )

    assert isinstance(result, JobPageHydrationResult)
    assert result.provider == "source_index_fallback"
    assert result.status_code == 200
    assert "not expose enough static job text" in result.error
