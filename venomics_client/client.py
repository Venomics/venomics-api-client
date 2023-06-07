import json
import requests
import time
from datetime import datetime

class VenomicsAPIClient:
    def __init__(self, api_key: str, host: str="https://www.venomics.xyz/"):
        self.api_key = api_key
        self.host = host

        self.s = requests.Session()
        self.s.headers.update({"Authorization": f"Key {api_key}"})

        if not self.test_credentials():
            raise Exception(f"Authorization with key {self.api_key} failed.")


    def get(self, uri: str,  **kwargs):
        res = self.s.get(f"{self.host}/api/{uri}",  **kwargs)

        if res.status_code != 200:
            raise Exception(f"[GET] /api/{uri} ({res.status_code})")

        return res

    def post(self, uri: str, payload: dict=None,  **kwargs):
        if payload is None or not isinstance(payload, dict):
            payload = {}

        data = json.dumps(payload)

        self.s.headers.update({"Content-Type": "application/json"})
        res = self.s.post(f"{self.host}/api/{uri}", data=data,  **kwargs)

        if res.status_code != 200:
            raise Exception(f"[POST] /api/{uri} ({res.status_code})")

        return res

    def delete(self, uri: str):
        res = self.s.delete(f"{self.host}/api/{uri}")

        if res.status_code != 200 and res.status_code != 204:
            raise Exception(f"[DELETE] /api/{uri} ({res.status_code})")

        return res

    def test_credentials(self):
        try:
            response = self.get("session")
            return True
        except requests.exceptions.HTTPError:
            return False

    def refresh_query(self, qry_id: int):
        return self.post(f"queries/{qry_id}/refresh")

    def alerts(self):
        """GET api/alerts
        This API endpoint is not paginated."""
        return self.get("alerts").json()

    def get_alert(self, alert_id):
        """GET api/alerts/<alert_id>"""
        return self.get(f"alerts/{alert_id}").json()

    def create_alert(self, name, options, query_id):
        """POST api/alerts to create a new alert"""

        payload = dict(
            name=name,
            options=options,
            query_id=query_id,
        )
        return self.post(f"alerts", payload).json()

    def update_alert(self, id, name=None, options=None, query_id=None, rearm=None):

        payload = dict(name=name, options=options, query_id=query_id, rearm=rearm)

        no_none = {key: val for key, val in payload.items() if val is not None}

        return self.post(f"alerts/{id}", no_none)


    def paginate(self, resource, page=1, page_size=100, **kwargs):
        """Load all items of a paginated resource
        """

        response = resource(page=page, page_size=page_size, **kwargs)
        items = response["results"]

        if response["page"] * response["page_size"] >= response["count"]:
            return items
        else:
            return [
                *items,
                *self.paginate(resource, page=page + 1, page_size=page_size, **kwargs),
            ]


    def queries(self, page=1, page_size=25, only_favorites=False):
        """GET queries"""

        target_url = "queries/favorites" if only_favorites else "queries"

        return self.get(target_url, params=dict(page=page, page_size=page_size)).json()

    def create_favorite(self, _type: str, id):
        """POST to queries/<id>/favorite or dashboards/<id>/favorite"""

        if _type == "dashboard":
            url = f"dashboards/{id}/favorite"
        elif _type == "query":
            url = f"queries/{id}/favorite"
        else:
            return

        return self.post(url, payload={})

    def get_query(self, query_id):
        """GET queries/<query_id>"""
        return self.get(f"queries/{query_id}").json()

    def users(self, page=1, page_size=25, only_disabled=False):
        """GET users"""

        params = dict(page=page, page_size=page_size, disabled=only_disabled)

        return self.get("users", params=params).json()

    def dashboards(self, page=1, page_size=25, only_favorites=False):
        """GET dashboards"""

        target_url = "dashboards/favorites" if only_favorites else "dashboards"

        return self.get(target_url, params=dict(page=page, page_size=page_size)).json()

    def get_dashboard(self, id):
        """GET dashboards/<id>"""

        return self.get(
            f"dashboards/{id}",
        ).json()

    def get_data_sources(self):
        """GET data_sources"""
        return self.get(
            "data_sources",
        ).json()

    def get_data_source(self, id):
        """GET data_sources/<id>"""

        return self.get("data_sources/{}".format(id)).json()

    def dashboard(self, slug):
        """GET dashboards/{slug}"""
        return self.get("dashboards/{}".format(slug)).json()

    def update_dashboard(self, dashboard_id, properties):
        return self.post(
            "dashboards/{}".format(dashboard_id), json=properties
        ).json()

    def create_widget(self, dashboard_id, visualization_id, text, options):
        data = {
            "dashboard_id": dashboard_id,
            "visualization_id": visualization_id,
            "text": text,
            "options": options,
            "width": 1,
        }
        return self.post("widgets", data)

    def duplicate_dashboard(self, slug, new_name=None):
        current_dashboard = self.dashboard(slug)

        if new_name is None:
            new_name = "Copy of: {}".format(current_dashboard["name"])

        new_dashboard = self.create_dashboard(new_name)
        if current_dashboard["tags"]:
            self.update_dashboard(
                new_dashboard["id"], {"tags": current_dashboard["tags"]}
            )

        for widget in current_dashboard["widgets"]:
            visualization_id = None
            if "visualization" in widget:
                visualization_id = widget["visualization"]["id"]
            self.create_widget(
                new_dashboard["id"], visualization_id, widget["text"], widget["options"]
            )

        return new_dashboard

    def duplicate_query(self, query_id, new_name=None):

        response = self.post(f"queries/{query_id}/fork")
        new_query = response.json()

        if not new_name:
            return new_query

        new_query["name"] = new_name

        return self.update_query(new_query.get("id"), new_query).json()

    def scheduled_queries(self):
        """Loads all queries and returns only the scheduled ones."""
        queries = self.paginate(self.queries)
        return filter(lambda query: query["schedule"] is not None, queries)

    def update_query(self, query_id, data):
        """POST /queries/{query_id} with the provided data object."""
        path = "queries/{}".format(query_id)
        return self.post(path, data)

    def update_visualization(self, viz_id, data):
        """POST /visualizations/{viz_id} with the provided data object."""
        path = "visualizations/{}".format(viz_id)
        return self.post(path, data)
