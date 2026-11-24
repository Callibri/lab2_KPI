from datetime import date

import pytest

from boxoffice.application.use_cases import (
    AddReport, CreateMovie, DeleteMovie, GetMovieSummary, GetTopMovies, ListReports, LoginUser,
    RegisterUser, UpdateMovie, UpdateReport,
)
from boxoffice.domain.errors import AuthenticationError, ConflictError, NotFoundError
from boxoffice.domain.factories import MovieFactory, ReportFactory, UserFactory
from tests.fakes import (
    FakeHasher, FakeTokens, InMemoryMovieRepository, InMemoryReportRepository,
    InMemoryUserRepository,
)

TODAY = date(2024, 6, 1)


@pytest.fixture()
def env():
    movies, reports, users = InMemoryMovieRepository(), InMemoryReportRepository(), InMemoryUserRepository()
    return dict(movies=movies, reports=reports, users=users,
                movie_factory=MovieFactory(movies),
                report_factory=ReportFactory(reports, today=lambda: TODAY))


def new_movie(env, title="Dune", release=date(2024, 3, 1), budget=1000):
    return CreateMovie(env["movie_factory"], env["movies"]).execute(title, "Sci-Fi", release, budget)


def test_register_and_login(env):
    hasher, tokens = FakeHasher(), FakeTokens()
    RegisterUser(UserFactory(env["users"], hasher), env["users"]).execute("a@b.com", "password1")
    login = LoginUser(env["users"], hasher, tokens)
    assert login.execute("A@b.com", "password1") == "token-1"
    for email, pwd in [("a@b.com", "wrong-pass"), ("nobody@b.com", "password1"), ("bad", "x")]:
        with pytest.raises(AuthenticationError):
            login.execute(email, pwd)


def test_create_movie_saves_and_conflicts(env):
    movie = new_movie(env)
    assert movie.id == 1 and env["movies"].add_calls == 1
    with pytest.raises(ConflictError):
        new_movie(env)
    assert env["movies"].add_calls == 1


def test_update_movie_rules(env):
    new_movie(env)
    new_movie(env, title="Barbie")
    update = UpdateMovie(env["movie_factory"], env["movies"])
    assert update.execute(1, "Dune 2", "Sci-Fi", date(2024, 3, 1), 2000).budget.amount_usd == 2000
    with pytest.raises(ConflictError):
        update.execute(2, "Dune 2", "Sci-Fi", date(2024, 3, 1), 10)
    with pytest.raises(NotFoundError):
        update.execute(99, "X", "Y", date(2024, 1, 1), 1)


def test_delete_movie(env):
    new_movie(env)
    DeleteMovie(env["movies"]).execute(1)
    assert env["movies"].get(1) is None
    with pytest.raises(NotFoundError):
        DeleteMovie(env["movies"]).execute(1)


def add_report(env, movie_id=1, day=date(2024, 3, 5), region="US", revenue=1500, tickets=100):
    return AddReport(env["movies"], env["reports"], env["report_factory"]).execute(
        movie_id, day, region, revenue, tickets)


def test_add_report_for_missing_movie(env):
    with pytest.raises(NotFoundError):
        add_report(env, movie_id=42)


def test_update_report_and_list(env):
    new_movie(env)
    add_report(env)
    add_report(env, region="UA", revenue=500, tickets=50)
    updated = UpdateReport(env["reports"]).execute(1, 1600, 110)
    assert updated.revenue.amount_usd == 1600
    lister = ListReports(env["movies"], env["reports"])
    assert len(lister.execute(1)) == 2
    assert len(lister.execute(1, region="ua")) == 1
    with pytest.raises(NotFoundError):
        lister.execute(9)


def test_summary_and_top_movies(env):
    new_movie(env)
    new_movie(env, title="Barbie", budget=200)
    add_report(env, revenue=1500, tickets=100)
    add_report(env, region="UA", revenue=500, tickets=50)
    add_report(env, movie_id=2, revenue=300, tickets=30)
    summary = GetMovieSummary(env["movies"], env["reports"]).execute(1)
    assert summary.total_revenue.amount_usd == 2000 and summary.roi == 1.0
    top = GetTopMovies(env["movies"], env["reports"]).execute(10)
    assert [t.movie.title for t in top] == ["Dune", "Barbie"] and top[1].roi == 0.5
