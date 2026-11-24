import os
from typing import Iterator

from fastapi import FastAPI
from sqlalchemy.orm import Session, sessionmaker

from boxoffice.application.use_cases import (
    AddReport, CreateMovie, DeleteMovie, DeleteReport, GetMovie, GetMovieSummary, GetRegionRevenue,
    GetTopMovies, ListMovies, ListReports, LoginUser, RegisterUser, UpdateMovie, UpdateReport,
    UseCases,
)
from boxoffice.domain.factories import MovieFactory, ReportFactory, UserFactory
from boxoffice.infrastructure.db import Base, make_engine
from boxoffice.infrastructure import orm_models
from boxoffice.infrastructure.repositories import (
    SqlAlchemyMovieRepository, SqlAlchemyReportRepository, SqlAlchemyUserRepository,
)
from boxoffice.infrastructure.security import JwtTokenService, Pbkdf2PasswordHasher
from boxoffice.presentation.api import create_app

DEFAULT_SECRET = "dev-secret-key-change-me-in-production-32b"


def build_use_cases(session: Session, hasher, tokens) -> UseCases:
    users = SqlAlchemyUserRepository(session)
    movies = SqlAlchemyMovieRepository(session)
    reports = SqlAlchemyReportRepository(session)
    movie_factory = MovieFactory(movies)
    return UseCases(
        register=RegisterUser(UserFactory(users, hasher), users),
        login=LoginUser(users, hasher, tokens),
        create_movie=CreateMovie(movie_factory, movies),
        update_movie=UpdateMovie(movie_factory, movies),
        delete_movie=DeleteMovie(movies),
        get_movie=GetMovie(movies),
        list_movies=ListMovies(movies),
        add_report=AddReport(movies, reports, ReportFactory(reports)),
        update_report=UpdateReport(reports),
        delete_report=DeleteReport(reports),
        list_reports=ListReports(movies, reports),
        movie_summary=GetMovieSummary(movies, reports),
        top_movies=GetTopMovies(movies, reports),
        region_revenue=GetRegionRevenue(reports),
    )


def build_app(database_url: str | None = None, secret_key: str | None = None) -> FastAPI:
    database_url = database_url or os.getenv("DATABASE_URL", "sqlite:///./boxoffice.db")
    engine = make_engine(database_url)
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    hasher = Pbkdf2PasswordHasher()
    tokens = JwtTokenService(secret_key or os.getenv("SECRET_KEY", DEFAULT_SECRET))

    def use_case_scope() -> Iterator[UseCases]:
        with session_factory() as session:
            yield build_use_cases(session, hasher, tokens)

    app = create_app(use_case_scope, tokens)
    app.state.session_factory = session_factory
    return app
