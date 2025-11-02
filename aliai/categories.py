"""
AliAI - Category Configuration
Predefined AliExpress categories for product discovery
"""

from dataclasses import dataclass
from typing import List


@dataclass
class AliExpressCategory:
    """Represents an AliExpress category"""
    category_id: str
    category_name: str
    url: str
    parent_id: str = ""
    description: str = ""


# Predefined AliExpress categories for product discovery
ALIEXPRESS_CATEGORIES: List[AliExpressCategory] = [
    # Electronics
    AliExpressCategory(
        category_id="100003070",
        category_name="Electronics",
        url="https://www.aliexpress.com/category/100003070/electronics.html",
        description="Consumer electronics, gadgets, and technology"
    ),
    
    # Electronics subcategories
    AliExpressCategory(
        category_id="5090301",
        category_name="Mobile & Accessories",
        url="https://www.aliexpress.com/category/5090301/mobile-accessories.html",
        parent_id="100003070",
        description="Phone cases, chargers, headphones, and mobile accessories"
    ),
    AliExpressCategory(
        category_id="5090302",
        category_name="Laptop & Accessories",
        url="https://www.aliexpress.com/category/5090302/laptop-accessories.html",
        parent_id="100003070",
        description="Laptops, bags, mice, keyboards, and laptop accessories"
    ),
    AliExpressCategory(
        category_id="7",
        category_name="Computer & Office",
        url="https://www.aliexpress.com/category/7/computer-office.html",
        parent_id="100003070",
        description="Desktop computers, tablets, office supplies"
    ),
    
    # Clothing
    AliExpressCategory(
        category_id="100003109",
        category_name="Apparel & Accessories",
        url="https://www.aliexpress.com/category/100003109/clothing.html",
        description="Fashion, clothing, and accessories"
    ),
    
    # Clothing subcategories
    AliExpressCategory(
        category_id="100003116",
        category_name="Women's Clothing",
        url="https://www.aliexpress.com/category/100003116/womens-clothing.html",
        parent_id="100003109",
        description="Women's fashion and clothing"
    ),
    AliExpressCategory(
        category_id="100003117",
        category_name="Men's Clothing",
        url="https://www.aliexpress.com/category/100003117/mens-clothing.html",
        parent_id="100003109",
        description="Men's fashion and clothing"
    ),
    
    # Home & Garden
    AliExpressCategory(
        category_id="15",
        category_name="Home & Garden",
        url="https://www.aliexpress.com/category/15/home-garden.html",
        description="Home improvement, furniture, and garden supplies"
    ),
    
    # Home & Garden subcategories
    AliExpressCategory(
        category_id="205950002",
        category_name="Kitchen & Dining",
        url="https://www.aliexpress.com/category/205950002/kitchen-dining.html",
        parent_id="15",
        description="Kitchen gadgets, utensils, and dining accessories"
    ),
    AliExpressCategory(
        category_id="205950003",
        category_name="Home Decor",
        url="https://www.aliexpress.com/category/205950003/home-decor.html",
        parent_id="15",
        description="Decorative items, art, and home accents"
    ),
    
    # Beauty & Health
    AliExpressCategory(
        category_id="66",
        category_name="Beauty & Health",
        url="https://www.aliexpress.com/category/66/beauty-health.html",
        description="Beauty products, cosmetics, and health supplies"
    ),
    
    # Beauty subcategories
    AliExpressCategory(
        category_id="1501",
        category_name="Makeup",
        url="https://www.aliexpress.com/category/1501/makeup.html",
        parent_id="66",
        description="Cosmetics and makeup products"
    ),
    AliExpressCategory(
        category_id="1502",
        category_name="Skincare",
        url="https://www.aliexpress.com/category/1502/skincare.html",
        parent_id="66",
        description="Skincare and beauty treatments"
    ),
    
    # Sports & Outdoors
    AliExpressCategory(
        category_id="36",
        category_name="Sports & Outdoors",
        url="https://www.aliexpress.com/category/36/sports-outdoors.html",
        description="Sports equipment, outdoor gear, and fitness"
    ),
    
    # Sports subcategories
    AliExpressCategory(
        category_id="50008163",
        category_name="Fitness & Body Building",
        url="https://www.aliexpress.com/category/50008163/fitness-body-building.html",
        parent_id="36",
        description="Fitness equipment and bodybuilding supplies"
    ),
    AliExpressCategory(
        category_id="205950006",
        category_name="Camping & Hiking",
        url="https://www.aliexpress.com/category/205950006/camping-hiking.html",
        parent_id="36",
        description="Camping gear and hiking equipment"
    ),
    
    # Toys & Hobbies
    AliExpressCategory(
        category_id="34",
        category_name="Toys & Hobbies",
        url="https://www.aliexpress.com/category/34/toys-hobbies.html",
        description="Toys, games, and hobby supplies"
    ),
    
    # Automotive
    AliExpressCategory(
        category_id="26",
        category_name="Automotive",
        url="https://www.aliexpress.com/category/26/automotive.html",
        description="Car accessories and automotive parts"
    ),
    
    # Jewelry & Accessories
    AliExpressCategory(
        category_id="1503",
        category_name="Jewelry & Accessories",
        url="https://www.aliexpress.com/category/1503/jewelry-accessories.html",
        description="Jewelry, watches, and fashion accessories"
    ),
]


def get_category_by_id(category_id: str) -> AliExpressCategory:
    """Get a category by its ID"""
    for category in ALIEXPRESS_CATEGORIES:
        if category.category_id == category_id:
            return category
    raise ValueError(f"Category ID {category_id} not found")


def get_top_level_categories() -> List[AliExpressCategory]:
    """Get only top-level categories (no parent)"""
    return [cat for cat in ALIEXPRESS_CATEGORIES if not cat.parent_id]


def get_subcategories(parent_id: str) -> List[AliExpressCategory]:
    """Get subcategories for a parent category"""
    return [cat for cat in ALIEXPRESS_CATEGORIES if cat.parent_id == parent_id]


def get_all_category_urls() -> List[str]:
    """Get all category URLs as a simple list"""
    return [cat.url for cat in ALIEXPRESS_CATEGORIES]

