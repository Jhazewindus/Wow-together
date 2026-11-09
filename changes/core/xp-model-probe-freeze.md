# RESPONSIVE XP ESTIMATES AND PROBE

## For players
XP estimates calculate in the background, so starting a guide stays responsive.
`/wt probe` reports the current destination without rerunning route calculations.

## Please check
- Start a full guide and confirm the XP estimate appears shortly after it loads.
- Run `/wt probe` while a route step is active and confirm the game stays responsive.

## Developer notes
The XP estimate retains its existing route eligibility and reward rules, but calculates in timer-driven slices. Probe output reads current route-step metadata only.
