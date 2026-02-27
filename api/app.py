from flask import Flask, jsonify, request
from dotenv import load_dotenv
from flask_cors import CORS

load_dotenv()

from config import Config
from models import db

from import_recipes import get_all_recipes, populate_db
from models.association import recipe_category
from models.category import Category
from models.ingredient import Ingredient
from models.recipe import Recipe

ERROR404_RESPONSE = {'error': 'recipe not found'}

app = Flask(__name__)
app.config.from_object(Config)
db.init_app(app)

CORS(app, origins=[Config.APP_URL or '*'])


def add_ingredients_to_db(ingredients, recipe_id):
    for ing in ingredients:
        try:
            quantity = float(ing['quantity'])
        except ValueError as exc:
            return jsonify({'error': f'quantity is not of type float: {exc}'}), 400

        ingredient = Ingredient(
            name=ing['name'],
            quantity=quantity,
            unit=ing['unit'],
            recipe_id=recipe_id,
        )
        db.session.add(ingredient)


@app.route('/')
def hello_world():
    return 'Welcome to my snack app!'


# Retrieve all recipes
@app.route('/api/recipes', methods=['GET'])
def get_recipes():
    recipes = []
    for recipe in Recipe.query.all():
        recipes.append(recipe.as_dict())
    return jsonify(recipes)


# Retrieve a specific recipe by ID
@app.route('/api/recipes/<int:recipe_id>', methods=['GET'])
def get_recipe(recipe_id):
    recipe = Recipe.query.get(recipe_id)
    if recipe:
        return jsonify(recipe.as_dict())
    else:
        return jsonify(ERROR404_RESPONSE), 404


# Create a new recipe
@app.route('/api/recipes', methods=['POST'])
def create_recipe():
    request_body = {
        'name': request.json.get('name'),
        'duration': request.json.get('duration'),
        'pictures': request.json.get('pictures'),
        'instructions': request.json.get('instructions'),
        'categories': request.json.get('categories'),
        'ingredients': request.json.get('ingredients'),
    }
    for key, value in request_body.items():
        if not value:
            return jsonify({'error': f'{key} is required'}), 400
    for cat in request_body['categories']:
        if 'name' not in cat:
            return jsonify({'error': 'categories must contain a name'}), 400
    for ing in request_body['ingredients']:
        if 'name' not in ing or 'quantity' not in ing:
            return jsonify({'error': 'ingredients must contain a name, quantity and unit (optional)'}), 400

    try:
        category_objs = []
        for cat in request_body['categories']:
            # Check if the category exists
            category = Category.query.filter_by(name=cat['name']).first()
            if not category:
                return jsonify({'error': f'category {cat["name"]} not found'}), 400
            category_objs.append(category)

        # Create a recipe object
        recipe = Recipe(
            name=request_body['name'],
            duration=request_body['duration'],
            pictures=request_body['pictures'],
            instructions=request_body['instructions'],
            categories=category_objs,
        )
        db.session.add(recipe)
        db.session.flush()  # Ensure recipe.id is available

        # Add ingredients
        add_ingredients_to_db(request_body['ingredients'], recipe.id)

        db.session.commit()
        print(f'Inserted recipe: {recipe.name}')
        return jsonify(recipe.as_dict()), 201
    except Exception as exc:
        db.session.rollback()
        return jsonify({'error': f'something went wrong: {exc}'}), 500


# Update an existing recipe
@app.route('/api/recipes/<int:recipe_id>', methods=['PUT'])
def edit_recipe(recipe_id):
    try:
        # Get the specific recipe
        recipe = Recipe.query.get(recipe_id)
        if not recipe:
            return jsonify(ERROR404_RESPONSE), 404

        # Update recipe's fields
        recipe.name = new_name if (new_name := request.json.get('name')) else recipe.name
        recipe.duration = new_duration if (new_duration := request.json.get('duration')) else recipe.duration
        recipe.pictures = new_pictures if (new_pictures := request.json.get('pictures')) else recipe.pictures
        recipe.instructions = new_instr if (new_instr := request.json.get('instructions')) else recipe.instructions

        # Update recipe's categories
        if new_categories := request.json.get('categories'):
            category_objs = []
            for cat in new_categories:
                # Check if the category exists
                category = Category.query.filter_by(name=cat['name']).first()
                if not category:
                    return jsonify({'error': f'category {cat["name"]} not found'}), 400
                category_objs.append(category)
            recipe.categories = category_objs

        # Update recipe's ingredients
        if new_ingredients := request.json.get('ingredients'):
            # Delete all the recipe's old ingredients
            Ingredient.query.filter_by(recipe_id=recipe_id).delete()
            # Add new ingredients
            add_ingredients_to_db(new_ingredients, recipe.id)

        db.session.commit()
        print(f'Updated recipe: {recipe.name}')
        return jsonify(recipe.as_dict()), 201
    except Exception as exc:
        db.session.rollback()
        return jsonify({'error': f'something went wrong: {exc}'}), 500


# Delete a recipe
@app.route('/api/recipes/<int:recipe_id>', methods=['DELETE'])
def delete_recipe(recipe_id):
    try:
        recipe = Recipe.query.filter_by(id=recipe_id)
        # Check if the recipe exists
        if recipe.first():
            # Delete all the recipe's ingredients
            Ingredient.query.filter_by(recipe_id=recipe_id).delete()
            # Delete all the associations between the recipe and its categories
            db.session.query(recipe_category).filter_by(recipe_id=recipe_id).delete()
            # Delete the recipe itself
            recipe.delete()
            db.session.commit()
            return '', 204
        else:
            return jsonify(ERROR404_RESPONSE), 404
    except Exception as exc:
        db.session.rollback()
        return jsonify({'error': f'something went wrong: {exc}'}), 500


@app.route('/api/categories', methods=['GET'])
def get_categories():
    categories = []
    for category in Category.query.all():
        categories.append(category.as_dict())
    return jsonify(categories)


@app.route('/api/categories', methods=['POST'])
def create_category():
    if not (category_name := request.json.get('name')):
        return jsonify({'error': 'categories must contain a name'}), 400
    color = category_color if (category_color := request.json.get('color')) else '#848482'

    try:
        # Check if the category exists
        if Category.query.filter_by(name=category_name).first():
            return jsonify({'error': f'category {category_name} already exists'}), 400
        # Create a category object
        category = Category(
            name=category_name,
            # Default to gray in hex if color is not provided in the request body
            color=color,
        )
        db.session.add(category)
        db.session.commit()
        print(f'Inserted category: {category.name}')
        return jsonify(category.as_dict()), 201
    except Exception as exc:
        db.session.rollback()
        return jsonify({'error': f'something went wrong: {exc}'}), 500


if __name__ == '__main__':
    # with app.app_context():
    #     db.drop_all()
    #     db.create_all()

    # Use the following line if you want to populate the database with sample data
    # populate_db(get_all_recipes(), app, db)

    # app.run(host="0.0.0.0")
    app.run(debug=True)
