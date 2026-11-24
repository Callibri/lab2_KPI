from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date

from boxoffice.domain.entities import BoxOfficeReport, Movie, User
from boxoffice.domain.value_objects import Email, Money, RegionCode


@dataclass(frozen=True)
class MovieTotals:
    movie_id: int
    total_revenue: Money
    total_tickets: int


@dataclass(frozen=True)
class RegionTotal:
    region: RegionCode
    revenue: Money


class UserRepository(ABC):
    @abstractmethod
    def add(self, user: User) -> User: ...

    @abstractmethod
    def get_by_email(self, email: Email) -> User | None: ...


class MovieRepository(ABC):
    @abstractmethod
    def add(self, movie: Movie) -> Movie: ...

    @abstractmethod
    def get(self, movie_id: int) -> Movie | None: ...

    @abstractmethod
    def update(self, movie: Movie) -> Movie: ...

    @abstractmethod
    def delete(self, movie_id: int) -> None: ...

    @abstractmethod
    def list(self, genre: str | None, year: int | None, limit: int, offset: int) -> list[Movie]: ...

    @abstractmethod
    def exists_by_title_and_date(
        self, title: str, release_date: date, exclude_id: int | None = None
    ) -> bool: ...


class ReportRepository(ABC):
    @abstractmethod
    def add(self, report: BoxOfficeReport) -> BoxOfficeReport: ...

    @abstractmethod
    def get(self, report_id: int) -> BoxOfficeReport | None: ...

    @abstractmethod
    def update(self, report: BoxOfficeReport) -> BoxOfficeReport: ...

    @abstractmethod
    def delete(self, report_id: int) -> None: ...

    @abstractmethod
    def exists(self, movie_id: int, report_date: date, region: RegionCode) -> bool: ...

    @abstractmethod
    def list_for_movie(
        self,
        movie_id: int,
        date_from: date | None = None,
        date_to: date | None = None,
        region: RegionCode | None = None,
    ) -> list[BoxOfficeReport]: ...

    @abstractmethod
    def totals_by_movie(self, limit: int) -> list[MovieTotals]: ...

    @abstractmethod
    def revenue_by_region(self) -> list[RegionTotal]: ...
