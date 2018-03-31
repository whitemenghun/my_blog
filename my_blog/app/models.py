from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from flask import current_app, request, url_for
from datetime import datetime
from markdown import markdown
import bleach
import hashlib

from . import db, login_manager
from app.exceptions import ValidationError

# 文章与标签的关系表
article_tags = db.Table('tags',
                        db.Column(
                            'tags_id', db.Integer, db.ForeignKey('tag.id')),
                        db.Column(
                            'posts_id', db.Integer, db.ForeignKey('post.id')),
                        )


#  用户表模型
class User(db.Model, UserMixin):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(64), unique=True, index=True)
    username = db.Column(db.String(64), unique=True, index=True)
    # 密码哈希值
    password_hash = db.Column(db.String(10000))

    name = db.Column(db.String(64))
    location = db.Column(db.String(64))
    about_me = db.Column(db.Text())

    def __init__(self, **kwargs):
        super(User, self).__init__(**kwargs)

    @property
    def password(self):
        raise AttributeError('password is not a readable attribute')

    def verify_password(self, password):
        return check_password_hash(self.password_hash, password)

    @password.setter
    def password(self, password):
        self.password_hash = generate_password_hash(password)

    # 生成认证令牌
    def generate_auth_token(self, expiration):
        s = Serializer(current_app.config['SECRET_KEY'],
                       expires_in=expiration)
        return s.dumps({'id': self.id}).decode('utf-8')

    # 验证认证令牌
    @staticmethod
    def verify_auth_token(token):
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token)
        except:
            return None
        return User.query.get(data['id'])

    # 把用户转换成json格式的序列化字典
    def to_json(self):
        json_user = {
            'url': url_for('api.get_user', id=self.id),
            'username': self.username,
            'member_since': self.member_since,
            'last_seen': self.last_seen,
            'posts_url': url_for('api.get_user_posts', id=self.id),
            'followed_posts_url': url_for('api.get_user_followed_posts',
                                          id=self.id),
            'post_count': self.posts.count()
        }
        return json_user

    def __reper__(self):
        return f'<User {self.username}'


# 评论模型
class Comment(db.Model):
    __tablename__ = 'comments'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(20))
    email = db.Column(db.String(50))
    body = db.Column(db.Text)
    body_html = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    disabled = db.Column(db.Boolean)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'))
    # 回复内容
    reply = db.Column(db.String(50), default=None)

    @staticmethod
    def on_changed_body(target, value, oldvalue, initiator):
        allowed_tags = ['a', 'abbr', 'acronym', 'b', 'code', 'em', 'i',
                        'strong']
        target.body_html = bleach.linkify(bleach.clean(
            markdown(value, output_format='html'),
            tags=allowed_tags, strip=True))


# 类别模型
class Category(db.Model):
    __tablename__ = 'category'
    id = db.Column(db.Integer, primary_key=True)
    category_name = db.Column(db.String(200), unique=True)

    def __init__(self, *args, **kwargs):
        super(Category, self).__init__(*args, **kwargs)

    def __repr__(self):
        return '<category name %r>' % self.category_name


class Post(db.Model):
    __tablename__ = 'post'
    id = db.Column(db.Integer, primary_key=True)
    tittle = db.Column(db.String(200), index=True)
    body = db.Column(db.Text)
    body_html = db.Column(db.Text)
    photo = db.Column(db.String(500))
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    # 与comment表间的一对多关系
    comments = db.relationship('Comment', foreign_keys=[Comment.post_id], backref='post', lazy='dynamic')
    # 与标签的多多关系
    tags = db.relationship('Tag', secondary=article_tags,
                           backref=db.backref('post', lazy='dynamic'), lazy='dynamic')
    tags_name = db.Column(db.Text)

    # 与Category类别表间的一对多关系
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'))
    categorys = db.relationship('Category', backref=db.backref('posts', lazy='dynamic'), lazy='select')
    # 是否加精
    isstar = db.Column(db.Boolean, default=False)

    # 在POST模型中处理markdown文本
    @staticmethod
    def on_changed_body(target, value, oldvalue, initiator):
        allowed_tags = ['a', 'abbr', 'acronym', 'b', 'blockquote', 'code',
                        'em', 'i', 'li', 'ol', 'pre', 'strong', 'ul',
                        'h1', 'h2', 'h3', 'p']
        target.body_html = bleach.linkify(bleach.clean(
            markdown(value, output_format='html'),
            tags=allowed_tags, strip=True))

    # 把文章转换成json格式的序列化字典
    def to_json(self):
        json_post = {
            'url': url_for('api.get_post', id=self.id),
            'body': self.body,
            'body_html': self.body_html,
            'timestamp': self.timestamp,
            'author_url': url_for('api.get_user', id=self.author_id),
            'comments_url': url_for('api.get_post_comments', id=self.id),
            'comment_count': self.comments.count()
        }
        return json_post

    # 从json格式数据创建一篇文章
    @staticmethod
    def from_json(json_post):
        body = json_post.get('body')
        if body is None or body == '':
            raise ValidationError('post does not have a body')
        return Post(body=body)


# 注册SQLalCHEmy‘set'事件监听程序，当Post.body有新值时on-changed-body函数将被执行
db.event.listen(Post.body, 'set', Post.on_changed_body)

# 注册监听程序Comment.on_changed_body
db.event.listen(Comment.body, 'set', Comment.on_changed_body)


# 标签模型
class Tag(db.Model):
    __tablename__ = "tag"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50))
    # 与文章的多多关系
    posts = db.relationship('Post', secondary=article_tags, lazy='dynamic')

    def __init__(self, *args, **kwargs):
        super(Tag, self).__init__(*args, **kwargs)

    def __repr__(self):
        return '<tag name %r>' % self.name


class Link(db.Model):
    __tablename = 'link'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50))
    link = db.Column(db.String(200))

    def __init__(self, *args, **kwargs):
        super(Link, self).__init__(*args, **kwargs)

    def __repr__(self):
        return f'<link {name}>'


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))
