# PreCommit AI --- UI/UX Design Specification

> **Product tagline:** Catch Bugs & Leakages Before They Commit.\
> **Product type:** Python AST-based static code analysis web
> application\
> **Document purpose:** Visual design and frontend implementation
> reference

------------------------------------------------------------------------

## 1. Design Direction

Create a minimal, premium, developer-focused landing page inspired by
modern SaaS product websites.

The interface should feel:

-   **Minimal:** Keep the page focused on one primary action.
-   **Modern:** Use a soft gradient, clean typography, and rounded
    surfaces.
-   **Trustworthy:** Use clear language and avoid exaggerated AI claims.
-   **Developer-friendly:** Make ZIP upload and GitHub repository
    analysis immediately understandable.
-   **Responsive:** Work well on desktop, tablet, and mobile screens.

The landing page should not look like a traditional admin dashboard. It
is an elegant entry point into the code-analysis workflow.

------------------------------------------------------------------------

## 2. Page Content and Hierarchy

### 2.1 Brand Header

**Brand name:** PreCommit AI

**Logo direction:** Two or more thin, overlapping circular outlines
forming a simple abstract mark, followed by the text `PreCommit AI`.

**Placement:** - Top-left corner. - Comfortable spacing from the top and
left edges. - Black logo and text. - No large navigation menu in the
initial version.

### 2.2 Hero Section

Small eyebrow text:

> AI-powered Python code analysis

Main headline:

# Catch Bugs & Leakages Before They Commit.

The headline should be the strongest visual element on the page. Use a
bold, heavy sans-serif font, centered alignment, and a maximum width
that allows the heading to wrap naturally into two lines on desktop.

Do not add a long explanatory paragraph beneath the headline. Keep the
page focused on the upload and repository input controls.

### 2.3 Project Upload Panel

**Panel title:**

> Upload your project

**Supporting text:**

> Drop a ZIP file or select a project folder

**Primary control:**

> Choose Files

**Behavior:** - Support drag-and-drop for ZIP files. - Open the system
file picker when the user selects `Choose Files`. - Display the selected
filename after a successful selection. - Show a clear validation message
for unsupported file types or oversized files. - Allow the user to
replace the selected file. - Show an upload/loading state while the
project is being submitted.

### 2.4 Alternative GitHub Input

Place a centered `OR` divider below the upload panel.

Add a single-line GitHub repository input with: - GitHub icon on the
left. - Placeholder: `https://github.com/username/repository` - Clear
focus border. - Full-width layout matching the upload panel.

Initially, support public GitHub repositories. If private repository
support is added later, use a secure authorization flow rather than
asking users to paste access tokens into the URL field.

### 2.5 Primary Action

Button label:

> Analyze Code →

**Behavior:** - Full width, black background, white text. - Rounded
corners consistent with the other controls. - Disabled until a valid ZIP
file or repository URL is provided. - On click, validate the input and
begin analysis. - Show a loading state such as `Analyzing Project...`. -
Prevent duplicate submissions while analysis is running.

------------------------------------------------------------------------

## 3. Visual Design System

### 3.1 Color Palette

  Token            Suggested value   Usage
  ---------------- ----------------- ----------------------------------
  Primary text     `#050505`         Headlines and main text
  Secondary text   `#555555`         Supporting text and placeholders
  Background       `#FFFFFF`         Main page background
  Primary button   `#000000`         Analyze Code button
  Button text      `#FFFFFF`         Primary button label
  Border           `#202020`         Input and panel outlines
  Subtle divider   `#A0A0A0`         OR separator
  Focus accent     `#278BEA`         Keyboard focus and active states

### 3.2 Background

Use a soft, atmospheric gradient: - Mostly white on the left side. -
Light blue around the upper-middle and right side. - A subtle lavender
tint toward the upper-right corner. - A gentle cyan/blue glow on the
right. - Keep the center behind the text readable.

Avoid strong saturated colors behind important text. The gradient should
be soft and textured, not distracting.

Suggested CSS direction:

``` css
background:
  radial-gradient(ellipse at 72% 12%, rgba(177, 155, 255, 0.28), transparent 35%),
  radial-gradient(ellipse at 72% 42%, rgba(45, 174, 255, 0.30), transparent 42%),
  #ffffff;
```

### 3.3 Typography

Use a modern sans-serif font such as **Inter**, **Geist**, or
**Manrope**.

  Element             Desktop guidance     Weight
  ----------------- ------------------ ----------
  Brand                      22--26 px   650--700
  Eyebrow                    18--20 px   400--500
  Hero headline              64--76 px   700--800
  Upload title               28--32 px   650--700
  Supporting text            18--21 px        400
  Button text                18--20 px        600

Use responsive font sizing on smaller screens. Avoid forcing the
headline into a single line.

### 3.4 Shapes and Borders

-   Upload panel: white or near-white surface, 1.5--2 px dark border,
    16--20 px radius.
-   GitHub field: white surface, 1.5--2 px dark border, 12--14 px
    radius.
-   Main button: black surface, 12--14 px radius.
-   File picker button: white surface, dark outline, rounded corners.
-   Use restrained shadows, or none, to preserve the clean visual style.

------------------------------------------------------------------------

## 4. Desktop Layout

Use a centered content column.

Suggested page structure:

``` text
+------------------------------------------------------+
|  ◯◯ PreCommit AI                                     |
|                                                      |
|                       ◯◯◯◯                           |
|               AI-powered Python code analysis       |
|                                                      |
|          Catch Bugs & Leakages Before                |
|                    They Commit.                      |
|                                                      |
|       +--------------------------------------+       |
|       |               Upload icon            |       |
|       |           Upload your project         |       |
|       |  Drop a ZIP file or select a folder  |       |
|       |              Choose Files            |       |
|       +--------------------------------------+       |
|                                                      |
|       ---------------- OR ----------------           |
|                                                      |
|       +--------------------------------------+       |
|       | GitHub icon  Repository URL          |       |
|       +--------------------------------------+       |
|                                                      |
|       +--------------------------------------+       |
|       |             Analyze Code →           |       |
|       +--------------------------------------+       |
|                                                      |
+------------------------------------------------------+
```

Recommended desktop dimensions: - Main content width: approximately
760--820 px. - Upload panel height: approximately 220--240 px. -
Vertical spacing: generous but consistent. - Header positioned
independently at the top-left. - Hero and form aligned centrally.

The design should fit comfortably within a typical desktop viewport
without unnecessary scrolling.

------------------------------------------------------------------------

## 5. Responsive Design

### Desktop (1024 px and above)

-   Keep the centered hero layout.
-   Use a large two-line headline.
-   Keep the upload panel and repository input at a consistent width.
-   Keep the brand in the top-left.

### Tablet (768--1023 px)

-   Reduce the headline size.
-   Keep the form nearly full width with horizontal page padding.
-   Preserve the centered alignment and visual hierarchy.

### Mobile (below 768 px)

-   Use 24--28 px page padding.
-   Reduce the headline to approximately 38--46 px, depending on
    available width.
-   Allow the headline to wrap naturally.
-   Make the upload panel full width.
-   Keep all buttons large enough for touch interaction.
-   Keep the GitHub icon and placeholder readable.
-   Avoid horizontal scrolling.
-   Reduce the overlapping-circle graphic size if needed.

------------------------------------------------------------------------

## 6. Interaction and State Design

  -----------------------------------------------------------------------
  State                               Expected UI behavior
  ----------------------------------- -----------------------------------
  Empty                               Show upload prompt and GitHub
                                      placeholder

  Drag over                           Highlight upload panel with a
                                      subtle blue border/background

  File selected                       Show filename and file size

  Invalid file                        Show a concise validation message

  Invalid GitHub URL                  Show an inline URL validation
                                      message

  Ready                               Enable Analyze Code

  Analyzing                           Show spinner/progress message and
                                      disable duplicate submission

  Success                             Navigate to or display the analysis
                                      report

  Failure                             Show a readable error and allow
                                      retry
  -----------------------------------------------------------------------

All controls must be keyboard accessible and have visible focus states.
Provide accessible labels for file upload and repository URL fields.

------------------------------------------------------------------------

## 7. Analysis Results Page --- Visual Direction

The landing page should lead into a separate analysis-results
experience.

Suggested results-page sections:

1.  **Project summary:** Repository or uploaded project name, scan date,
    and number of files scanned.
2.  **Summary metrics:** Total findings, syntax errors, resource-leak
    warnings, and other warnings.
3.  **Finding filters:** All, Errors, Warnings, and Information.
4.  **Findings list:** Rule name, severity, file path, line number, and
    concise explanation.
5.  **Finding details:** Why the issue matters and a suggested
    remediation.
6.  **Actions:** Start a new scan and export the report.

Use severity labels consistently: - Error - Warning - Information

Do not imply that every static-analysis warning is a confirmed runtime
leak.

------------------------------------------------------------------------

## 8. Frontend Component Structure

Suggested component organization:

``` text
src/
├── components/
│   ├── BrandLogo
│   ├── HeroSection
│   ├── ProjectUpload
│   ├── GitHubRepositoryInput
│   ├── OrDivider
│   └── AnalyzeButton
├── pages/
│   ├── HomePage
│   └── AnalysisPage
├── styles/
│   ├── globals
│   └── landing-page
└── App
```

Keep upload validation, GitHub URL validation, API communication, and
visual components separated where practical.

------------------------------------------------------------------------

## 9. Functional Requirements

-   [ ] Display the PreCommit AI brand and logo.
-   [ ] Display the headline: "Catch Bugs & Leakages Before They
    Commit."
-   [ ] Provide ZIP file upload.
-   [ ] Provide drag-and-drop upload.
-   [ ] Display the selected file name.
-   [ ] Provide a GitHub repository URL field.
-   [ ] Validate the selected input.
-   [ ] Enable Analyze Code only when the input is valid.
-   [ ] Show loading, success, and error states.
-   [ ] Support desktop, tablet, and mobile layouts.
-   [ ] Meet basic keyboard and screen-reader accessibility
    requirements.

------------------------------------------------------------------------

## 10. Design Acceptance Checklist

The implementation is ready for review when:

-   The page closely follows the specified minimal visual direction.
-   The logo, hero headline, upload panel, OR divider, GitHub field, and
    Analyze Code button are visually clear.
-   The headline reads exactly **"Catch Bugs & Leakages Before They
    Commit."**
-   There is no unwanted explanatory paragraph between the headline and
    upload panel.
-   The gradient remains subtle and does not reduce text contrast.
-   Upload and GitHub input options are equally understandable.
-   The layout works on mobile without horizontal overflow.
-   All interactive controls have functional states rather than being
    decorative.

------------------------------------------------------------------------

**Product:** PreCommit AI\
**Tagline:** Catch Bugs & Leakages Before They Commit.\
**Design style:** Minimal, modern, gradient-based developer SaaS\
**Primary user action:** Upload a project or enter a GitHub repository
URL, then analyze the code.
