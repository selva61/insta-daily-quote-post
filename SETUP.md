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

## 2. Create a Meta app and add the Instagram use case

The Meta dashboard moved from an "Add Product" model to a "Use cases" model — this is
the current (verified working, Aug 2026) flow:

1. Go to [developers.facebook.com/apps](https://developers.facebook.com/apps) → **Create App**.
2. App type: **Other** → **Business** (or "Consumer" if that's not offered — either works,
   since you're not submitting for App Review).
3. On the app dashboard, go to the **Use cases** tab.
4. Pick **"Manage messaging and content on Instagram"** → **Customize**. (Not obviously
   named "Instagram," but this is the one that unlocks content-publishing permissions.)
5. In the left-side menu of that page, click **"API setup with Instagram Login"**.

## 3. Work through the setup checklist on that page

1. **Add required permissions** — the page lists `instagram_business_basic`,
   `instagram_business_manage_comments`, `instagram_business_manage_messages` as
   required; add those. Then separately find and add
   **`instagram_business_content_publish`** — it won't be in the "required" list but is
   the one that actually lets the API post — it'll show "Ready for testing", meaning it
   works immediately on your own tester account with no app review.
2. **Instagram Tester** — add `nocturnalnotesselva` as a tester, then on the Instagram
   app itself: **Settings → Website permissions → Tester invites → Accept**. Skip this
   and every API call fails with a silent permission error.
3. **Configure webhooks** — skip entirely, leave blank. Webhooks are for *receiving*
   events (comments, DMs); this pipeline only publishes.
4. **Set up Instagram business login** — it asks for a **Redirect URL**. This pipeline
   never uses a custom OAuth page (see step 4 below), so any real HTTPS URL satisfies
   the field — your repo URL works fine:
   `https://github.com/selva61/insta-daily-quote-post`
5. **Complete app review** — skip. Only required if people *other than you* need to use
   the app. Posting to your own tester account works indefinitely in development mode.

## 4. Generate the access token

Once the checklist above is done, go to that page's **"Generate access tokens"** step
and click **Generate token** next to `nocturnalnotesselva`.

The token this button gives you is **already a long-lived, directly-usable token** —
verified by calling `graph.instagram.com/me` with it (works immediately) and
`graph.instagram.com/refresh_access_token` with it (returns a fresh 60-day token right
away). No OAuth `ig_exchange_token` step, no App Secret needed for this at all — that
manual exchange is only relevant if you're building your own OAuth authorization flow,
which the dashboard button does for you.

The **"Generate access tokens"** section of the page also displays your Instagram
**User ID** directly next to the account name (a long numeric ID) — that's `IG_USER_ID`,
no separate API call needed.

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

| Secret | Value | Status |
|---|---|---|
| `IG_USER_ID` | from step 4 | ✅ set (`17841470838558384`) |
| `IG_ACCESS_TOKEN` | the long-lived token from step 4 | ✅ set |
| `PEXELS_API_KEY` | from step 5 | ✅ set |
| `GH_PAT_SECRETS` | a fine-grained PAT, scoped to just this repo, with **Secrets: Read and write** permission — create at github.com/settings/tokens?type=beta. Used only by `refresh-token.yml` to rotate `IG_ACCESS_TOKEN` automatically. | ✅ set |

**Approval environment**: already created — `instagram-live` exists on this repo with
you set as the required reviewer.

This is the gate: every day, the `generate` job builds the card and posts a preview to
the workflow run's job summary; the `publish` job then waits for your approval in that
same run before it touches Instagram.

Note: posts are Reels now (for background music — Instagram's music library isn't
API-accessible, only pre-embedded audio in a video is). No new Meta app permissions
needed for this — `instagram_business_content_publish` (already granted in step 3)
covers both photo and Reels publishing.

---

## 7. Test it

1. Actions tab → **Daily Instagram quote post** → **Run workflow** → check
   **dry_run** → Run. This generates a real Reel (quote card + zoom + royalty-free
   music), commits it, and verifies the public URL is fetchable — but stops short of
   posting.
2. Open the run, check the `generate` job's summary for the thumbnail + caption + a
   link to preview the Reel with audio before deciding.
3. If it looks good, run again **without** dry_run checked, approve when prompted, and
   confirm the Reel lands on `@nocturnalnotesselva`'s Reels tab (Instagram's own
   processing can lag a little past our own poll completing).
4. From here the `30 3 * * *` UTC cron takes over — one Reel a day, paused for your
   approval each time.

## Local testing (optional)

`ffmpeg` composites the still card into the Reel — install it once for local testing:
`brew install ffmpeg`. Not needed for the actual pipeline; GitHub's `ubuntu-latest`
runners have it preinstalled already.

## Turning off approval (optional, later)

If you decide you trust the pipeline and want it fully hands-off, delete the
`environment: instagram-live` line from the `publish` job in
`.github/workflows/daily-post.yml` — the job will then run straight through.
