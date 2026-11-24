from dataclasses import dataclass
from datetime import date

from boxoffice.application.ports import TokenService
from boxoffice.domain.entities import BoxOfficeReport, Movie, User
from boxoffice.domain.errors import AuthenticationError, DomainValidationError, NotFoundError
from boxoffice.domain.factories import MovieFactory, ReportFactory, UserFactory
from boxoffice.domain.ports import PasswordHasher
from boxoffice.domain.repositories import (
    MovieRepository,
    RegionTotal,
    ReportRepository,
    UserRepository,
)
from boxoffice.domain.services import MovieSummary, roi, summarize
from boxoffice.domain.value_objects import Email, Money, RegionCode


def _movie_or_404(movies: MovieRepository, movie_id: int) -> Movie:
    movie = movies.get(movie_id)
    if movie is None:
        raise NotFoundError("Movie not found")
    return movie


def _report_or_404(reports: ReportRepository, report_id: int) -> BoxOfficeReport:
    report = reports.get(report_id)
    if report is None:
        raise NotFoundError("Report not found")
    return report


class RegisterUser:
    def __init__(self, factory: UserFactory, users: UserRepository):
        self._factory, self._users = factory, users

    def execute(self, email: str, password: str) -> User:
        return self._users.add(self._factory.create(email, password))


class LoginUser:
    def __init__(self, users: UserRepository, hasher: PasswordHasher, tokens: TokenService):
        self._users, self._hasher, self._tokens = users, hasher, tokens

    def execute(self, email: str, password: str) -> str:
        try:
            email_vo = Email(email)
        except DomainValidationError:
            raise AuthenticationError("Invalid email or password")
        user = self._users.get_by_email(email_vo)
        if user is None or not self._hasher.verify(password, user.password_hash):
            raise AuthenticationError("Invalid email or password")
        return self._tokens.issue(user.id)


class CreateMovie:
    def __init__(self, factory: MovieFactory, movies: MovieRepository):
        self._factory, self._movies = factory, movies

    def execute(self, title: str, genre: str, release_date: date, budget_usd: int) -> Movie:
        return self._movies.add(self._factory.create(title, genre, release_date, budget_usd))


class UpdateMovie:
    def __init__(self, factory: MovieFactory, movies: MovieRepository):
        self._factory, self._movies = factory, movies

    def execute(
        self, movie_id: int, title: str, genre: str, release_date: date, budget_usd: int
    ) -> Movie:
        movie = _movie_or_404(self._movies, movie_id)
        movie.update(title=title, genre=genre, release_date=release_date, budget=Money(budget_usd))
        self._factory.ensure_unique(movie)
        return self._movies.update(movie)


class DeleteMovie:
    def __init__(self, movies: MovieRepository):
        self._movies = movies

    def execute(self, movie_id: int) -> None:
        _movie_or_404(self._movies, movie_id)
        self._movies.delete(movie_id)


class GetMovie:
    def __init__(self, movies: MovieRepository):
        self._movies = movies

    def execute(self, movie_id: int) -> Movie:
        return _movie_or_404(self._movies, movie_id)


class ListMovies:
    def __init__(self, movies: MovieRepository):
        self._movies = movies

    def execute(self, genre: str | None, year: int | None, limit: int, offset: int) -> list[Movie]:
        return self._movies.list(genre, year, limit, offset)


class AddReport:
    def __init__(self, movies: MovieRepository, reports: ReportRepository, factory: ReportFactory):
        self._movies, self._reports, self._factory = movies, reports, factory

    def execute(
        self, movie_id: int, report_date: date, region: str, revenue_usd: int, tickets_sold: int
    ) -> BoxOfficeReport:
        movie = _movie_or_404(self._movies, movie_id)
        report = self._factory.create(movie, report_date, region, revenue_usd, tickets_sold)
        return self._reports.add(report)


class UpdateReport:
    def __init__(self, reports: ReportRepository):
        self._reports = reports

    def execute(self, report_id: int, revenue_usd: int, tickets_sold: int) -> BoxOfficeReport:
        report = _report_or_404(self._reports, report_id)
        report.correct(revenue=Money(revenue_usd), tickets_sold=tickets_sold)
        return self._reports.update(report)


class DeleteReport:
    def __init__(self, reports: ReportRepository):
        self._reports = reports

    def execute(self, report_id: int) -> None:
        _report_or_404(self._reports, report_id)
        self._reports.delete(report_id)


class ListReports:
    def __init__(self, movies: MovieRepository, reports: ReportRepository):
        self._movies, self._reports = movies, reports

    def execute(
        self,
        movie_id: int,
        date_from: date | None = None,
        date_to: date | None = None,
        region: str | None = None,
    ) -> list[BoxOfficeReport]:
        _movie_or_404(self._movies, movie_id)
        region_vo = RegionCode(region) if region else None
        return self._reports.list_for_movie(movie_id, date_from, date_to, region_vo)


class GetMovieSummary:
    def __init__(self, movies: MovieRepository, reports: ReportRepository):
        self._movies, self._reports = movies, reports

    def execute(self, movie_id: int) -> MovieSummary:
        movie = _movie_or_404(self._movies, movie_id)
        return summarize(movie, self._reports.list_for_movie(movie_id))


@dataclass(frozen=True)
class TopMovie:
    movie: Movie
    total_revenue: Money
    total_tickets: int
    roi: float


class GetTopMovies:
    def __init__(self, movies: MovieRepository, reports: ReportRepository):
        self._movies, self._reports = movies, reports

    def execute(self, limit: int) -> list[TopMovie]:
        result = []
        for totals in self._reports.totals_by_movie(limit):
            movie = self._movies.get(totals.movie_id)
            result.append(
                TopMovie(movie, totals.total_revenue, totals.total_tickets, roi(movie, totals.total_revenue))
            )
        return result


class GetRegionRevenue:
    def __init__(self, reports: ReportRepository):
        self._reports = reports

    def execute(self) -> list[RegionTotal]:
        return self._reports.revenue_by_region()


@dataclass
class UseCases:

    register: RegisterUser
    login: LoginUser
    create_movie: CreateMovie
    update_movie: UpdateMovie
    delete_movie: DeleteMovie
    get_movie: GetMovie
    list_movies: ListMovies
    add_report: AddReport
    update_report: UpdateReport
    delete_report: DeleteReport
    list_reports: ListReports
    movie_summary: GetMovieSummary
    top_movies: GetTopMovies
    region_revenue: GetRegionRevenue
