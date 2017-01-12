import os
import logging
from flask import Flask, g, request, render_template
from werkzeug.utils import import_string

import file_ipc
import render_utils
from models.base import init_db
from thirdparty.alarm import Base as AlarmBase
from thirdparty import containerize

blueprints = (
    'index',
    'pollings',
    'alarm',
    'redis',
    'cluster',
    'command',
    'task',
    'audit',
    'prune',
    'myself',
    'translation',
)


def import_bp_string(module_name):
    import_name = '%s.bps.%s:bp' % (__package__, module_name)
    return import_string(import_name)


def init_logging(config):
    args = {'level': config.LOG_LEVEL}
    if config.LOG_FILE:
        args['filename'] = config.LOG_FILE
    args['format'] = config.LOG_FORMAT
    logging.basicConfig(**args)


class RedisCtl(Flask):
    def __init__(self, config):
        Flask.__init__(self, 'RedisCtl', static_url_path='/static')

        self.jinja_env.globals['render'] = render_template
        self.jinja_env.globals['render_user'] = self.render_user_by_id
        self.jinja_env.globals['render_me'] = self.render_me
        self.jinja_env.globals['user_valid'] = self.access_ctl_user_valid
        self.jinja_env.globals['login_url'] = self.login_url

        self.jinja_env.globals['stats_enabled'] = self.stats_enabled
        self.jinja_env.globals['alarm_enabled'] = self.alarm_enabled
        self.jinja_env.globals['container_enabled'] = self.container_enabled
        self.jinja_env.globals['body_classes'] = self.body_classes

        for u in dir(render_utils):
            if u.startswith('g_'):
                self.jinja_env.globals[u[2:]] = getattr(render_utils, u)
            elif u.startswith('f_'):
                self.jinja_env.filters[u[2:]] = getattr(render_utils, u)

        init_logging(config)
        self.config['SQLALCHEMY_DATABASE_URI'] = self.db_uri(config)
        self.config_node_max_mem = config.NODE_MAX_MEM
        self.debug = config.DEBUG == 1

        logging.info('Use database %s', self.config['SQLALCHEMY_DATABASE_URI'])
        init_db(self)
        self.stats_client = self.init_stats_client(config)
        self.alarm_client = self.init_alarm_client(config)
        self.container_client = self.init_container_client(config)
        logging.info('Stats enabled: %s', self.stats_enabled())
        logging.info('Alarm enabled: %s', self.alarm_enabled())
        logging.info('Containerizing enabled: %s', self.container_enabled())

        self.polling_file = file_ipc.POLL_FILE
        self.instance_detail_file = file_ipc.INSTANCE_FILE
        logging.info('Polling file: %s', self.polling_file)
        logging.info('Instance detail file: %s', self.instance_detail_file)

    @staticmethod
    def db_uri(config):
        return 'mysql+pymysql://%s:%s@%s:%d/%s?charset=%s' % (
            config.MYSQL_USERNAME, config.MYSQL_PASSWORD,
            config.MYSQL_HOST, config.MYSQL_PORT, config.MYSQL_DATABASE, config.MYSQL_CHARSET)

    def register_blueprints(self):
        self.secret_key = os.urandom(24)
        self.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

        for bp in blueprints:
            self.register_blueprint(import_bp_string(bp))
        if self.stats_enabled():
            self.register_blueprint(import_bp_string('statistics'))
        if self.container_enabled():
            self.register_blueprint(import_bp_string('containerize'))
            self.register_blueprint(import_bp_string('cont_image'))

        for bp in self.ext_blueprints():
            self.register_blueprint(bp)

        @self.before_request
        def init_global_vars():
            g.page = request.args.get('page', type=int, default=0)
            g.start = request.args.get('start', type=int, default=g.page * 20)
            g.limit = request.args.get('limit', type=int, default=20)
            g.user = self.get_user()
            g.lang = self.language()
            g.display_login_entry = self.display_login_entry()
            g.container_client = self.container_client

    def get_user(self):
        return None

    def get_user_id(self):
        return None if g.user is None else g.user.id

    def default_user_id(self):
        return None

    def access_ctl_user_valid(self):
        return True

    def access_ctl_user_adv(self):
        return True

    def login_url(self):
        return '#'

    def render_user_by_id(self, user_id):
        return '<span data-localize="nobody">-</span>'

    def render_me(self):
        return ''

    def display_login_entry(self):
        return not self.access_ctl_user_valid()

    def language(self):
        lang = request.headers.get('Accept-Language')
        if lang is None:
            return None
        try:
            return lang.split(';')[0].split('-')[0]
        except LookupError:
            return None

    def ext_blueprints(self):
        return []

    def polling_result(self):
        return file_ipc.read_details()

    def polling_targets(self):
        return file_ipc.read_poll()

    def write_polling_details(self, redis_details, proxy_details):
        file_ipc.write_details(redis_details, proxy_details)

    def write_polling_targets(self):
        file_ipc.write_nodes_proxies_from_db()

    def on_loop_begin(self):
        if self.alarm_client is not None:
            self.alarm_client.on_loop_begin()

    def init_stats_client(self, config):
        if config.OPEN_FALCON and config.OPEN_FALCON['db']:
            from thirdparty.openfalcon import Client
            return Client(**config.OPEN_FALCON)
        return None

    def stats_enabled(self):
        return self.stats_client is not None

    def stats_query(self, addr, fields, span, now, interval):
        if self.stats_client is None:
            return []
        return self.do_stats_query(addr, fields, span, now, interval)

    def stats_write(self, addr, points):
        if self.stats_client is not None:
            self.do_stats_write(addr, points)

    def do_stats_query(self, addr, fields, span, now, interval):
        return self.stats_client.query(addr, fields, span, now, interval)

    def do_stats_write(self, addr, points):
        self.stats_client.write_points(addr, points)

    def init_alarm_client(self, config):
        if config.ALARM is not None and isinstance(config.ALARM, AlarmBase):
            return config.ALARM
        return None

    def alarm_enabled(self):
        return self.alarm_client is not None

    def send_alarm(self, endpoint, message, exception):
        if self.alarm_client is not None:
            self.do_send_alarm(endpoint, message, exception)

    def do_send_alarm(self, endpoint, message, exception):
        self.alarm_client.send_alarm(endpoint, message, exception)

    def init_container_client(self, config):
        if config.CONTAINER is not None and isinstance(config.CONTAINER, containerize.Base):
            return config.CONTAINER
        return None

    def container_enabled(self):
        return self.container_client is not None

    def body_classes(self):
        c = []
        if not self.stats_enabled():
            c.append('no-stats-mode')
        if not self.alarm_enabled():
            c.append('no-alarm-mode')
        if not self.container_enabled():
            c.append('no-container-mode')
        if not self.access_ctl_user_adv():
            c.append('no-adv-user-mode')
        return c
