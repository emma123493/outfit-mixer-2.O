from app import db, Item

def load_sample():
    samples = [
        ("White Tee", "top", "white"),
        ("Blue Jeans", "bottom", "blue"),
        ("Black Sneakers", "shoes", "black"),
        ("Red Dress", "dress", "red"),
        ("Denim Jacket", "outer", "blue"),
        ("Gold Necklace", "accessory", "gold"),
    ]

    for name, cat, color in samples:
        item = Item(name=name, category=cat, color=color)
        db.session.add(item)
    db.session.commit()

if __name__ == '__main__':
    load_sample()
    print('Sample data loaded.')
