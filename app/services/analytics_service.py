from datetime import datetime, date, timedelta
from typing import Dict, Any, List, Optional
from collections import defaultdict
import pandas as pd

from app.models.transaction import Transaction
from app.models.profile import SpendingProfile
from app.utils.date_utils import (
    parse_date, 
    get_start_of_day, 
    get_end_of_day, 
    get_week_bounds, 
    get_month_bounds
)


class AnalyticsService:
    """Service providing chart-ready JSON analytics data for frontend rendering."""

    @staticmethod
    def _get_filtered_query(user_id: int, filters: Dict[str, Any]):
        query = Transaction.query.filter_by(user_id=user_id)

        if filters.get("profile_id"):
            query = query.filter_by(profile_id=int(filters["profile_id"]))

        if filters.get("category"):
            query = query.filter_by(category=filters["category"].strip())

        if filters.get("start_date"):
            start_d = parse_date(filters["start_date"])
            if start_d:
                query = query.filter(Transaction.transaction_date >= get_start_of_day(start_d))

        if filters.get("end_date"):
            end_d = parse_date(filters["end_date"])
            if end_d:
                query = query.filter(Transaction.transaction_date <= get_end_of_day(end_d))

        return query

    @staticmethod
    def get_summary(user_id: int, filters: Dict[str, Any]) -> Dict[str, Any]:
        """High-level spending KPI summary."""
        query = AnalyticsService._get_filtered_query(user_id, filters)
        transactions = query.all()

        profile = None
        currency = "INR"
        if filters.get("profile_id"):
            profile = SpendingProfile.query.filter_by(id=int(filters["profile_id"]), user_id=user_id).first()
            if profile:
                currency = profile.currency

        if not transactions:
            return {
                "currency": currency,
                "profile_id": profile.id if profile else None,
                "profile_name": profile.name if profile else "All Profiles",
                "total_spending": 0.0,
                "transaction_count": 0,
                "average_transaction": 0.0,
                "anomaly_count": 0,
                "top_category": None,
                "top_category_spending": 0.0,
            }

        total_spending = sum(t.amount for t in transactions)
        tx_count = len(transactions)
        avg_spending = total_spending / tx_count if tx_count > 0 else 0.0
        anomaly_count = sum(1 for t in transactions if t.anomaly_status)

        # Top category
        cat_totals = defaultdict(float)
        for t in transactions:
            cat_totals[t.category] += t.amount

        top_cat = max(cat_totals.items(), key=lambda x: x[1]) if cat_totals else (None, 0.0)

        return {
            "currency": currency,
            "profile_id": profile.id if profile else None,
            "profile_name": profile.name if profile else "All Profiles",
            "total_spending": round(total_spending, 2),
            "transaction_count": tx_count,
            "average_transaction": round(avg_spending, 2),
            "anomaly_count": anomaly_count,
            "top_category": top_cat[0],
            "top_category_spending": round(top_cat[1], 2),
        }

    @staticmethod
    def get_spending_trend(
        user_id: int, 
        filters: Dict[str, Any], 
        period: str = "day",
        fill_zeros: bool = True
    ) -> Dict[str, Any]:
        """
        Aggregate spending trend by day, week, or month with correct boundaries.
        Optionally returns continuous zero-spending intervals for smooth chart rendering.
        """
        query = AnalyticsService._get_filtered_query(user_id, filters)
        transactions = query.order_by(Transaction.transaction_date.asc()).all()

        profile = None
        currency = "INR"
        if filters.get("profile_id"):
            profile = SpendingProfile.query.filter_by(id=int(filters["profile_id"]), user_id=user_id).first()
            if profile:
                currency = profile.currency

        if not transactions:
            return {
                "period": period,
                "currency": currency,
                "data": []
            }

        # Determine boundaries
        start_date = (
            parse_date(filters.get("start_date")) 
            or transactions[0].transaction_date.date()
        )
        end_date = (
            parse_date(filters.get("end_date")) 
            or transactions[-1].transaction_date.date()
        )

        aggregated: Dict[str, Dict[str, Any]] = defaultdict(lambda: {"total_spending": 0.0, "count": 0})

        for t in transactions:
            t_date = t.transaction_date.date()
            if period == "day":
                key = t_date.isoformat()
            elif period == "week":
                w_start, _ = get_week_bounds(t_date)
                key = w_start.isoformat()
            elif period == "month":
                key = f"{t_date.year}-{t_date.month:02d}-01"
            else:
                key = t_date.isoformat()

            aggregated[key]["total_spending"] += t.amount
            aggregated[key]["count"] += 1

        # Continuous filling if requested
        result_data = []
        if fill_zeros and start_date <= end_date:
            curr = start_date
            while curr <= end_date:
                if period == "day":
                    key = curr.isoformat()
                    curr += timedelta(days=1)
                elif period == "week":
                    w_start, _ = get_week_bounds(curr)
                    key = w_start.isoformat()
                    curr = w_start + timedelta(days=7)
                elif period == "month":
                    key = f"{curr.year}-{curr.month:02d}-01"
                    if curr.month == 12:
                        curr = date(curr.year + 1, 1, 1)
                    else:
                        curr = date(curr.year, curr.month + 1, 1)
                else:
                    key = curr.isoformat()
                    curr += timedelta(days=1)

                # Avoid duplicate insertion for weeks/months
                if not any(d["period_start"] == key for d in result_data):
                    val = aggregated.get(key, {"total_spending": 0.0, "count": 0})
                    result_data.append({
                        "period_start": key,
                        "total_spending": round(val["total_spending"], 2),
                        "transaction_count": val["count"],
                    })
        else:
            for k in sorted(aggregated.keys()):
                result_data.append({
                    "period_start": k,
                    "total_spending": round(aggregated[k]["total_spending"], 2),
                    "transaction_count": aggregated[k]["count"],
                })

        return {
            "period": period,
            "currency": currency,
            "data": result_data
        }

    @staticmethod
    def get_category_breakdown(user_id: int, filters: Dict[str, Any]) -> Dict[str, Any]:
        """Category-wise spending distribution."""
        query = AnalyticsService._get_filtered_query(user_id, filters)
        transactions = query.all()

        profile = None
        currency = "INR"
        if filters.get("profile_id"):
            profile = SpendingProfile.query.filter_by(id=int(filters["profile_id"]), user_id=user_id).first()
            if profile:
                currency = profile.currency

        total_all = sum(t.amount for t in transactions)
        cat_map: Dict[str, Dict[str, Any]] = defaultdict(lambda: {"amount": 0.0, "count": 0})

        for t in transactions:
            cat_map[t.category]["amount"] += t.amount
            cat_map[t.category]["count"] += 1

        breakdown = []
        for cat, val in sorted(cat_map.items(), key=lambda x: x[1]["amount"], reverse=True):
            pct = (val["amount"] / total_all * 100.0) if total_all > 0 else 0.0
            breakdown.append({
                "category": cat,
                "total_spending": round(val["amount"], 2),
                "transaction_count": val["count"],
                "percentage": round(pct, 2),
            })

        return {
            "currency": currency,
            "total_spending": round(total_all, 2),
            "breakdown": breakdown
        }

    @staticmethod
    def get_payment_channel_breakdown(user_id: int, filters: Dict[str, Any]) -> Dict[str, Any]:
        """Online versus offline spending breakdown."""
        query = AnalyticsService._get_filtered_query(user_id, filters)
        transactions = query.all()

        profile = None
        currency = "INR"
        if filters.get("profile_id"):
            profile = SpendingProfile.query.filter_by(id=int(filters["profile_id"]), user_id=user_id).first()
            if profile:
                currency = profile.currency

        total_all = sum(t.amount for t in transactions)
        channel_map = {"online": {"amount": 0.0, "count": 0}, "offline": {"amount": 0.0, "count": 0}}

        for t in transactions:
            ch = t.payment_channel.lower()
            if ch not in channel_map:
                channel_map[ch] = {"amount": 0.0, "count": 0}
            channel_map[ch]["amount"] += t.amount
            channel_map[ch]["count"] += 1

        channels = []
        for ch, val in channel_map.items():
            pct = (val["amount"] / total_all * 100.0) if total_all > 0 else 0.0
            channels.append({
                "channel": ch,
                "total_spending": round(val["amount"], 2),
                "transaction_count": val["count"],
                "percentage": round(pct, 2),
            })

        return {
            "currency": currency,
            "total_spending": round(total_all, 2),
            "channels": channels
        }

    @staticmethod
    def get_payment_method_breakdown(user_id: int, filters: Dict[str, Any]) -> Dict[str, Any]:
        """Distribution by payment method (UPI, cash, card, net banking, other)."""
        query = AnalyticsService._get_filtered_query(user_id, filters)
        transactions = query.all()

        profile = None
        currency = "INR"
        if filters.get("profile_id"):
            profile = SpendingProfile.query.filter_by(id=int(filters["profile_id"]), user_id=user_id).first()
            if profile:
                currency = profile.currency

        total_all = sum(t.amount for t in transactions)
        method_map: Dict[str, Dict[str, Any]] = defaultdict(lambda: {"amount": 0.0, "count": 0})

        for t in transactions:
            m = t.payment_method.lower()
            method_map[m]["amount"] += t.amount
            method_map[m]["count"] += 1

        methods = []
        for m, val in sorted(method_map.items(), key=lambda x: x[1]["amount"], reverse=True):
            pct = (val["amount"] / total_all * 100.0) if total_all > 0 else 0.0
            methods.append({
                "payment_method": m,
                "total_spending": round(val["amount"], 2),
                "transaction_count": val["count"],
                "percentage": round(pct, 2),
            })

        return {
            "currency": currency,
            "total_spending": round(total_all, 2),
            "methods": methods
        }

    @staticmethod
    def get_profile_comparison(user_id: int, filters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Compare spending across distinct profiles (e.g. College vs Home vs Travel).
        Preserves currency isolation to prevent invalid multi-currency aggregation.
        """
        profiles = SpendingProfile.query.filter_by(user_id=user_id).all()
        comparison = []

        for p in profiles:
            p_filters = dict(filters)
            p_filters["profile_id"] = p.id
            query = AnalyticsService._get_filtered_query(user_id, p_filters)
            txs = query.all()

            total = sum(t.amount for t in txs)
            count = len(txs)
            anomalies = sum(1 for t in txs if t.anomaly_status)

            comparison.append({
                "profile_id": p.id,
                "profile_name": p.name,
                "currency": p.currency,
                "total_spending": round(total, 2),
                "transaction_count": count,
                "average_transaction": round(total / count, 2) if count > 0 else 0.0,
                "anomaly_count": anomalies,
            })

        return {
            "profiles_count": len(profiles),
            "profiles": comparison
        }

    @staticmethod
    def get_anomalies_summary(user_id: int, filters: Dict[str, Any]) -> Dict[str, Any]:
        """Detailed overview of detected anomalies for review."""
        query = AnalyticsService._get_filtered_query(user_id, filters).filter_by(anomaly_status=True)
        anomalies = query.order_by(Transaction.transaction_date.desc()).all()

        by_severity = {"high": 0, "medium": 0, "low": 0}
        by_status = defaultdict(int)

        for a in anomalies:
            sev = a.anomaly_severity or "medium"
            by_severity[sev] = by_severity.get(sev, 0) + 1
            by_status[a.user_confirmation_status] += 1

        return {
            "total_anomalies": len(anomalies),
            "by_severity": by_severity,
            "by_confirmation_status": dict(by_status),
            "recent_anomalies": [a.to_dict() for a in anomalies[:10]],
        }
