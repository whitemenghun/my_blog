import os
from flask_migrate import Migrate, MigrateCommand
from flask_script import Manager, Shell

from app import create_app, db
from app.models import User, Post, Tag, Comment, Category, Link

app = create_app('production')
manager = Manager(app)
migrate = Migrate(app, db)

# 覆盖检测
COV = None
if os.environ.get('FLASK_COVERAGE'):
    import coverage

    COV = coverage.coverage(branch=True, include='app/*')
    COV.start()


def make_shell_context():
    return dict(app=app, db=db, User=User, Category=Category, Post=Post, Tag=Tag, Comment=Comment, Link=Link)


manager.add_command("shell", Shell(make_context=make_shell_context))
manager.add_command('db', MigrateCommand)


@manager.command
def test(coverage=False):
    """启动单元测试"""
    if coverage and os.environ.get('FLASK_COVERAGE'):
        import sys
        os.environ['FLASK_COVERAGE'] = '1'
        os.execvp(sys.executable, [sys.executable] + sys.argv)
    import unittest
    tests = unittest.TestLoader().discover('tests')
    unittest.TextTestRunner(verbosity=2).run(tests)
    if COV:
        COV.stop()
        COV.save()
        print('覆盖报告:')
        basedir = os.path.abspath(os.path.dirname(__file__))
        covdir = os.path.join(basedir, 'tmp/coverage')
        COV.html_report(directory=covdir)
        print('HTML version:file://{}/index.html'.format(covdir))
        COV.erase()


@app.template_filter('sub')
def sub(filename):
    if filename:
        return filename[10:]
    return filename


if __name__ == '__main__':
    # manager.run()
    app.run()
