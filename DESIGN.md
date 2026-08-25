# CADRE Design System

## Intent

**Physical scene:** a private bridge console at night, used in low ambient light with disciplined focus while quiet instrument lights confirm the state of the vessel.

The interface is a restrained operational product, not a themed cockpit. Near-black neutral space reduces glare; an atmospheric cobalt anchor identifies action and selection; a clear brass accent denotes authority and approval. Typography, spacing, and state language carry most of the character.

## Color

Use OKLCH values directly. Color strategy is restrained: neutrals dominate and brand color stays below ten percent of the visible surface.

```css
:root {
  --color-bg: oklch(0.1 0 0);
  --color-surface: oklch(0.145 0.008 230);
  --color-surface-raised: oklch(0.19 0.012 230);
  --color-line: oklch(0.3 0.018 230);
  --color-ink: oklch(0.95 0.008 230);
  --color-muted: oklch(0.72 0.022 230);
  --color-primary: oklch(0.58 0.12 230);
  --color-primary-strong: oklch(0.5 0.14 230);
  --color-authority: oklch(0.86 0.12 85);
  --color-success: oklch(0.72 0.13 155);
  --color-warning: oklch(0.82 0.14 85);
  --color-danger: oklch(0.64 0.18 25);
  --color-info: oklch(0.72 0.1 230);
}
```

- Use primary for the single primary action, current navigation selection, links, and focus.
- Use authority for approved/canonical indicators and sparingly for executive controls.
- Pair white text with saturated primary, success, and danger fills. Use dark neutral text only on the high-lightness authority and warning fills.
- Status always includes a text label or icon; color is supplemental.

## Typography

Use one familiar product family: `Inter`, `SF Pro Text`, `Segoe UI`, system sans-serif. Use a fixed modular scale from `0.75rem` to `2rem`; do not use fluid display typography in the application shell.

- Body: 0.9375rem / 1.5
- Compact labels and metadata: 0.75rem–0.8125rem / 1.4
- Section heading: 1.125rem / 1.3, semibold
- Page heading: 1.5rem–2rem / 1.2, semibold
- Long prose: maximum 70 characters per line
- IDs and machine state may use the system monospace stack

## Spatial System

Use a 4px base with 8, 12, 16, 24, 32, and 48px steps. The desktop shell uses a 248px navigation rail, a flexible work surface, and an optional 320px contextual inspector. On smaller screens, navigation becomes an accessible drawer and secondary panes stack below the primary task.

## Components

- **Navigation:** one stable vocabulary across desktop and mobile; active state uses primary color plus weight, not decorative effects.
- **Buttons:** 8px radius, 36–42px height, clear default/hover/focus/active/disabled/loading states.
- **Inputs:** 8px radius, persistent labels, visible focus ring, inline validation, and no placeholder-only labeling.
- **Panels:** use hierarchy and spacing before borders. Maximum radius is 12px. Never nest decorative cards.
- **Tables and lists:** prefer rows for conversations, jobs, artifacts, notifications, and audit history. Preserve density and scanability.
- **Status:** compact label plus shape/icon; standardized vocabulary for queued, running, needs approval, review, ready, failed, delivered, and archived.
- **Loading:** skeletons for content regions; progress text for durable jobs.
- **Empty states:** explain the purpose of the surface and provide the next valid action.

## Motion

Use 150–220ms ease-out transitions only to communicate focus, selection, disclosure, or state change. Do not stage page-load choreography. Under `prefers-reduced-motion: reduce`, remove nonessential transforms and make transitions effectively immediate.

## Accessibility

Meet WCAG 2.2 AA for text, focus, navigation, and controls. Preserve logical tab order, provide skip navigation, maintain 44px coarse-pointer targets, announce asynchronous status changes, and never place private content in service-worker caches.

## Anti-patterns

No gradients, glassmorphism, decorative grid backgrounds, animated imagery, side-stripe callouts, oversized hero metrics, over-rounded panels, or ornamental maritime graphics. CADRE earns its identity through disciplined state, language, and operational clarity.
