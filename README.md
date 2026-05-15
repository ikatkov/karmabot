⚠️ Karmabot is archived and will not receive any updates going forward

# Karmabot for Slack

This is an implementation of Karma in Python that should be fairly robust to handle a largerish deployment.

## Features

* Karma rate-limiting:  Only 60 Karma operations per hour from any user
* Separation of thing/user/group/channel Karma
* Top and Bottom list for all, things, users, channels
* Karma expiration
* General Karma statistics


## What is Karma?

Karma is a quazi-reputation system.  You may have used it in other Chat systems.  Simply put, you can add a `++` or `--` to the end of subject to add or remove karma.
Anyone (except bots) can give Karma.  Karma isn't a perfect system — it can be gamed, but it can be a fun way to show your gratitude when someone helps you out.

## Architecture

This implementation uses Flask and SQLite.


The Flask web service listens for the events from Slack and executes them in a separate thread using `flask-executor`. SQLite is used to store the Karma operations.

### SQLite

Karma operations are stored in the `karma_events` table.  Each row includes:

```
{
    "workspace_id" : "T12345678",
    "expires_at" : "2018-06-02T20:57:13",
    "created_at" : "2018-03-04T20:57:13",
    "subject" : "foo",
    "subject_type" : "thing",
    "gifter" : "U12345678,
    "quantity" : 1
}
```

For the `subject_type`, it can be one of `thing`, `user`, `channel`, or `group`. Users, Channels, and Groups should be stored by their ID, not the display name, to support name changes without loosing Karma.

SQLite does not have MongoDB-style TTL indexes. Karmabot removes expired karma rows before reads and writes.

### Observability

Karmabot emits metrics through OpenTelemetry when `OTEL_EXPORTER_OTLP_ENDPOINT` is configured. The app is vendor-neutral; point the endpoint at any OTLP-compatible collector or leave it unset to disable metric export.

## Setup

* Choose a persistent location for the SQLite database if you don't want to loose your Karma
* Create the app entry in `api.slack.com/apps`.
  * Create `/karma` command pointed to the proper HTTP endpoint for commands
    * Make sure to select "Escape channels, users, and links"
* Start the Karmabot instance somewhere.  Its designed to be a Docker service, and configuration is handled via environment variables. 
* Update the app entry in `api.slack.com/apps`:
 * Create event subscriptions and point at the proper HTTP endpoint for events. Subscribe to Bot Events:
     * `app_mention`
     * `message.channels`
     * `message.groups`
  * Set OAuth permissions to include:
    * `bot`
    * `commands`
    * `channels:write`
    * `chat:write:bot`
    * `im:write`
* Invite the Karma bot into channels you wish to track Karma

### Development

This project uses `uv` for dependency management.

```
uv sync
uv run ruff check karmabot tests
uv run pytest
uv run radon cc karmabot -a -nc
```

### CI and Docker Publishing

GitHub Actions runs Ruff, pytest, Radon, and a Docker build on every push and pull request.

Docker Hub publishing is manual. Start the `Publish Docker image` workflow, choose the image tag to publish, and optionally publish `latest`. Configure these repository secrets first:

* `DOCKERHUB_USERNAME` Docker Hub username or organization.
* `DOCKERHUB_TOKEN` Docker Hub access token.

Images are published as `${DOCKERHUB_USERNAME}/karmabot`.

### Environment Variables

As mentioned, configuration is handled via environment variables.  Here is the list of things you can configure:
 * `VERIFICATION_TOKEN` The verification from your Slack App config. There is no default, you must set this.
 * `SQLITE_PATH` The SQLite database path. Defaults to `data/karmabot.db`
 * `OTEL_EXPORTER_OTLP_ENDPOINT` Optional OTLP endpoint for OpenTelemetry metrics. When unset, metrics export is disabled.
 * `OTEL_SERVICE_NAME` The OpenTelemetry service name. Defaults to `karmabot`.
 * `SLACK_EVENTS_ENDPOINT` The base URI to accept Slack events on.  Defaults to `/slack_events`
 * `KARMA_RATE_LIMIT` Number of Karma operations per hour a user can do.  Defaults to `60`
 * `KARMA_TTL` How quickly Karma expires, in days.  Defaults to `90`
 * `KARMA_COLOR` The highlight color to use when Karmabot posts messages. Defaults to `#af8b2d`
 * `FAKE_SLACK` Only used for testing.  When set to `True` it will not actually connect to Slack, and instead mocks out the Slack services.

Since the app may be installed to multiple workspaces, there are two ways to handle the OAuth and Bot access tokens, using Hashicorp Vault or environment variables.

Using Vault requires more infrastructure, but allows for dynamically adding workspaces without needing to restart services.  Using environment variables is simpler, but requires restarting the service when adding new workspaces.


To use environment variables, leave `USE_VAULT` unset, or set it to `False`. Then store the tokens like this:

 * `ACCESS_{workspace_id}` The OAuth Access Token for workspace `{workspace_id}`
 * `BOT_{workspace_id}` The Bot Access Token for workspace `{workspace_id}`
 

To use Vault, set

 * `USE_VAULT` to `True` . Defaults to False.
 * `VAULT_URI` to the Vault URI to connect to.  Defaults to None.
 * `VAULT_TOKEN` to the Vault authentication token. Defaults to None.
 * `VAULT_BASE` to the location in Vault where tokens can be found.  Defaults to `secrets`

Store the tokens in the `VALUT_BASE` location with the name `access_{workspace_id}.txt` where `{workspace}` is the workspace ID (case sensitive), using the kv1 method.  For example:

```
vault write secret/secrets/access_T1234.txt value=xoxa-1234-5678
vault write secret/secrets/bot_T1234.txt value=xoxb-1234-5678
```  

## How to contribute

This is intended to be a community driven project. Feel free to submit a PR if you think you can improve it, or just open an issue if you have an idea but can't implement it.

We won't take every feature request, but if its a good idea, we will take it in.


## Contributors

* Jay Kline (@slushpupie)
* Jordan Sussman (@JordanSussman)
* Jim Male (@JMaleTarget)
* Emmanuel Meinen (@meinenec)
* James Bell (@lemoney)
* Thiti Vutisalchavakul (@vutisat)
