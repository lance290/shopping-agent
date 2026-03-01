import re
import os

def patch_coupon_provider():
    path = "apps/backend/services/coupon_provider.py"
    with open(path, "r") as f:
        content = f.read()

    # ManualProvider
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
        search_terms = category.lower().split()
        if product_name:
            search_terms.extend(product_name.lower().split())

        for s in swaps:
            s_cat = s.category.lower() if s.category else ""
            s_target = s.target_product.lower() if s.target_product else ""
            
            # Simple substring matching: does the swap category appear in the search query, or vice-versa?
            if s_cat in category.lower() or category.lower() in s_cat:
                matched_swaps.append(s)
            elif s_target and (s_target in category.lower() or category.lower() in s_target):
                matched_swaps.append(s)
            elif product_name and (s_cat in product_name.lower() or s_target and s_target in product_name.lower()):
                matched_swaps.append(s)
            elif any(term in s_cat or term in s_target for term in search_terms if len(term) > 3):
                matched_swaps.append(s)

        # Deduplicate
        matched_swaps = list({s.id: s for s in matched_swaps}.values())

        return sorted(
            [_swap_to_offer(s) for s in matched_swaps],
            key=lambda o: o.savings_cents,
            reverse=True,
        )"""
    content = content.replace(old_manual, new_manual)

    # HomeBrewProvider
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
        search_terms = category.lower().split()
        if product_name:
            search_terms.extend(product_name.lower().split())

        for s in available:
            s_cat = s.category.lower() if s.category else ""
            s_target = s.target_product.lower() if s.target_product else ""
            
            if s_cat in category.lower() or category.lower() in s_cat:
                matched_swaps.append(s)
            elif s_target and (s_target in category.lower() or category.lower() in s_target):
                matched_swaps.append(s)
            elif product_name and (s_cat in product_name.lower() or s_target and s_target in product_name.lower()):
                matched_swaps.append(s)
            elif any(term in s_cat or term in s_target for term in search_terms if len(term) > 3):
                matched_swaps.append(s)

        matched_swaps = list({s.id: s for s in matched_swaps}.values())

        return sorted(
            [_swap_to_offer(s) for s in matched_swaps],
            key=lambda o: o.savings_cents,
            reverse=True,
        )"""
    content = content.replace(old_homebrew, new_homebrew)

    with open(path, "w") as f:
        f.write(content)

def patch_pop_list():
    path = "apps/backend/routes/pop_list.py"
    with open(path, "r") as f:
        content = f.read()

    if "from services.coupon_provider import get_coupon_provider" not in content:
        content = content.replace("from models.rows import ProjectMember\n", "from models.rows import ProjectMember\nfrom services.coupon_provider import get_coupon_provider\n")

    if "provider = get_coupon_provider()" not in content:
        content = content.replace("    items = []\n    for row in rows:", "    provider = get_coupon_provider()\n    items = []\n    for row in rows:")

    swap_logic = """        for b in priced_bids:
            deal = {
                "id": b.id,
                "title": b.item_title,
                "price": b.price,
                "source": b.source,
                "url": b.canonical_url,
                "image_url": b.image_url,
            }
            deals.append(deal)
            if lowest_price is None or b.price < lowest_price:
                lowest_price = b.price
            if b.is_swap:
                swaps.append({
                    "id": b.id,
                    "title": b.item_title,
                    "price": b.price,
                    "source": b.source,
                    "url": b.canonical_url,
                    "image_url": b.image_url,
                    "savings_vs_first": round(deals[0]["price"] - b.price, 2) if deals and b.price < deals[0]["price"] else None,
                })

        # Fetch provider swaps (brand coupons/rebates)
        provider_swaps = await provider.search_swaps(category=row.title, product_name=row.title, session=session)
        for s in provider_swaps:
            base_price = deals[0]["price"] if deals else None
            swap_price = base_price - (s.savings_cents / 100) if base_price else None
            if swap_price is not None and swap_price < 0:
                swap_price = 0.0
            
            swaps.append({
                "id": s.swap_id + 1000000 if s.swap_id else 0,
                "title": f"{s.swap_product_name} ({s.offer_description})" if s.offer_description else s.swap_product_name,
                "price": swap_price,
                "source": f"{s.provider.capitalize()} Offer",
                "url": s.swap_product_url,
                "image_url": s.swap_product_image,
                "savings_vs_first": s.savings_cents / 100,
            })
"""
    content = re.sub(r'        for b in priced_bids:.*?(?=\n        items\.append\(\{)', swap_logic, content, flags=re.DOTALL)

    with open(path, "w") as f:
        f.write(content)

def patch_pop_helpers():
    path = "apps/backend/routes/pop_helpers.py"
    with open(path, "r") as f:
        content = f.read()

    if "from services.coupon_provider import get_coupon_provider" not in content:
        content = content.replace("from models.bids import Bid\n", "from models.bids import Bid\nfrom services.coupon_provider import get_coupon_provider\n")

    swap_logic = """    deals = []
    swaps = []
    lowest_price = None
    priced_bids = [b for b in bids if b.price is not None]

    for b in priced_bids:
        deal = {
            "id": b.id,
            "title": b.item_title,
            "price": b.price,
            "source": b.source,
            "url": b.canonical_url,
            "image_url": b.image_url,
            "is_selected": b.is_selected or False,
        }
        deals.append(deal)
        if lowest_price is None or b.price < lowest_price:
            lowest_price = b.price
        if b.is_swap:
            swaps.append({
                "id": b.id,
                "title": b.item_title,
                "price": b.price,
                "source": b.source,
                "url": b.canonical_url,
                "image_url": b.image_url,
                "savings_vs_first": round(deals[0]["price"] - b.price, 2) if deals and b.price < deals[0]["price"] else None,
            })

    provider = get_coupon_provider()
    provider_swaps = await provider.search_swaps(category=row.title, product_name=row.title, session=session)
    for s in provider_swaps:
        base_price = deals[0]["price"] if deals else None
        swap_price = base_price - (s.savings_cents / 100) if base_price else None
        if swap_price is not None and swap_price < 0:
            swap_price = 0.0
        
        swaps.append({
            "id": s.swap_id + 1000000 if s.swap_id else 0,
            "title": f"{s.swap_product_name} ({s.offer_description})" if s.offer_description else s.swap_product_name,
            "price": swap_price,
            "source": f"{s.provider.capitalize()} Offer",
            "url": s.swap_product_url,
            "image_url": s.swap_product_image,
            "savings_vs_first": s.savings_cents / 100,
        })

    return {
        "id": row.id,
        "title": row.title,
        "status": row.status,
        "deals": deals,
        "swaps": swaps[:3],
        "lowest_price": lowest_price,
        "deal_count": len(deals),
    }"""
    content = re.sub(r'    deals = \[\]\n.*?deal_count": len\(deals\),\n    \}', swap_logic, content, flags=re.DOTALL)

    with open(path, "w") as f:
        f.write(content)


patch_coupon_provider()
patch_pop_list()
patch_pop_helpers()
print("Patched successfully")
