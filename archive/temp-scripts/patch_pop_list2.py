import re

with open("apps/backend/routes/pop_list.py", "r") as f:
    content = f.read()

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

        # Also fetch provider swaps (brand coupons/rebates)
        provider_swaps = await provider.search_swaps(category=row.title, product_name=row.title, session=session)
        for s in provider_swaps:
            base_price = deals[0]["price"] if deals else None
            swap_price = base_price - (s.savings_cents / 100) if base_price else None
            if swap_price is not None and swap_price < 0:
                swap_price = 0.0
            
            swaps.append({
                "id": s.swap_id + 1000000 if s.swap_id else 0,  # Offset ID to avoid collision with bids if frontend needs unique key
                "title": f"{s.swap_product_name} ({s.offer_description})" if s.offer_description else s.swap_product_name,
                "price": swap_price,
                "source": f"{s.provider.capitalize()} Offer",
                "url": s.swap_product_url,
                "image_url": s.swap_product_image,
                "savings_vs_first": s.savings_cents / 100,
            })
"""

# Regex substitution
content = re.sub(r'        for b in priced_bids:.*?(?=\n        items\.append\(\{)', swap_logic, content, flags=re.DOTALL)

with open("apps/backend/routes/pop_list.py", "w") as f:
    f.write(content)
