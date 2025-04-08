from setuptools import setup, find_packages

setup(
    name="parking_gateout_app",
    version="0.1",
    packages=find_packages(),
    install_requires=[
        "flask==2.3.3",
        "flask-sqlalchemy==3.1.1",
        "flask-login==0.6.2",
        "flask-limiter==3.5.0",
        "flask-cors==4.0.0",
        "psycopg2-binary==2.9.9",
        "python-dotenv==1.0.0",
        "pyjwt==2.8.0",
        "werkzeug==2.3.7"
    ],
) 