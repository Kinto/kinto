import { test, expect, request } from '@playwright/test';

const baseUrl = "http://localhost:8888/v1/";
const auth = {
  user: "user",
  password: "p4ssw0rd"
};


test('init user account', async() => {
  const context = await request.newContext({
    baseURL: baseUrl
  });

  try { // create test user
    await context.post("accounts", {
      data: {
        data: {
          id: auth.user,
          password: auth.password
        }
      }
    });
  } catch (ex) {
    console.warn("Error while setting up test user, already exists?", ex);
  }
});


test('Login form loads and user is able to login', async ({ page }) => {
  await page.goto(`${baseUrl}admin/`);
  
  await expect(page).toHaveTitle(/Kinto Administration/);
  await page.getByLabel("Kinto Account Auth").click();

  const txtUsername = await page.getByLabel(/Username/);
  const txtPassword = await page.getByLabel(/Username/);
  expect(txtUsername).toBeTruthy();
  expect(txtPassword).toBeTruthy();

  txtUsername.fill(auth.user);
  txtPassword.fill(auth.password);
  await page.getByText(/Sign in using Kinto Account Auth/).click();

  await expect(page.getByText("Kinto Administreation")).toBeTruthy();
  await expect(page.getByText("project_name")).toBeTruthy();
  await expect(page.getByText("project_version")).toBeTruthy();
  await expect(page.getByText("http_api_version")).toBeTruthy();
  await expect(page.getByText("project_docs")).toBeTruthy();
});
