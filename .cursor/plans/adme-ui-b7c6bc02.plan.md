<!-- b7c6bc02-df6f-450a-9702-ea1a1306774d 6eb983d4-0598-46c5-8690-7f4f1d24b227 -->
# ADME@NCATS UI Styling Modernization

## Design Direction

- Scientific/professional aesthetic appropriate for NIH/government
- Refined purple-based color palette with better contrast and depth
- Full responsiveness across all viewport sizes
- Cosmetic changes only - no structural or functional modifications

## Key Files to Modify

### 1. Global Styles (`client/src/styles.scss`)

- Add CSS custom properties (variables) for colors, spacing, typography, shadows
- Define modern purple palette: primary, accent, background tints
- Replace Roboto with a more distinctive font pairing (e.g., Source Sans Pro for body, Libre Franklin for headings)
- Add global utility classes for consistent spacing and elevation
- Fix container responsiveness with proper max-width and fluid widths

### 2. App Shell (`client/src/app/app.component.scss`)

- Modernize toolbar with subtle gradient or shadow depth
- Improve navigation link styling with better hover states and active indicators
- Fix responsive navigation breakpoints (currently breaks at 490px)
- Update footer with better spacing, visual separation, and responsive layout

### 3. Home Page (`client/src/app/home/home.component.scss`)

- Add subtle background texture or gradient
- Improve typography hierarchy for headings and body text
- Style publication list with better visual separation
- Add card-like styling for content sections

### 4. Predictions Page (`client/src/app/predictions/predictions.component.scss`)

- Improve tab styling with better visual feedback
- Style model checkboxes with consistent spacing
- Fix error message styling (softer, more professional)
- Ensure full responsive layout for input sections

### 5. Predictions Table (`client/src/app/predictions-table/predictions-table.component.scss`)

- Add table row hover effects
- Improve header styling with background differentiation
- Fix table overflow/scroll behavior on small screens
- Style action buttons consistently

### 6. Method Pages (`client/src/app/method/method.component.scss`)

- Style definition lists with better visual hierarchy
- Improve table styling for protocol data
- Add subtle section separators
- Ensure responsive table handling

### 7. Contact Page (`client/src/app/contact/contact.component.scss`)

- Style profile cards with subtle elevation
- Improve image container styling
- Add hover effects for resource links
- Fix responsive layout for profile rows

### 8. Data Page (`client/src/app/data/data.component.scss`)

- Improve data table styling
- Style download icons with hover feedback
- Add visual hierarchy to table headers

### 9. Supporting Components

- `text-file.component.scss`: Style file input forms
- `sketcher.component.scss`: Improve sketcher container styling
- `loading.component.scss`: Modernize loading overlay
- `swagger-ui.component.scss`: Ensure API docs match overall theme

### 10. Index HTML (`client/src/index.html`)

- Add Google Fonts link for new typography

## Responsive Breakpoints Strategy

- Mobile: < 576px
- Tablet: 576px - 768px  
- Desktop: > 768px
- Fix existing 490px/550px/700px breakpoints for consistency

## Color Palette (Purple-Based)

```
--primary-dark: #4a148c
--primary: #673ab7
--primary-light: #9575cd
--primary-lightest: #ede7f6
--accent: #7c4dff
--text-primary: #212121
--text-secondary: #757575
--background: #fafafa
--surface: #ffffff
--error: #c62828
```

### To-dos

- [ ] Create CSS variable system and update global styles.scss with typography, colors, responsive containers
- [ ] Modernize toolbar, navigation, and footer in app.component.scss with responsive fixes
- [ ] Update home.component.scss with improved typography and card styling
- [ ] Improve predictions.component.scss tabs, checkboxes, and error states
- [ ] Enhance predictions-table.component.scss with hover effects and responsive tables
- [ ] Update method.component.scss definition lists and tables
- [ ] Style contact.component.scss and data.component.scss consistently
- [ ] Update text-file, sketcher, loading, and swagger-ui component styles
- [ ] Add modern font imports to index.html