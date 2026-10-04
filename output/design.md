# Problem 10 — Website Design

## Yale visual system

The storefront now uses a Yale-inspired palette built around deep Yale blue (`#0b3b70`), pale Yale blue surfaces, white space, and restrained navy typography. Buttons, navigation states, product controls, and the basket indicator share the same color system so the site feels coherent and recognizable.

## Handsome Dan

I found an existing Handsome Dan SVG asset in the Yale class project files and copied it into `frontend/public/assets/handsome-dan.svg` for HW4. It appears in the purchase celebration as an actual asset rather than a generic placeholder.

## Purchase celebration

The product detail page now has an “Add to basket” action. After adding an item, the page shows a Handsome Dan approval overlay, animated confetti, and a short Web Audio two-tone bark approximation. The basket count also increments in the header. The effect gives clear feedback that the action worked and makes the interaction feel rewarding without blocking the shopper for long.

## Social proof

Product cards and detail pages show a deterministic “bought” count for each catalogue item. The count is tied to the product ID so it stays stable between renders and does not pretend to be a live order count. This gives shoppers a quick signal of popularity and helps reduce uncertainty when choosing among similar items.

## Why this should help

- A consistent Yale visual language builds recognition and trust.
- Clear basket feedback prevents uncertainty after an add-to-basket action.
- Handsome Dan and the approval sound create a memorable, school-specific moment.
- Social proof helps shoppers decide faster and encourages confidence in popular products.
- The celebration is brief, and the reduced-motion preference can be respected in a future accessibility pass without changing the purchase flow.
