# LoanTrack full-stack demo

This is a test-only loan-progress portal with a Flask backend, browser sessions, customer/manager logins, a seeded test database, shared status updates, and a simulated collateral/title-verification workflow.

## Install it as a phone app

This version is a Progressive Web App (PWA). After deployment, open the Render URL using Chrome on Android and choose **Install app** or **Add to Home screen** from Chrome's menu. It will appear as LoanTrack on the phone. See `android-twa/README.md` when you are ready to create an installable Android APK wrapper.

## Test accounts

| Role | Username | Password/PIN |
| --- | --- | --- |
| Customer | `LT-260912-041` | `2468` |
| Customer | `LT-260911-018` | `1357` |
| Manager | `manager.demo` | `Manager2026!` |

Sign in as the manager, update a case, sign out, and then sign in as the matching customer to see the progress bar change.

## Test the collateral workflow

1. Sign in as `manager.demo`.
2. Open Mary Wanjiku's application and use **Collateral & title verification - test workflow**.
3. Change the test status, save, then sign in as Mary to see the customer-safe collateral update.

The workflow records a local demo audit trail only. It does **not** contact Ardhisasa, the Ministry of Lands or any official registry, and “Demo: simulated match” is not an official verification result.

The manager dashboard has an **Ardhisasa integration simulator**. It creates a fictional official-search reference and demonstrates either a matching result or a discrepancy for presentation purposes. It is visibly labelled as a simulation and sends no data outside the demo application.

## Render deployment

1. Create a separate GitHub repository and upload all files in this folder.
2. In Render, choose **New → Blueprint**, select the repository, and deploy.
3. Open the generated `onrender.com` address.

Render's filesystem can reset on a redeploy or restart. The app automatically recreates its fictional demo data, so that is fine for presentation use. Do not add real customer data.

## Production boundary

This is not a banking or lending system. It has no production authentication, KYC, regulatory integration, audit-security controls, or encrypted bank-data architecture. A real release requires written bank authorization, professional security review, legal/compliance approval, and an authorised Ministry of Lands integration. Never automate logins to a government portal or claim title verification from a document upload alone.
