from pyrus import client
import pyrus.models.requests
from pyrus.models.entities import CatalogItem
from pyrus_api_handler import PyrusAPI
from datetime import datetime
from typing import List, Optional


class Notification_in_pyrus_task:
    def __init__(
        self, catalog_id, pyrus_login, pyrus_security_key, sentry_sdk, cache=None
    ):
        self.catalog_id = int(catalog_id)
        self.pyrus_client = client.PyrusAPI(pyrus_login, pyrus_security_key)
        self.pyrus_api = PyrusAPI(
            cache, pyrus_login, pyrus_security_key, self.pyrus_client.access_token
        )
        self.sentry_sdk = sentry_sdk

    def _create_shipment_date_formatted_text(self, author, date: str, time: str = ""):
        author_link_name = f"<a href='https://pyrus.com/t#{author.id}'>{author.first_name} {author.last_name}</a>"
        date_obj = datetime.strptime(str(date), "%Y-%m-%d")
        formatted_date = date_obj.strftime("%A, %d %B, %Y")
        formated_time = f", {time}" if time != "" else ""
        formatted_text = "{}<br>Связаться с Клиентом и подтвердить дату забора заказа на сегодня! ({}{})<br>В случае изменение даты, обязательно изменить поле 'Дата отгрузки' в форме на актуальную дату, а также не забыть сменить даты реализации и ордера в 1С.".format(
            author_link_name, formatted_date, formated_time
        )
        return formatted_text

    def _create_payment_date_formatted_text(self, author):
        author_link_name = f"<a href='https://pyrus.com/t#{author.id}'>{author.first_name} {author.last_name}</a>"
        formatted_text = f"{author_link_name}<br>❗Планируемый срок оплаты назначен на сегодня🗓️. Связаться с клиентом и согласовать оплату💵."
        return formatted_text

    def _auth(self):
        auth_response = self.pyrus_client.auth()
        if auth_response.success:
            pass
        else:
            self.sentry_sdk.set_context("Auth error", auth_response.original_response)
            self.sentry_sdk.capture_message(
                "Nonitification Debug message: error with auth", level="error"
            )
            raise Exception(auth_response.original_response)

    def _get_catalog(self):
        catalog_response = self.pyrus_client.get_catalog(self.catalog_id)
        items = catalog_response.items
        return items

    def _get_task(self, task_id):
        task = self.pyrus_client.get_task(int(task_id)).task
        return task

    def send(self):
        self._auth()
        catalog: Optional[List[CatalogItem]] = self._get_catalog()
        if catalog is not None:
            date_now = datetime.now().date()
            catalog_headers = ["task_id", "timestamp", "message_type"]
            catalog_items_new = []
            for item in catalog:
                if item.values is not None:
                    item_id, item_timestamp, item_type_message = item.values
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
                            """ Pyrus lib doesn't support formatting text

                                # request = pyrus.models.requests.TaskCommentRequest(
                                #     text=formatted_text
                                # )
                                # task = self.pyrus_client.comment_task(
                                #     int(item_id), request
                                # ).task
                            """
                            self.pyrus_api.post_request(
                                url=f"https://api.pyrus.com/v4/tasks/{int(item_id)}/comments",
                                data={"formatted_text": formatted_text},
                            )
                            print(
                                "✅ Notify: Notification is sent. This item will be deleted"
                            )
                        if (
                            item_type_message == "payment_date"
                            and task is not None
                            and task.author is not None
                        ):
                            formatted_text = self._create_payment_date_formatted_text(
                                author=task.author
                            )
                            self.pyrus_api.post_request(
                                url=f"https://api.pyrus.com/v4/tasks/{int(item_id)}/comments",
                                data={"formatted_text": formatted_text},
                            )
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
            if delted:
                print("🔎 Notify: delted: ", delted)

            updated = response.updated
            if updated:
                print("🔎 Notify: updated: ", updated)

            added = response.added
            if added:
                print("🔎 Notify: added: ", added)

            new_headers = response.catalog_headers
            if new_headers:
                print("🔎 Notify: new_headers: ", new_headers)
