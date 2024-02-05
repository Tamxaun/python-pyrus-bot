# import unittest
# from main import pyrus_api
# from bot.reminder_step import format_fields


# class Test_bot_reminder_step(unittest.TestCase):
#     def test_field_scan(self):
#         forms_test = pyrus_api.get_request("https://api.pyrus.com/v4/forms/1058514")
#         task_test = pyrus_api.get_request("https://api.pyrus.com/v4/tasks/201740291")

#         self.assertNotIsInstance(forms_test, type(None))
#         self.assertNotIsInstance(task_test, type(None))

#         if forms_test is not None and task_test is not None:
#             fields = format_fields(
#                 forms_test["fields"],
#                 task_test["task"]["fields"],
#                 1,
#                 field_html_tag_begin="<li>",
#                 field_html_tag_end="</li>",
#             )

#             print("🚀 fields", fields)

#         self.assertEqual(True, True)


# if __name__ == "__main__":
#     unittest.main()
