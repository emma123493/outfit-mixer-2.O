import os
import random
import json
from itertools import combinations
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash
from werkzeug.utils import secure_filename
from flask_sqlalchemy import SQLAlchemy

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(BASE_DIR, 'items.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = os.path.join('static', 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 4 * 1024 * 1024  # 4MB upload limit
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif'}
app.secret_key = os.environ.get('FLASK_SECRET', 'dev-secret')

db = SQLAlchemy(app)


class Item(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    color = db.Column(db.String(50), nullable=True)
    image = db.Column(db.String(300), nullable=True)

    def __repr__(self):
        return f'<Item {self.name} ({self.category})>'


class Outfit(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=True)
    items_json = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def items(self):
        try:
            return json.loads(self.items_json)
        except Exception:
            return []


def ensure_upload_folder():
    path = os.path.join(BASE_DIR, app.config['UPLOAD_FOLDER'])
    os.makedirs(path, exist_ok=True)
    return path


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']


def generate_outfits(items, max_outfits=6, size_range=(2, 3), color_mode=None):
    # items: list of Item instances
    results = []
    if not items:
        return results

    # group by category to avoid duplicates in an outfit
    for size in range(size_range[0], size_range[1] + 1):
        # all combinations of items of length size
        for combo in combinations(items, size):
            cats = {i.category for i in combo}
            if len(cats) != len(combo):
                continue

            # color-based preferences
            colors = [ (i.color or '').strip().lower() for i in combo ]
            if color_mode == 'match':
                # prefer combos where all known colors are the same
                known = [c for c in colors if c]
                if known and len(set(known)) != 1:
                    continue
            elif color_mode == 'mix':
                # prefer combos where colors are different (if known)
                known = [c for c in colors if c]
                if len(known) >= 2 and len(set(known)) != len(known):
                    continue

            results.append(combo)
            if len(results) >= max_outfits:
                return results

    # fallback: random mixes (allowing category duplicates) if too few
    while len(results) < max_outfits and len(items) >= size_range[0]:
        size = random.randint(*size_range)
        combo = tuple(random.sample(items, min(size, len(items))))
        if combo not in results:
            results.append(combo)

    return results


def get_filtered_items(category=None, color=None, query=None):
    q = Item.query
    if category:
        q = q.filter(Item.category == category)
    if color:
        like = f"%{color.strip().lower()}%"
        q = q.filter(Item.color.ilike(like))
    if query:
        like = f"%{query.strip().lower()}%"
        q = q.filter(Item.name.ilike(like))
    return q.order_by(Item.id.desc()).all()


@app.before_first_request
def init_db():
    ensure_upload_folder()
    db.create_all()


@app.route('/', methods=['GET'])
def index():
    items = Item.query.order_by(Item.id.desc()).all()
    outfits = []
    saved = Outfit.query.order_by(Outfit.created_at.desc()).all()
    return render_template('index.html', items=items, outfits=outfits, saved_outfits=saved, all_items=items)


@app.route('/add', methods=['POST'])
def add_item():
    name = request.form.get('name', '').strip()
    category = request.form.get('category', '').strip()
    color = request.form.get('color', '').strip() or None

    if not name or not category:
        return redirect(url_for('index'))

    image_file = request.files.get('image')
    filename = None
    if image_file and image_file.filename:
        if not allowed_file(image_file.filename):
            flash('Invalid image type; allowed: png,jpg,jpeg,gif')
        else:
            filename = secure_filename(image_file.filename)
            save_path = os.path.join(ensure_upload_folder(), filename)
            image_file.save(save_path)

    item = Item(name=name, category=category, color=color or None, image=filename)
    db.session.add(item)
    db.session.commit()
    return redirect(url_for('index'))


@app.route('/generate', methods=['POST'])
def generate():
    # support filters when generating
    category = request.form.get('filter_category') or None
    color = request.form.get('filter_color') or None
    query = request.form.get('filter_query') or None
    items = get_filtered_items(category=category, color=color, query=query)
    color_mode = request.form.get('color_mode')
    outfits = generate_outfits(items, max_outfits=8, size_range=(2, 3), color_mode=color_mode)
    saved = Outfit.query.order_by(Outfit.created_at.desc()).all()
    all_items = Item.query.order_by(Item.id.desc()).all()
    return render_template('index.html', items=items, outfits=outfits, saved_outfits=saved, all_items=all_items)


@app.route('/export', methods=['POST'])
def export_outfits():
    items = Item.query.all()
    color_mode = request.form.get('color_mode')
    outfits = generate_outfits(items, max_outfits=50, size_range=(2, 3), color_mode=color_mode)

    data = []
    for outfit in outfits:
        data.append([{"name": i.name, "category": i.category, "color": i.color} for i in outfit])

    from flask import jsonify
    return jsonify({"outfits": data})


@app.route('/delete/<int:item_id>', methods=['POST'])
def delete_item(item_id):
    item = Item.query.get_or_404(item_id)
    # remove file
    if item.image:
        try:
            os.remove(os.path.join(ensure_upload_folder(), item.image))
        except Exception:
            pass
    db.session.delete(item)
    db.session.commit()
    flash('Item deleted')
    return redirect(url_for('index'))


@app.route('/edit/<int:item_id>', methods=['GET', 'POST'])
def edit_item(item_id):
    item = Item.query.get_or_404(item_id)
    if request.method == 'POST':
        item.name = request.form.get('name', item.name)
        item.category = request.form.get('category', item.category)
        color = request.form.get('color')
        item.color = color or None
        image_file = request.files.get('image')
        if image_file and image_file.filename and allowed_file(image_file.filename):
            filename = secure_filename(image_file.filename)
            image_file.save(os.path.join(ensure_upload_folder(), filename))
            # remove old
            if item.image:
                try:
                    os.remove(os.path.join(ensure_upload_folder(), item.image))
                except Exception:
                    pass
            item.image = filename
        db.session.commit()
        flash('Item updated')
        return redirect(url_for('index'))
    return render_template('edit_item.html', item=item)


@app.route('/save_outfit', methods=['POST'])
def save_outfit():
    ids = request.form.getlist('item_id')
    name = request.form.get('outfit_name') or None
    if not ids:
        flash('No items to save')
        return redirect(url_for('index'))
    outfit = Outfit(name=name, items_json=json.dumps(ids))
    db.session.add(outfit)
    db.session.commit()
    flash('Outfit saved')
    return redirect(url_for('index'))


@app.route('/delete_outfit/<int:outfit_id>', methods=['POST'])
def delete_outfit(outfit_id):
    o = Outfit.query.get_or_404(outfit_id)
    db.session.delete(o)
    db.session.commit()
    flash('Saved outfit deleted')
    return redirect(url_for('index'))


@app.route('/clear', methods=['POST'])
def clear():
    # remove all items (for quick reset)
    Item.query.delete()
    db.session.commit()
    # remove uploaded files
    folder = ensure_upload_folder()
    for fname in os.listdir(folder):
        path = os.path.join(folder, fname)
        try:
            if os.path.isfile(path):
                os.remove(path)
        except Exception:
            pass
    return redirect(url_for('index'))


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
