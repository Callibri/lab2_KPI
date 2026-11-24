from datetime import date

from pydantic import BaseModel

from boxoffice.domain.entities import BoxOfficeReport, Movie, User
from boxoffice.domain.repositories import RegionTotal
from boxoffice.application.use_cases import TopMovie
from boxoffice.domain.services import MovieSummary


class RegisterRequest(BaseModel):
    email: str
    password: str


class LoginRequest(BaseModel):
    email: str
    password: str


class UserResponse(BaseModel):
    id: int
    email: str

    @classmethod
    def from_entity(cls, user: User) -> "UserResponse":
        return cls(id=user.id, email=user.email.value)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class MovieRequest(BaseModel):
    title: str
    genre: str
    release_date: date
    budget_usd: int


class MovieResponse(BaseModel):
    id: int
    title: str
    genre: str
    release_date: date
    budget_usd: int

    @classmethod
    def from_entity(cls, m: Movie) -> "MovieResponse":
        return cls(id=m.id, title=m.title, genre=m.genre, release_date=m.release_date,
                   budget_usd=m.budget.amount_usd)


class ReportRequest(BaseModel):
    report_date: date
    region: str
    revenue_usd: int
    tickets_sold: int


class ReportUpdateRequest(BaseModel):
    revenue_usd: int
    tickets_sold: int


class ReportResponse(BaseModel):
    id: int
    movie_id: int
    report_date: date
    region: str
    revenue_usd: int
    tickets_sold: int

    @classmethod
    def from_entity(cls, r: BoxOfficeReport) -> "ReportResponse":
        return cls(id=r.id, movie_id=r.movie_id, report_date=r.report_date, region=r.region.value,
                   revenue_usd=r.revenue.amount_usd, tickets_sold=r.tickets_sold)


class RegionRevenueResponse(BaseModel):
    region: str
    revenue_usd: int

    @classmethod
    def from_total(cls, t: RegionTotal) -> "RegionRevenueResponse":
        return cls(region=t.region.value, revenue_usd=t.revenue.amount_usd)


class MovieSummaryResponse(BaseModel):
    movie_id: int
    title: str
    budget_usd: int
    total_revenue_usd: int
    total_tickets: int
    avg_ticket_price_usd: float | None
    roi: float
    revenue_by_region: list[RegionRevenueResponse]

    @classmethod
    def from_summary(cls, s: MovieSummary) -> "MovieSummaryResponse":
        return cls(
            movie_id=s.movie.id, title=s.movie.title, budget_usd=s.movie.budget.amount_usd,
            total_revenue_usd=s.total_revenue.amount_usd, total_tickets=s.total_tickets,
            avg_ticket_price_usd=s.avg_ticket_price_usd, roi=s.roi,
            revenue_by_region=[RegionRevenueResponse(region=r, revenue_usd=v) for r, v in s.revenue_by_region],
        )


class TopMovieResponse(BaseModel):
    movie_id: int
    title: str
    total_revenue_usd: int
    total_tickets: int
    roi: float

    @classmethod
    def from_top(cls, t: TopMovie) -> "TopMovieResponse":
        return cls(movie_id=t.movie.id, title=t.movie.title, total_revenue_usd=t.total_revenue.amount_usd,
                   total_tickets=t.total_tickets, roi=t.roi)
