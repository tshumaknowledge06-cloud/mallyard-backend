from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.db.models.category import Category
from app.db.models.subcategory import SubCategory


def seed_categories(db: Session):
    categories_data = [
        {
            "name": "Electronics",
            "subcategories": ["Smartphones", "Laptops", "Accessories"]
        },
        {
            "name": "Services",
            "subcategories": ["Plumbing", "Electrical", "Cleaning"]
        },
        {
            "name": "Fashion",
            "subcategories": ["Men", "Women", "Kids"]
        }
    ]

    for category_data in categories_data:
        # Check if category already exists
        existing_category = db.query(Category).filter(
            Category.name == category_data["name"]
        ).first()

        if existing_category:
            category = existing_category
        else:
            category = Category(name=category_data["name"])
            db.add(category)
            db.commit()
            db.refresh(category)

        # Seed subcategories
        for sub_name in category_data["subcategories"]:
            existing_sub = db.query(SubCategory).filter(
                SubCategory.name == sub_name,
                SubCategory.category_id == category.id
            ).first()

            if not existing_sub:
                subcategory = SubCategory(
                    name=sub_name,
                    category_id=category.id
                )
                db.add(subcategory)

        db.commit()


def run_seed():
    db = SessionLocal()
    try:
        seed_categories(db)
        print("✅ Database seeding completed successfully.")
    finally:
        db.close()


if __name__ == "__main__":
    run_seed()
