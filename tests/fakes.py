from dataclasses import replace
from datetime import date

from boxoffice.application.ports import TokenService
from boxoffice.domain.entities import BoxOfficeReport, Movie, User
from boxoffice.domain.errors import AuthenticationError
from boxoffice.domain.ports import PasswordHasher
from boxoffice.domain.repositories import (
    MovieRepository, MovieTotals, RegionTotal, ReportRepository, UserRepository,
)
from boxoffice.domain.value_objects import Money


class FakeHasher(PasswordHasher):
    def hash(self, raw_password):
        return f"hashed:{raw_password}"

    def verify(self, raw_password, password_hash):
        return password_hash == f"hashed:{raw_password}"


class FakeTokens(TokenService):
    def issue(self, user_id):
        return f"token-{user_id}"

    def verify(self, token):
        if not token.startswith("token-"):
            raise AuthenticationError("bad token")
        return int(token.split("-")[1])


class InMemoryUserRepository(UserRepository):
    def __init__(self):
        self.items: dict[int, User] = {}

    def add(self, user):
        saved = replace(user, id=len(self.items) + 1)
        self.items[saved.id] = saved
        return saved

    def get_by_email(self, email):
        return next((u for u in self.items.values() if u.email == email), None)


class InMemoryMovieRepository(MovieRepository):
    def __init__(self):
        self.items: dict[int, Movie] = {}
        self.add_calls = 0

    def add(self, movie):
        self.add_calls += 1
        saved = replace(movie, id=len(self.items) + 1)
        self.items[saved.id] = saved
        return saved

    def get(self, movie_id):
        movie = self.items.get(movie_id)
        return replace(movie) if movie else None

    def update(self, movie):
        self.items[movie.id] = replace(movie)
        return movie

    def delete(self, movie_id):
        self.items.pop(movie_id, None)

    def list(self, genre, year, limit, offset):
        movies = [m for m in self.items.values()
                  if (not genre or m.genre == genre) and (not year or m.release_date.year == year)]
        return movies[offset: offset + limit]

    def exists_by_title_and_date(self, title, release_date: date, exclude_id=None):
        return any(m.title == title and m.release_date == release_date and m.id != exclude_id
                   for m in self.items.values())


class InMemoryReportRepository(ReportRepository):
    def __init__(self):
        self.items: dict[int, BoxOfficeReport] = {}

    def add(self, report):
        saved = replace(report, id=len(self.items) + 1)
        self.items[saved.id] = saved
        return saved

    def get(self, report_id):
        report = self.items.get(report_id)
        return replace(report) if report else None

    def update(self, report):
        self.items[report.id] = replace(report)
        return report

    def delete(self, report_id):
        self.items.pop(report_id, None)

    def exists(self, movie_id, report_date, region):
        return any(r.movie_id == movie_id and r.report_date == report_date and r.region == region
                   for r in self.items.values())

    def list_for_movie(self, movie_id, date_from=None, date_to=None, region=None):
        return [r for r in self.items.values()
                if r.movie_id == movie_id
                and (not date_from or r.report_date >= date_from)
                and (not date_to or r.report_date <= date_to)
                and (not region or r.region == region)]

    def totals_by_movie(self, limit):
        sums: dict[int, list[int]] = {}
        for r in self.items.values():
            s = sums.setdefault(r.movie_id, [0, 0])
            s[0] += r.revenue.amount_usd
            s[1] += r.tickets_sold
        ordered = sorted(sums.items(), key=lambda kv: -kv[1][0])[:limit]
        return [MovieTotals(mid, Money(rev), t) for mid, (rev, t) in ordered]

    def revenue_by_region(self):
        sums = {}
        for r in self.items.values():
            sums[r.region] = sums.get(r.region, 0) + r.revenue.amount_usd
        return [RegionTotal(reg, Money(v)) for reg, v in sorted(sums.items(), key=lambda kv: -kv[1])]
