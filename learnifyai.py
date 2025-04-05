from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import os
import json
from openai import OpenAI
from openai._exceptions import RateLimitError
import openai



app = Flask(__name__)
app.secret_key = 'supersecretkey'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)




class API:
    @staticmethod
    def generate_course(title):
        try:
            openai.api_key = os.getenv("OPENAI_API_KEY")
            client = OpenAI(api_key=openai.api_key)

            prompt = f"""
            Сгенерируй учебный курс по теме: "{title}".
            Курс должен состоять из списка уроков. Каждый урок должен иметь:
            - номер (integer)
            - название (title)
            - краткое описание (description)
            - список ключевых понятий (keywords, list of strings)

            Ответ верни строго в формате JSON, без пояснений, без текста до или после. Пример структуры:
            [
              {{
                "number": 1,
                "title": "Введение",
                "description": "Краткое описание...",
                "keywords": ["понятие 1", "понятие 2"]
              }},
              ...
            ]
            """

            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "Ты - преподаватель, создающий учебные курсы."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7
            )

            content = response.choices[0].message.content
            course_data = json.loads(content)
            lessons_dict = {lesson["number"]: lesson for lesson in course_data}

            return {
                "title": title,
                "description": f"Курс по теме '{title}'",
                "lessons": lessons_dict
            }

        except RateLimitError:
            return {
                "title": title,
                "description": "Превышен лимит запросов к OpenAI API. Пожалуйста, попробуйте позже.",
                "lessons": {}
            }

        except Exception as e:
            return {
                "title": title,
                "description": f"Произошла ошибка при генерации курса: {str(e)}",
                "lessons": {}
            }


current_course = None


@app.route('/')
def home():
    return render_template('index.html')


@app.route('/courses')
def courses():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    if current_course:
        return render_template('course.html', course=current_course)
    return render_template('courses.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = generate_password_hash(request.form['password'])

        try:
            new_user = User(username=username, email=email, password=password)
            db.session.add(new_user)
            db.session.commit()
            session['logged_in'] = True
            session['username'] = username
            return redirect(url_for('home'))
        except:
            return 'Ошибка при регистрации'

    return render_template('register.html', show_header=False)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password):
            session['logged_in'] = True
            session['username'] = user.username
            return redirect(url_for('home'))
        return 'Неверные данные для входа'

    return render_template('login.html', show_header=False)


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))


@app.route('/generate-course', methods=['POST'])
def generate_course():
    global current_course
    title = request.form.get('course-title')
    if title:
        current_course = API.generate_course(title)
    return redirect(url_for('courses'))


@app.route('/lesson/<int:lesson_id>')
def lesson(lesson_id):
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    if current_course and lesson_id in current_course['lessons']:
        next_lesson = lesson_id + 1 if lesson_id + 1 in current_course['lessons'] else None
        return render_template('lesson.html',
                               lesson=current_course['lessons'][lesson_id],
                               course=current_course,
                               next_lesson=next_lesson)
    return redirect(url_for('courses'))


def create_templates():
    templates = {
        'base.html': '''<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}AI Learning Platform{% endblock %}</title>
    <style>
        :root {
            --primary: #6200ea;
            --secondary: #03dac6;
            --dark: #121212;
            --light: #f4f4f9;
            --gray: #e0e0e0;
        }
        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        }
        body {
            background-color: var(--light);
            color: var(--dark);
            line-height: 1.6;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 0 20px;
        }
        header {
            background: linear-gradient(135deg, var(--primary), #7c4dff);
            color: white;
            padding: 1rem 0;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        nav {
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .logo {
            font-size: 1.8rem;
            font-weight: bold;
            color: white;
            text-decoration: none;
        }
        .nav-links a {
            color: white;
            text-decoration: none;
            margin-left: 1.5rem;
            padding: 0.5rem 1rem;
            border-radius: 4px;
            transition: all 0.3s ease;
        }
        .nav-links a:hover {
            background-color: rgba(255,255,255,0.1);
        }
        main {
            min-height: calc(100vh - 120px);
            padding: 2rem 0;
        }
        footer {
            background-color: var(--dark);
            color: white;
            text-align: center;
            padding: 1rem;
        }
        .btn {
            display: inline-block;
            background-color: var(--primary);
            color: white;
            padding: 0.8rem 1.5rem;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            text-decoration: none;
            transition: all 0.3s ease;
        }
        .btn:hover {
            background-color: #7c4dff;
            transform: translateY(-2px);
        }
        .form-group {
            margin-bottom: 1.5rem;
        }
        .form-control {
            width: 100%;
            padding: 0.8rem;
            border: 1px solid var(--gray);
            border-radius: 4px;
            font-size: 1rem;
        }
        .course-content {
            background-color: white;
            border-radius: 8px;
            padding: 2rem;
            box-shadow: 0 2px 10px rgba(0,0,0,0.05);
        }
        .lesson-content {
            background-color: white;
            border-radius: 8px;
            padding: 2rem;
            box-shadow: 0 2px 10px rgba(0,0,0,0.05);
            line-height: 1.8;
        }
        .lesson-navigation {
            display: flex;
            justify-content: space-between;
            margin-top: 2rem;
        }
        .auth-form {
            max-width: 400px;
            margin: 0 auto;
            padding: 2rem;
            background-color: white;
            border-radius: 8px;
            box-shadow: 0 2px 20px rgba(0,0,0,0.05);
        }
    </style>
</head>
<body>
    {% if show_header|default(True) %}
    <header>
        <div class="container">
            <nav>
                <a href="/" class="logo">AI Learn</a>
                <div class="nav-links">
                    <a href="/">Главная</a>
                    <a href="/courses">Курсы</a>
                    {% if not session.logged_in %}
                        <a href="/register">Регистрация</a>
                        <a href="/login">Войти</a>
                    {% else %}
                        <a href="/logout">Выйти</a>
                    {% endif %}
                </div>
            </nav>
        </div>
    </header>
    {% endif %}

    <main class="container">
        {% block content %}{% endblock %}
    </main>

    <footer>
        <div class="container">
            <p>© 2025 LearnifyAI Все права защищены</p>
        </div>
    </footer>
</body>
</html>''',

        'index.html': '''{% extends "base.html" %}
{% block content %}
<section class="hero">
    <h1>Создайте свой курс обучения</h1>
    <p>Введите тему, и наша платформа сгенерирует для вас персонализированный курс</p>
</section>

<div class="course-generator">
    <form action="/generate-course" method="POST">
        <div class="form-group">
            <input type="text" name="course-title" class="form-control" placeholder="Введите тему курса" required>
        </div>
        <button type="submit" class="btn">Сгенерировать курс</button>
    </form>
</div>
{% endblock %}''',

        'courses.html': '''{% extends "base.html" %}
{% block content %}
<div class="course-content">
    <h1>Доступные курсы</h1>
    {% if current_course %}
        <div class="course-card">
            <h2>{{ current_course.title }}</h2>
            <p>{{ current_course.description }}</p>
            <a href="/lesson/1" class="btn">Начать курс</a>
        </div>
    {% else %}
        <p>Пока нет созданных курсов. Создайте курс на главной странице.</p>
    {% endif %}
</div>
{% endblock %}''',

        'course.html': '''{% extends "base.html" %}
{% block title %}{{ course.title }}{% endblock %}
{% block content %}
<div class="course-content">
    <h1>{{ course.title }}</h1>
    <p>{{ course.description }}</p>

    <div class="lessons-list">
        <h2>Уроки курса</h2>
        {% for id, lesson in course.lessons.items() %}
        <div class="lesson-item">
            <h3>{{ lesson.title }}</h3>
            <a href="/lesson/{{ id }}" class="btn">Начать урок</a>
        </div>
        {% endfor %}
    </div>
</div>
{% endblock %}''',

        'lesson.html': '''{% extends "base.html" %}
{% block title %}{{ lesson.title }}{% endblock %}
{% block content %}
<div class="lesson-content">
    <h1>{{ lesson.title }}</h1>
    <p>{{ lesson.content }}</p>

    <div class="lesson-navigation">
        <a href="/courses" class="btn">Назад к курсу</a>
        {% if next_lesson %}
        <a href="/lesson/{{ next_lesson }}" class="btn">Следующий урок</a>
        {% endif %}
    </div>
</div>
{% endblock %}''',

        'register.html': '''{% extends "base.html" %}
{% block content %}
<div class="auth-form">
    <h2>Регистрация</h2>
    <form method="POST">
        <div class="form-group">
            <input type="text" name="username" class="form-control" placeholder="Имя пользователя" required>
        </div>
        <div class="form-group">
            <input type="email" name="email" class="form-control" placeholder="Email" required>
        </div>
        <div class="form-group">
            <input type="password" name="password" class="form-control" placeholder="Пароль" required>
        </div>
        <button type="submit" class="btn">Зарегистрироваться</button>
    </form>
</div>
{% endblock %}''',

        'login.html': '''{% extends "base.html" %}
{% block content %}
<div class="auth-form">
    <h2>Вход</h2>
    <form method="POST">
        <div class="form-group">
            <input type="email" name="email" class="form-control" placeholder="Email" required>
        </div>
        <div class="form-group">
            <input type="password" name="password" class="form-control" placeholder="Пароль" required>
        </div>
        <button type="submit" class="btn">Войти</button>
    </form>
</div>
{% endblock %}'''
    }

    if not os.path.exists('templates'):
        os.makedirs('templates')

    for filename, content in templates.items():
        with open(f'templates/{filename}', 'w', encoding='utf-8') as f:
            f.write(content)


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    create_templates()
    app.run(debug=True)
