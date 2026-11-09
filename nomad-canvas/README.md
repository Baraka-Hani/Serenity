# Roam / Make

A responsive React prototype for founders, creators, and travellers. Visitors can add video clips; the browser samples a frame from the first clip and derives the site's colour palette and energy score locally. It also scans supported QuickTime/MP4 metadata for embedded ISO 6709 GPS coordinates and a capture date.

The landing-page primary action opens a three-part feed: **Discover** shows published videos playing inline, **Create** stages a video batch, album title, and optional destination, trip dates, and trip description, while **Friends** remains a future social feed placeholder. In Firebase mode, pressing **Publish collection** (after confirming visibility) publishes the trip and videos to signed-in app users. In local demo mode, **Save collection** remains device-only. Discover shows published collections, and opening one shows its trip details, clips, and travel logistics.

## Run locally

```bash
npm install
npm run dev
```

## Build

```bash
npm run build
```

## No-billing Firebase test deployment

The no-billing test uses Firebase Spark for Hosting, Authentication, and Firestore only. It does **not** enable billing or create a Firebase Storage bucket. Therefore users can create accounts and save private travel metadata, but they cannot publish or persist video albums across devices or accounts. The Create screen explains this limit and disables publishing when no Storage bucket is configured. Video clips can still be selected and analyzed locally during a session.

The repo includes `firebase.json` for the Vite `dist` output, SPA route fallback, and Firestore security rules. Install Node.js/npm and the Firebase CLI, sign in with `firebase login`, select the intended project with `firebase use <project-id>`, and configure `.env.local` from `.env.example` (leave `VITE_FIREBASE_STORAGE_BUCKET` empty), then run:

```bash
npm install
npm run build
firebase deploy --only hosting,firestore:rules
```

Before inviting test users, enable Email/Password (and optionally Google) in Firebase Authentication, create the Firestore database in the selected region, configure the Firebase web app settings, and add the Hosting domain to Authentication's authorized domains. A browser test account can then register from the app's sign-in screen. Do not commit `.env.local`, service-account keys, or payment secrets. Do not enable Blaze billing for this test deployment.

## Reuse on iOS

The palette extraction lives in `src/theme.ts`, separate from the interface. Keep this shared domain shape when moving to React Native, then swap its browser video/canvas implementation for a native frame extractor. The visual tokens (`primary`, `secondary`, `background`, `ink`, and `energy`) can be shared between the web and native themes.

## Firebase setup

Copy `.env.example` to `.env.local` and fill in the Firebase **web app** configuration values. `VITE_FIREBASE_STORAGE_BUCKET` is optional for this no-billing configuration and must remain empty. Enable Email/Password and Google sign-in in Firebase Authentication, create Firestore, then deploy `firestore.rules`. Never put service-account credentials, Stripe secret keys, or travel-provider API keys in Vite environment variables. Firebase Auth uses browser-local persistence so a signed-in user remains signed in across reloads and can sign out explicitly. On returning, the app restores the session and loads published trips and owned legacy albums in pages. Private approximate travel entries remain under `users/{uid}/travel`; creator-owned album records are under `users/{uid}/albums`.

When a Firebase Storage bucket is configured on a billing-enabled deployment, pressing **Publish collection** uploads videos to `publicTrips/{uid}/{tripId}/` and writes a public trip document to `publicTrips/{tripId}`. In this Spark test configuration, Storage is not initialized and publishing is disabled. Account email and private travel records are not copied to public documents.

When Firebase is not configured, the app remains in a local demo mode. Saving an album requires a valid email for this device's local feed. Album metadata is stored in local storage and video files are stored in IndexedDB, subject to browser storage quota; neither is authenticated or synchronized across devices.

## Travel inventory backend

The client only sends a travel search after the user presses **Find stays & activities**. It sends a location rounded to two decimal places, selected check-in/check-out dates, requested categories, and a Firebase ID token to `VITE_TRAVEL_SEARCH_URL`. Configure that value to a backend endpoint such as `POST /api/travel/search`. The endpoint must use HTTPS; plain HTTP is allowed only for local development. The backend must verify the Firebase token, validate dates and coordinates, rate-limit the caller, and call enabled lodging/activity providers using server-side credentials. Do not call partner APIs or expose provider keys directly from the browser.

Expected request body:

```json
{
  "location": { "latitude": 43.65, "longitude": -79.38 },
  "checkIn": "2026-11-01",
  "checkOut": "2026-11-04",
  "categories": ["stay", "activity"]
}
```

Expected response shape:

```json
{
  "offers": [
    {
      "id": "provider-offer-id",
      "name": "Example stay",
      "category": "stay",
      "provider": "Provider",
      "location": "City or area",
      "price": 180,
      "currency": "USD",
      "url": "https://provider.example/listing"
    }
  ]
}
```

The client validates offer fields and only renders HTTPS provider links. No travel inventory is available until the backend endpoint and provider agreements are configured.

### Stripe Connect and trip checkout

Creators can start Connect onboarding from their profile using `VITE_STRIPE_CONNECT_URL` (`POST`). The authenticated endpoint must create or resume a Stripe Connect account for the verified Firebase user and return `{ "url": "https://connect.stripe.com/..." }`. The client only accepts Stripe's HTTPS Connect host.

After inventory search, travelers can select priced items and continue to checkout through `VITE_TRIP_CHECKOUT_URL` (`POST`). The client sends the Firebase bearer token and `{ "tripId": "...", "offerIds": ["..."], "checkIn": "YYYY-MM-DD", "checkOut": "YYYY-MM-DD" }`; it deliberately does not send prices, Stripe account IDs, or redirect URLs. The authenticated server must load the published trip, verify its creator and completed Connect onboarding, revalidate each provider offer's availability and price for those dates, create a Stripe Checkout session that routes funds to the creator's connected account, and fulfill/confirm the provider bookings idempotently. It returns `{ "url": "https://checkout.stripe.com/..." }`. Set up Stripe webhooks for payment success/failure and booking confirmation; never treat returning from Checkout alone as proof a trip was booked.

The app currently provides the public feed, trip dates and offer selection, Connect/Checkout client handoffs, and response validation. It does **not** include a deployed provider booking service, Stripe secrets, Connect onboarding server, Checkout server, webhook, or a live payment integration. Those services and provider agreements must be configured before travelers can book or pay. Local demo mode is private to one browser and cannot publish trips or process payments.

Travel archive entries in local demo mode are saved in browser local storage under the normalized account email. Only a broad region, longitude-derived approximate UTC offset, and capture date are stored there. For travel search, an album stores a coarse coordinate rounded to two decimal places; exact GPS coordinates are never stored. In Firebase mode, travel metadata and albums are scoped to the authenticated user. Local-demo storage does not synchronize across devices and its email scope is not authentication or a secure account boundary.

GPS extraction currently supports decimal-degree ISO 6709 location strings commonly embedded in QuickTime/MP4 metadata. Videos without that metadata cannot provide a captured location; the app does not substitute the device's current location. UTC offsets and region names are intentionally approximate and should not be treated as precise travel records.
