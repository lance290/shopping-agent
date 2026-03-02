import re

with open("apps/backend/routes/pop_helpers.py", "r") as f:
    content = f.read()

import_statement = "from services.coupon_provider import get_coupon_provider\n"
if "get_coupon_provider" not in content:
    content = content.replace("from models.bids import Bid\n", "from models.bids import Bid\n" + import_statement)

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

with open("apps/backend/routes/pop_helpers.py", "w") as f:
    f.write(content)
