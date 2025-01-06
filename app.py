from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO, emit
from flask_sqlalchemy import SQLAlchemy
import json

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
app.config['SQLALCHEMY_BINDS'] = {
    'default': 'sqlite:///shopping_lists.db'
}
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = 'your_secret_key'
db = SQLAlchemy(app)
socketio = SocketIO(app)

# Section model to keep track of all sections
class Section(db.Model):
    __bind_key__ = 'default'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    
    def to_dict(self):
        return {'id': self.id, 'name': self.name}
    
    def __repr__(self):
        return f"<Section {self.name}>"

# Shopping item model with section reference
class ShoppingItem(db.Model):
    __bind_key__ = 'default'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    section_id = db.Column(db.Integer, db.ForeignKey('section.id', ondelete='CASCADE'), nullable=False)
    
    def __repr__(self):
        return f"<ShoppingItem {self.name}>"

# Saved item model with section reference
class SavedItem(db.Model):
    __bind_key__ = 'default'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    section_id = db.Column(db.Integer, db.ForeignKey('section.id', ondelete='CASCADE'), nullable=False)
    
    def __repr__(self):
        return f"<SavedItem {self.name}>"

# Initialize database
with app.app_context():
    db.create_all()


@app.route('/')
def index():
    # Get all sections with their items
    sections_data = []
    sections = Section.query.all()
    
    for section in sections:
        saved_items = SavedItem.query.filter_by(section_id=section.id).all()
        current_items = ShoppingItem.query.filter_by(section_id=section.id).all()
        
        sections_data.append({
            'id': section.id,
            'name': section.name,
            'saved_items': [item.name for item in saved_items],
            'current_items': [item.name for item in current_items]
        })
    
    return render_template('index.html', initial_data=sections_data)


# Create new section
@socketio.on('create_section')
def handle_create_section(data):
    section_name = data.get('name')
    if section_name:
        section = Section(name=section_name)
        db.session.add(section)
        db.session.commit()
        emit('section_created', {
            'id': section.id,
            'name': section.name
        }, broadcast=True)

# Get items for a specific section
@app.route('/section/<int:section_id>/current_list')
def get_current_list(section_id):
    items = ShoppingItem.query.filter_by(section_id=section_id).all()
    return jsonify([item.name for item in items])

@app.route('/section/<int:section_id>/saved_list')
def get_saved_list(section_id):
    items = SavedItem.query.filter_by(section_id=section_id).all()
    return jsonify([item.name for item in items])

# Handle adding items to specific section
@socketio.on('add_item')
def handle_add_item(data):
    item_name = data.get('item')
    section_id = data.get('section_id')
    if item_name and section_id:
        existing_item = ShoppingItem.query.filter_by(name=item_name, section_id=section_id).first()
        if not existing_item:
            new_item = ShoppingItem(name=item_name, section_id=section_id)
            db.session.add(new_item)
            db.session.commit()
            current_list = ShoppingItem.query.filter_by(section_id=section_id).all()
            emit('update_list', {
                'section_id': section_id,
                'items': [item.name for item in current_list]
            }, broadcast=True)

@socketio.on('add_saved_item')
def handle_add_saved_item(data):
    item_name = data.get('item')
    section_id = data.get('section_id')
    if item_name and section_id:
        existing_item = SavedItem.query.filter_by(name=item_name, section_id=section_id).first()
        if not existing_item:
            new_item = SavedItem(name=item_name, section_id=section_id)
            db.session.add(new_item)
            db.session.commit()
            saved_items = SavedItem.query.filter_by(section_id=section_id).all()
            emit('update_saved_list', {
                'section_id': section_id,
                'items': [item.name for item in saved_items]
            }, broadcast=True)

@socketio.on('remove_item')
def handle_remove_item(data):
    item_name = data.get('item')
    section_id = data.get('section_id')
    if item_name and section_id:
        item = ShoppingItem.query.filter_by(name=item_name, section_id=section_id).first()
        if item:
            db.session.delete(item)
            db.session.commit()
            current_list = ShoppingItem.query.filter_by(section_id=section_id).all()
            emit('update_list', {
                'section_id': section_id,
                'items': [item.name for item in current_list]
            }, broadcast=True)

@socketio.on('remove_saved_item')
def handle_remove_saved_item(data):
    item_name = data.get('item')
    section_id = data.get('section_id')
    if item_name and section_id:
        item = SavedItem.query.filter_by(name=item_name, section_id=section_id).first()
        if item:
            db.session.delete(item)
            db.session.commit()
            saved_items = SavedItem.query.filter_by(section_id=section_id).all()
            emit('update_saved_list', {
                'section_id': section_id,
                'items': [item.name for item in saved_items]
            }, broadcast=True)


@socketio.on('delete_section')
def handle_delete_section(data):
    section_id = data.get('section_id')
    if section_id:
        section = Section.query.get(section_id)
        if section:
            # Delete all associated items first
            ShoppingItem.query.filter_by(section_id=section_id).delete()
            SavedItem.query.filter_by(section_id=section_id).delete()
            
            # Delete the section
            db.session.delete(section)
            db.session.commit()
            
            # Notify all clients about the deletion
            emit('section_deleted', {'section_id': section_id}, broadcast=True)


@app.route('/get_all_sections')
def get_all_sections():
    sections = Section.query.all()
    sections_data = []
    
    for section in sections:
        section_data = section.to_dict()
        # Get shopping items for this section
        shopping_items = ShoppingItem.query.filter_by(section_id=section.id).all()
        saved_items = SavedItem.query.filter_by(section_id=section.id).all()
        
        section_data['shopping_items'] = [item.name for item in shopping_items]
        section_data['saved_items'] = [item.name for item in saved_items]
        
        sections_data.append(section_data)
    
    return jsonify(sections_data)

if __name__ == '__main__':
    socketio.run(app, debug=True, port=8080)