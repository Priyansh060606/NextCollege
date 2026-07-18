---
name: NextCollege AI
colors:
  surface: '#f7f9fb'
  surface-dim: '#d8dadc'
  surface-bright: '#f7f9fb'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#f2f4f6'
  surface-container: '#eceef0'
  surface-container-high: '#e6e8ea'
  surface-container-highest: '#e0e3e5'
  on-surface: '#191c1e'
  on-surface-variant: '#45464d'
  inverse-surface: '#2d3133'
  inverse-on-surface: '#eff1f3'
  outline: '#76777d'
  outline-variant: '#c6c6cd'
  surface-tint: '#565e74'
  primary: '#000000'
  on-primary: '#ffffff'
  primary-container: '#131b2e'
  on-primary-container: '#7c839b'
  inverse-primary: '#bec6e0'
  secondary: '#0058be'
  on-secondary: '#ffffff'
  secondary-container: '#2170e4'
  on-secondary-container: '#fefcff'
  tertiary: '#000000'
  on-tertiary: '#ffffff'
  tertiary-container: '#002109'
  on-tertiary-container: '#009844'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#dae2fd'
  primary-fixed-dim: '#bec6e0'
  on-primary-fixed: '#131b2e'
  on-primary-fixed-variant: '#3f465c'
  secondary-fixed: '#d8e2ff'
  secondary-fixed-dim: '#adc6ff'
  on-secondary-fixed: '#001a42'
  on-secondary-fixed-variant: '#004395'
  tertiary-fixed: '#6bff8f'
  tertiary-fixed-dim: '#4ae176'
  on-tertiary-fixed: '#002109'
  on-tertiary-fixed-variant: '#005321'
  background: '#f7f9fb'
  on-background: '#191c1e'
  surface-variant: '#e0e3e5'
typography:
  display-lg:
    fontFamily: Inter
    fontSize: 48px
    fontWeight: '700'
    lineHeight: 56px
    letterSpacing: -0.02em
  display-lg-mobile:
    fontFamily: Inter
    fontSize: 32px
    fontWeight: '700'
    lineHeight: 40px
    letterSpacing: -0.02em
  headline-md:
    fontFamily: Inter
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
  body-base:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 24px
  label-mono:
    fontFamily: Geist
    fontSize: 14px
    fontWeight: '500'
    lineHeight: 20px
    letterSpacing: 0.05em
  stat-lg:
    fontFamily: Inter
    fontSize: 36px
    fontWeight: '700'
    lineHeight: 44px
rounded:
  sm: 0.125rem
  DEFAULT: 0.25rem
  md: 0.375rem
  lg: 0.5rem
  xl: 0.75rem
  full: 9999px
spacing:
  container-max: 1280px
  gutter: 1.5rem
  margin-mobile: 1rem
  margin-desktop: 2.5rem
  stack-sm: 0.5rem
  stack-md: 1rem
  stack-lg: 2rem
---

## Brand & Style
The brand personality is **Authoritative, Visionary, and Analytical**. It serves as a high-stakes advisor for students and parents, necessitating a visual language that balances the gravitas of academia with the precision of advanced machine learning.

The design style is **Corporate Modern with subtle Glassmorphism**. This combination uses a structured, reliable foundation (Corporate) while utilizing semi-transparent "data layers" (Glassmorphism) to represent the transparency and depth of the AI’s logic. The interface should feel like a high-end dashboard: clean, expansive, and high-fidelity. High whitespace ratios are mandatory to ensure that complex admission data does not overwhelm the user.

## Colors
This design system utilizes a high-contrast palette to drive focus and trust.

*   **Primary (Navy/Cobalt):** Used for sidebars, primary navigation, and heavy headers to establish authority.
*   **Secondary (Electric Blue):** The "AI Accent." Used for interactive elements, data visualization peaks, and indicating machine-learning active states.
*   **Tertiary (Success Green):** Specifically reserved for high-probability admission indicators and positive growth trends in student profiles.
*   **Backgrounds:** A tiered system of neutrals. The base layer is `#F8FAFC`, with white (`#FFFFFF`) used for elevated cards and widgets to create a clear visual hierarchy.
*   **Data Accents:** Use a refined palette of Slate and Indigo for secondary chart metrics to avoid visual competition with the primary AI insights.

## Typography
The typography is centered on **Inter** for its exceptional legibility in data-heavy environments. To emphasize the technical nature of the AI platform, **Geist** is used for labels, metadata, and monospaced data points (like SAT scores or GPA ranks).

*   **Headlines:** Use tight letter-spacing and bold weights to ground the page.
*   **Stats:** Large numbers in "stat-lg" should be used for admission probabilities to ensure immediate impact.
*   **Readability:** Maintain a 1.5x line height for body text to keep complex application instructions accessible.

## Layout & Spacing
The layout follows a **12-column fluid grid** for desktop and a **4-column grid** for mobile. 

*   **Dashboard Logic:** Use a 280px fixed left-navigation bar on desktop. The main content area uses a "Masonry-lite" card layout for dashboard widgets.
*   **Negative Space:** Implement "Generous Padding" (stack-lg) between distinct sections (e.g., separating the College List from the Admissions Predictor) to reduce cognitive load.
*   **Data Density:** While the overall layout is spacious, internal card padding should be tighter (stack-md) to keep data-rich tables and charts cohesive.

## Elevation & Depth
The design system uses **Tonal Layers** combined with **Soft Ambient Shadows** to distinguish interactive elements from static data.

*   **Level 0 (Background):** Solid Slate-50.
*   **Level 1 (Cards/Widgets):** White background with a 1px border in Slate-200. No shadow.
*   **Level 2 (Active/Hover):** White background with a 12% opacity Blue-500 shadow, 20px blur. This indicates an element is "Analyzed" or "Selected."
*   **AI Insights:** Use a Backdrop Blur (12px) on semi-transparent secondary blue backgrounds to highlight AI-generated suggestions or "Pro-Tips."

## Shapes
The shape language is **Professional and Controlled**. 

*   **Corners:** Use a consistent 0.25rem (Soft) radius for most UI elements to maintain a serious, institutional feel. 
*   **Large Components:** Dashboard cards and primary containers use `rounded-lg` (0.5rem) to slightly soften the technical aesthetic.
*   **Data Markers:** Points on line charts and gauge needles should remain sharp or minimally rounded to emphasize mathematical precision.

## Components
Consistent component styling ensures the platform feels like a unified analytical tool.

*   **Predictor Cards:** Use a Level 1 elevation. Include a header section with a "Gauge Chart" for probability and a footer section for "Top Factors" using small neutral chips.
*   **Probability Gauges:** Semi-circular charts. Use a gradient stroke from Gray-200 to Secondary Blue (or Tertiary Green for >75% probability).
*   **Action Buttons:** Primary buttons are solid Navy with white text. Secondary buttons use an Electric Blue outline. Use `rounded-sm` for a sharp, "buttoned-up" look.
*   **Data Tables:** High-contrast rows. Use a subtle Slate-50 background on zebra-striping. Header text must be in "label-mono" (Geist) for a technical feel.
*   **Input Fields:** Minimalist design with a 1px Slate-300 border. On focus, the border transitions to Electric Blue with a soft 2px glow.
*   **Trend Lines:** Line charts should use a 2px stroke width with "Area Under the Curve" filled with a 5% opacity gradient of the line color.