# Setup — one-time manual steps

Everything code-level is done. These steps can't be automated — they involve your
Instagram account, a Meta developer app, and GitHub repo settings. Do them in order.

---

## 1. Switch Instagram to a Business account

Instagram app → your profile → ☰ → **Settings and privacy** → **Account type and tools**
→ **Switch to professional account** → choose **Business** (not Creator — the publishing
API doesn't reliably support Creator accounts).

This is free and reversible. It adds Insights and a contact button to your profile; it
doesn't change who can see your posts.

---

## 2. Create a Meta app and add the Instagram product

1. Go to [developers.facebook.com/apps](https://developers.facebook.com/apps) → **Create App**.
2. App type: **Other** → **Business** (or "Consumer" if that's not offered — either works
   for this use case, since you're not submitting for App Review).
3. Once created, in the left sidebar: **Add Product** → find **Instagram** → **Set Up**.
4. Choose **API setup with Instagram login** (this is the Facebook-Page-free path).

## 3. Add yourself as an Instagram Tester

Still in the Instagram product setup page:

1. Under **Business login settings**, note the **Instagram App ID** and **App Secret**
   (Secret is under App Settings → Basic — click "Show").
2. Under **Instagram Tester**, click **Add Instagram Testers**, enter your
   `@nocturnalnotesselva` username, and send the invite.
3. On the Instagram app itself (phone or web): **Settings → Website permissions →
   Apps and websites → Tester invites**, and **accept** the invite.

Without this step, all API calls return a permission error — the account has to
explicitly accept being a tester of your app, since the app is in development mode.

## 4. Generate a long-lived access token

The Instagram product setup page has a **"Generate access token"** step (step 4 on that
page) that walks you through authorizing your own account and hands you a token
directly — use that; it's simpler than the manual OAuth exchange.

1. Click **Generate token**, log in as `@nocturnalnotesselva` when prompted, approve
   the requested permissions (`instagram_business_basic`,
   `instagram_business_content_publish`).
2. Copy the token shown — this is a **short-lived** token (1 hour). Immediately exchange
   it for a long-lived one (60 days):

   ```bash
   curl -s "https://graph.instagram.com/access_token?grant_type=ig_exchange_token&client_secret=<APP_SECRET>&access_token=<SHORT_LIVED_TOKEN>"
   ```

   The response's `access_token` is your long-lived token — this is what goes into the
   `IG_ACCESS_TOKEN` secret.

3. Get your Instagram User ID:

   ```bash
   curl -s "https://graph.instagram.com/me?fields=user_id,username&access_token=<LONG_LIVED_TOKEN>"
   ```

   The `user_id` in the response is `IG_USER_ID`.

Keep both values somewhere private for step 6 — don't commit them anywhere.

---

## 5. Get a Pexels API key

[pexels.com/api](https://www.pexels.com/api/) → **Get Started** → sign up (free) →
copy the API key from your dashboard. This is `PEXELS_API_KEY`.

---

## 6. Configure the repo

Already done: the repo is pushed to
[github.com/selva61/insta-daily-quote-post](https://github.com/selva61/insta-daily-quote-post)
(public) and the `instagram-live` approval environment exists with you as required
reviewer. What's left is adding secrets.

**Repo secrets** (Settings → Secrets and variables → Actions → New repository secret):

| Secret | Value |
|---|---|
| `IG_USER_ID` | from step 4 |
| `IG_ACCESS_TOKEN` | the long-lived token from step 4 |
| `PEXELS_API_KEY` | from step 5 |
| `GH_PAT_SECRETS` | a fine-grained PAT, scoped to just this repo, with **Secrets: Read and write** permission — create at github.com/settings/tokens?type=beta. Used only by `refresh-token.yml` to rotate `IG_ACCESS_TOKEN` automatically. |

**Approval environment**: already created — `instagram-live` exists on this repo with
you set as the required reviewer.

This is the gate: every day, the `generate` job builds the card and posts a preview to
the workflow run's job summary; the `publish` job then waits for your approval in that
same run before it touches Instagram.

---

## 7. Test it

1. Actions tab → **Daily Instagram quote post** → **Run workflow** → check
   **dry_run** → Run. This generates a real card, commits it, and verifies the public
   URL is fetchable — but stops short of posting.
2. Open the run, check the `generate` job's summary for the rendered card + caption.
3. If it looks good, run again **without** dry_run checked, approve when prompted, and
   confirm the post lands on `@nocturnalnotesselva`.
4. From here the `30 3 * * *` UTC cron takes over — one card a day, paused for your
   approval each time.

## Turning off approval (optional, later)

If you decide you trust the pipeline and want it fully hands-off, delete the
`environment: instagram-live` line from the `publish` job in
`.github/workflows/daily-post.yml` — the job will then run straight through.
