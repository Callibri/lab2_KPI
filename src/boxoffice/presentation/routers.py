from datetime import date

from fastapi import APIRouter, Depends, Query, Response

from boxoffice.application.use_cases import UseCases
from boxoffice.presentation.dependencies import get_use_cases, require_user
from boxoffice.presentation.schemas import (
    LoginRequest, MovieRequest, MovieResponse, MovieSummaryResponse, RegionRevenueResponse,
    RegisterRequest, ReportRequest, ReportResponse, ReportUpdateRequest, TokenResponse,
    TopMovieResponse, UserResponse,
)

auth_router = APIRouter(prefix="/auth", tags=["auth"])
movies_router = APIRouter(prefix="/movies", tags=["movies"], dependencies=[Depends(require_user)])
reports_router = APIRouter(tags=["reports"], dependencies=[Depends(require_user)])
analytics_router = APIRouter(tags=["analytics"], dependencies=[Depends(require_user)])


@auth_router.post("/register", status_code=201, response_model=UserResponse)
def register(body: RegisterRequest, uc: UseCases = Depends(get_use_cases)):
    return UserResponse.from_entity(uc.register.execute(body.email, body.password))


@auth_router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, uc: UseCases = Depends(get_use_cases)):
    return TokenResponse(access_token=uc.login.execute(body.email, body.password))


@movies_router.post("", status_code=201, response_model=MovieResponse)
def create_movie(body: MovieRequest, uc: UseCases = Depends(get_use_cases)):
    movie = uc.create_movie.execute(body.title, body.genre, body.release_date, body.budget_usd)
    return MovieResponse.from_entity(movie)


@movies_router.get("", response_model=list[MovieResponse])
def list_movies(
    genre: str | None = None,
    year: int | None = None,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    uc: UseCases = Depends(get_use_cases),
):
    return [MovieResponse.from_entity(m) for m in uc.list_movies.execute(genre, year, limit, offset)]


@movies_router.get("/{movie_id}", response_model=MovieResponse)
def get_movie(movie_id: int, uc: UseCases = Depends(get_use_cases)):
    return MovieResponse.from_entity(uc.get_movie.execute(movie_id))


@movies_router.put("/{movie_id}", response_model=MovieResponse)
def update_movie(movie_id: int, body: MovieRequest, uc: UseCases = Depends(get_use_cases)):
    movie = uc.update_movie.execute(movie_id, body.title, body.genre, body.release_date, body.budget_usd)
    return MovieResponse.from_entity(movie)


@movies_router.delete("/{movie_id}", status_code=204)
def delete_movie(movie_id: int, uc: UseCases = Depends(get_use_cases)):
    uc.delete_movie.execute(movie_id)
    return Response(status_code=204)


@reports_router.post("/movies/{movie_id}/reports", status_code=201, response_model=ReportResponse)
def add_report(movie_id: int, body: ReportRequest, uc: UseCases = Depends(get_use_cases)):
    report = uc.add_report.execute(movie_id, body.report_date, body.region, body.revenue_usd, body.tickets_sold)
    return ReportResponse.from_entity(report)


@reports_router.get("/movies/{movie_id}/reports", response_model=list[ReportResponse])
def list_reports(
    movie_id: int,
    date_from: date | None = None,
    date_to: date | None = None,
    region: str | None = None,
    uc: UseCases = Depends(get_use_cases),
):
    reports = uc.list_reports.execute(movie_id, date_from, date_to, region)
    return [ReportResponse.from_entity(r) for r in reports]


@reports_router.put("/reports/{report_id}", response_model=ReportResponse)
def update_report(report_id: int, body: ReportUpdateRequest, uc: UseCases = Depends(get_use_cases)):
    return ReportResponse.from_entity(uc.update_report.execute(report_id, body.revenue_usd, body.tickets_sold))


@reports_router.delete("/reports/{report_id}", status_code=204)
def delete_report(report_id: int, uc: UseCases = Depends(get_use_cases)):
    uc.delete_report.execute(report_id)
    return Response(status_code=204)


@analytics_router.get("/movies/{movie_id}/summary", response_model=MovieSummaryResponse)
def movie_summary(movie_id: int, uc: UseCases = Depends(get_use_cases)):
    return MovieSummaryResponse.from_summary(uc.movie_summary.execute(movie_id))


@analytics_router.get("/analytics/top", response_model=list[TopMovieResponse])
def top_movies(limit: int = Query(10, ge=1, le=50), uc: UseCases = Depends(get_use_cases)):
    return [TopMovieResponse.from_top(t) for t in uc.top_movies.execute(limit)]


@analytics_router.get("/analytics/regions", response_model=list[RegionRevenueResponse])
def revenue_by_region(uc: UseCases = Depends(get_use_cases)):
    return [RegionRevenueResponse.from_total(t) for t in uc.region_revenue.execute()]
