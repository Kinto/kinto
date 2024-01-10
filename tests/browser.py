import time
import unittest
from urllib.parse import urljoin

import requests
from selenium import webdriver
from selenium.webdriver.common.by import By


SERVER_URL = "http://localhost:8888/v1"
DEFAULT_AUTH = ("user", "p4ssw0rd")


class BrowserTest(unittest.TestCase):
    def setUp(self):
        options = webdriver.FirefoxOptions()
        options.headless = True
        self.driver = webdriver.Firefox(options=options)
        self.driver.implicitly_wait(10)  # seconds

    @classmethod
    def setUpClass(cls):
        # Make sure our user exists.
        requests.post(
            urljoin(SERVER_URL, "/accounts"),
            json={"data": {"id": DEFAULT_AUTH[0], "password": DEFAULT_AUTH[1]}},
        )

        # Create a bucket and a collection for our user.
        bucket_url = urljoin(SERVER_URL, "/buckets/workspace")
        collection_url = f"{bucket_url}/collections/articles"
        session = requests.Session()
        session.auth = DEFAULT_AUTH
        resp = session.put(bucket_url)
        resp.raise_for_status()
        resp = session.put(collection_url)
        resp.raise_for_status()

    def tearDown(self):
        self.driver.close()

    def test_admin_ui_renders_properly(self):
        base_url = urljoin(SERVER_URL, "/v1/admin/")
        self.driver.get(base_url)

        # Load auth page.
        header = self.driver.find_element(By.CSS_SELECTOR, ".content div > h1")
        self.assertIn("Administration", header.text)
        self.assertTrue(header.is_displayed())

        # Select Kinto Accounts.
        radio = self.driver.find_element(By.XPATH, "//label[contains(.,'Kinto Account Auth')]")
        radio.click()

        # Fill username and password.
        user_field = self.driver.find_element(By.ID, "root_credentials_username")
        user_field.send_keys(DEFAULT_AUTH[0])
        user_pass = self.driver.find_element(By.ID, "root_credentials_password")
        user_pass.send_keys(DEFAULT_AUTH[1])
        # Login
        submit = self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
        submit.click()

        # Navigate to simple review page (uses React Hooks and broke a few times)
        review_url = base_url + "#/buckets/workspace/collections/articles/simple-review"
        self.driver.get(review_url)
        time.sleep(1)
        self.assertTrue(self.driver.find_element(By.CSS_SELECTOR, ".alert-warning").is_displayed())
