from dataclasses import dataclass

from boxoffice.domain.entities import BoxOfficeReport, Movie
from boxoffice.domain.value_objects import Money


def roi(movie: Movie, total_revenue: Money) -> float:
    budget = movie.budget.amount_usd
    return round((total_revenue.amount_usd - budget) / budget, 4)


@dataclass(frozen=True)
class MovieSummary:
    movie: Movie
    total_revenue: Money
    total_tickets: int
    avg_ticket_price_usd: float | None
    roi: float
    revenue_by_region: list[tuple[str, int]]


def summarize(movie: Movie, reports: list[BoxOfficeReport]) -> MovieSummary:
    total = Money.zero()
    tickets = 0
    by_region: dict[str, int] = {}
    for r in reports:
        total = total + r.revenue
        tickets += r.tickets_sold
        by_region[r.region.value] = by_region.get(r.region.value, 0) + r.revenue.amount_usd
    avg = round(total.amount_usd / tickets, 2) if tickets else None
    ordered = sorted(by_region.items(), key=lambda kv: (-kv[1], kv[0]))
    return MovieSummary(movie, total, tickets, avg, roi(movie, total), ordered)
