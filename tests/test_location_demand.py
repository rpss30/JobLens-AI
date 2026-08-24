import pandas as pd

from src.analysis.location_demand import summarize_location_demand


def summarize(locations: list[str], **columns) -> object:
    frame = pd.DataFrame({"location": locations, **columns})
    return summarize_location_demand(frame)


def counts(summary) -> dict[str, int]:
    return {row["location"]: row["job_count"] for row in summary.locations}


def test_workplace_types_leave_the_location_ranking():
    # "Hybrid" outranked every real city while it was counted as a place.
    # Remote is the exception: it is somewhere a job can be done from, so it
    # stays a place, while hybrid only says how the work happens.
    summary = summarize(["Hybrid", "Hybrid", "Toronto, ON", "Remote, Canada"])

    assert "Hybrid" not in counts(summary)
    assert counts(summary)["Toronto, ON"] == 1
    assert counts(summary)["Remote, Canada"] == 1
    assert "Canada" not in counts(summary)
    assert summary.postings_without_location == 2

    workplace = {row["workplace_type"]: row["job_count"] for row in summary.workplace_types}

    assert workplace["Hybrid"] == 2
    assert workplace["Remote"] == 1


def test_a_posting_counts_once_for_every_site_it_lists():
    summary = summarize([
        "San Francisco, CA | New York City, NY",
        "New York City, NY; Seattle, WA",
        "Dublin, London",
    ])

    assert counts(summary)["New York, NY"] == 2
    assert counts(summary)["San Francisco, CA"] == 1
    assert counts(summary)["Seattle, WA"] == 1
    # Comma separates two cities here, rather than qualifying one.
    assert counts(summary)["Dublin"] == 1
    assert counts(summary)["London"] == 1


def test_one_city_written_several_ways_is_counted_once():
    summary = summarize([
        "San Francisco, CA",
        "San Francisco, California",
        "San Francisco, California, USA",
        "San Francisco",
        # A city list, not a city in a state: this must not make San
        # Francisco a New York city.
        "Seattle, San Francisco, New York",
    ])

    assert counts(summary)["San Francisco, CA"] == 5
    assert counts(summary)["New York"] == 1


def test_contested_cities_are_left_apart():
    summary = summarize([
        "London, ON",
        "London, ON",
        "London, United Kingdom",
        "London, United Kingdom",
        "London",
    ])

    # Nothing says which London a bare mention meant, so it stays its own row.
    assert counts(summary)["London"] == 1
    assert counts(summary)["London, ON"] == 2
    assert counts(summary)["London, United Kingdom"] == 2


def test_remote_work_keeps_the_country_it_is_scoped_to():
    summary = summarize(["Remote - USA", "Remote: India", "Brazil - Remote", "Remote"])

    assert counts(summary)["Remote, United States"] == 1
    assert counts(summary)["Remote, India"] == 1
    assert counts(summary)["Remote, Brazil"] == 1
    # Remote with no country named is still somewhere a job is done from.
    assert counts(summary)["Remote"] == 1
    assert summary.postings_without_location == 0


def test_declared_workplace_columns_win_over_the_location_text():
    summary = summarize(
        ["Vancouver, BC", "Toronto, ON"],
        workplace_type=["Hybrid", ""],
        is_remote=[False, True],
    )

    workplace = {row["workplace_type"]: row["job_count"] for row in summary.workplace_types}

    assert workplace["Hybrid"] == 1
    assert workplace["Remote"] == 1
    # Both are still real places; how the work is done is a separate question.
    assert counts(summary) == {"Vancouver, BC": 1, "Toronto, ON": 1}


def test_a_region_written_without_a_comma_still_counts():
    # The local sample writes "Toronto ON"; the Canada snapshot writes
    # "Toronto, ON". They are the same place and must not rank separately.
    summary = summarize(["Toronto ON", "Toronto, ON", "Kitchener on the lake"])

    assert counts(summary)["Toronto, ON"] == 2
    # "on" here is the English word, not Ontario.
    assert "Kitchener On The Lake" not in counts(summary)
    assert counts(summary)["Kitchener on the lake"] == 1


def test_a_posting_that_never_says_is_not_called_on_site():
    summary = summarize(["Bengaluru, India"])

    assert summary.workplace_types == [{"workplace_type": "Not stated", "job_count": 1}]
