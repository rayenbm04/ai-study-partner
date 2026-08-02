# AI Study Coach — Mobile

Expo (React Native + web) client for the AI Study Coach backend (see [`../backend/README.md`](../backend/README.md)). One codebase targets iOS, Android, and web via Expo's web export — no separate frontend project for each platform.

This replaces the original architecture doc's plan to evolve `rag-frontend` (the forked React/Vite app) into the new frontend. Given the product is used mainly on mobile, we pivoted to a native-first Expo app instead; `rag-frontend` is left untouched and unused going forward.

## Setup

```bash
cd mobile
npm install
cp .env.example .env   # point EXPO_PUBLIC_API_URL at your running backend
npx expo start
```

Then press `w` for web, `i` for iOS simulator (macOS only), `a` for Android emulator, or scan the QR code with Expo Go on a physical device.

**If testing on a physical device or emulator**, `localhost` in `.env` won't reach your computer's backend — use your machine's LAN IP instead (e.g. `http://192.168.1.23:8000`).

## Design system

- **Colors** (`constants/theme.ts`): warm beige/white backgrounds, violet as the primary interactive color (buttons, links, selection), amber as a highlight/accent color (due-today badges, selected chips) — never a competing second primary.
- **Typography**: Inter only (no serif/display font), loaded via `@expo-google-fonts/inter` in `app/_layout.tsx`.
- **No mascot/character system** — icons only (`@expo/vector-icons`) for now.

All tokens (colors, spacing, radii, font sizes) live in `constants/theme.ts`. Change them there, not per-component.

## Structure

```
app/                 expo-router routes (file-based)
  (auth)/             login, register
  (tabs)/             the four main tabs: subjects, study-plan, progress, settings
  subject/            subject detail + create-subject
  quiz/               quiz-taking flow
  onboarding.tsx      first-run setup (create first subject + daily study time)
  _layout.tsx          root layout: font loading, Stack.Protected auth gating, navigation shell
components/ui/        shared primitives (Button, Card, TextField, ProgressBar, Text, Screen)
constants/theme.ts     design tokens
lib/api/               typed API client, one module per backend engine
lib/auth-context.tsx   global auth state (login/register/logout, token refresh)
```

## API client

`lib/api/client.ts` wraps `fetch` with: auth token injection, automatic one-shot refresh-and-retry on a 401, and normalized error messages (the backend's `DomainError` handler always returns `{"detail": "..."}`, which `ApiError` unwraps). Tokens go through `lib/storage.ts`, not `AsyncStorage`, since they're credentials — that wrapper uses real `expo-secure-store` on iOS/Android and `localStorage` on web, because `expo-secure-store`'s web target is a long-standing broken upstream (throws `getValueWithKeyAsync is not a function` instead of falling back) rather than something we could fix by calling it differently.

Each backend engine has its own typed module under `lib/api/` (`auth.ts`, `subjects.ts`, `quizzes.ts`, `flashcards.ts`, `progress.ts`, `studyPlans.ts`, `analytics.ts`, `documents.ts`) mirroring the backend's own per-engine structure. Types in `lib/api/types.ts` are hand-mirrored from the backend's pydantic response schemas — there's no shared codegen yet, so if a backend response shape changes, update the type here too.

`app/_layout.tsx` gates auth with `Stack.Protected guard={...}`, not a `useEffect` + `router.replace`. The effect-based version has a real race condition: it renders whichever screen the router picks first and only redirects a tick later, so an unauthenticated load would still mount `(tabs)/index` for one frame and fire its data-fetching effect with no access token — surfacing as `ApiError: Not authenticated`. `Stack.Protected` prevents a guarded screen from mounting at all until its guard is true, closing that race at the source.

## What's built vs. what's next

Built: register/login (with token refresh), a short onboarding flow, the four-tab shell, a real subject list wired to the analytics engine (due-card counts, mastery), subject detail with a documents list, quiz generation + the full step-by-step quiz-taking flow with results, and a study-plan generation form.

Known gaps, in rough priority order:

1. **Document upload isn't wired up on mobile yet** (`lib/api/documents.ts` is read-only). Needs `expo-document-picker` + a multipart upload — the backend endpoint already exists (`POST /subjects/{id}/documents`).
2. **No "list my study plans" endpoint on the backend** — the Study Plan tab can generate a plan and show it, but a generated plan isn't persisted anywhere the app can re-fetch it after a restart. The architecture doc's Planning Engine API contract only specifies generate/get-one/update-item; adding a `GET /study-plans` (list mine) is a small, natural backend follow-up.
3. **Flashcard review screen isn't built yet** — `lib/api/flashcards.ts` has the calls (`listDueFlashcards`, `reviewFlashcard`), no screen consumes them yet.
4. **Chat, summaries, and exams have no screens yet** — same story, the API modules would follow the same pattern as `quizzes.ts`.
5. **The onboarding daily-minutes choice isn't persisted as a user preference** (no such backend setting exists yet) — it's passed through as a router param to pre-fill the Study Plan tab once, not saved.
6. **Push notifications** (flashcard-due / study-plan-session reminders) aren't set up — would use `expo-notifications` with an EAS development build (push doesn't work in Expo Go as of SDK 53+).

## Troubleshooting

- **`TypeError: Failed to fetch` on web**: almost always CORS — the backend's `ALLOWED_ORIGINS` (in `backend/.env`) needs to include the Expo web dev server's origin, `http://localhost:8081` by default. Restart the backend after changing it (env vars load once at startup, not on `--reload`'s hot-reload). Also double-check the backend is actually running and that `mobile/.env`'s `EXPO_PUBLIC_API_URL` matches its port.
- **`ApiError: Not authenticated`**: fixed by switching auth gating to `Stack.Protected` (see above) — if you see this again, it means some screen is firing an authenticated request while `user` is still null, which is a real bug to chase down rather than a config issue.

## Building for real devices / production

Local `npx expo start` + Expo Go covers iOS/Android during development for most of this app. Push notifications and any other native module that needs config beyond Expo Go's defaults require an EAS development build (`eas build --profile development`) instead — see [Expo's EAS Build docs](https://docs.expo.dev/build/introduction/).
