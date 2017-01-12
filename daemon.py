import gevent.monkey

gevent.monkey.patch_all()

import config
from daemonutils.node_polling import NodeStatCollector
from daemonutils.cluster_task import TaskPoller


def run(interval, app):
    daemons = [
        TaskPoller(app, interval),
        NodeStatCollector(app, interval),
    ]
    for d in daemons:
        d.start()
    for d in daemons:
        d.join()


def front(app):
    app.register_blueprints()
    app.write_polling_targets()
    app.run(host='127.0.0.1' if app.debug else '0.0.0.0',
            port=config.SERVER_PORT)


def main():
    app = config.App(config)
    gevent.spawn(front, app).start()
    run(config.POLL_INTERVAL, app)


if __name__ == '__main__':
    main()
