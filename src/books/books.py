from flask import Blueprint, jsonify, request
from app import mongo
from flask_pymongo import ObjectId
from schemas.books import validate_book
from flask_jwt_extended import jwt_required, get_jwt_identity
from utils.decorators import user_access_required
from utils.users import get_user_id, get_username, validate_admin
from utils.books import validate_author, validate_category

books_blueprint = Blueprint('books', __name__)


@books_blueprint.route('/books', methods=['POST'])
@jwt_required()
@user_access_required('create', 'not_created', pass_user_id=True)
def createBook(user_id):
    if not validate_admin(user_id):
        return jsonify({'msg': 'You are not administrator',
                        'status': {
                            'name': 'not_authorized',
                            'action': 'delete',
                            'delete': False
                        }
                        }), 401
    
    book = request.json.get('book')
    if not book:
        return jsonify({'msg': 'No book provided',
                        'status': {
                            'name': 'not_created',
                            'action': 'create',
                            'create': False
                        }
                        }), 400

    if not validate_book(book):
        return jsonify({'msg': 'Invalid book',
                        'status': {
                            'name': 'not_created',
                            'action': 'create',
                            'create': False
                        }
                        }), 400

    id = mongo.db.books.insert_one({
        'name': book.get('name'),
        'description': book.get('description'),
        'author': book.get('author'),
        'categories': book.get('categories')
    })

    author = mongo.db.authors.find_one_and_update(
        {'author': book.get('author')},
        {'$addToSet': {'books': id.inserted_id}},
        upsert=True,
        return_document=True
    )

    mongo.db.books.update_one(
        {'_id': id.inserted_id},
        {'$set': {'author_id': author['_id']}}
    )

    return jsonify({'msg': 'Book created',
                    'status': {
                        'name': 'created',
                        'action': 'create',
                        'create': True
                    },
                    'data': {
                        'id': str(id.inserted_id),
                    }
                    })


@books_blueprint.route('/books', methods=['GET'])
def getBooks(): 
    Filter = request.args.get('filter')
    if not Filter:
        books = mongo.db.books.find({})
    else:
        if Filter.startswith('@'):
            Filter = Filter.replace('@', '')
            if not validate_author(Filter):
                return jsonify({'msg': f'invalid author "{Filter}"',
                                'status': {
                                    'name': 'bad_request',
                                    'action': 'get',
                                    'get': False
                                }
                                }), 400
            author_id = mongo.db.authors.find_one({'author': Filter}).get('_id')
            books = mongo.db.books.find({'author_id': author_id})
        elif Filter.startswith('¿'):
            category = Filter[1:]
            if not validate_category(category):
                return jsonify({'msg': f'invalid category "{category}"',
                                'status': {
                                    'name': 'bad_request',
                                    'action': 'get',
                                    'get': False
                                }
                                }), 400
            books = mongo.db.books.find(
                {'categories': {'$elemMatch': {'$eq': category}}})

    books = list(books)
    return jsonify({
        'msg': 'Books retrieved',
        'status': {
            'name': 'retrieved',
            'action': 'get',
            'get': True
        },
        'data': list(map(lambda book: {
            'id': str(book.get('_id')),
            'name': book.get('name'),
            'description': book.get('description'),
            'author': book.get('author'),
            'categories': book.get('categories')
        }, books))
    })