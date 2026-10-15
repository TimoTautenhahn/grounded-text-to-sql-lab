"""Gold set: natural-language questions paired with reference SQL.

Each pair is answerable from the orders / returns / people schema. The gold SQL
is the source of truth: evaluation compares a candidate's result set against the
result of running these queries, so the questions can stay stable even if a
model phrases its SQL differently.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GoldItem:
    id: str
    question: str
    sql: str
    tags: tuple[str, ...] = ()


GOLD: list[GoldItem] = [
    GoldItem("q01", "How many orders are there in total?",
             "SELECT COUNT(DISTINCT order_id) FROM orders", ("count",)),
    GoldItem("q02", "What is the total sales rounded to two decimals?",
             "SELECT ROUND(SUM(sales), 2) FROM orders", ("aggregate",)),
    GoldItem("q03", "What is the total profit per region, ordered by region?",
             "SELECT region, ROUND(SUM(profit), 2) FROM orders GROUP BY region ORDER BY region",
             ("groupby",)),
    GoldItem("q04", "Which product category has the highest total sales?",
             "SELECT category FROM orders GROUP BY category ORDER BY SUM(sales) DESC LIMIT 1",
             ("rank",)),
    GoldItem("q05", "How many orders were returned?",
             "SELECT COUNT(*) FROM returns WHERE returned = 'Yes'", ("join-free",)),
    GoldItem("q06", "What is the average discount in the Technology category?",
             "SELECT ROUND(AVG(discount), 4) FROM orders WHERE category = 'Technology'",
             ("filter", "aggregate")),
    GoldItem("q07", "List the top 3 customers by total sales, highest first.",
             "SELECT customer_id, ROUND(SUM(sales), 2) AS s FROM orders "
             "GROUP BY customer_id ORDER BY s DESC, customer_id LIMIT 3", ("rank", "groupby")),
    GoldItem("q08", "What is the total sales for orders placed in 2023?",
             "SELECT ROUND(SUM(sales), 2) FROM orders WHERE order_date >= '2023-01-01' "
             "AND order_date < '2024-01-01'", ("date",)),
    GoldItem("q09", "Who is the person responsible for the West region?",
             "SELECT person FROM people WHERE region = 'West'", ("lookup",)),
    GoldItem("q10", "What is the total quantity sold in the Furniture category?",
             "SELECT SUM(quantity) FROM orders WHERE category = 'Furniture'",
             ("filter", "aggregate")),
    GoldItem("q11", "How many distinct customers are in the Consumer segment?",
             "SELECT COUNT(DISTINCT customer_id) FROM orders WHERE segment = 'Consumer'",
             ("filter", "count")),
    GoldItem("q12", "What is the total profit for the Central region?",
             "SELECT ROUND(SUM(profit), 2) FROM orders WHERE region = 'Central'",
             ("filter", "aggregate")),
    GoldItem("q13", "Which region has the most returned orders?",
             "SELECT o.region FROM orders o JOIN returns r ON o.order_id = r.order_id "
             "WHERE r.returned = 'Yes' GROUP BY o.region ORDER BY COUNT(*) DESC, o.region LIMIT 1",
             ("join", "rank")),
]
