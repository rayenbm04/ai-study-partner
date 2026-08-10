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

- **Colors** (`constants/theme.ts`, "Organic" system): warm cream/ink palette (`#F8F3EA` background, near-black `#201E1D` primary CTA color), terracotta-amber (`#E0982B`) as the accent for streaks/due-today badges/progress rings/selection, olive-sage for "mastered"/correct states. Full light + dark palettes, switched at runtime via `lib/theme-context.tsx` (defaults to the device scheme; a manual choice in Settings overrides it and persists).
- **Typography**: Caprasimo (display serif, headings/big numbers) + Figtree (everything else), loaded via `@expo-google-fonts/caprasimo` and `@expo-google-fonts/figtree` in `app/_layout.tsx`.
- **Shape language**: pill-shaped buttons/inputs, large soft-shadowed cards, no hard borders.
- **No mascot/character system** — icons only (`@expo/vector-icons`).

All tokens (colors, spacing, radii, font sizes) live in `constants/theme.ts`. Change them there, not per-component.

## Internationalization

English, French, and Arabic, via `lib/i18n/translations.ts` + `lib/language-context.tsx` (`useLanguage()` exposes `t()`/`tn()`). Arabic also flips layout direction — `I18nManager`'s RTL flag is native and only takes full effect after a reload, so `setLanguage()` applies translated text immediately but a language switch to/from Arabic prompts the user to restart. Language choice persists via the same cross-platform `storage` wrapper used for the theme preference.

## Structure

```
app/                 expo-router routes (file-based)
  (auth)/             login, register, forgot-password, reset-password
  (tabs)/             the four main tabs: home, cards, study-plan, progress, settings
  subject/            subject detail (documents, summaries, exams) + create-subject
  subject-pack/       curriculum pack picker (Country -> System -> Level -> Section -> preview)
  materials/          per-subject document list + upload + summaries
  concepts/           per-subject concept-mastery tree
  coach/              RAG chat screen (whole-subject or scoped to one document)
  quiz/               quiz-taking flow
  onboarding.tsx      first-run setup (create first subject + daily study time)
  _layout.tsx          root layout: font loading, Stack.Protected auth gating, navigation shell
components/ui/        shared primitives (Button, Card, TextField, DatePickerField, SchoolPickerField, ProgressBar, Text, Screen, Tag, Avatar, RingProgress, AnimatedNumber, IconButton)
constants/theme.ts     design tokens
lib/api/               typed API client, one module per backend engine
lib/auth-context.tsx   global auth state (login/register/logout, token refresh)
lib/theme-context.tsx  light/dark mode
lib/language-context.tsx  en/fr/ar + RTL
```

## API client

`lib/api/client.ts` wraps `fetch` with: auth token injection, automatic one-shot refresh-and-retry on a 401, and normalized error messages (the backend's `DomainError` handler always returns `{"detail": "..."}`, which `ApiError` unwraps). Tokens go through `lib/storage.ts`, not `AsyncStorage`, since they're credentials — that wrapper uses real `expo-secure-store` on iOS/Android and `localStorage` on web, because `expo-secure-store`'s web target is a long-standing broken upstream (throws `getValueWithKeyAsync is not a function` instead of falling back) rather than something we could fix by calling it differently.

Each backend engine has its own typed module under `lib/api/` (`auth.ts`, `account.ts`, `schools.ts`, `curriculum.ts`, `subjectPacks.ts`, `subjects.ts`, `documents.ts`, `chat.ts`, `summaries.ts`, `quizzes.ts`, `exams.ts`, `flashcards.ts`, `progress.ts`, `studyPlans.ts`, `analytics.ts`) mirroring the backend's own per-engine structure. Types in `lib/api/types.ts` are hand-mirrored from the backend's pydantic response schemas — there's no shared codegen yet, so if a backend response shape changes, update the type here too. `schools.ts` deliberately passes `auth: false` on every call — those backend routes are public, since a student searches for/adds their school *during* the registration form, before a token exists.

`app/_layout.tsx` gates auth with `Stack.Protected guard={...}`, not a `useEffect` + `router.replace`. The effect-based version has a real race condition: it renders whichever screen the router picks first and only redirects a tick later, so an unauthenticated load would still mount `(tabs)/index` for one frame and fire its data-fetching effect with no access token — surfacing as `ApiError: Not authenticated`. `Stack.Protected` prevents a guarded screen from mounting at all until its guard is true, closing that race at the source.

## What's built vs. what's next

Built: register (name/email/pseudo/date of birth/school picker/password+confirm, with live inline validation) / login (with token refresh, account-lockout messaging) / forgot-password + reset-password (code-based, since there's no deep-link scheme set up — see backend/README.md's Email section for why the code has to be copied from the server console for now), a short onboarding flow with a curriculum pack picker (also reachable later from Settings to add another pack), the five-tab shell, a real subject list wired to the analytics engine (due-card counts, mastery), subject detail with document upload + a documents list, per-document summaries, RAG chat (whole-subject or scoped to a single document via "ask about this document"), quiz + exam generation with the full step-by-step attempt flow and results, flashcard review (SM-2), a concept-mastery tree view, a study-plan generation form, and account settings (theme, language, reset account).

The school field on registration is `SchoolPickerField` (`components/ui/SchoolPickerField.tsx`) — search-as-you-type against `GET /schools`, or add a new one inline if it's not found (same "not in list" fallback the date-of-birth/classe pickers don't need, since schools have no fixed catalog to browse). No verify-email screen exists yet — there's a working `authApi.verifyEmail()` call but nothing in the UI drives it, since login isn't blocked on verification either (see backend/README.md).

Known gaps, in rough priority order:

1. **No "list my study plans" endpoint on the backend** — the Study Plan tab can generate a plan and show it, but a generated plan isn't persisted anywhere the app can re-fetch it after a restart. The architecture doc's Planning Engine API contract only specifies generate/get-one/update-item; adding a `GET /study-plans` (list mine) is a small, natural backend follow-up.
2. **The onboarding daily-minutes choice isn't persisted as a user preference** (no such backend setting exists yet) — it's passed through as a router param to pre-fill the Study Plan tab once, not saved.
3. **Push notifications** (flashcard-due / study-plan-session reminders) aren't set up — would use `expo-notifications` with an EAS development build (push doesn't work in Expo Go as of SDK 53+).
4. **No verify-email screen** — the API call exists (`authApi.verifyEmail`), nothing in the UI calls it yet.

## Troubleshooting

- **`TypeError: Failed to fetch` on web**: almost always CORS — the backend's `ALLOWED_ORIGINS` (in `backend/.env`) needs to include the Expo web dev server's origin, `http://localhost:8081` by default. Restart the backend after changing it (env vars load once at startup, not on `--reload`'s hot-reload). Also double-check the backend is actually running and that `mobile/.env`'s `EXPO_PUBLIC_API_URL` matches its port.
- **`ApiError: Not authenticated`**: fixed by switching auth gating to `Stack.Protected` (see above) — if you see this again, it means some screen is firing an authenticated request while `user` is still null, which is a real bug to chase down rather than a config issue.

## Building for real devices / production

Local `npx expo start` + Expo Go covers iOS/Android during development for most of this app. Push notifications and any other native module that needs config beyond Expo Go's defaults require an EAS development build (`eas build --profile development`) instead — see [Expo's EAS Build docs](https://docs.expo.dev/build/introduction/).
