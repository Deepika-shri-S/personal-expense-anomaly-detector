import re
from datetime import datetime, date, timedelta
from typing import Dict, Any, List, Optional
from abc import ABC, abstractmethod

from app.models.transaction import Transaction
from app.models.profile import SpendingProfile
from app.models.bill import Bill
from app.utils.date_utils import get_week_bounds, get_month_bounds, get_start_of_day, get_end_of_day
from app.services.analytics_service import AnalyticsService
from app.services.bill_service import BillService


class BaseChatbotProvider(ABC):
    """Interface for conversational financial assistant."""

    @abstractmethod
    def handle_message(
        self, 
        user_id: int, 
        message: str, 
        profile_id: Optional[int] = None
    ) -> Dict[str, Any]:
        pass


class RuleBasedChatbotProvider(BaseChatbotProvider):
    """
    Deterministic rule-based conversational assistant that queries the SQLite database directly.
    Ensures zero hallucination and complete user isolation.
    """

    def handle_message(
        self, 
        user_id: int, 
        message: str, 
        profile_id: Optional[int] = None
    ) -> Dict[str, Any]:
        msg_clean = message.lower().strip()

        # Resolve active profile context
        profile = None
        if profile_id:
            profile = SpendingProfile.query.filter_by(id=profile_id, user_id=user_id).first()
        if not profile:
            profile = SpendingProfile.query.filter_by(user_id=user_id, is_default=True).first()
        if not profile:
            profile = SpendingProfile.query.filter_by(user_id=user_id).first()

        curr = profile.currency if profile else "INR"
        prof_name = profile.name if profile else "All profiles"

        # 1. Fraud inquiry check
        if any(w in msg_clean for w in ["is this fraud", "is it fraud", "fraudulent", "am i hacked", "is this a scam"]):
            return {
                "reply": (
                    "Our anomaly detector identifies statistical deviations and unusual behavioral patterns "
                    "(such as unexpected amounts, unfamiliar merchants, or atypical transaction hours). "
                    "An anomaly is not automatically fraudulent. You should check if you recognize the merchant "
                    "and authorized the payment. If you do not recognize it, contact your bank immediately."
                ),
                "intent": "fraud_inquiry",
                "related_transactions": [],
                "suggested_questions": [
                    "Why was my latest transaction flagged?",
                    "What should I review in my recent spending?",
                    "Show my recent alerts"
                ],
            }

        # 2. Why was latest transaction flagged?
        if any(p in msg_clean for p in ["why was my latest", "why was my last", "latest transaction flagged", "why flagged", "unusual expense"]):
            q = Transaction.query.filter_by(user_id=user_id, anomaly_status=True)
            if profile:
                q = q.filter_by(profile_id=profile.id)
            latest_anomaly = q.order_by(Transaction.transaction_date.desc()).first()

            if not latest_anomaly:
                return {
                    "reply": f"You currently have no flagged anomalies in your '{prof_name}' profile.",
                    "intent": "why_flagged_latest",
                    "related_transactions": [],
                    "suggested_questions": ["How much did I spend this week?", "What are my upcoming bills?"],
                }

            reasons = latest_anomaly.anomaly_explanation
            reason_str = " ".join(reasons) if reasons else "It differed from your typical spending baseline."
            reply = (
                f"Your transaction of {curr} {latest_anomaly.amount:,.2f} at '{latest_anomaly.merchant}' "
                f"on {latest_anomaly.transaction_date.strftime('%b %d, %Y')} was flagged with {latest_anomaly.anomaly_severity.upper()} severity.\n\n"
                f"Reasons:\n• {reason_str}\n\n"
                f"Recommended action: {latest_anomaly.recommended_action}"
            )
            return {
                "reply": reply,
                "intent": "why_flagged_latest",
                "related_transactions": [latest_anomaly.id],
                "suggested_questions": [
                    "What should I review in my recent spending?",
                    "How much did I spend this month?",
                    "Which category accounts for the most spending?"
                ],
            }

        # 3. Spending this week
        if any(p in msg_clean for p in ["spend this week", "spent this week", "spending this week", "this week"]):
            today = date.today()
            w_start, w_end = get_week_bounds(today)
            txs = Transaction.query.filter(
                Transaction.user_id == user_id,
                Transaction.transaction_date >= get_start_of_day(w_start),
                Transaction.transaction_date <= get_end_of_day(today),
            )
            if profile:
                txs = txs.filter_by(profile_id=profile.id)
            records = txs.all()
            total = sum(t.amount for t in records)

            reply = (
                f"You have spent {curr} {total:,.2f} across {len(records)} transactions so far this week "
                f"(since Monday, {w_start.strftime('%b %d')})."
            )
            return {
                "reply": reply,
                "intent": "spending_this_week",
                "related_transactions": [t.id for t in records[:5]],
                "suggested_questions": [
                    "Which category accounts for the most spending?",
                    "How much did I spend online?",
                    "What are my upcoming bills?"
                ],
            }

        # 4. Spending this month
        if any(p in msg_clean for p in ["spend this month", "spent this month", "spending this month", "this month"]):
            today = date.today()
            m_start, _ = get_month_bounds(today.year, today.month)
            txs = Transaction.query.filter(
                Transaction.user_id == user_id,
                Transaction.transaction_date >= get_start_of_day(m_start),
                Transaction.transaction_date <= get_end_of_day(today),
            )
            if profile:
                txs = txs.filter_by(profile_id=profile.id)
            records = txs.all()
            total = sum(t.amount for t in records)

            reply = (
                f"Your total spending for {today.strftime('%B %Y')} in '{prof_name}' is "
                f"{curr} {total:,.2f} across {len(records)} transactions."
            )
            return {
                "reply": reply,
                "intent": "spending_this_month",
                "related_transactions": [t.id for t in records[:5]],
                "suggested_questions": [
                    "Which category accounts for the most spending?",
                    "How much did I spend this week?",
                    "What are my upcoming bills?"
                ],
            }

        # 5. Top spending category
        if any(p in msg_clean for p in ["most spending", "top category", "highest category", "spend the most on"]):
            cat_data = AnalyticsService.get_category_breakdown(
                user_id, 
                {"profile_id": profile.id if profile else None}
            )
            breakdown = cat_data.get("breakdown", [])
            if not breakdown:
                return {
                    "reply": f"No spending recorded yet for '{prof_name}'.",
                    "intent": "top_category",
                    "related_transactions": [],
                    "suggested_questions": ["What are my upcoming bills?"],
                }

            top = breakdown[0]
            reply = (
                f"Your top spending category in '{prof_name}' is '{top['category']}', "
                f"accounting for {curr} {top['total_spending']:,.2f} ({top['percentage']}% of your total spending)."
            )
            return {
                "reply": reply,
                "intent": "top_category",
                "related_transactions": [],
                "suggested_questions": [
                    "How much did I spend online?",
                    "How much did I spend this month?",
                    "Why was my latest transaction flagged?"
                ],
            }

        # 6. Online vs offline spending
        if any(p in msg_clean for p in ["online", "offline", "channel"]):
            ch_data = AnalyticsService.get_payment_channel_breakdown(
                user_id, 
                {"profile_id": profile.id if profile else None}
            )
            channels = {c["channel"]: c for c in ch_data.get("channels", [])}
            on = channels.get("online", {"total_spending": 0.0, "percentage": 0.0})
            off = channels.get("offline", {"total_spending": 0.0, "percentage": 0.0})

            reply = (
                f"In '{prof_name}':\n"
                f"• Online spending: {curr} {on['total_spending']:,.2f} ({on['percentage']}%)\n"
                f"• Offline spending: {curr} {off['total_spending']:,.2f} ({off['percentage']}%)"
            )
            return {
                "reply": reply,
                "intent": "channel_spending",
                "related_transactions": [],
                "suggested_questions": [
                    "Which category accounts for the most spending?",
                    "How much did I spend this week?"
                ],
            }

        # 7. Upcoming and overdue bills
        if any(p in msg_clean for p in ["upcoming bills", "due bills", "bills due", "bills", "reminders"]):
            upcoming = BillService.get_upcoming_bills(user_id, days_ahead=30)
            overdue = BillService.get_overdue_bills(user_id)

            if not upcoming and not overdue:
                return {
                    "reply": "You have no upcoming or overdue bills scheduled for the next 30 days.",
                    "intent": "upcoming_bills",
                    "related_transactions": [],
                    "suggested_questions": ["How much did I spend this month?"],
                }

            lines = []
            if overdue:
                lines.append(f"⚠️ Overdue ({len(overdue)}):")
                for b in overdue[:3]:
                    lines.append(f"• {b['bill_name']} ({curr} {b['amount']:,.2f}) - Due on {b['due_date']}")

            if upcoming:
                lines.append(f"📅 Upcoming ({len(upcoming)}):")
                for b in upcoming[:4]:
                    lines.append(f"• {b['bill_name']} ({curr} {b['amount']:,.2f}) - Due on {b['due_date']} (in {b['days_remaining']} days)")

            return {
                "reply": "\n".join(lines),
                "intent": "upcoming_bills",
                "related_transactions": [],
                "suggested_questions": ["What should I review in my recent spending?"],
            }

        # 8. Flagged today
        if any(p in msg_clean for p in ["flagged today", "anomalies today"]):
            today_start = get_start_of_day(date.today())
            txs = Transaction.query.filter(
                Transaction.user_id == user_id,
                Transaction.anomaly_status == True,
                Transaction.transaction_date >= today_start
            ).all()

            if not txs:
                return {
                    "reply": "No transactions have been flagged as anomalies today.",
                    "intent": "flagged_today",
                    "related_transactions": [],
                    "suggested_questions": ["Why was my latest transaction flagged?", "Show spending this week"],
                }

            reply = f"Found {len(txs)} transaction(s) flagged today:\n"
            for t in txs:
                reply += f"• {curr} {t.amount:,.2f} at {t.merchant} ({t.category}) - Severity: {t.anomaly_severity}\n"

            return {
                "reply": reply,
                "intent": "flagged_today",
                "related_transactions": [t.id for t in txs],
                "suggested_questions": ["What should I review in my recent spending?"],
            }

        # 9. Profile comparison (e.g. College vs Home)
        if any(p in msg_clean for p in ["college", "home", "compare", "differ from"]):
            profiles = SpendingProfile.query.filter_by(user_id=user_id).all()
            if len(profiles) < 2:
                return {
                    "reply": (
                        "You currently have only one spending profile. "
                        "Create another profile (like 'College' or 'Home') under Profiles to compare your spending across locations."
                    ),
                    "intent": "profile_comparison",
                    "related_transactions": [],
                    "suggested_questions": ["How much did I spend this month?"],
                }

            lines = ["Here is how your spending compares across your profiles:"]
            for p in profiles:
                txs = Transaction.query.filter_by(user_id=user_id, profile_id=p.id).all()
                tot = sum(t.amount for t in txs)
                avg = (tot / len(txs)) if txs else 0.0
                lines.append(
                    f"• {p.name}: Total {p.currency} {tot:,.2f} across {len(txs)} transactions (Avg: {p.currency} {avg:,.2f})"
                )

            return {
                "reply": "\n".join(lines),
                "intent": "profile_comparison",
                "related_transactions": [],
                "suggested_questions": ["Which category accounts for the most spending?"],
            }

        # 10. Electricity / utility bill higher inquiry
        if any(p in msg_clean for p in ["electricity", "utility", "bill higher"]):
            elec_bills = Bill.query.filter(
                Bill.user_id == user_id,
                Bill.category.ilike("%electric%") | Bill.bill_name.ilike("%electric%")
            ).order_by(Bill.due_date.desc()).all()

            if not elec_bills:
                return {
                    "reply": "I couldn't find any recorded electricity bills in your account.",
                    "intent": "bill_inquiry",
                    "related_transactions": [],
                    "suggested_questions": ["What are my upcoming bills?"],
                }

            latest = elec_bills[0]
            if len(elec_bills) > 1:
                prev = elec_bills[1]
                diff = latest.amount - prev.amount
                if diff > 0:
                    reply = (
                        f"Your latest electricity bill is {curr} {latest.amount:,.2f}, which is "
                        f"{curr} {diff:,.2f} higher than your previous bill of {curr} {prev.amount:,.2f}. "
                        "Seasonal appliances (such as ACs or heaters) or higher tariff rates often cause this difference."
                    )
                else:
                    reply = f"Your latest electricity bill is {curr} {latest.amount:,.2f}, which is within your normal range."
            else:
                reply = f"Your current electricity bill is {curr} {latest.amount:,.2f} due on {latest.due_date}."

            return {
                "reply": reply,
                "intent": "bill_inquiry",
                "related_transactions": [],
                "suggested_questions": ["What are my upcoming bills?"],
            }

        # 11. What should I review in my recent spending?
        if any(p in msg_clean for p in ["review", "what should i review", "attention"]):
            unreviewed = Transaction.query.filter_by(
                user_id=user_id,
                anomaly_status=True,
                user_confirmation_status="pending",
            ).order_by(Transaction.transaction_date.desc()).limit(3).all()

            overdue = BillService.get_overdue_bills(user_id)

            parts = []
            if unreviewed:
                parts.append(f"You have {len(unreviewed)} flagged transaction(s) pending review:")
                for u in unreviewed:
                    parts.append(f"• {curr} {u.amount:,.2f} at {u.merchant} ({u.anomaly_severity} severity)")
            else:
                parts.append("✅ All flagged transactions have been reviewed.")

            if overdue:
                parts.append(f"\n⚠️ You have {len(overdue)} overdue bill(s) requiring payment:")
                for b in overdue[:2]:
                    parts.append(f"• {b['bill_name']} ({curr} {b['amount']:,.2f})")

            return {
                "reply": "\n".join(parts),
                "intent": "what_to_review",
                "related_transactions": [u.id for u in unreviewed],
                "suggested_questions": [
                    "Why was my latest transaction flagged?",
                    "What are my upcoming bills?"
                ],
            }

        # 12. Fallback / Ambiguous clarification
        return {
            "reply": (
                "I'm not quite sure what you'd like to check. "
                "You can ask me about your recent flagged transactions, weekly spending, "
                "category breakdown, online vs offline spending, or upcoming bills."
            ),
            "intent": "ambiguous",
            "related_transactions": [],
            "suggested_questions": [
                "Why was my latest transaction flagged?",
                "How much did I spend this week?",
                "Which category accounts for the most spending?",
                "What are my upcoming bills?",
                "What should I review in my recent spending?"
            ],
        }


class ChatbotService:
    """Entry point for the expense chatbot, allowing swappable providers."""

    def __init__(self, provider: Optional[BaseChatbotProvider] = None):
        self.provider = provider or RuleBasedChatbotProvider()

    def process_message(
        self, 
        user_id: int, 
        message: str, 
        profile_id: Optional[int] = None
    ) -> Dict[str, Any]:
        return self.provider.handle_message(user_id, message, profile_id)


chatbot_service = ChatbotService()
