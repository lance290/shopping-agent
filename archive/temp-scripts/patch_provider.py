import re

with open("apps/backend/services/coupon_provider.py", "r") as f:
    content = f.read()

# Replace ManualProvider query
old_manual = """        # Filter by category (case-insensitive substring match)
        stmt = stmt.where(PopSwap.category.ilike(f"%{category}%"))

        result = await session.exec(stmt)
        swaps = result.all()

        return sorted(
            [_swap_to_offer(s) for s in swaps],
            key=lambda o: o.savings_cents,
            reverse=True,
        )"""

new_manual = """        result = await session.exec(stmt)
        swaps = result.all()

        matched_swaps = []
        search_term = category.lower()
        product_term = (product_name or "").lower()
        for s in swaps:
            s_cat = s.category.lower()
            s_target = (s.target_product or "").lower()
            
            if s_cat in search_term or search_term in s_cat:
                matched_swaps.append(s)
            elif s_target and (s_target in search_term or search_term in s_target):
                matched_swaps.append(s)
            elif product_term and (s_cat in product_term or product_term in s_cat or (s_target and (s_target in product_term or product_term in s_target))):
                matched_swaps.append(s)

        return sorted(
            [_swap_to_offer(s) for s in matched_swaps],
            key=lambda o: o.savings_cents,
            reverse=True,
        )"""

content = content.replace(old_manual, new_manual)

# Replace HomeBrewProvider query
old_homebrew = """            .where(PopSwap.category.ilike(f"%{category}%"))

        # If max_redemptions set, exclude fully redeemed offers
        result = await session.exec(stmt)
        swaps = result.all()

        available = [
            s for s in swaps
            if s.max_redemptions is None or s.current_redemptions < s.max_redemptions
        ]

        return sorted(
            [_swap_to_offer(s) for s in available],
            key=lambda o: o.savings_cents,
            reverse=True,
        )"""

new_homebrew = """        # If max_redemptions set, exclude fully redeemed offers
        result = await session.exec(stmt)
        swaps = result.all()

        available = [
            s for s in swaps
            if s.max_redemptions is None or s.current_redemptions < s.max_redemptions
        ]

        matched_swaps = []
        search_term = category.lower()
        product_term = (product_name or "").lower()
        for s in available:
            s_cat = s.category.lower()
            s_target = (s.target_product or "").lower()
            
            if s_cat in search_term or search_term in s_cat:
                matched_swaps.append(s)
            elif s_target and (s_target in search_term or search_term in s_target):
                matched_swaps.append(s)
            elif product_term and (s_cat in product_term or product_term in s_cat or (s_target and (s_target in product_term or product_term in s_target))):
                matched_swaps.append(s)

        return sorted(
            [_swap_to_offer(s) for s in matched_swaps],
            key=lambda o: o.savings_cents,
            reverse=True,
        )"""

content = content.replace(old_homebrew, new_homebrew)

with open("apps/backend/services/coupon_provider.py", "w") as f:
    f.write(content)
