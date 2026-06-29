import json
import os
from datetime import datetime, timezone

from flask import current_app

from apps.adminpanel.revenue_data import summary as manual_revenue_summary


SCOPES = ("https://www.googleapis.com/auth/analytics.readonly",)


class GASetupError(RuntimeError):
    pass


def _number(value):
    if value in (None, ""):
        return 0
    try:
        if "." in str(value):
            return float(value)
        return int(value)
    except (TypeError, ValueError):
        return value


def _metric_value(row, index):
    try:
        return _number(row.metric_values[index].value)
    except (IndexError, AttributeError):
        return 0


def _dimension_value(row, index):
    try:
        return row.dimension_values[index].value
    except (IndexError, AttributeError):
        return ""


def _rows(response, dimensions, metrics):
    out = []
    for row in getattr(response, "rows", []) or []:
        item = {}
        for index, name in enumerate(dimensions):
            item[name] = _dimension_value(row, index)
        for index, name in enumerate(metrics):
            item[name] = _metric_value(row, index)
        out.append(item)
    return out


def _client():
    try:
        from google.analytics.data_v1beta import BetaAnalyticsDataClient
        from google.oauth2 import service_account
    except ImportError as exc:
        raise GASetupError("Installera google-analytics-data i miljön.") from exc

    credentials_json = current_app.config.get("GA_CREDENTIALS_JSON")
    credentials_file = current_app.config.get("GA_CREDENTIALS_FILE")

    if credentials_json:
        info = json.loads(credentials_json)
        credentials = service_account.Credentials.from_service_account_info(info, scopes=SCOPES)
        return BetaAnalyticsDataClient(credentials=credentials)

    if credentials_file:
        credentials_file = os.path.abspath(credentials_file)
        credentials = service_account.Credentials.from_service_account_file(credentials_file, scopes=SCOPES)
        return BetaAnalyticsDataClient(credentials=credentials)

    if not os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
        raise GASetupError("GA credentials saknas.")

    return BetaAnalyticsDataClient()


def _date_range(range_key):
    if range_key == "7d":
        return "7daysAgo"
    if range_key == "90d":
        return "90daysAgo"
    return "30daysAgo"


def _run_report(client, property_id, *, dimensions=None, metrics=None, range_key="30d",
                limit=20, order_metric=None, dimension_filter=None):
    from google.analytics.data_v1beta.types import (
        DateRange,
        Dimension,
        Metric,
        OrderBy,
        RunReportRequest,
    )

    dimensions = dimensions or []
    metrics = metrics or []
    request = RunReportRequest(
        property=f"properties/{property_id}",
        date_ranges=[DateRange(start_date=_date_range(range_key), end_date="today")],
        dimensions=[Dimension(name=name) for name in dimensions],
        metrics=[Metric(name=name) for name in metrics],
        limit=limit,
        dimension_filter=dimension_filter,
    )
    if order_metric:
        request.order_bys = [OrderBy(metric=OrderBy.MetricOrderBy(metric_name=order_metric), desc=True)]
    response = client.run_report(request)
    return _rows(response, dimensions, metrics)


def _run_realtime(client, property_id, *, dimensions=None, metrics=None, limit=20):
    from google.analytics.data_v1beta.types import Dimension, Metric, RunRealtimeReportRequest

    dimensions = dimensions or []
    metrics = metrics or ["activeUsers"]
    response = client.run_realtime_report(
        RunRealtimeReportRequest(
            property=f"properties/{property_id}",
            dimensions=[Dimension(name=name) for name in dimensions],
            metrics=[Metric(name=name) for name in metrics],
            limit=limit,
        )
    )
    return _rows(response, dimensions, metrics)


def _safe(label, callback, fallback):
    try:
        return callback()
    except Exception as exc:
        return {"error": label, "message": str(exc), "data": fallback}


def _string_filter(field_name, value, match_type="CONTAINS"):
    from google.analytics.data_v1beta.types import Filter, FilterExpression

    return FilterExpression(
        filter=Filter(
            field_name=field_name,
            string_filter=Filter.StringFilter(match_type=getattr(Filter.StringFilter.MatchType, match_type), value=value),
        )
    )


def _event_filter(names):
    from google.analytics.data_v1beta.types import Filter, FilterExpression, FilterExpressionList

    filters = [
        FilterExpression(
            filter=Filter(
                field_name="eventName",
                string_filter=Filter.StringFilter(match_type=Filter.StringFilter.MatchType.EXACT, value=name),
            )
        )
        for name in names
    ]
    return FilterExpression(or_group=FilterExpressionList(expressions=filters))


def _sum_metric(rows, metric):
    if isinstance(rows, dict):
        rows = rows.get("data", [])
    return sum(float(row.get(metric, 0) or 0) for row in rows)


def overview(range_key="30d"):
    manual_revenue = manual_revenue_summary(range_key)
    property_id = current_app.config.get("GA_PROPERTY_ID")
    if not property_id:
        return {
            "configured": False,
            "reason": "GA_PROPERTY_ID saknas.",
            "needs": ["GA_PROPERTY_ID", "GA_CREDENTIALS_FILE eller GA_CREDENTIALS_JSON"],
            "manualRevenue": manual_revenue,
        }

    try:
        client = _client()
    except GASetupError as exc:
        needs = ["google-analytics-data"]
        if "credentials" in str(exc).lower():
            needs = ["GA_CREDENTIALS_FILE eller GA_CREDENTIALS_JSON"]
        return {"configured": False, "reason": str(exc), "needs": needs, "manualRevenue": manual_revenue}
    except Exception as exc:
        return {"configured": False, "reason": str(exc), "needs": ["Google service account credentials"], "manualRevenue": manual_revenue}

    def report(**kwargs):
        return _run_report(client, property_id, range_key=range_key, **kwargs)

    summary_traffic = _safe(
        "summary_traffic",
        lambda: report(metrics=["activeUsers", "totalUsers", "newUsers", "sessions", "screenPageViews"], limit=1),
        [],
    )
    summary_engagement = _safe(
        "summary_engagement",
        lambda: report(metrics=["engagementRate", "bounceRate", "averageSessionDuration", "sessionsPerUser", "keyEvents"], limit=1),
        [],
    )
    new_returning = _safe(
        "new_returning",
        lambda: report(
            dimensions=["newVsReturning"],
            metrics=["activeUsers", "sessions"],
            order_metric="activeUsers",
            limit=2,
        ),
        [],
    )
    ecommerce = _safe(
        "ecommerce",
        lambda: report(metrics=["totalRevenue", "ecommercePurchases", "purchaseRevenue"], limit=1),
        [],
    )

    realtime_total = _safe(
        "realtime_total",
        lambda: _run_realtime(client, property_id, metrics=["activeUsers"], limit=1),
        [],
    )
    realtime_pages = _safe(
        "realtime_pages",
        lambda: _run_realtime(client, property_id, dimensions=["unifiedScreenName"], metrics=["activeUsers"], limit=8),
        [],
    )
    realtime_countries = _safe(
        "realtime_countries",
        lambda: _run_realtime(client, property_id, dimensions=["country"], metrics=["activeUsers"], limit=8),
        [],
    )
    realtime_devices = _safe(
        "realtime_devices",
        lambda: _run_realtime(client, property_id, dimensions=["deviceCategory"], metrics=["activeUsers"], limit=8),
        [],
    )
    realtime_events = _safe(
        "realtime_events",
        lambda: _run_realtime(client, property_id, dimensions=["eventName"], metrics=["eventCount"], limit=8),
        [],
    )

    top_pages = _safe(
        "top_pages",
        lambda: report(
            dimensions=["pagePath", "pageTitle"],
            metrics=["screenPageViews", "activeUsers", "userEngagementDuration"],
            order_metric="screenPageViews",
            limit=12,
        ),
        [],
    )
    sources = _safe(
        "sources",
        lambda: report(
            dimensions=["sessionDefaultChannelGroup", "sessionSourceMedium", "sessionCampaignName"],
            metrics=["sessions", "activeUsers", "newUsers", "keyEvents"],
            order_metric="sessions",
            limit=12,
        ),
        [],
    )
    countries = _safe(
        "countries",
        lambda: report(dimensions=["country"], metrics=["activeUsers", "sessions"], order_metric="activeUsers", limit=10),
        [],
    )
    cities = _safe(
        "cities",
        lambda: report(dimensions=["city"], metrics=["activeUsers", "sessions"], order_metric="activeUsers", limit=10),
        [],
    )
    languages = _safe(
        "languages",
        lambda: report(dimensions=["language"], metrics=["activeUsers", "sessions"], order_metric="activeUsers", limit=10),
        [],
    )
    devices = _safe(
        "devices",
        lambda: report(dimensions=["deviceCategory"], metrics=["activeUsers", "sessions", "screenPageViews"], order_metric="activeUsers", limit=10),
        [],
    )
    browsers = _safe(
        "browsers",
        lambda: report(dimensions=["browser"], metrics=["activeUsers", "sessions"], order_metric="activeUsers", limit=10),
        [],
    )
    operating_systems = _safe(
        "operating_systems",
        lambda: report(dimensions=["operatingSystem"], metrics=["activeUsers", "sessions"], order_metric="activeUsers", limit=10),
        [],
    )
    events = _safe(
        "events",
        lambda: report(dimensions=["eventName"], metrics=["eventCount", "activeUsers", "keyEvents"], order_metric="eventCount", limit=15),
        [],
    )
    key_events = _safe(
        "key_events",
        lambda: report(dimensions=["eventName"], metrics=["keyEvents", "eventCount"], order_metric="keyEvents", limit=15),
        [],
    )
    traffic_series = _safe(
        "traffic_series",
        lambda: report(dimensions=["date"], metrics=["activeUsers", "sessions", "screenPageViews", "keyEvents"], limit=120),
        [],
    )

    startsida = _safe("funnel_home", lambda: report(metrics=["screenPageViews"], dimension_filter=_string_filter("pagePath", "/", "EXACT"), limit=1), [])
    tjanster = _safe("funnel_services", lambda: report(metrics=["screenPageViews"], dimension_filter=_string_filter("pagePath", "/tjanster"), limit=1), [])
    kontakt = _safe("funnel_contact", lambda: report(metrics=["screenPageViews"], dimension_filter=_string_filter("pagePath", "/kontakt"), limit=1), [])
    submit_events = _safe(
        "funnel_submit",
        lambda: report(metrics=["eventCount"], dimension_filter=_event_filter(["form_submit", "contact_submit", "generate_lead"]), limit=1),
        [],
    )

    return {
        "configured": True,
        "propertyId": property_id,
        "range": range_key,
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "summary": {
            "traffic": summary_traffic,
            "engagement": summary_engagement,
            "newReturning": new_returning,
            "ecommerce": ecommerce,
        },
        "realtime": {
            "total": realtime_total,
            "pages": realtime_pages,
            "countries": realtime_countries,
            "devices": realtime_devices,
            "events": realtime_events,
        },
        "trafficSeries": traffic_series,
        "topPages": top_pages,
        "sources": sources,
        "geography": {
            "countries": countries,
            "cities": cities,
            "languages": languages,
        },
        "tech": {
            "devices": devices,
            "browsers": browsers,
            "operatingSystems": operating_systems,
        },
        "events": events,
        "keyEvents": key_events,
        "ecommerce": ecommerce,
        "manualRevenue": manual_revenue,
        "funnel": [
            {"step": "Startsida", "metric": "screenPageViews", "value": _sum_metric(startsida, "screenPageViews")},
            {"step": "Tjänster", "metric": "screenPageViews", "value": _sum_metric(tjanster, "screenPageViews")},
            {"step": "Kontakt", "metric": "screenPageViews", "value": _sum_metric(kontakt, "screenPageViews")},
            {"step": "Skickat formulär", "metric": "eventCount", "value": _sum_metric(submit_events, "eventCount")},
        ],
    }
