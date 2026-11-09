# GOLD PRICE GUIDANCE

For players:
- Show vendor value and optional auction quotes with their age and confidence.
- Use the optional TSM market-price source when it is available.

Please check:
- Without TSM, confirm the vendor floor remains and no market quote is shown.
- With a quote, confirm its realm, faction and age are clear.
- Without core scan support, confirm the addon does not start an auction scan.

Developer notes:
- Keep quote data scoped by realm, faction and build; use only feature-probed market and core scan APIs.
