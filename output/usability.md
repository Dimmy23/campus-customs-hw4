# Problem 9 — Usability Improvements

## Frontend improvement 1 — Catalogue search and category filters

### What I added

The Products page now has a search field and category buttons for All products, Clothing, Accessories, and Gifts. Results filter immediately as the shopper types or changes category.

### Why it helps

The catalogue is large, so shoppers can reach a relevant Yale item without scrolling through every product. The category controls also make the store easier to scan on a phone.

## Frontend improvement 2 — Clear availability feedback and chat starters

### What I added

Product cards show a stock status derived from the database, and the chat panel includes quick questions such as “What hoodies do you have?” and “What is in stock?”. Loading and no-result messages are explicit.

### Why it helps

Shoppers can understand availability before opening a detail page, and the suggested questions make the assistant easier to discover for first-time visitors.

## Agent/backend improvement 1 — Context-aware product lookup

### What I added

The agent can use `product_by_id` for the product currently open on the page. Follow-up questions such as “do you have this in pink?” therefore resolve against the exact product rather than a broad catalogue search.

### Why it helps

This reduces ambiguous recommendations and makes color, price, description, and stock answers more accurate for product-page conversations.

## Agent/backend improvement 2 — Ranked and bounded catalogue search

### What I added

`search_products` now normalizes simple plurals, ranks exact name matches above descriptive matches, and caps results at eight cards even if a caller requests a larger number.

### Why it helps

The agent receives more relevant products with less context, which improves answer quality, reduces unnecessary model input, and keeps the storefront response fast.
