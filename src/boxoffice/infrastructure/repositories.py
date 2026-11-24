from datetime import date

from sqlalchemy import extract, func, select
from sqlalchemy.orm import Session

from boxoffice.domain.entities import BoxOfficeReport, Movie, User
from boxoffice.domain.repositories import (
    MovieRepository,
    MovieTotals,
    RegionTotal,
    ReportRepository,
    UserRepository,
)
from boxoffice.domain.value_objects import Email, Money, RegionCode
from boxoffice.infrastructure import mappers
from boxoffice.infrastructure.orm_models import MovieRow, ReportRow, UserRow


class SqlAlchemyUserRepository(UserRepository):
    def __init__(self, session: Session):
        self._s = session

    def add(self, user: User) -> User:
        row = UserRow(email=user.email.value, password_hash=user.password_hash)
        self._s.add(row)
        self._s.commit()
        return mappers.user_to_domain(row)

    def get_by_email(self, email: Email) -> User | None:
        row = self._s.scalar(select(UserRow).where(UserRow.email == email.value))
        return mappers.user_to_domain(row) if row else None


class SqlAlchemyMovieRepository(MovieRepository):
    def __init__(self, session: Session):
        self._s = session

    def add(self, movie: Movie) -> Movie:
        row = MovieRow()
        mappers.apply_movie(row, movie)
        self._s.add(row)
        self._s.commit()
        return mappers.movie_to_domain(row)

    def get(self, movie_id: int) -> Movie | None:
        row = self._s.get(MovieRow, movie_id)
        return mappers.movie_to_domain(row) if row else None

    def update(self, movie: Movie) -> Movie:
        row = self._s.get(MovieRow, movie.id)
        mappers.apply_movie(row, movie)
        self._s.commit()
        return mappers.movie_to_domain(row)

    def delete(self, movie_id: int) -> None:
        row = self._s.get(MovieRow, movie_id)
        if row is not None:
            self._s.delete(row)
            self._s.commit()

    def list(self, genre, year, limit, offset) -> list[Movie]:
        query = select(MovieRow).order_by(MovieRow.id)
        if genre:
            query = query.where(MovieRow.genre == genre)
        if year:
            query = query.where(extract("year", MovieRow.release_date) == year)
        rows = self._s.scalars(query.limit(limit).offset(offset)).all()
        return [mappers.movie_to_domain(r) for r in rows]

    def exists_by_title_and_date(self, title: str, release_date: date, exclude_id=None) -> bool:
        query = select(MovieRow.id).where(
            MovieRow.title == title, MovieRow.release_date == release_date
        )
        if exclude_id is not None:
            query = query.where(MovieRow.id != exclude_id)
        return self._s.scalar(query) is not None


class SqlAlchemyReportRepository(ReportRepository):
    def __init__(self, session: Session):
        self._s = session

    def add(self, report: BoxOfficeReport) -> BoxOfficeReport:
        row = ReportRow()
        mappers.apply_report(row, report)
        self._s.add(row)
        self._s.commit()
        return mappers.report_to_domain(row)

    def get(self, report_id: int) -> BoxOfficeReport | None:
        row = self._s.get(ReportRow, report_id)
        return mappers.report_to_domain(row) if row else None

    def update(self, report: BoxOfficeReport) -> BoxOfficeReport:
        row = self._s.get(ReportRow, report.id)
        mappers.apply_report(row, report)
        self._s.commit()
        return mappers.report_to_domain(row)

    def delete(self, report_id: int) -> None:
        row = self._s.get(ReportRow, report_id)
        if row is not None:
            self._s.delete(row)
            self._s.commit()

    def exists(self, movie_id: int, report_date: date, region: RegionCode) -> bool:
        query = select(ReportRow.id).where(
            ReportRow.movie_id == movie_id,
            ReportRow.report_date == report_date,
            ReportRow.region == region.value,
        )
        return self._s.scalar(query) is not None

    def list_for_movie(self, movie_id, date_from=None, date_to=None, region=None):
        query = select(ReportRow).where(ReportRow.movie_id == movie_id)
        if date_from:
            query = query.where(ReportRow.report_date >= date_from)
        if date_to:
            query = query.where(ReportRow.report_date <= date_to)
        if region:
            query = query.where(ReportRow.region == region.value)
        rows = self._s.scalars(query.order_by(ReportRow.report_date, ReportRow.region)).all()
        return [mappers.report_to_domain(r) for r in rows]

    def totals_by_movie(self, limit: int) -> list[MovieTotals]:
        total = func.sum(ReportRow.revenue_usd)
        rows = self._s.execute(
            select(ReportRow.movie_id, total, func.sum(ReportRow.tickets_sold))
            .group_by(ReportRow.movie_id)
            .order_by(total.desc(), ReportRow.movie_id)
            .limit(limit)
        ).all()
        return [MovieTotals(mid, Money(rev), tickets) for mid, rev, tickets in rows]

    def revenue_by_region(self) -> list[RegionTotal]:
        total = func.sum(ReportRow.revenue_usd)
        rows = self._s.execute(
            select(ReportRow.region, total).group_by(ReportRow.region).order_by(total.desc(), ReportRow.region)
        ).all()
        return [RegionTotal(RegionCode(region), Money(rev)) for region, rev in rows]
