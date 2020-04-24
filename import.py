import os
import csv

from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

engine = create_engine("postgres://qrugxbfzhodefb:67970bf8ea7c2b5d9fde6f6c2d6e971a0c43b652e16abadd740d831ff1527e12@ec2-34-193-232-231.compute-1.amazonaws.com:5432/dals1ukovsebn9")
db = scoped_session(sessionmaker(bind=engine))

def main():
    f = open("books.csv")
    reader = csv.reader(f)
    next(reader, None)
    for isbn, title, author, year in reader:
        db.execute("INSERT INTO books (isbn, title, author, year) VALUES (:isbn, :title, :author, :year)",
                    {"isbn": isbn, "title": title, "author": author, "year": year})
        print(f"Added book {title} to the database")
    db.commit()
if __name__ == "__main__":
    main()