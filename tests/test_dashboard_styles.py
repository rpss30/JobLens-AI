import inspect

from src.dashboard.styles import inject_global_styles


def test_search_input_reserves_space_for_submit_hint() -> None:
    style_source = inspect.getsource(inject_global_styles)

    assert 'input[aria-label="Search jobs"]' in style_source
    assert "min-height: 3.75rem" in style_source
    assert "padding-bottom: 1.55rem" in style_source
    assert 'span[data-testid="stTextInputIcon"]' in style_source
    assert "height: 2.25rem" in style_source
