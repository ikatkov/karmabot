# Running Karmabot Against a Real Slack Workspace

This guide covers running Karmabot locally while receiving real Slack events and
commands through an HTTPS tunnel.

## 1. Run Karmabot Locally

Install dependencies:

```bash
uv sync
```

Start the app with fake Slack disabled:

```bash
VERIFICATION_TOKEN=<slack-verification-token> \
FAKE_SLACK=False \
LOG_LEVEL=DEBUG \
SQLITE_PATH=.context/karmabot-real-slack.db \
BOT_<TEAM_ID>=xoxb-... \
ACCESS_<TEAM_ID>=xoxp-or-xoxa-if-needed \
uv run gunicorn -b 127.0.0.1:5000 --access-logfile - 'karmabot:create_app()'
```

Replace `<TEAM_ID>` with the Slack workspace ID, such as `T123456`.

## 2. Expose the Local Server Over HTTPS

Slack needs a public HTTPS URL. One common local option is ngrok:

```bash
ngrok http 5000
```

Use the generated `https://...ngrok-free.app` URL in Slack.

## 3. Configure Slack App URLs

Set these Slack app URLs, replacing `<ngrok-host>` with the generated host:

```text
Events Request URL:
https://<ngrok-host>/slack_events/v1/karmabot-v1_events

/karma Request URL:
https://<ngrok-host>/slack_events/v1/karmabot-v1_commands

/badge Request URL:
https://<ngrok-host>/slack_events/v1/karmabot-v1_commands

Interactivity Request URL:
https://<ngrok-host>/slack_events/v1/karmabot-v1_interactions
```

For `/karma` and `/badge`, enable "Escape channels, users, and links sent to
your app". Karmabot expects Slack IDs such as `<@U...>` and `<#C...>`.

## 4. Configure Slack Scopes and Events

Start with these bot token scopes:

```text
chat:write
commands
app_mentions:read
channels:history
groups:history
users:read
channels:read
```

Subscribe to these bot events:

```text
app_mention
message.channels
message.groups
```

After changing scopes or events, reinstall the Slack app into the workspace.
Then invite the bot to the channel you want to test in.

## Verification Token Caveat

This app currently validates Slack's legacy `verification token` field. Slack's
current platform guidance prefers signed request verification with the app
signing secret. If a new Slack app does not provide a usable verification token,
Karmabot will need a small auth update before real Slack testing works.

