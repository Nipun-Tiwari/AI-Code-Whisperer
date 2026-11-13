# Design Reference

Place the original UI screenshot(s) in this directory for visual QA during implementation.

## Design Language Summary

- **Canvas:** White or very light neutral
- **Secondary surfaces:** Restrained light grey
- **Text:** Charcoal/near-black primary, muted grey secondary
- **Borders:** Subtle neutral grey
- **Accent:** Single restrained blue (`#2563eb`)
- **Status colours:** Only for meaningful success/warning/danger/info states
- **Typography:** Inter, clean hierarchy, no oversized hero text
- **Components:** Subtle borders, small consistent radius, compact buttons, no emoji icons
- **Anti-patterns to avoid:** Excessive gradients, glassmorphism, glowing borders, decorative illustrations, nested cards without purpose

## Token Reference

Design tokens are defined in:
- CSS variables: `frontend/src/index.css`
- TypeScript constants: `frontend/src/design-system/tokens.ts`
- Tailwind extensions: `frontend/tailwind.config.js`
