# LegalMetrix Developer Guide

## 1. Project Overview

LegalMetrix is a static web prototype for packaged commodity compliance inspections. An enforcement officer can:

- Open a dashboard.
- Select or drag and drop a product image.
- Choose a product category.
- Run a simulated compliance analysis.
- Review extracted product information and detected issues.
- Save an inspection in the browser.
- Search and filter saved inspections in History.
- Save the officer name in Profile.

The current project is frontend-only. There is no backend server, API, database, OCR service, authentication system, or real compliance engine in this repository yet.

## 2. Current Folder Structure

```text
SIH6024/
| index.html                 Root entry page for the local server
| claude.md                  This developer and Claude guide
| frontend/
    | index.html              Dashboard page
    | history.html            Inspection history page
    | profile.html            Officer profile page
    | style.css               Shared layout, theme, navigation, and buttons
    | dashboard.css           Dashboard-specific styles
    | history.css              History-specific styles
    | profile.css              Profile-specific styles
    | app.js                  Shared utilities and localStorage helpers
    | dashboard.jss            Empty and unused file; likely an accidental extension
    | js/
        | app.js              Shared utilities used by the Profile page
        | dashboard.js         Dashboard interaction and mock analysis logic
        | history.js           History rendering, searching, and filtering
        | profile.js            Profile loading and saving
|-- index.html                 Root entry page for the local server
|-- claude.md                  This developer and Claude guide
`-- frontend/
  |-- index.html              Dashboard page
  |-- history.html            Inspection history page
  |-- profile.html            Officer profile page
  |-- style.css               Shared layout, theme, navigation, and buttons
  |-- dashboard.css           Dashboard-specific styles
  |-- history.css              History-specific styles
  |-- profile.css              Profile-specific styles
  |-- app.js                  Shared utilities and localStorage helpers
  |-- dashboard.jss            Empty and unused file; likely an accidental extension
  `-- js/
    |-- app.js              Shared utilities used by the Profile page
    |-- dashboard.js         Dashboard interaction and mock analysis logic
    |-- history.js           History rendering, searching, and filtering
    `-- profile.js            Profile loading and saving
```

The unusual characters in the tree above represent branches only. The actual names are the filenames shown in the indented sections.

## 3. Running the Project

### Using a static server

The current local server is expected to serve the repository root:

```text
http://localhost:5500/
```

The root `index.html` redirects to `frontend/index.html`. This was added because serving the repository root previously returned `Cannot GET /`.

The frontend can also be opened directly through a static server from the `frontend` folder, in which case `index.html` is the dashboard entry point.

There is no `package.json`, build step, dependency installation, or test runner at present. A browser with JavaScript and `localStorage` enabled is required.

## 4. Frontend Responsibilities

### `frontend/index.html`

Dashboard markup. It contains:

- Sidebar navigation to Dashboard, History, and Profile.
- Officer name and avatar placeholders.
- Summary statistics: total scans, compliant scans, violations, and compliance rate.
- Product image upload and drag-and-drop area.
- Product category selector.
- Analyze button and progress display.
- Extracted product information result section.
- Compliance score and detected issues.
- New Scan and Save Inspection actions.
- Toast notification container.

Important element IDs used by JavaScript include `productImage`, `uploadArea`, `analyzeButton`, `previewImage`, `previewContainer`, `productCategory`, `analysisProgress`, `extractedSection`, `overallStatus`, `violationsList`, and the statistics IDs.

### `frontend/history.html`

History page markup. It contains a product search field, status filter, inspection table, and empty-state message. The table body is populated by `js/history.js`.

### `frontend/profile.html`

Profile page markup. It contains officer name and assigned unit fields, profile avatar/name display, a Save Profile button, and a toast container.

The assigned unit field is currently visual only. It is not saved or read by the current JavaScript.

### CSS files

- `frontend/style.css`: shared CSS reset, CSS variables, sidebar, navigation, main content layout, top bar, buttons, form controls, responsive rules, and toast styling.
- `frontend/dashboard.css`: dashboard welcome panel, statistics cards, scanner, image preview, analysis progress, extracted data, compliance status, violations, and result actions.
- `frontend/history.css`: history card, filters, responsive table wrapper, status pills, and empty state.
- `frontend/profile.css`: profile card, avatar, profile form, and input styling.

Pages load `style.css` plus one page-specific stylesheet.

## 5. Frontend JavaScript Responsibilities

### Shared utility: `frontend/app.js`

Used by Dashboard and History. It provides:

- `getInspections()`: reads and parses `legalMetrixInspections` from `localStorage`; returns an empty array if the value is missing or invalid.
- `saveInspection(result)`: appends an inspection to the same `localStorage` array.
- `showToast(message)`: displays a toast for approximately 2.2 seconds.
- `scrollToScanner()`: smoothly scrolls to the dashboard scanner section.

### Shared utility: `frontend/js/app.js`

This file contains the same utility functions as `frontend/app.js`. Profile currently loads this copy, while Dashboard and History load the root copy. Keep the behavior synchronized if both files remain, or consolidate them into one shared file during cleanup.

### `frontend/js/dashboard.js`

Controls the dashboard workflow:

1. On `DOMContentLoaded`, loads saved dashboard statistics and registers event handlers.
2. Validates selected files as images smaller than 10 MB.
3. Reads the image with `FileReader` and displays a preview.
4. Enables Analyze Product after a valid image is selected.
5. Simulates analysis with an 1.8-second timeout.
6. Calls `generateMockAnalysis()` and renders its result.
7. Saves the rendered inspection through `saveInspection()`.
8. Calculates dashboard totals from saved inspections.
9. Resets the scanner for a new inspection.

`generateMockAnalysis()` currently returns hard-coded example data for ABC Premium Rice, including an 88% score, `WARNING` status, and two example violations. Replace this function with an API call when a backend analysis service is available.

The dashboard script uses optional chaining in a few places, so the target browser must support modern JavaScript.

### `frontend/js/history.js`

- Reads saved inspections using `getInspections()`.
- Filters by `productName` using the search input.
- Filters by `status` using the status selector.
- Rebuilds the history table whenever a filter changes.
- Shows the empty state when no records match.

The current table uses `innerHTML` for inspection values. When records come from a backend or user input, render cell text with `textContent` or sanitize values to prevent HTML injection.

### `frontend/js/profile.js`

- Loads `legalMetrixOfficerName` from `localStorage`.
- Updates the profile name and avatar.
- Saves a trimmed officer name, defaulting to `Officer`.
- Displays a success toast.

The assigned unit is not persisted yet.

## 6. Data Stored in the Browser

The current localStorage keys are:

| Key | Shape | Used by |
| --- | --- | --- |
| `legalMetrixInspections` | JSON array of inspection objects | Dashboard, History |
| `legalMetrixOfficerName` | String | Dashboard, Profile |

An inspection currently contains fields similar to:

```js
{
  id: "LM-<timestamp>",
  productName: "ABC Premium Rice",
  manufacturer: "ABC Foods Pvt. Ltd.",
  mrp: "₹120.00",
  netQuantity: "5 kg",
  manufacturingDate: "08/2026",
  bestBefore: "6 Months",
  consumerCare: "1800-123-4567",
  countryOrigin: "India",
  score: "88%",
  status: "WARNING",
  category: "Food / Grocery",
  image: "data:image/...",
  date: "<ISO date string>"
}
```

`image` is currently stored as a base64 data URL. This is acceptable for a small demo but should be replaced by backend/object storage references for production because browser storage is limited and data URLs are large.

Supported statuses are `COMPLIANT`, `WARNING`, and `NON_COMPLIANT`. Dashboard violation counts currently count only `NON_COMPLIANT` records, while the example analysis returns `WARNING`.

## 7. Backend Status and Recommended Boundary

### Current backend

No backend exists yet. Do not describe `localStorage` as a backend: it is client-side browser storage and is isolated per browser/device.

### Recommended future backend

A backend should own:

- Authentication and officer accounts.
- Officer profile persistence.
- Image upload and secure storage.
- OCR processing.
- Product declaration extraction.
- Legal Metrology rule evaluation.
- Compliance score and violation generation.
- Inspection persistence and audit history.
- Validation, authorization, rate limiting, and error handling.

A possible API shape is:

```text
POST   /api/auth/login
GET    /api/profile
PUT    /api/profile
POST   /api/inspections/analyze
POST   /api/inspections
GET    /api/inspections
GET    /api/inspections/:id
```

The frontend should send an image and category to `POST /api/inspections/analyze`, receive a structured result, and then save through the API. The backend should never trust the score, status, extracted fields, or officer ID supplied by the client.

Suggested backend directories when implementation begins:

```text
backend/
| src/
    | server.js or app.js       Server startup and middleware
    | routes/                    HTTP route definitions
    | controllers/               Request/response orchestration
    | services/                   OCR and compliance workflows
    | rules/                      Legal Metrology rule definitions
    | models/                     Database models or schemas
    | middleware/                 Auth, validation, and errors
    | config/                     Environment and database setup
| tests/                         API and rule tests
|-- src/
  |-- server.js or app.js       Server startup and middleware
  |-- routes/                    HTTP route definitions
  |-- controllers/               Request/response orchestration
  |-- services/                  OCR and compliance workflows
  |-- rules/                     Legal Metrology rule definitions
  |-- models/                    Database models or schemas
  |-- middleware/                Auth, validation, and errors
  `-- config/                   Environment and database setup
`-- tests/                        API and rule tests
```

Keep OCR integration and compliance rules in services/rules rather than placing them directly in route handlers. That makes rule changes and automated testing easier.

## 8. Recommended Feature Workflow

For a new feature:

1. Decide whether it is presentation, browser interaction, domain logic, or persistence.
2. Keep HTML responsible for structure and IDs, CSS responsible for appearance, and JavaScript responsible for interaction.
3. Keep compliance decisions in one domain service when a backend is added.
4. Define or update the inspection data contract before wiring a new field.
5. Add loading, empty, success, and error states.
6. Validate user input on both frontend and backend.
7. Test the affected workflow in a clean browser state and with existing saved records.
8. Update this document when file ownership, storage, API contracts, or commands change.

## 9. Current Limitations and Cleanup Tasks

- `frontend/dashboard.jss` is empty and unused. The active dashboard logic is `frontend/js/dashboard.js`; remove or rename the empty file only after confirming no external tool depends on it.
- `frontend/app.js` and `frontend/js/app.js` duplicate shared utilities. Consolidate them to avoid drift.
- The Camera button has markup but no camera implementation.
- Logout button markup exists but has no logout handler or authentication flow.
- Analysis is mocked and does not perform OCR or legal rule evaluation.
- Inspections are device-local and disappear when browser storage is cleared.
- Profile assigned unit is not saved.
- There are no automated tests, linting, type checking, or dependency metadata.
- History rows should avoid unsanitized `innerHTML` for backend or user-controlled values.
- The dashboard compliance rate counts only `COMPLIANT` records. Confirm the desired business definition before production use.

## 10. Coding Conventions for Future Changes

- Preserve the existing plain HTML/CSS/JavaScript setup unless a framework migration is intentional.
- Use descriptive function and variable names.
- Reuse shared utilities instead of duplicating storage or toast behavior.
- Keep selectors and element IDs stable, or update every consuming script in the same change.
- Keep API and domain logic out of page markup.
- Never put secrets, API keys, or database credentials in frontend files.
- Treat uploaded images and extracted text as potentially sensitive data.
- Prefer explicit error handling for storage, network, file parsing, and OCR failures.
- Add focused tests for compliance rules and API contracts before changing production behavior.
