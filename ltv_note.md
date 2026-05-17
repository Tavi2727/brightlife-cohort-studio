# LTV Definition & How It Could Mislead

## Our Definition

Lifetime Value (LTV) in this dashboard is defined as the **sum of all gross revenue attributed to a customer from their first order to the latest date in the dataset**, grouped by their acquisition channel.

## How It Could Mislead

**1. Survivorship bias.** Customers with more months in the dataset mechanically accumulate more revenue. A cohort acquired 12 months ago will always show higher LTV than one acquired 2 months ago — not because they are better customers, but because they have had more time to spend. Comparing LTV across cohorts of different ages is therefore misleading.

**2. Gross ≠ net.** Gross revenue ignores returns, discounts, and cost of goods. A high-LTV channel that drives frequent returns could be less profitable than a lower-LTV channel with cleaner margins.

**3. Single-touch attribution.** LTV is assigned to the first acquisition channel only. A customer acquired via Instagram who later converts repeatedly through email looks like an Instagram win — masking email's role.

## Mitigation

Normalise LTV by cohort age (revenue per customer per month active). Present margin-adjusted LTV where cost data is available. Use multi-touch attribution for channel comparisons.
