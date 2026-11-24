from datetime import date

import pytest

from boxoffice.domain.entities import BoxOfficeReport, Movie
from boxoffice.domain.errors import DomainValidationError
from boxoffice.domain.services import summarize
from boxoffice.domain.value_objects import Money, RegionCode


def make_movie(**kw):
    data = dict(title="Dune", genre="Sci-Fi", release_date=date(2024, 3, 1), budget=Money(1000))
    return Movie(**{**data, **kw})


def test_movie_title_trimmed():
    assert make_movie(title="  Dune ").title == "Dune"


@pytest.mark.parametrize("kw", [{"title": " "}, {"genre": ""}, {"budget": Money(0)}])
def test_movie_invariants(kw):
    with pytest.raises(DomainValidationError):
        make_movie(**kw)


def test_movie_update_is_atomic():
    movie = make_movie()
    with pytest.raises(DomainValidationError):
        movie.update(title="New", genre="Drama", release_date=date(2025, 1, 1), budget=Money(0))
    assert movie.title == "Dune"


def test_movie_report_date_rules():
    movie = make_movie()
    today = date(2024, 6, 1)
    movie.ensure_accepts_report_for(date(2024, 3, 5), today)
    with pytest.raises(DomainValidationError):
        movie.ensure_accepts_report_for(date(2024, 2, 1), today)
    with pytest.raises(DomainValidationError):
        movie.ensure_accepts_report_for(date(2024, 7, 1), today)


def test_report_correct_validates():
    report = BoxOfficeReport(1, date(2024, 3, 5), RegionCode("US"), Money(10), 1)
    report.correct(revenue=Money(20), tickets_sold=2)
    assert (report.revenue, report.tickets_sold) == (Money(20), 2)
    with pytest.raises(DomainValidationError):
        report.correct(revenue=Money(5), tickets_sold=-1)
    assert report.tickets_sold == 2


def test_summarize():
    movie = make_movie(budget=Money(1000))
    movie.id = 1
    reports = [
        BoxOfficeReport(1, date(2024, 3, 5), RegionCode("US"), Money(1500), 100),
        BoxOfficeReport(1, date(2024, 3, 5), RegionCode("UA"), Money(500), 50),
    ]
    s = summarize(movie, reports)
    assert s.total_revenue == Money(2000) and s.total_tickets == 150
    assert s.avg_ticket_price_usd == 13.33 and s.roi == 1.0
    assert s.revenue_by_region == [("US", 1500), ("UA", 500)]


def test_summarize_empty():
    s = summarize(make_movie(), [])
    assert s.total_tickets == 0 and s.avg_ticket_price_usd is None and s.roi == -1.0
