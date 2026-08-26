# LegalMetrix

LegalMetrix is a simple browser-based demonstration tool for checking whether packaged products show the information required for a compliance inspection.

It is designed for an enforcement officer or project evaluator to demonstrate this workflow:

```text
Product image
     ↓
Image upload
     ↓
Text and product information review
     ↓
Compliance result
     ↓
Compliant or review required
```

## What the project can do

- Open a compliance dashboard.
- Upload a product image.
- Preview the selected image.
- Select a product category.
- Run a sample product analysis.
- Display product information such as product name, manufacturer, price, quantity, date, and country of origin.
- Show a compliance score and detected issues.
- Save an inspection in the browser.
- View saved inspections in History.
- Search and filter saved inspections.
- Save an officer name in Profile.

## Important: demo limitations

This is currently a frontend demonstration. It does not yet have:

- A backend server.
- A database.
- User login or authentication.
- Real OCR processing.
- A real Gemini AI connection.
- A real Legal Metrology rules engine.
- Cloud image storage.

The analysis result currently uses sample/mock data so the screen can demonstrate the intended workflow. Saved inspections are kept only in the browser's `localStorage`. They may disappear if browser data is cleared or if the demo is opened in another browser or device.

## How to open the website

### Option 1: VS Code Live Server

1. Open the `SIH6024` folder in VS Code.
2. Open the root `index.html` file.
3. Right-click the file and choose **Open with Live Server**, or click **Go Live**.
4. Open this address in your browser:

   `http://localhost:5500/`

The root page automatically opens the dashboard inside the `frontend` folder.

If the root address does not redirect automatically, open:

`http://localhost:5500/frontend/`

### Option 2: Python local server

If Python is installed:

1. Open a terminal in the `SIH6024` folder.
2. Run:

   ```text
   python -m http.server 8000
   ```

3. Open:

   `http://localhost:8000/`

## How to use the website

### Dashboard

1. Open the Dashboard.
2. Click **Choose Image** and select a product image.
3. Check the image preview.
4. Select the product category.
5. Click **Analyze Product**.
6. Wait for the sample analysis to finish.
7. Review the extracted product information, score, and detected issues.
8. Click **Save Inspection** if you want to keep the result.

You can also drag an image into the upload area. The image must be an image file smaller than 10 MB.

### History

Open **History** from the left navigation menu. Saved inspections appear in a table. Use the search field to find a product or use the status filter to show only compliant, warning, or non-compliant inspections.

### Profile

Open **Profile** from the left navigation menu. Enter the officer's name and click **Save Profile**. The saved name is shown on the dashboard.

## Project files

```text
SIH6024/
├── index.html                 Root page that opens the frontend dashboard
├── README.md                 This guide
└── frontend/
    ├── index.html             Dashboard page
    ├── history.html           Inspection history page
    ├── profile.html           Officer profile page
    ├── style.css              Shared page styles
    ├── dashboard.css          Dashboard styles
    ├── history.css            History styles
    ├── profile.css            Profile styles
    ├── app.js                 Dashboard behavior and storage helpers
    └── js/
        ├── app.js             Shared helpers for other pages
        ├── dashboard.js       Dashboard interactions
        ├── history.js         History search and filtering
        └── profile.js         Profile loading and saving
```

## Browser requirements

Use a modern browser such as Google Chrome, Microsoft Edge, or Firefox. JavaScript and browser storage must be enabled.

The dashboard uses the `localStorage` feature of the browser to remember inspections and the officer name.

## Future development

The next production step would be to connect the dashboard to a secure backend. The backend should receive the uploaded image, perform OCR, send the extracted text to Gemini or another approved AI service, apply verified compliance rules, and store the final inspection in a database.

The browser should not be trusted to decide the final compliance result. Scores, extracted fields, and validation decisions should be checked again by the backend before they are saved as official inspection records.
