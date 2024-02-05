import re
import unittest

from playwright.sync_api import expect, sync_playwright


baseUrl = "http://localhost:8888/v1/"
auth = {"user": "user", "password": "p4ssw0rd"}

browser = sync_playwright().start().firefox.launch()
context = browser.new_context(base_url=baseUrl)
page = browser.new_page()


class BrowserTest(unittest.TestCase):
    def setUp(self):
        request = context.request

        request.post("accounts", data={"data": {"id": auth["user"], "password": auth["password"]}})

    def test_login_and_view_home_page(self):
        page.goto(f"{baseUrl}admin/")

        expect(page).to_have_title(re.compile("Kinto Administration"))

        page.get_by_label("Kinto Account Auth").click()
        txtUsername = page.get_by_label(re.compile("Username"))
        txtPassword = page.get_by_label(re.compile("Password"))

        txtUsername.fill(auth["user"])
        txtPassword.fill(auth["password"])
        page.get_by_text(re.compile("Sign in using Kinto Account Auth")).click()

        expect(page.get_by_text("Kinto Administration")).to_be_visible()
        expect(page.get_by_text("project_name")).to_be_visible()
        expect(page.get_by_text("project_version")).to_be_visible()
        expect(page.get_by_text("http_api_version")).to_be_visible()
        expect(page.get_by_text("project_docs")).to_be_visible()
