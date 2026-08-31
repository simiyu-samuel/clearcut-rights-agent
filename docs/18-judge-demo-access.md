# Demo access

ClearCut supports a dedicated public demo path for hackathon reviewers. It is enabled only when the hosted web build and API runtime are configured with the same demo email.

## Firebase account

Create an Email/Password user in Firebase Authentication:

~~~text
Email:    demo@clearcut.app
Password: ClearCut-Judge-2026!
Name:     Hackathon Judge
~~~

Email verification is not required by the current ClearCut sign-in flow. Google sign-in, normal email/password registration, and workspace invitations remain available for regular users.

## Configuration

Web build arguments:

~~~text
NEXT_PUBLIC_DEMO_ENABLED=true
NEXT_PUBLIC_DEMO_EMAIL=demo@clearcut.app
NEXT_PUBLIC_DEMO_PASSWORD=ClearCut-Judge-2026!
~~~

API runtime variables:

~~~text
DEMO_ACCESS_ENABLED=true
DEMO_ACCESS_EMAIL=demo@clearcut.app
DEMO_ACCESS_ORGANIZATION_ID=clearcut-demo-org
DEMO_ACCESS_ORGANIZATION_NAME=DEMO
DEMO_ACCESS_ROLE=producer
~~~

The demo password belongs only in the web build because Firebase performs the credential check. The API receives no password; it verifies the Firebase ID token and matches the verified email against its allowlist.

## Seeded judge journey

The first successful demo sign-in creates or reuses an isolated `DEMO` organization and adds:

- **The Last Signal**, a feature-film project with territories, distribution modes, and a release target.
- A screenplay source with five extracted rights-bearing assets.
- Two completed Parallel research snapshots with four research angles each.
- Two pending human-review clearance cards with evidence and risk scores.
- A draft music permission request.
- Activity history, a notification, and a ready clearance report with PDF support.

The seed uses deterministic identifiers and is safe to run repeatedly. It is a demonstration snapshot, not a declaration that any asset is legally cleared. Judges should be encouraged to open the project, inspect the source, review a card, try a decision, view the report, and then create or upload their own material if desired.

## Reset and teardown

To reset the demo workspace before judging, remove the `clearcut-demo-org` tenant records from the staging database or restore a pre-demo Cloud SQL backup, then sign in again. To disable public access, set `DEMO_ACCESS_ENABLED=false` on the API and build the web image with `NEXT_PUBLIC_DEMO_ENABLED=false`. Rotate or delete the Firebase user after the contest.
