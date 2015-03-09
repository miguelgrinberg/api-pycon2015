from flask import request
from ..models import db, Class, Registration
from ..decorators import json, collection, etag
from . import api


@api.route('/classes/', methods=['GET'])
@etag
@json
@collection(Class)
def get_classes():
    return Class.query


@api.route('/classes/<int:id>', methods=['GET'])
@etag
@json
def get_class(id):
    return Class.query.get_or_404(id)


@api.route('/classes/<int:id>/registrations/', methods=['GET'])
@etag
@json
@collection(Registration)
def get_class_registrations(id):
    class_ = Class.query.get_or_404(id)
    return class_.registrations


@api.route('/classes/', methods=['POST'])
@json
def new_class():
    class_ = Class().import_data(request.get_json(force=True))
    db.session.add(class_)
    db.session.commit()
    return {}, 201, {'Location': class_.get_url()}


@api.route('/classes/<int:id>/registrations/', methods=['POST'])
@json
def new_class_registration(id):
    class_ = Class.query.get_or_404(id)
    data = request.get_json(force=True)
    data['class_url'] = class_.get_url()
    reg = Registration().import_data(data)
    db.session.add(reg)
    db.session.commit()
    return {}, 201, {'Location': reg.get_url()}


@api.route('/classes/<int:id>', methods=['PUT'])
@json
def edit_class(id):
    class_ = Class.query.get_or_404(id)
    class_.import_data(request.get_json(force=True))
    db.session.add(class_)
    db.session.commit()
    return {}


@api.route('/classes/<int:id>', methods=['DELETE'])
@json
def delete_class(id):
    class_ = Class.query.get_or_404(id)
    db.session.delete(class_)
    db.session.commit()
    return {}
