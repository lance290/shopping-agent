import re

with open("apps/backend/services/coupon_provider.py", "r") as f:
    content = f.read()

def replace_manual():
    old = """        # Filter by category (case-insensitive substring match)
        stmt = stmt.where(PopSwap.category.ilike(f"%{category}%"))

        result = await session.exec(stmt)
        swaps = result.all()

        return sorted(
            [_swap_to_offer(s) for s in swaps],
            key=lambda o: o.savings_cents,
            reverse=True,
        )"""
    new = """        result = await session.exec(stmt)
        swaps = result.all()
        
        search_terms = category.lower().split()
        if product_name:
            search_terms.extend(product_name.lower().split())
        
        matched_swaps = []
        for s in swaps:
            s_cat = s.category.lower() if s.category else ""
            s_target = s.target_product.lower() if s.target_product else ""
            
            # Simple substring matching
            if any(term in s_cat or term in s_target for term in search_terms) or \
               any(s_cat in term or (s_target and s_target in term) for term in search_terms):
                matched_swaps.append(s)

        return sorted(
            [_swap_to_offer(s) for s in matched_swaps],
            key=lambda o: o.savings_cents,
            reverse=True,
        )"""
    return content.replace(old, new)

content = replace_manual()

def replace_homebrew():
    old = """            .where(PopSwap.category.ilike(f"%{category}%"))

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
    new = """        # If max_redemptions set, exclude fully redeemed offers
        result = await session.exec(stmt)
        swaps = result.all()

        available = [
            s for s in swaps
            if s.max_redemptions is None or s.current_redemptions < s.max_redemptions
        ]
        
        search_terms = category.lower().split()
        if product_name:
            search_terms.extend(product_name.lower().split())
            
        matched_swaps = []
        for s in available:
            s_cat = s.category.lower() if s.category else ""
            s_target = s.target_product.lower() if s.target_product else ""
            
            # Simple substring matching
            if any(term in s_cat or term in s_target for term in search_terms) or \
               any(s_cat in term or (s_target and s_target in term) for term in search_terms):
                matched_swaps.append(s)

        return sorted(
            [_swap_to_offer(s) for s in matched_swaps],
            key=lambda o: o.savings_cents,
            reverse=True,
        )"""
    return content.replace(old, new)

content = replace_homebrew()

with open("apps/backend/services/coupon_provider.py", "w") as f:
    f.write(content)
