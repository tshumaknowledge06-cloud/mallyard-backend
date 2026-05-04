from sqlalchemy import func
from difflib import get_close_matches
from app.db.models.city import City


def normalize_city_name(name: str) -> str:
    name = name.strip().lower()
    noise_words = ["city", "town", "municipality"]

    for word in noise_words:
        name = name.replace(word, "")

    return name.strip()


def resolve_city(db, city_name: str):
    if not city_name:
        return None

    normalized = normalize_city_name(city_name)

    # 1️⃣ EXACT MATCH
    city = db.query(City).filter(
        func.lower(City.name) == normalized
    ).first()
    if city:
        return city.id

    # 2️⃣ PARTIAL MATCH
    city = db.query(City).filter(
        func.lower(City.name).like(f"%{normalized}%")
    ).first()
    if city:
        return city.id

    # 3️⃣ FUZZY MATCH
    all_cities = db.query(City).all()
    city_names = [c.name.lower() for c in all_cities]

    matches = get_close_matches(normalized, city_names, n=1, cutoff=0.7)

    if matches:
        matched_name = matches[0]
        matched_city = next(c for c in all_cities if c.name.lower() == matched_name)
        return matched_city.id

    return None