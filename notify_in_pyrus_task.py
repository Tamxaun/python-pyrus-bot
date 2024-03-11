from pyrus import client
import pyrus.models.requests
from datetime import datetime


class Notification_in_pyrus_task:
    def __init__(self, catalog_id, pyrus_login, pyrus_security_key, sentry_sdk):
        self.catalog_id = int(catalog_id)
        self.pyrus_client = client.PyrusAPI(pyrus_login, pyrus_security_key)
        self.sentry_sdk = sentry_sdk

    def _create_shipment_date_formatted_text(self, author, date: str, time: str = ""):
        author_link_name = f"<a href='https://pyrus.com/t#{author['id']}'>{author['first_name']} {author['last_name']}</a>"
        date_obj = datetime.strptime(str(date), "%Y-%m-%d")
        formatted_date = date_obj.strftime("%A, %B %d, %Y")
        formated_time = f", {time}" if time != "" else ""
        formatted_text = "{}<br>Связаться с Клиентом и подтвердить дату забора заказа на сегодня! ({}, {})<br>В случае изменение даты, обязательно изменить поле 'Дата отгрузки' в форме на актуальную дату, а также не забыть сменить даты реализации и ордера в 1С.".format(
            author_link_name, formatted_date, formated_time
        )
        return formatted_text

    def _auth(self):
        auth_response = self.pyrus_client.auth()
        if auth_response.success:
            pass
        else:
            self.sentry_sdk.set_context("Auth error", auth_response)
            self.sentry_sdk.capture_message(
                "Nonitification Debug message: error with auth", level="error"
            )
            raise Exception(auth_response)

    def _get_catalog(self):
        catalog_response = self.pyrus_client.get_catalog(self.catalog_id)
        items = catalog_response.items
        return items

    def _get_task(self, task_id):
        task = self.pyrus_client.get_task(task_id).task
        return task

    def send(self):
        self._auth()
        catalog = self._get_catalog()
        if catalog:
            date_now = datetime.now().date()
            catalog_headers = ["task_id", "timestamp", "message_type"]
            catalog_items_new = []
            for item in catalog:
                item_id, item_timestamp, item_type_message = item["values"]
                timestamp = datetime.strptime(str(item_timestamp), "%Y-%m-%d")
                if timestamp.date() == date_now:
                    task = self._get_task(item_id)
                    if (
                        item_type_message == "shipment_date"
                        and task is not None
                        and task.author is not None
                    ):
                        formatted_text = self._create_shipment_date_formatted_text(
                            author=task.author, date=item_timestamp
                        )
                        request = pyrus.models.requests.TaskCommentRequest(
                            text=formatted_text
                        )
                        task = self.pyrus_client.comment_task(item_id, request).task
                        print(
                            "✅ Notify: Notification is sent. This item will be deleted"
                        )
                if timestamp.date() > date_now:
                    print("✅ Notify: This item will be added to new catalog")
                    catalog_items_new.append(
                        [item_id, item_timestamp, item_type_message]
                    )
                if timestamp.date() < date_now:
                    print("⚒️ Notify: This item will be deleted")
                    pass
            request = pyrus.models.requests.SyncCatalogRequest(
                apply=True, catalog_headers=catalog_headers, items=catalog_items_new
            )
            response = self.pyrus_client.sync_catalog(self.catalog_id, request)
            delted = response.deleted
            updated = response.updated
            added = response.added
            new_headers = response.catalog_headers
            print("✅ Notify: All items are checked")
            print("🔎 Notify: delted: ", delted)
            print("🔎 Notify: updated: ", updated)
            print("🔎 Notify: added: ", added)
            print("🔎 Notify: new_headers: ", new_headers)
