import os
import csv

from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

# Check for environment variable
if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")

# Set up database
engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))

# Insert book data from books.csv into database
with open("books.csv") as file:
    data = file.read()
    for book in csv.reader(data.splitlines(), skipinitialspace=True):
        db.execute("INSERT INTO books (isbn, title, author, year) VALUES (:isbn, :title, :author, :year)",
                   {"isbn": book[0], "title": book[1], "author": book[2], "year": book[3]})
        db.commit()
