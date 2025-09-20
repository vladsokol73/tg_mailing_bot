from setuptools import setup, find_packages

setup(
    name="image_bot",
    version="0.1",
    packages=find_packages(),
    install_requires=[
        "python-telegram-bot>=20.0",
        "pillow>=10.0.0",
        "pyyaml>=6.0",
        "numpy>=1.24.0",
        "python-dotenv>=1.0.0",
        "loguru>=0.7.0",
        "psycopg2-binary>=2.9.9",
        "sqlalchemy>=2.0.0",
        "alembic>=1.13.0",
        "asyncpg>=0.29.0",
        "aiohttp>=3.9.0"
    ]
)
