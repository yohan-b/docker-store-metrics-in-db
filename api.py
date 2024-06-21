from flask import Flask, request
from flask_restx import Api, Resource, fields
from functools import wraps
from flask_sqlalchemy import SQLAlchemy
import json
import logging
import yaml
import os
import sys

logging.basicConfig(level=logging.WARNING)

authorizations = {
    'apikey': {
        'type': 'apiKey',
        'in': 'header',
        'name': 'X-API-KEY'
    }
}

with open('./conf.yml') as conf:
    yaml_conf = yaml.safe_load(conf)
    flask_settings = yaml_conf.get("flask_settings")
    api_key = yaml_conf.get("api_key")
    if os.environ['FLASK_ENV'] == 'development':
        flask_settings_env = yaml_conf.get("flask_settings_dev")
        logging.getLogger().setLevel(logging.DEBUG)
    elif os.environ['FLASK_ENV'] == 'production':
        flask_settings_env = yaml_conf.get("flask_settings_prod")
        logging.getLogger().setLevel(logging.WARNING)
    else:
        logging.error("FLASK_ENV must be set to development or production.")
        sys.exit(1)

def auth_required(func):
    func = api.doc(security='apikey')(func)
    @wraps(func)
    def check_auth(*args, **kwargs):
        if 'X-API-KEY' not in request.headers:
            api.abort(401, 'API key required')
        key = request.headers['X-API-KEY']
        # Check key validity
        if key != api_key:
            api.abort(401, 'Wrong API key')
        return func(*args, **kwargs)
    return check_auth

app = Flask(__name__)
app.config.from_mapping(flask_settings)
app.config.from_mapping(flask_settings_env)
db = SQLAlchemy(app)
api = Api(app, version='1.0', title='Store metrics in DB',
    description='API to record and access metrics.', authorizations=authorizations)

ns_stock = api.namespace('stock/', description='Stock API')
ns_float_metric = api.namespace('float_metric/', description='Float metric API')
ns_integer_metric = api.namespace('integer_metric/', description='Integer metric API')

class Stock(db.Model):
    __tablename__ = "Stock"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    time = db.Column(db.DateTime, index=True, nullable=False)
    price = db.Column(db.Float, nullable=False)
    volume = db.Column(db.Integer, nullable=False)
    metric = db.Column(db.String(10), index=True, nullable=False)

class Float_metric(db.Model):
    __tablename__ = "Float_metric"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    time = db.Column(db.DateTime, index=True, nullable=False)
    value = db.Column(db.Float, nullable=False)
    metric = db.Column(db.String(50), index=True, nullable=False)

class Integer_metric(db.Model):
    __tablename__ = "Integer_metric"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    time = db.Column(db.DateTime, index=True, nullable=False)
    value = db.Column(db.Integer, nullable=False)
    metric = db.Column(db.String(50), index=True, nullable=False)

Stock_resource_fields = {
    'time': fields.DateTime(dt_format='iso8601'),
    'price': fields.Float(required=True, description='price'),
    'volume': fields.Integer(required=True, description='volume'),
    'metric': fields.String(required=True, description='Stock name'),
}

Float_metric_resource_fields = {
    'time': fields.DateTime(dt_format='iso8601'),
    'value': fields.Float(required=True, description='value'),
    'metric': fields.String(required=True, description='Metric name'),
}

Integer_metric_resource_fields = {
    'time': fields.DateTime(dt_format='iso8601'),
    'value': fields.Integer(required=True, description='value'),
    'metric': fields.String(required=True, description='Metric name'),
}

Stock_model = api.model('Stock_Model', Stock_resource_fields)
Float_metric_model = api.model('Float_metric_Model', Float_metric_resource_fields)
Integer_metric_model = api.model('Integer_metric_Model', Integer_metric_resource_fields)

Stock_fields_pagination = {
    'current_page': fields.Integer(description='current page number'),
    'pages': fields.Integer(description='pages count'),
    'total_results': fields.Integer(description='results count'),
    'datas': fields.Nested(api.model('Stock_Model_resource', Stock_resource_fields))
}

Float_metric_fields_pagination = {
    'current_page': fields.Integer(description='current page number'),
    'pages': fields.Integer(description='pages count'),
    'total_results': fields.Integer(description='results count'),
    'datas': fields.Nested(api.model('Float_metric_Model_resource', Float_metric_resource_fields))
}

Integer_metric_fields_pagination = {
    'current_page': fields.Integer(description='current page number'),
    'pages': fields.Integer(description='pages count'),
    'total_results': fields.Integer(description='results count'),
    'datas': fields.Nested(api.model('Integer_metric_Model_resource', Integer_metric_resource_fields))
}


Stock_model_pagination = api.model('Stock_Model_pagination', Stock_fields_pagination)
Float_metric_model_pagination = api.model('Float_metric_Model_pagination', Float_metric_fields_pagination)
Integer_metric_model_pagination = api.model('Integer_metric_Model_pagination', Integer_metric_fields_pagination)

@ns_stock.route('/add')
class Global_stocks(Resource):
    @auth_required 
    @api.expect(Stock_model, validate=True)
    def post(self):
        try:
            data = Stock(**request.json)
            db.session.add(data)
            db.session.commit()
            return "OK", 201
        except Exception as e:
            logging.error(e)
            return "K0", 400

@ns_stock.route('/search')
class Search_stocks(Resource):
    @auth_required
    @api.marshal_with(Stock_model_pagination, envelope='resource')
    def get(self):
        logging.debug(json.loads(request.args.get("filter")))
        page = request.args.get('page', default = 1, type = int)
        filters = json.loads(request.args.get("filter", default = '*', type = str))
        record_query = Stock.query.filter()
        for stock_filter in filters:
            if 'name' in stock_filter.keys():
                if stock_filter['name'] == 'metric':
                    record_query = record_query.filter(Stock.metric == stock_filter["val"])
                if stock_filter['name'] in ['price', 'volume', 'time']:
                    if stock_filter['op'] == 'le':
                        record_query = record_query.filter(getattr(Stock, stock_filter['name']) <= stock_filter["val"])
                    if stock_filter['op'] == 'ge':
                        record_query = record_query.filter(getattr(Stock, stock_filter['name']) >= stock_filter["val"])
                    if stock_filter['op'] == 'eq':
                        record_query = record_query.filter(getattr(Stock, stock_filter['name']) == stock_filter["val"])
                
        record_query = record_query.paginate(page=page, per_page=20)
        result = dict(datas=record_query.items, 
                   total_results=record_query.total, 
                   current_page=record_query.page,
                   pages=record_query.pages)
        logging.debug(result)
        return result

@ns_float_metric.route('/add')
class Global_float_metric(Resource):
    @auth_required 
    @api.expect(Float_metric_model, validate=True)
    def post(self):
        try:
            data = Float_metric(**request.json)
            db.session.add(data)
            db.session.commit()
            return "OK", 201
        except Exception as e:
            logging.error(e)
            return "K0", 400

@ns_float_metric.route('/search')
class Search_float_metric(Resource):
    @auth_required
    @api.marshal_with(Float_metric_model_pagination, envelope='resource')
    def get(self):
        logging.debug(json.loads(request.args.get("filter")))
        page = request.args.get('page', default = 1, type = int)
        filters = json.loads(request.args.get("filter", default = '*', type = str))
        record_query = Float_metric.query.filter()
        for metric_filter in filters:
            if 'name' in metric_filter.keys():
                if metric_filter['name'] == 'metric':
                    record_query = record_query.filter(Float_metric.metric == metric_filter["val"])
                if metric_filter['name'] in ['value', 'time']:
                    if metric_filter['op'] == 'le':
                        record_query = record_query.filter(getattr(Float_metric, metric_filter['name']) <= metric_filter["val"])
                    if metric_filter['op'] == 'ge':
                        record_query = record_query.filter(getattr(Float_metric, metric_filter['name']) >= metric_filter["val"])
                    if metric_filter['op'] == 'eq':
                        record_query = record_query.filter(getattr(Float_metric, metric_filter['name']) == metric_filter["val"])
                
        record_query = record_query.paginate(page=page, per_page=20)
        result = dict(datas=record_query.items, 
                   total_results=record_query.total, 
                   current_page=record_query.page,
                   pages=record_query.pages)
        logging.debug(result)
        return result

@ns_integer_metric.route('/add')
class Global_integer_metric(Resource):
    @auth_required 
    @api.expect(Integer_metric_model, validate=True)
    def post(self):
        try:
            data = Integer_metric(**request.json)
            db.session.add(data)
            db.session.commit()
            return "OK", 201
        except Exception as e:
            logging.error(e)
            return "K0", 400

@ns_integer_metric.route('/search')
class Search_integer_metric(Resource):
    @auth_required
    @api.marshal_with(Integer_metric_model_pagination, envelope='resource')
    def get(self):
        logging.debug(json.loads(request.args.get("filter")))
        page = request.args.get('page', default = 1, type = int)
        filters = json.loads(request.args.get("filter", default = '*', type = str))
        record_query = Integer_metric.query.filter()
        for metric_filter in filters:
            if 'name' in metric_filter.keys():
                if metric_filter['name'] == 'metric':
                    record_query = record_query.filter(Integer_metric.metric == metric_filter["val"])
                if metric_filter['name'] in ['value', 'time']:
                    if metric_filter['op'] == 'le':
                        record_query = record_query.filter(getattr(Integer_metric, metric_filter['name']) <= metric_filter["val"])
                    if metric_filter['op'] == 'ge':
                        record_query = record_query.filter(getattr(Integer_metric, metric_filter['name']) >= metric_filter["val"])
                    if metric_filter['op'] == 'eq':
                        record_query = record_query.filter(getattr(Integer_metric, metric_filter['name']) == metric_filter["val"])
                
        record_query = record_query.paginate(page=page, per_page=20)
        result = dict(datas=record_query.items, 
                   total_results=record_query.total, 
                   current_page=record_query.page,
                   pages=record_query.pages)
        logging.debug(result)
        return result


api.add_namespace(ns_stock)
api.add_namespace(ns_float_metric)
api.add_namespace(ns_integer_metric)
db.create_all()

