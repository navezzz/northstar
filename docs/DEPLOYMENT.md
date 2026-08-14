# Deployment

## Phase 1: GitHub Pages

The workflow in `.github/workflows/pages.yml` runs on pushes to `main`, on a
manual dispatch, and at 4:37 PM America/New_York every weekday. The non-round
minute reduces the likelihood of GitHub's top-of-hour scheduler congestion.

Each run installs Northstar, stores raw Yahoo bars and corporate actions,
normalizes and validates them, creates a content-addressed dataset snapshot,
evaluates the strategy offline from that snapshot, and deploys `site/` as a
GitHub Pages artifact. Generated market data is not committed to Git.

GitHub runners are ephemeral. The dataset ID and manifest provenance are
published with the research result, but long-term Parquet archival requires
persistent Phase 2 storage.

The published site is read-only. It has no server process, credentials, account
state, or order execution. Both the calculation timestamp and each ticker's
market-data date are visible.

## Manual deployment

Open the repository's **Actions** tab, select **Refresh and deploy Northstar**,
and choose **Run workflow**. A manual run is useful after changing the watchlist
or strategy.

## Configuration

The default watchlist is defined by `NORTHSTAR_WATCHLIST`. The workflow currently
uses the application default. Add a repository variable and pass it into the
workflow when watchlist configuration needs to move out of source control.

Private-repository Pages availability depends on the GitHub account plan. If
Pages cannot be enabled while the repository remains private, retain this build
workflow and publish the `site/` artifact to another static host.

## Phase 2 boundary

Move to a persistent service when Northstar needs user authentication, portfolio
state edited from the browser, reliable job retries, alerting, intraday updates,
or broker integration. The strategy and provider modules remain reusable; the
static exporter is replaced by FastAPI plus PostgreSQL-backed endpoints.
